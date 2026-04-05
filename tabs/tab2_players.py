import streamlit as st
import pandas as pd

def render_tab2(df, scored_df, cap_df, selected_day):

    st.markdown("## 👥 Player Breakdown by Owner")

    # --------------------------------------------------
    # OWNER SELECTION
    # --------------------------------------------------
    owner_list = sorted(df["owner_name"].unique())
    selected_owner = st.selectbox(
        "Select Owner",
        owner_list,
        key="tab2_owner"
    )

    # --------------------------------------------------
    # AGGREGATE TOTAL POINTS
    # --------------------------------------------------
    owner_points_df = (
        scored_df
        .loc[scored_df["owner_name"] == selected_owner]
        .groupby(["player_name", "franchise"])["player_points"]
        .sum()
        .reset_index()
        .sort_values("player_points", ascending=False)
    )

    # --------------------------------------------------
    # CAPTAIN DATA (CLEAN)
    # --------------------------------------------------
    cap_df.columns = [c.lower() for c in cap_df.columns]

    owner_caps = (
        cap_df[
            (cap_df["owner_name"] == selected_owner) &
            (cap_df["from_day"] <= selected_day)
        ]
        .sort_values("from_day")
    )

    if not owner_caps.empty:
        latest = owner_caps.iloc[-1]
        current_c = latest["captain"]
        current_vc = latest["vice_captain"]
    else:
        current_c = None
        current_vc = None

    # --------------------------------------------------
    # MATCH-WISE GAINS
    # --------------------------------------------------
    def get_player_daywise_gains(player_name):

        player_row = df[
            (df["owner_name"] == selected_owner) &
            (df["player_name"] == player_name)
        ]

        if player_row.empty:
            return "—"

        row = player_row.iloc[0]
        gains = []

        for d in range(1, selected_day + 1):

            day_col = f"day{d}"
            if day_col not in df.columns:
                continue

            points = pd.to_numeric(row.get(day_col, 0), errors="coerce")
            points = 0 if pd.isna(points) else points

            # Dynamic captain lookup
            cap_row = owner_caps[owner_caps["from_day"] <= d]

            if not cap_row.empty:
                latest_cap = cap_row.iloc[-1]
                c = latest_cap["captain"]
                vc = latest_cap["vice_captain"]
            else:
                c, vc = None, None

            multiplier = 1.0

            if player_name == c:
                multiplier = 2.0
            elif player_name == vc:
                multiplier = 1.5

            value = round(points * multiplier, 1)

            if value != 0:
                gains.append(value)

        return "—" if not gains else f"({', '.join(map(str, gains))})"

    owner_points_df["Match-wise Gains"] = owner_points_df["player_name"].apply(
        get_player_daywise_gains
    )

    # --------------------------------------------------
    # CAPTAIN / VC LABEL
    # --------------------------------------------------
    def cv_label(player):
        if player == current_c:
            return "🧢 Captain"
        if player == current_vc:
            return "🎖️ Vice Captain"
        return ""

    owner_points_df["C / VC"] = owner_points_df["player_name"].apply(cv_label)

    # --------------------------------------------------
    # FINAL FORMAT
    # --------------------------------------------------
    owner_points_df = owner_points_df.rename(columns={
        "player_name": "Player",
        "franchise": "Franchise",
        "player_points": "Points"
    })

    # --------------------------------------------------
    # STYLING
    # --------------------------------------------------
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

    # --------------------------------------------------
    # DISPLAY
    # --------------------------------------------------
    st.dataframe(
        styled_owner_df,
        use_container_width=True,
        hide_index=True
    )