import streamlit as st
import pandas as pd
import os
import re
import plotly.express as px

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
# PLAYER SUMMARY PER OWNER
# --------------------------------------------------
player_summary_df = (
    scored_df
    .groupby(["owner_name", "player_name"])["player_points"]
    .sum()
    .reset_index()
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
    .apply(lambda x: ", ".join(x))
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

# --------------------------------------------------
# KPI VALUES
# --------------------------------------------------
total_teams = team_df.shape[0]
top_team = team_df.iloc[0]["Owner"]
total_points = round(team_df["Total Points"].sum(), 1)

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
# KPI SECTION
# --------------------------------------------------
st.markdown('<div class="section kpi-section">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📌 League Snapshot</div>', unsafe_allow_html=True)

k1, k2, k3 = st.columns(3)

with k1:
    st.markdown(f"<div class='kpi-card'><h2>Total Teams</h2><p>{total_teams}</p></div>", unsafe_allow_html=True)
with k2:
    st.markdown(f"<div class='kpi-card'><h2>Top Team</h2><p>{top_team}</p></div>", unsafe_allow_html=True)
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
# RANKING SECTION (SINGLE TABLE, TOP 3 STYLED)
# --------------------------------------------------
st.markdown('<div class="section ranking-section">', unsafe_allow_html=True)
st.markdown('<div class="section-title ranking-title">📊 Team Rankings</div>', unsafe_allow_html=True)

def highlight_top3(row):
    if row["Rank"] == 1:
        return ["background-color:#facc15;color:black;font-weight:800"] * len(row)
    if row["Rank"] == 2:
        return ["background-color:#d1d5db;color:black;font-weight:700"] * len(row)
    if row["Rank"] == 3:
        return ["background-color:#fb923c;color:black;font-weight:700"] * len(row)
    return [""] * len(row)

styled_team_df = (
    team_df[["Rank", "Owner", "Total Points", "Players (Points)"]]
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
# CHARTS SECTION
# --------------------------------------------------
st.markdown('<div class="section chart-section">', unsafe_allow_html=True)
st.markdown('<div class="section-title chart-title">📈 Insights</div>', unsafe_allow_html=True)

fig_team = px.bar(
    team_df,
    x="Owner",
    y="Total Points",
    title="Points by Team",
    text_auto=True
)
fig_team.update_layout(template="plotly_dark", title_x=0.5)

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
    title="Points Contribution by Role",
    text_auto=True
)
fig_role.update_layout(template="plotly_dark", title_x=0.5)

c1, c2 = st.columns(2)
c1.plotly_chart(fig_team, use_container_width=True)
c2.plotly_chart(fig_role, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown(
    '<div class="footer">Designed for clarity. Built to impress.</div>',
    unsafe_allow_html=True
)
