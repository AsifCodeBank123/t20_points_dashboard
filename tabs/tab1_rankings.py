import streamlit as st
import pandas as pd
import plotly.express as px
import textwrap

def render_tab1(df, team_df, cap_df,matches_df,scored_df,selected_day, get_c_vc_points,get_current_c_vc):

    st.markdown(f"""
    <span style="color:#94a3b8;font-size:0.85rem;">
    ℹ️ Rankings & movement are based on completed matches. Watchlist shows upcoming players for Day {selected_day}.
    </span>
    """, unsafe_allow_html=True)

    st.markdown("### 🏆 Team Rankings")

    display_df = team_df[
        ["Rank", "Owner", "Points", "Movement", "Next Rank", "1st Rank", "Win %", "Watchlist"]
    ].rename(columns={
        "Points": "Total Points",
        "Watchlist": f"Watchlist (Day {selected_day})"
    })

    # 🔥 Highlight Top 3
    def highlight_top3(row):
        if row["Rank"] == 1:
            style = "background-color:#FFD700;color:black;font-weight:800"
        elif row["Rank"] == 2:
            style = "background-color:#C0C0C0;color:black;font-weight:700"
        elif row["Rank"] == 3:
            style = "background-color:#CD7F32;color:black;font-weight:700"
        else:
            style = ""
        return [style] * len(row)

    styled_df = (
        display_df
        .style
        .format({
            "Total Points": "{:.1f}",
            "Next Rank": "{:.1f}",
            "1st Rank": "{:.1f}",
            "Win %": "{:.1f}%"
        })
        .apply(highlight_top3, axis=1)
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # --------------------------------------------------
    # UPCOMING MATCH FORECASTS
    # --------------------------------------------------

    st.markdown("## 📈 Upcoming Match Forecasts")

    # --------------------------------------------------
    # NEXT 5 MATCHES
    # --------------------------------------------------
    future_matches = matches_df[
        matches_df["Day"] >= selected_day
    ].head(5).copy()

    if not future_matches.empty:

        future_matches["match_label"] = future_matches.apply(
            lambda x: (
                f"Day {x['Day']} - "
                f"{x['Teams'].split(',')[0].strip()} vs "
                f"{x['Teams'].split(',')[1].strip()}"
            ),
            axis=1
        )
        # --------------------------------------------------
        # BUILD FORECASTS
        # --------------------------------------------------

        all_match_forecasts = {}
        summary_rows = []

        for _, match in future_matches.iterrows():

            match_label = match["match_label"]

            teams = [
                t.strip()
                for t in match["Teams"].split(",")
            ]

            forecast_rows = []

            # ----------------------------------------
            # OWNER FORECAST
            # ----------------------------------------
            for owner, group in df.groupby("owner_name"):

                owner_players = group[
                    group["franchise"].isin(teams)
                ].copy()

                total = 0

                # current captain / VC for that match day
                captain, vice_captain = get_current_c_vc(
                    cap_df,
                    owner,
                    match["Day"]
                )

                # ----------------------------------------
                # PLAYER FORECAST
                # ----------------------------------------
                for _, r in owner_players.iterrows():

                    player = r["player_name"]

                    player_scores = []

                    for d in range(1, selected_day + 1):

                        day_col = f"day{d}"

                        pts = pd.to_numeric(
                            r.get(day_col, 0),
                            errors="coerce"
                        )

                        pts = 0 if pd.isna(pts) else pts

                        # ----------------------------------------
                        # APPLY FORECAST MULTIPLIER
                        # ----------------------------------------
                        if player == captain:
                            pts *= 2

                        elif player == vice_captain:
                            pts *= 1.5

                        if pts != 0:
                            player_scores.append(pts)

                    # ----------------------------------------
                    # PLAYER AVERAGE
                    # ----------------------------------------
                    avg_points = (
                        sum(player_scores) / len(player_scores)
                        if player_scores else 0
                    )

                    total += avg_points

                forecast_rows.append({
                    "Owner": owner,
                    "Predicted Points": round(total, 1)
                })

            # ----------------------------------------
            # FORECAST DF
            # ----------------------------------------
            forecast_df = pd.DataFrame(forecast_rows)

            forecast_df = forecast_df.sort_values(
                "Predicted Points",
                ascending=False
            )

            all_match_forecasts[match_label] = forecast_df

            # ----------------------------------------
            # SUMMARY ROW
            # ----------------------------------------
            top_row = forecast_df.iloc[0]

            summary_rows.append({
                "Match": match_label,
                "Top Owner": top_row["Owner"],
                "Best Forecast": round(top_row["Predicted Points"], 1)
            })

        # --------------------------------------------------
        # SUMMARY DF
        # --------------------------------------------------
        summary_df = pd.DataFrame(summary_rows)

    
        # --------------------------------------------------
        # MATCH FORECAST CARDS
        # --------------------------------------------------

        card_cols = st.columns(len(summary_df))

        for i, (_, row) in enumerate(summary_df.iterrows()):
            # Split the match string (assuming format "Day 45 • PBKS vs DC")
            day_part = row['Match'].split('-')[0].replace('Day', '').strip()
            team_part = row['Match'].split('-')[1].strip()

            # Use dedent to ensure no leading spaces trigger a "code block" look
            html = textwrap.dedent(f"""
                <div class="match-card">
                    <div class="match-top">
                        <div class="match-day">DAY {day_part}</div>
                        <div class="match-teams">{team_part}</div>
                    </div>
                    <div class="match-divider"></div>
                    <div class="match-label">🔥 Top Owner</div>
                    <div class="match-owner">{row['Top Owner']}</div>
                    <div class="match-points-label">Forecast</div>
                    <div class="match-points">{row['Best Forecast']} pts</div>
                </div>
            """)

            # Send to the specific column and use unsafe_allow_html
            if i < len(card_cols):
                card_cols[i].markdown(html, unsafe_allow_html=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # --------------------------------------------------
        # MATCH SELECTOR
        # --------------------------------------------------
        selected_match = st.selectbox(
            "Select Match for Detailed Forecast",
            list(all_match_forecasts.keys())
        )

        selected_df = all_match_forecasts[selected_match]

        # --------------------------------------------------
        # TOP CARD
        # --------------------------------------------------
        top_owner = selected_df.iloc[0]

        st.markdown(f"""
        <div class="forecast-top-card">
            🔥 <b>{top_owner['Owner']}</b>
            projected to dominate
            <b>{selected_match}</b>
            with
            <b>{top_owner['Predicted Points']} pts</b>
        </div>
        """, unsafe_allow_html=True)

        # --------------------------------------------------
        # BAR CHART
        # --------------------------------------------------
        fig_forecast = px.bar(
            selected_df,
            x="Owner",
            y="Predicted Points",
            color="Predicted Points",
            text_auto=True
        )

        fig_forecast.update_layout(
            template="plotly_dark",
            height=420,
            xaxis_title=None,
            yaxis_title="Projected Match Points",
            coloraxis_showscale=False
        )

        st.plotly_chart(
            fig_forecast,
            use_container_width=True
        )

    else:
        st.info("No upcoming matches remaining.")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # --------------------------------------------------
    # FINAL TOURNAMENT FORECAST
    # --------------------------------------------------

    st.markdown("## 🏆 Final Tournament Forecast")

    future_matches_all = matches_df[
        matches_df["Day"] >= selected_day
    ].copy()

    forecast_rows = []

    for owner, group in df.groupby("owner_name"):

        # ----------------------------------------
        # CURRENT POINTS
        # ----------------------------------------
        current_points = team_df.loc[
            team_df["Owner"] == owner,
            "Points"
        ].values[0]

        future_projection = 0

        # ----------------------------------------
        # SIMULATE EACH FUTURE MATCH
        # ----------------------------------------
        for _, match in future_matches_all.iterrows():

            teams = [
                t.strip()
                for t in match["Teams"].split(",")
            ]

            owner_players = group[
                group["franchise"].isin(teams)
            ].copy()

            captain, vice_captain = get_current_c_vc(
                cap_df,
                owner,
                match["Day"]
            )

            match_projection = 0

            for _, r in owner_players.iterrows():

                player = r["player_name"]

                scores = []

                for d in range(1, selected_day + 1):

                    pts = pd.to_numeric(
                        r.get(f"day{d}", 0),
                        errors="coerce"
                    )

                    pts = 0 if pd.isna(pts) else pts

                    # ----------------------------------------
                    # APPLY C / VC
                    # ----------------------------------------
                    if player == captain:
                        pts *= 2

                    elif player == vice_captain:
                        pts *= 1.5

                    if pts != 0:
                        scores.append(pts)

                avg_points = (
                    sum(scores) / len(scores)
                    if scores else 0
                )

                match_projection += avg_points

            future_projection += match_projection

        predicted_final = (
            current_points +
            future_projection
        )

        forecast_rows.append({
            "Owner": owner,
            "Current": round(current_points, 1),
            "Projected Gain": round(future_projection, 1),
            "Predicted Final": round(predicted_final, 1)
        })

    # --------------------------------------------------
    # FINAL DF
    # --------------------------------------------------

    forecast_df = pd.DataFrame(forecast_rows)

    forecast_df = forecast_df.sort_values(
        "Predicted Final",
        ascending=False
    ).reset_index(drop=True)

    forecast_df.index += 1

    # --------------------------------------------------
    # SESSION FORECAST CACHE
    # --------------------------------------------------

    if "previous_final_forecast" not in st.session_state:
        st.session_state["previous_final_forecast"] = {}

    previous_forecast = st.session_state["previous_final_forecast"]

    # --------------------------------------------------
    # FORECAST CARDS GRID
    # --------------------------------------------------

    forecast_list = forecast_df.to_dict("records")

    for row_start in range(0, len(forecast_list), 5):

        row_cards = forecast_list[row_start:row_start + 5]

        cols = st.columns(5)

        for i, row in enumerate(row_cards):

            owner = row["Owner"]

            current = row["Predicted Final"]

            old = previous_forecast.get(owner, current)

            delta = round(current - old, 1)

            trend = "➖"
            trend_class = "same"

            if delta > 0:
                trend = "🔼"
                trend_class = "up"

            elif delta < 0:
                trend = "🔽"
                trend_class = "down"

            html = textwrap.dedent(f"""
            <div class="final-forecast-card">
                <div class="forecast-rank">#{row_start + i + 1}</div>
                <div class="forecast-owner">{owner}</div>
                <div class="forecast-final-score">{current:,.0f}</div>
                <div class="forecast-trend">{trend}</div>
            </div>""")

            cols[i].markdown(html,unsafe_allow_html=True)

    # --------------------------------------------------
    # UPDATE CACHE
    # --------------------------------------------------

    st.session_state["previous_final_forecast"] = {
        r["Owner"]: r["Predicted Final"]
        for _, r in forecast_df.iterrows()
    }

    st.markdown('<div class="section-divider"></div>',unsafe_allow_html=True)

    # ==================================================
    # 🧠 CAPTAIN STRATEGY (FINAL CLEAN VERSION)
    # ==================================================
    st.markdown("### 🧠 Captain Strategy")

    cap_df.columns = [c.lower() for c in cap_df.columns]

    # 🔧 Clean history + return changes count
    def format_history(series):
        if series.empty:
            return "—", 0

        cleaned = []
        prev = None

        for name in series.tolist():
            if name != prev:
                cleaned.append(name)
                prev = name

        history_str = cleaned[0] if len(cleaned) == 1 else " → ".join(cleaned)
        changes = max(len(cleaned) - 1, 0)

        return history_str, changes

    rows = []

    for owner in df["owner_name"].unique():

        oc = cap_df[
            cap_df["owner_name"] == owner
        ].sort_values("from_day")

        if not oc.empty:
            captain_history, cap_changes = format_history(oc["captain"])
            vc_history, vc_changes = format_history(oc["vice_captain"])
        else:
            captain_history, vc_history = "—", "—"
            cap_changes, vc_changes = 0, 0

        # ✅ Total changes (Captain + VC)
        total_changes = cap_changes + vc_changes

        rows.append({
            "Owner": owner,
            "Captain": captain_history,
            "Cap Points": get_c_vc_points(df,cap_df,owner,selected_day,role="captain"),
            "Vice Captain": vc_history,
            "VC Points": get_c_vc_points(df,cap_df,owner,selected_day,role="vice_captain"),
            "Changes": total_changes
        })

    cap_table = pd.DataFrame(rows)

    st.dataframe(
        cap_table,
        use_container_width=True,
        hide_index=True
    )