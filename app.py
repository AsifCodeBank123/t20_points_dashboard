import streamlit as st
import pandas as pd
import os
import re
import plotly.express as px
import numpy as np

from config.captains import CAPTAIN_CONFIG
from config.t20_rankings import T20_RANKINGS
from config.auction_config import (
    INITIAL_PURSE,
    MINI_AUCTION_MIN_PRICE,
    PURSE_TO_POINTS_RATIO
)


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
DATA_PATH = "data/points.csv"
if not os.path.exists(DATA_PATH):
    st.error("CSV not found at data/points.csv")
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
# LOAD MATCH TEAMS BY DAY
# --------------------------------------------------
MATCH_PATH = "data/matches_by_day.csv"

if os.path.exists(MATCH_PATH):
    matches_df = pd.read_csv(MATCH_PATH)
else:
    matches_df = pd.DataFrame(columns=["Day", "Teams"])


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
# COUNTRIES PLAYING ON SELECTED DAY (NEW CSV FORMAT)
# --------------------------------------------------
day_row = matches_df[matches_df["Day"] == selected_day]

playing_countries = set()

if not day_row.empty:
    teams_str = day_row.iloc[0]["Teams"]
    playing_countries = {
        t.strip() for t in teams_str.split(",")
    }


# --------------------------------------------------
# BUILD WATCHLIST PER OWNER (WITH CAPTAIN / VC HIGHLIGHT)
# --------------------------------------------------

GROUP_STAGE_END = 14  # change if needed

owner_watch_map = {}

for owner, group in df.groupby("owner_name"):

    # Exclude released/injured players
    eligible = group[
        (group["country"].isin(playing_countries)) &
        (group["released_injured"].fillna("").str.upper() != "Y")
    ]

    watch_players = []

    for _, row in eligible.iterrows():

        player = row["player_name"]

        # Determine captain / VC based on stage
        if selected_day <= GROUP_STAGE_END:

            is_c = row.get("c_grp", 0) == 1
            is_vc = row.get("vc_grp", 0) == 1

        else:

            is_c = row.get("c_super", 0) == 1
            is_vc = row.get("vc_super", 0) == 1

        # Add highlight symbols
        if is_c:
            player = f"🧢 {player}"

        elif is_vc:
            player = f"🎖️ {player}"

        watch_players.append(player)

    owner_watch_map[owner] = (
        ", ".join(sorted(watch_players))
        if watch_players else "—"
    )


tab1, tab2, tab3 = st.tabs(["🏆 Dashboard", "👥 Player Breakdown", "🧠 Replacement Finder"])


# --------------------------------------------------
# TEAM POINTS FOR A GIVEN DAY
# --------------------------------------------------
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
# POINT CALCULATION (FIXED FOR c_grp / c_super)
# --------------------------------------------------
def calculate_points(upto_day: int) -> pd.DataFrame:

    temp = df.copy()

    # Ensure captain columns are numeric (important fix)
    for col in ["c_grp", "vc_grp", "c_super", "vc_super"]:
        if col in temp.columns:
            temp[col] = pd.to_numeric(temp[col], errors="coerce").fillna(0)
        else:
            temp[col] = 0

    temp["player_points"] = 0.0

    for d in range(1, upto_day + 1):

        day_col = f"day{d}"

        if day_col not in temp.columns:
            continue

        points = pd.to_numeric(
            temp[day_col],
            errors="coerce"
        ).fillna(0)

        # -------------------------
        # SELECT CORRECT PHASE
        # -------------------------
        if d <= 14:
            c_col = "c_grp"
            vc_col = "vc_grp"
        else:
            c_col = "c_super"
            vc_col = "vc_super"

        # -------------------------
        # MULTIPLIER CALCULATION
        # -------------------------
        multiplier = pd.Series(1.0, index=temp.index)

        multiplier.loc[temp[c_col] == 1] = 2.0
        multiplier.loc[temp[vc_col] == 1] = 1.5

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

