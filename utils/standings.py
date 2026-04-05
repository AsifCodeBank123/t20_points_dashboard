import pandas as pd
from utils.calculator import calculate_points
from utils.helpers import build_watchlist
from utils.metrics import get_day_wise_gainers


def prepare_team_standings(df, cap_df, matches_df, selected_day, effective_day):

    # ----------------------------------------
    # BASE CALCULATION
    # ----------------------------------------
    scored_df = calculate_points(df, cap_df, effective_day)
    watch_map = build_watchlist(df, matches_df, cap_df, selected_day)

    team_df = (
        scored_df.groupby("owner_name")["player_points"]
        .sum().reset_index()
        .rename(columns={"owner_name": "Owner", "player_points": "Points"})
        .sort_values("Points", ascending=False)
    )

    team_df["Rank"] = range(1, len(team_df) + 1)
    team_df["Watchlist"] = team_df["Owner"].map(watch_map)

    # ----------------------------------------
    # MOVEMENT
    # ----------------------------------------
    if effective_day > 1:
        prev_df = calculate_points(df, cap_df, effective_day - 1)

        prev_team = (
            prev_df.groupby("owner_name")["player_points"]
            .sum().reset_index()
            .rename(columns={"owner_name": "Owner", "player_points": "Prev"})
        )

        prev_team["Prev Rank"] = prev_team["Prev"].rank(ascending=False)

        team_df = team_df.merge(prev_team, on="Owner", how="left")
        team_df["Movement"] = team_df["Prev Rank"] - team_df["Rank"]

    else:
        team_df["Movement"] = 0

    # ----------------------------------------
    # GAINERS
    # ----------------------------------------
    top_owners, top_owner, low_owner, max_points, min_points = get_day_wise_gainers(df, effective_day)

    # ----------------------------------------
    # MOVEMENT FORMAT
    # ----------------------------------------
    def format_movement(row):
        movement = row["Movement"]
        owner = row["Owner"]

        if movement > 0:
            text = f"▲ +{int(movement)}"
        elif movement < 0:
            text = f"▼ {int(movement)}"
        else:
            text = "— 0"

        if owner in top_owners:
            return f"{text} 🔥"

        return text

    team_df["Movement"] = team_df.apply(format_movement, axis=1)

    # ----------------------------------------
    # DELTAS
    # ----------------------------------------
    scores = team_df["Points"].values

    next_delta = [None] + [round(scores[i-1] - scores[i], 1) for i in range(1, len(scores))]
    first_delta = [None] + [round(scores[0] - s, 1) for s in scores[1:]]

    team_df["Next Rank"] = next_delta
    team_df["1st Rank"] = first_delta

    return team_df, scored_df, top_owner, low_owner, max_points, min_points