import streamlit as st
import pandas as pd
import os
import re
import plotly.express as px

from config.captains import CAPTAIN_CONFIG


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Fantasy T20 Dashboard",
    page_icon="🏏",
    layout="wide"
)

# --------------------------------------------------
# LOAD CSS
# --------------------------------------------------
CSS_PATH = "style/style.css"
if os.path.exists(CSS_PATH):
    with open(CSS_PATH) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
DATA_PATH = "data/points_new.csv"
if not os.path.exists(DATA_PATH):
    st.error("CSV not found at data/points_new.csv")
    st.stop()

df = pd.read_csv(DATA_PATH)

# normalize column names
df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.lower()
    .str.replace(" ", "", regex=False)
)

# --------------------------------------------------
# DETECT DAY COLUMNS
# --------------------------------------------------
day_cols = [c for c in df.columns if re.fullmatch(r"day\d+", c)]
if not day_cols:
    st.error("No day columns found (expected day1, day2, ...)")
    st.stop()

day_cols.sort(key=lambda x: int(x.replace("day", "")))
day_numbers = [int(c.replace("day", "")) for c in day_cols]

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.markdown("## 🏏 Fantasy T20 Tracker")
st.sidebar.markdown("Premium League Dashboard")

st.sidebar.markdown("---")
selected_day = st.sidebar.selectbox(
    "Show rankings up to day",
    day_numbers,
    index=len(day_numbers) - 1
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Scoring Rules")
st.sidebar.write("Captain = 2×")
st.sidebar.write("Vice Captain = 1.5×")

tab1, tab2 = st.tabs(["🏆 Dashboard", "👥 Player Breakdown"])


def get_team_points_for_day(day: int) -> pd.DataFrame:
    temp = calculate_points(day)
    return (
        temp
        .groupby("owner_name")["player_points"]
        .sum()
        .reset_index()
        .rename(columns={
            "owner_name": "Owner",
            "player_points": "Points"
        })
    )

# --------------------------------------------------
# POINT CALCULATION
# --------------------------------------------------
def calculate_points(upto_day: int) -> pd.DataFrame:
    temp = df.copy()
    temp["player_points"] = 0.0

    for d in range(1, upto_day + 1):
        day_col = f"day{d}"
        c_col = f"c_day{d}"
        vc_col = f"vc_day{d}"

        if day_col not in temp.columns:
            continue

        points = pd.to_numeric(
            temp[day_col], errors="coerce"
        ).fillna(0)

        multiplier = pd.Series(1.0, index=temp.index)

        if c_col in temp.columns:
            multiplier[temp[c_col] == 1] = 2.0
        if vc_col in temp.columns:
            multiplier[temp[vc_col] == 1] = 1.5

        temp["player_points"] += points * multiplier

    return temp

scored_df = calculate_points(selected_day)

# --------------------------------------------------
# DAY-WISE TEAM POINTS (FOR TREND CHART)
# --------------------------------------------------
trend_rows = []

for d in day_numbers:
    temp_df = calculate_points(d)

    team_points_day = (
        temp_df
        .groupby("owner_name")["player_points"]
        .sum()
        .reset_index()
    )

    team_points_day["Day"] = f"Day {d}"

    trend_rows.append(team_points_day)

trend_df = pd.concat(trend_rows, ignore_index=True)

# --------------------------------------------------
# TEAM OVERTAKE INDICATOR (DAY 1 SAFE)
# --------------------------------------------------
if selected_day > 1:
    today_df = get_team_points_for_day(selected_day)
    yesterday_df = get_team_points_for_day(selected_day - 1)

    today_points = dict(zip(today_df["Owner"], today_df["Points"]))
    yesterday_points = dict(zip(yesterday_df["Owner"], yesterday_df["Points"]))

    teams = list(today_points.keys())
    overtake_scores = {}

    for team in teams:
        score = 0
        for other in teams:
            if team == other:
                continue

            yesterday_diff = yesterday_points[team] - yesterday_points[other]
            today_diff = today_points[team] - today_points[other]

            if yesterday_diff < 0 and today_diff > 0:
                score += 1
            elif yesterday_diff > 0 and today_diff < 0:
                score -= 1

        overtake_scores[team] = score
else:
    # Day 1: no overtakes possible
    overtake_scores = {
        team: 0
        for team in df["owner_name"].unique()
    }




# --------------------------------------------------
# TOP PLAYER
# --------------------------------------------------
top_player_row = (
    scored_df
    .groupby("player_name")["player_points"]
    .sum()
    .reset_index()
    .sort_values("player_points", ascending=False)
    .iloc[0]
)

top_player_name = top_player_row["player_name"]
top_player_points = round(top_player_row["player_points"], 1)

# --------------------------------------------------
# PLAYER SUMMARY PER OWNER (SORTED BY POINTS DESC)
# --------------------------------------------------
player_summary_df = (
    scored_df
    .groupby(["owner_name", "player_name"])["player_points"]
    .sum()
    .reset_index()
    .sort_values(
        ["owner_name", "player_points"],
        ascending=[True, False]
    )
)

player_summary_df["player_display"] = (
    player_summary_df["player_name"]
    + " ("
    + player_summary_df["player_points"].round(1).astype(str)
    + ")"
)

players_per_owner = (
    player_summary_df
    .groupby("owner_name")["player_display"]
    .apply(lambda x: " • ".join(x))
    .reset_index()
    .rename(columns={
        "owner_name": "Owner",
        "player_display": "Players (Points)"
    })
)

# --------------------------------------------------
# TEAM RANKINGS
# --------------------------------------------------
team_df = (
    scored_df
    .groupby("owner_name")["player_points"]
    .sum()
    .reset_index()
    .rename(columns={
        "owner_name": "Owner",
        "player_points": "Total Points"
    })
)

team_df["Rank"] = team_df["Total Points"].rank(
    ascending=False, method="min"
).astype(int)

team_df = team_df.sort_values("Rank")

team_df = team_df.merge(
    players_per_owner,
    on="Owner",
    how="left"
)

with tab1:
    # --------------------------------------------------
    # HERO SECTION
    # --------------------------------------------------
    st.markdown(f"""
    <div class="section hero-section">
        <div class="hero-title">🏆 Fantasy T20 Rankings</div>
        <div class="hero-subtitle">
            Cumulative leaderboard up to Day {selected_day}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------
    # KPI VALUES
    # --------------------------------------------------
    total_teams = team_df.shape[0]
    top_team = team_df.iloc[0]["Owner"]
    total_points = round(team_df["Total Points"].sum(), 1)

    # --------------------------------------------------
    # KPI SECTION
    # --------------------------------------------------
    st.markdown('<div class="section kpi-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📌 League Snapshot</div>', unsafe_allow_html=True)

    k1, k2, k3 = st.columns(3)

    with k1:
        st.markdown(
            f"<div class='kpi-card'><h2>Total Teams</h2><p>{total_teams}</p></div>",
            unsafe_allow_html=True
        )

    with k2:
        st.markdown(
            f"<div class='kpi-card'><h2>Top Team</h2><p>{top_team}</p></div>",
            unsafe_allow_html=True
        )

    with k3:
        st.markdown(
            f"""
            <div class='kpi-card'>
                <h2>Top Player</h2>
                <p>{top_player_name}</p>
                <span style="font-size:14px;color:#9ca3af;">
                    {top_player_points} pts
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------------------
    # RANKING SECTION (STABLE)
    # --------------------------------------------------
    st.markdown('<div class="section ranking-section">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title ranking-title">📊 Team Rankings</div>',
        unsafe_allow_html=True
    )

    def overtake_label(x):
        if x > 0:
            return f"▲ +{x}"
        if x < 0:
            return f"▼ {x}"
        return "— 0"

    team_df["Movement"] = team_df["Owner"].map(overtake_scores)
    team_df["Movement"] = team_df["Movement"].apply(overtake_label)


    def highlight_top3(row):
        if row["Rank"] == 1:
            style = "background-color:#facc15;color:black;font-weight:800"
        elif row["Rank"] == 2:
            style = "background-color:#d1d5db;color:black;font-weight:700"
        elif row["Rank"] == 3:
            style = "background-color:#fb923c;color:black;font-weight:700"
        else:
            style = ""

        # Apply style only to first 3 columns
        return [style, style, style, style, ""]

    styled_team_df = (
        team_df[["Rank", "Owner", "Total Points", "Movement","Players (Points)"]]
        .style
        .format({"Total Points": "{:.1f}"})
        .apply(highlight_top3, axis=1)
        .set_properties(**{"text-align": "center"})
        .set_table_styles(
            [{"selector": "th", "props": [("text-align", "center")]}]
        )
    )

    st.dataframe(
        styled_team_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------------------
    # INSIGHTS SECTION (FINAL LAYOUT)
    # --------------------------------------------------
    st.markdown('<div class="section chart-section">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title chart-title">📈 Insights</div>',
        unsafe_allow_html=True
    )

    # ==================================================
    # ROW 1: TWO BAR CHARTS SIDE BY SIDE
    # ==================================================
    c1, c2 = st.columns(2)

    # ---------- CARD 1: POINTS BY TEAM ----------
    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="chart-card-title">Points by Team</div>',
            unsafe_allow_html=True
        )

        fig_team = px.bar(
            team_df,
            x="Owner",
            y="Total Points",
            text_auto=True
        )
        fig_team.update_layout(
            template="plotly_dark",
            #title=None,
            xaxis_title=None,
            yaxis_title="Total Points"
        )

        st.plotly_chart(fig_team, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- CARD 2: POINTS BY ROLE ----------
    with c2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="chart-card-title">Points Contribution by Role</div>',
            unsafe_allow_html=True
        )

        role_df = (
            scored_df
            .groupby("role")["player_points"]
            .sum()
            .reset_index()
        )

        fig_role = px.bar(
            role_df,
            x="role",
            y="player_points",
            text_auto=True
        )
        fig_role.update_layout(
            template="plotly_dark",
            #title=None,
            xaxis_title="Role",
            yaxis_title="Points"
        )

        st.plotly_chart(fig_role, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================================================
    # SLIM DIVIDER
    # ==================================================
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ==================================================
    # ROW 2: DAY-WISE TREND LINE CHART (FULL WIDTH)
    # ==================================================
    with st.container():
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="chart-card-title">Day-wise Team Performance Trend</div>',
            unsafe_allow_html=True
        )

        fig_trend = px.line(
            trend_df,
            x="Day",
            y="player_points",
            color="owner_name",
            markers=True
        )

        fig_trend.update_layout(
            template="plotly_dark",
            #title=None, it shows undefined message
            xaxis_title="Match Day",
            yaxis_title="Cumulative Points",
            legend_title="Team"
        )

        st.plotly_chart(fig_trend, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ==================================================
# TAB 2: PLAYER BREAKDOWN
# ==================================================
with tab2:
    st.markdown("## 👥 Player Breakdown by Owner")

    owner_list = sorted(df["owner_name"].unique())
    selected_owner = st.selectbox(
        "Select Owner",
        owner_list
    )

    # Filter players for selected owner
    owner_df = (
        scored_df
        .loc[scored_df["owner_name"] == selected_owner]
        .groupby(["player_name", "role"])["player_points"]
        .sum()
        .reset_index()
        .sort_values("player_points", ascending=False)
    )

    # Captain / VC from config
    captain = CAPTAIN_CONFIG.get(selected_owner, {}).get("C")
    vice_captain = CAPTAIN_CONFIG.get(selected_owner, {}).get("VC")

    # Add C / VC indicator
    def cv_label(player):
        if player == captain:
            return "🧢 Captain"
        if player == vice_captain:
            return "🎖️ Vice Captain"
        return ""

    owner_df["C / VC"] = owner_df["player_name"].apply(cv_label)

    # Rename columns for display
    owner_df = owner_df.rename(columns={
        "player_name": "Player",
        "role": "Role",
        "player_points": "Points"
    })

    owner_df["Points"] = owner_df["Points"].astype(float).round(1)

    def highlight_cv(row):
        if row["C / VC"] == "🧢 Captain":
            return [
                "background-color:rgba(251,191,36,0.15);"
                "border-left:4px solid #fbbf24;"
                "font-weight:600"
            ] * len(row)

        if row["C / VC"] == "🎖️ Vice Captain":
            return [
                "background-color:rgba(56,189,248,0.15);"
                "border-left:4px solid #38bdf8;"
                "font-weight:600"
            ] * len(row)

        return [""] * len(row)


    styled_owner_df = owner_df.style.format({"Points": "{:.1f}"}).apply(highlight_cv, axis=1)

    st.dataframe(
        styled_owner_df,
        use_container_width=True,
        hide_index=True
    )

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown(
    '<div class="footer">Designed for clarity. Built to impress.</div>',
    unsafe_allow_html=True
)
