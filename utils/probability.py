import pandas as pd

def calculate_win_probability(df, scored_df, matches_df, selected_day):

    # Normalize
    matches_df.columns = [c.strip() for c in matches_df.columns]

    # ----------------------------------------
    # CURRENT POINTS
    # ----------------------------------------
    current_points = (
        scored_df.groupby("owner_name")["player_points"]
        .sum()
    )

    owners = current_points.index.tolist()

    # ----------------------------------------
    # PLAYER AVG
    # ----------------------------------------
    day_cols = [c for c in df.columns if c.startswith("day")]

    player_avg = df.copy()

    player_avg["avg_points"] = (
        player_avg[day_cols]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .mean(axis=1)
    )

    # ----------------------------------------
    # TEAM MATCH COUNT
    # ----------------------------------------
    remaining_matches = matches_df[matches_df["Day"] >= selected_day]

    team_match_count = {}

    for _, row in remaining_matches.iterrows():
        teams = [t.strip() for t in row["Teams"].split(",")]

        for t in teams:
            team_match_count[t] = team_match_count.get(t, 0) + 1

    # ----------------------------------------
    # FUTURE + EXPLANATION
    # ----------------------------------------
    owner_future = {}
    explanations = {}

    for owner in owners:

        owner_players = player_avg[
            (player_avg["owner_name"] == owner) &
            (player_avg["released_injured"].fillna("").str.upper() != "Y")
        ]

        total_future = 0
        player_contrib = []

        for _, p in owner_players.iterrows():

            team = p["franchise"]
            avg = p["avg_points"]

            matches_left = team_match_count.get(team, 0)

            future_points = avg * matches_left
            total_future += future_points

            if future_points > 0:
                player_contrib.append((p["player_name"], future_points))

        # Top 3 contributors
        player_contrib = sorted(player_contrib, key=lambda x: x[1], reverse=True)[:3]

        explanations[owner] = {
            "top_players": player_contrib,
            "matches": sum(team_match_count.values())
        }

        owner_future[owner] = total_future

    # ----------------------------------------
    # PROJECTION
    # ----------------------------------------
    prob_df = pd.DataFrame({
        "Owner": owners,
        "Current": current_points.values,
        "Future": [owner_future[o] for o in owners]
    })

    prob_df["Projected"] = prob_df["Current"] + prob_df["Future"]

    total_proj = prob_df["Projected"].sum()

    prob_df["Win %"] = (prob_df["Projected"] / total_proj) * 100

    prob_df = prob_df.sort_values("Win %", ascending=False)

    return prob_df, explanations