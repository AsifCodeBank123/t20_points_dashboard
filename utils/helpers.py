import pandas as pd

def build_watchlist(df, matches_df, cap_df, selected_day):

    rows = matches_df[matches_df["Day"] == selected_day]

    playing = set()

    for _, r in rows.iterrows():
        teams = [t.strip() for t in r["Teams"].split(",")]
        playing.update(teams)

    watch = {}

    for owner, grp in df.groupby("owner_name"):

        eligible = grp[
            (grp["franchise"].isin(playing)) &
            (grp["released_injured"].fillna("").str.upper() != "Y")
        ]

        owner_caps = cap_df[
            (cap_df["owner_name"] == owner) &
            (cap_df["from_day"] <= selected_day)
        ].sort_values("from_day")

        c = vc = None
        if not owner_caps.empty:
            last = owner_caps.iloc[-1]
            c = last["captain"]
            vc = last["vice_captain"]

        players = []
        for _, r in eligible.iterrows():
            name = r["player_name"]
            if name == c:
                name = f"🧢 {name}"
            elif name == vc:
                name = f"🎖️ {name}"
            players.append(name)

        watch[owner] = ", ".join(players) if players else "—"

    return watch

# ----------------------------------------
# HELPER FUNCTION
# ----------------------------------------
def get_c_vc_points(df,cap_df,owner,selected_day,role="captain"):

    oc = cap_df[cap_df["owner_name"] == owner].sort_values("from_day")
    if oc.empty:
        return "—"

    pts_list = []
    for d in range(1, selected_day + 1):
        day_col = f"day{d}"
        if day_col not in df.columns:
            continue

        cap_row = oc[oc["from_day"] <= d]
        if cap_row.empty:
            continue

        latest = cap_row.iloc[-1]
        player = latest["captain"] if role == "captain" else latest["vice_captain"]

        player_row = df[(df["owner_name"] == owner) & (df["player_name"] == player)]
        if player_row.empty:
            continue

        pts = pd.to_numeric(player_row.iloc[0].get(day_col, 0), errors="coerce")
        pts = 0 if pd.isna(pts) else pts

        mult = 2.0 if role == "captain" else 1.5
        val = round(pts * mult, 1)

        if val != 0:
            pts_list.append(val)

    return "—" if not pts_list else f"({', '.join(map(str, pts_list))})"

def get_current_c_vc(cap_df, owner, day):

    owner_changes = cap_df[
        (cap_df["owner_name"] == owner) &
        (cap_df["from_day"] <= day)
    ]

    if owner_changes.empty:
        return None, None

    latest = owner_changes.sort_values(
        "from_day"
    ).iloc[-1]

    return (
        latest["captain"],
        latest["vice_captain"]
    )