team_df["Watchlist"] = team_df["Owner"].map(owner_watch_map)


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

    # --------------------------------------------------
    # RANK DELTA COLUMNS (Next Rank & 1st Rank)
    # --------------------------------------------------
    scores = team_df["Total Points"].values

    def format_delta(val):
        if pd.isna(val):
            return np.nan
        return round(val, 1)

    # Next Rank Delta
    next_rank_delta = [np.nan]
    for i in range(1, len(scores)):
        next_rank_delta.append(format_delta(scores[i - 1] - scores[i]))

    # 1st Rank Delta
    first_rank_delta = [
        np.nan if i == 0 else format_delta(scores[0] - s)
        for i, s in enumerate(scores)
    ]

    team_df["Next Rank Δ"] = next_rank_delta
    team_df["1st Rank Δ"] = first_rank_delta



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
        return [style, style, style, style, "","",""]

    styled_team_df = (
        team_df[
            [
                "Rank",
                "Owner",
                "Total Points",
                "Movement",
                "Next Rank Δ",
                "1st Rank Δ",
                "Watchlist",
            ]
        ]
        .style
        .format({
            "Total Points": "{:.1f}",
            "Next Rank Δ": "{:.1f}",
            "1st Rank Δ": "{:.1f}",
        })
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
    selected_owner = st.selectbox("Select Owner", owner_list)

    # Aggregate points per player (SAFE)
    owner_points_df = (
        scored_df
        .loc[scored_df["owner_name"] == selected_owner]
        .groupby(["player_name", "role", "country"])["player_points"]
        .sum()
        .reset_index()
        .sort_values("player_points", ascending=False)
    )

    # Helper: compute match-wise gains (NO ZERO)
    def get_player_daywise_gains(player_name):
        player_rows = df[
            (df["owner_name"] == selected_owner) &
            (df["player_name"] == player_name)
        ]

        gains = []

        for d in range(1, selected_day + 1):
            day_col = f"day{d}"
            c_col = f"c_day{d}"
            vc_col = f"vc_day{d}"

            if day_col not in player_rows:
                continue

            points = pd.to_numeric(player_rows.iloc[0][day_col], errors="coerce")
            points = 0 if pd.isna(points) else points

            multiplier = 1.0
            if c_col in player_rows and player_rows.iloc[0][c_col] == 1:
                multiplier = 2.0
            elif vc_col in player_rows and player_rows.iloc[0][vc_col] == 1:
                multiplier = 1.5

            value = round(points * multiplier, 1)

            if value != 0:
                gains.append(value)

        return "—" if not gains else f"({', '.join(str(g) for g in gains)})"

    # Add match-wise gains AFTER grouping
    owner_points_df["Match-wise Gains"] = owner_points_df["player_name"].apply(
        get_player_daywise_gains
    )

    # Captain / VC from config
    captain = CAPTAIN_CONFIG.get(selected_owner, {}).get("C")
    vice_captain = CAPTAIN_CONFIG.get(selected_owner, {}).get("VC")

    def cv_label(player):
        if player == captain:
            return "🧢 Captain"
        if player == vice_captain:
            return "🎖️ Vice Captain"
        return ""

    owner_points_df["C / VC"] = owner_points_df["player_name"].apply(cv_label)

    # Rename for display
    owner_points_df = owner_points_df.rename(columns={
        "player_name": "Player",
        "role": "Role",
        "country": "Country",
        "player_points": "Points"
    })

    # Styling
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

    styled_owner_df = (
        owner_points_df
        .style
        .format({"Points": "{:.1f}"})
        .apply(highlight_cv, axis=1)
    )

    st.dataframe(
        styled_owner_df,
        use_container_width=True,
        hide_index=True
    )

with tab3:
    st.markdown("## 🔁 Replacement Finder")

    # ==================================================
    # OWNER SELECTION
    # ==================================================
    owner_list = sorted(df["owner_name"].unique())

    selected_owner = st.selectbox(
        "Select Owner",
        owner_list,
        key="replacement_owner"
    )

    owner_players_df = df[df["owner_name"] == selected_owner]

    # ==================================================
    # RULED OUT PLAYER SELECTION
    # ==================================================
    ruled_out_player = st.selectbox(
        "Select Ruled-Out Player",
        owner_players_df["player_name"].unique(),
        key="ruled_out_player"
    )

    r = owner_players_df[
        owner_players_df["player_name"] == ruled_out_player
    ].iloc[0]

    r_price = r["bid_price"]
    r_country = r["country"]

    # Dream XI cumulative points
    r_points = scored_df.loc[
        (scored_df["owner_name"] == selected_owner) &
        (scored_df["player_name"] == ruled_out_player),
        "player_points"
    ].sum()

    st.markdown(
        f"""
        ### 🧾 Ruled Out Player Details

        • **Price:** ${r_price}  
        • **Country:** {r_country}  
        • **Dream XI Points:** {round(r_points, 1)}
        """
    )

    # ==================================================
    # RULE 1 — ELIGIBILITY CHECK
    # ==================================================
    if r_price < 500:
        st.error("Replacement NOT allowed. Auction price must be ≥ $500.")
        st.stop()

    # ==================================================
    # CHECK SPECIAL CASE
    # ==================================================
    same_country_count = owner_players_df[
        owner_players_df["country"] == r_country
    ].shape[0]

    only_player_case = same_country_count == 1

    # ==================================================
    # SHOW RULES (CLEAR EXPLANATION)
    # ==================================================
    if not only_player_case:

        st.info(
            """
            ### 📜 Normal Replacement Rules

            1. Replacement price must be **at least $50 higher** than ruled-out player.
            2. Replacement Dream XI points must be:
               - ≥ ruled-out player points  
               - ≤ ruled-out player points + 50
            """
        )

    else:

        st.warning(
            """
            ### ⚠ Special Case Rules (Only Player From That Country)

            1. Replacement price must be between:
               - 50% of ruled-out price (rounded to nearest 10)
               - Up to ruled-out price
            2. Dream XI points rule is removed.
            3. Replacement must be from:
               - Same country OR
               - Any country ranked lower in T20 rankings.
               (Higher-ranked teams are NOT allowed.)
            """
        )

    # ==================================================
    # PREPARE CANDIDATE POOL
    # ==================================================
    candidate_df = df[
        ~df["player_name"].isin(owner_players_df["player_name"])
    ].copy()

    # Add cumulative Dream XI points
    total_points_df = (
        scored_df.groupby("player_name")["player_points"]
        .sum()
        .reset_index()
    )

    candidate_df = candidate_df.merge(
        total_points_df,
        on="player_name",
        how="left"
    )

    candidate_df["player_points"] = candidate_df["player_points"].fillna(0)

    # ==================================================
    # APPLY RULES
    # ==================================================
    if not only_player_case:

        # ----------------------------
        # NORMAL CASE
        # ----------------------------

        # Rule 3: Price must be ≥ ruled price + 50
        candidate_df = candidate_df[
            candidate_df["bid_price"] >= r_price + 50
        ]

        # Rule 4: Points band restriction
        candidate_df = candidate_df[
            (candidate_df["player_points"] >= r_points) &
            (candidate_df["player_points"] <= r_points + 50)
        ]

    else:

        # ----------------------------
        # SPECIAL CASE
        # ----------------------------

        # Price lower bound = 50%, rounded to nearest 10
        lower_price = round((r_price * 0.5) / 10) * 10

        candidate_df = candidate_df[
            (candidate_df["bid_price"] >= lower_price) &
            (candidate_df["bid_price"] <= r_price)
        ]

        # Strict ranking enforcement
        r_rank = T20_RANKINGS.get(r_country)

        candidate_df = candidate_df[
            candidate_df["country"].apply(
                lambda c: (
                    c in T20_RANKINGS and
                    T20_RANKINGS[c] >= r_rank
                )
            )
        ]

    # ==================================================
    # FINAL DISPLAY
    # ==================================================
    candidate_df = candidate_df.rename(columns={
        "player_name": "Player",
        "country": "Country",
        "bid_price": "Price",
        "player_points": "Dream XI Points"
    })

    candidate_df["Dream XI Points"] = candidate_df["Dream XI Points"].round(1)

    display_cols = ["Player", "Country", "Price", "Dream XI Points"]

    st.markdown("### ✅ Eligible Replacement Players")

    if candidate_df.empty:
        st.warning("No valid replacements found under current rules.")
    else:
        st.dataframe(
            candidate_df[display_cols]
            .sort_values("Price"),
            use_container_width=True,
            hide_index=True
        )

# with tab4:

#     st.markdown("## 💰 Mini Auction Planner")

#     # ============================
#     # OWNER SELECTION
#     # ============================
#     owner_list = sorted(df["owner_name"].unique())

#     selected_owner = st.selectbox(
#         "Select Owner",
#         owner_list,
#         key="mini_owner"
#     )

#     owner_df = df[df["owner_name"] == selected_owner]

#     # ============================
#     # CURRENT PURSE CALCULATION
#     # ============================

#     spent = owner_df["bid_price"].sum()

#     current_purse = INITIAL_PURSE - spent

#     st.markdown(f"""
#     ### Current Purse Status

#     Initial Purse: ${INITIAL_PURSE}  
#     Spent: ${spent}  
#     Remaining Purse: ${current_purse}
#     """)

#     # ============================
#     # RELEASE PLAYER SELECTION
#     # ============================

#     release_players = st.multiselect(
#         "Select up to 2 players to release",
#         owner_df["player_name"].tolist(),
#         max_selections=2
#     )

#     released_df = owner_df[
#         owner_df["player_name"].isin(release_players)
#     ]

#     # ============================
#     # PURSE RECOVERY FUNCTION
#     # ============================

#     def purse_recovery(price):

#         if price <= 200:
#             return price

#         recovery = price * 0.5

#         recovery = int((recovery + 9) // 10 * 10)

#         return recovery

#     released_df["Recovery"] = released_df["bid_price"].apply(purse_recovery)

#     recovered_total = released_df["Recovery"].sum()

#     revised_purse = current_purse + recovered_total

#     st.markdown(f"""
#     ### Purse After Release

#     Purse Recovered: ${recovered_total}  
#     Revised Purse: ${revised_purse}
#     """)

#     # ============================
#     # PURSE TO POINTS VALUE
#     # ============================

#     convertible_points = revised_purse * PURSE_TO_POINTS_RATIO

#     st.markdown(f"""
#     If unused, purse converts to:

#     **{round(convertible_points,1)} points**
#     """)

#     # ============================
#     # RELEASE SUGGESTION ENGINE
#     # ============================

#     owner_points = (
#         scored_df[
#             scored_df["owner_name"] == selected_owner
#         ]
#         .groupby("player_name")["player_points"]
#         .sum()
#         .reset_index()
#     )

#     owner_points = owner_points.merge(
#         owner_df[["player_name", "bid_price"]],
#         on="player_name"
#     )

#     owner_points["Value Score"] = (
#         owner_points["player_points"] /
#         owner_points["bid_price"]
#     )

#     suggest_release = owner_points.sort_values(
#         "Value Score"
#     ).head(5)

#     st.markdown("### Suggested Players to Release (Worst Value)")

#     st.dataframe(
#         suggest_release.rename(columns={
#             "player_name": "Player",
#             "player_points": "Points",
#             "bid_price": "Price",
#             "Value Score": "Points per Dollar"
#         }),
#         hide_index=True
#     )

#     # ============================
#     # TARGET PLAYER POOL
#     # ============================

#     released_names = released_df["player_name"].tolist()

#     unsold_pool = df.copy()

#     # Remove players already owned except released
#     unsold_pool = unsold_pool[
#         (~unsold_pool["player_name"].isin(owner_df["player_name"]))
#         |
#         (unsold_pool["player_name"].isin(released_names))
#     ]

#     unsold_pool = unsold_pool.merge(
#         scored_df.groupby("player_name")["player_points"].sum().reset_index(),
#         on="player_name",
#         how="left"
#     )

#     unsold_pool["player_points"] = unsold_pool["player_points"].fillna(0)

#     # Filter affordable targets
#     affordable_targets = unsold_pool[
#         unsold_pool["bid_price"] <= revised_purse
#     ]

#     affordable_targets = affordable_targets[
#         affordable_targets["bid_price"] >= MINI_AUCTION_MIN_PRICE
#     ]

#     st.markdown("### Affordable Targets in Mini Auction")

#     st.dataframe(
#         affordable_targets.rename(columns={
#             "player_name": "Player",
#             "country": "Country",
#             "bid_price": "Expected Price",
#             "player_points": "Dream XI Points"
#         }).sort_values("Expected Price"),
#         hide_index=True,
#         use_container_width=True
#     )

#     # ============================
#     # SUMMARY
#     # ============================

#     st.markdown(f"""
#     ### Mini Auction Summary

#     Players Released: {len(release_players)}  
#     Purse Available: ${revised_purse}  
#     Max Possible Conversion: {round(convertible_points,1)} points  
#     """)


# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown(
    '<div class="footer">Designed for clarity. Built to impress.</div>',
    unsafe_allow_html=True
)
