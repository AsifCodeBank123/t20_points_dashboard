import streamlit as st
import pandas as pd

def render_tab6(df, matches_df, selected_day):

    st.subheader("📅 Match-wise Points")

    # -------------------------------
    # 🔹 Day Selection
    # -------------------------------
    day_list = sorted(matches_df["Day"].unique())

    selected_day_mp = st.selectbox(
        "Select Day",
        day_list,
        key="mp_day"
    )

    # -------------------------------
    # 🔹 Get Matches
    # -------------------------------
    rows = matches_df[matches_df["Day"] == selected_day_mp]

    teams = []
    for _, r in rows.iterrows():
        teams.extend([t.strip() for t in r["Teams"].split(",")])

    # Create match pairs
    matches = [
        (teams[i], teams[i+1])
        for i in range(0, len(teams), 2)
        if i + 1 < len(teams)
    ]

    if not matches:
        st.warning("No matches found for this day.")
        st.stop()

    # -------------------------------
    # 🔹 Match Selection
    # -------------------------------
    match_options = list(range(1, len(matches) + 1))

    selected_match_no = st.selectbox(
        "Select Match",
        match_options,
        key="mp_match"
    )

    team1, team2 = matches[selected_match_no - 1]

    st.markdown(f"### 🏏 {team1} vs {team2}")

    # -------------------------------
    # 🔹 Points Extraction
    # -------------------------------
    day_col = f"day{selected_day_mp}"

    if day_col not in df.columns:
        st.warning("No points data available for this day.")
        st.stop()

    match_df = df[
        df["franchise"].isin([team1, team2])
    ].copy()

    match_df[day_col] = pd.to_numeric(
        match_df[day_col],
        errors="coerce"
    ).fillna(0)

    # -------------------------------
    # 🔹 Prepare Table
    # -------------------------------
    display_df = match_df[
        ["owner_name", "player_name", "franchise", day_col]
    ].rename(columns={
        "owner_name": "Owner",
        "player_name": "Player",
        "franchise": "Team",
        day_col: "Points"
    }).sort_values("Points", ascending=False)

    if display_df.empty:
        st.warning("No player data available for this match.")
        st.stop()

    # -------------------------------
    # 🔥 Highlight Top Performer
    # -------------------------------
    max_pts = display_df["Points"].max()

    def highlight(row):
        if row["Points"] == max_pts and max_pts > 0:
            return ["background-color: rgba(34,197,94,0.3)"] * len(row)
        return [""] * len(row)

    st.dataframe(
        display_df.style
            .format({"Points": "{:.0f}"})
            .apply(highlight, axis=1),
        use_container_width=True,
        hide_index=True
    )