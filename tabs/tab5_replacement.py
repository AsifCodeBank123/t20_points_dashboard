import streamlit as st
import pandas as pd

def render_tab5(df, selected_day):

    st.subheader("🔁 Player Replacement")

    # -------------------------------
    # 🔹 Dynamic Day Columns
    # -------------------------------
    import re

    day_cols = sorted(
        [col for col in df.columns if col.startswith("day")],
        key=lambda x: int(re.findall(r'\d+', x)[0])
    )

    df[day_cols] = df[day_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["total_points"] = df[day_cols].sum(axis=1)

    # -------------------------------
    # 🔹 Owner Selection
    # -------------------------------
    owners = sorted(df["owner_name"].unique())

    selected_owner = st.selectbox(
        "Select Owner",
        owners,
        key="tab5_owner"
    )

    # -------------------------------
    # 🔹 Player Selection
    # -------------------------------
    owner_players = df[df["owner_name"] == selected_owner]

    selected_player = st.selectbox(
        "Select Player to Replace",
        owner_players["player_name"],
        key="tab5_player"
    )

    # -------------------------------
    # 🔹 Selected Player Details
    # -------------------------------
    player_data = owner_players[
        owner_players["player_name"] == selected_player
    ].iloc[0]

    bid_price = player_data["bid_price"]
    player_points = player_data["total_points"]

    st.markdown(f"""
    **Selected Player:** {selected_player}  
    💰 Price: {bid_price}  
    📊 Total Points: {player_points}
    """)

    # -------------------------------
    # 🔹 Eligibility Check
    # -------------------------------
    if bid_price < 350:
        st.error("❌ Not eligible for replacement (Price < $350)")
        eligible_players = None
    else:
        st.success("✅ Eligible for replacement")

        # Show allowed price range
        st.caption(f"Allowed price: ≤ {int(bid_price + 50)}")

        # -------------------------------
        # 🔹 Eligible Players Filter
        # -------------------------------
        eligible_players = df[
            (df["player_name"] != selected_player) &
            (df["owner_name"] != selected_owner) &
            (df["bid_price"] <= bid_price + 50) &          # ✅ upper limit only
            (df["total_points"] <= player_points + 50)     # ✅ upper limit only
        ].copy()

    # -------------------------------
    # 🔹 Display Results
    # -------------------------------
    if eligible_players is not None:

        if eligible_players.empty:
            st.warning("No eligible replacement players found.")
        else:
            eligible_players = eligible_players[
                ["player_name", "owner_name", "bid_price", "total_points"]
            ].sort_values(by="total_points", ascending=False)

            # Add point difference
            eligible_players["point_diff"] = (
                eligible_players["total_points"] - player_points
            )

            # Highlight better players
            def highlight(row):
                if row["point_diff"] > 0:
                    return ["background-color: rgba(34,197,94,0.2)"] * len(row)
                return [""] * len(row)

            # ✅ Apply format (NO decimals)
            st.dataframe(
                eligible_players.style
                    .format({
                        "bid_price": "{:.0f}",
                        "total_points": "{:.0f}",
                        "point_diff": "{:.0f}"
                    })
                    .apply(highlight, axis=1),
                use_container_width=True,
                hide_index=True
            )

        # -------------------------------
        # 🔹 Divider
        # -------------------------------
        st.markdown("---")

        # -------------------------------
        # 🔹 Rules
        # -------------------------------
        st.info("""
        📌 **Replacement Rules**

        1. Player price must be ≥ $350  
        2. The replacement player should be priced at most at $50 higher than the ruled out player
        3. The replacement players fantasy XI points should be equal to or max 50 points higher the ruled out player 
        4. Points count from next match only  
        5. If player is already C/VC in another team, cannot assign C/VC again  
        """)