import pandas as pd

def get_day_wise_gainers(df, effective_day):

    day_col = f"day{effective_day}"

    # ❌ No column
    if day_col not in df.columns:
        return [], "—", "—", 0, 0

    # Aggregate
    day_points = (
        df.groupby("owner_name")[day_col]
        .sum()
        .reset_index()
    )

    # Clean values
    day_points[day_col] = pd.to_numeric(
        day_points[day_col],
        errors="coerce"
    ).fillna(0)

    max_points = day_points[day_col].max()
    min_points = day_points[day_col].min()

    # ✅ Fix: avoid all owners getting 🔥 when all are 0
    if max_points > 0:
        top_owners = day_points[
            day_points[day_col] == max_points
        ]["owner_name"].tolist()

        top_owner = day_points.loc[
            day_points[day_col].idxmax(),
            "owner_name"
        ]

        low_owner = day_points.loc[
            day_points[day_col].idxmin(),
            "owner_name"
        ]
    else:
        top_owners = []
        top_owner = "—"
        low_owner = "—"

    return top_owners, top_owner, low_owner, max_points, min_points