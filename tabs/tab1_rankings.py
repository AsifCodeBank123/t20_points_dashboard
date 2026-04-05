import streamlit as st
import pandas as pd

def render_tab1(df, team_df, cap_df, selected_day, get_c_vc_points):

    st.markdown(f"""
    <span style="color:#94a3b8;font-size:0.85rem;">
    ℹ️ Rankings & movement are based on completed matches. Watchlist shows upcoming players for Day {selected_day}.
    </span>
    """, unsafe_allow_html=True)

    st.markdown("### 🏆 Team Rankings")

    display_df = team_df[
        ["Rank", "Owner", "Points", "Movement", "Next Rank", "1st Rank", "Watchlist"]
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
            "1st Rank": "{:.1f}"
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
            "Cap Points": get_c_vc_points(owner, "captain"),
            "Vice Captain": vc_history,
            "VC Points": get_c_vc_points(owner, "vc"),
            "Changes": total_changes
        })

    cap_table = pd.DataFrame(rows)

    st.dataframe(
        cap_table,
        use_container_width=True,
        hide_index=True
    )