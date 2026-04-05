import streamlit as st
import plotly.express as px
import pandas as pd


def render_tab3(df, scored_df, team_df, selected_day):

    st.markdown("### 📊 Insights")

    # ----------------------------------------
    # PLAYER IMPACT SEGMENTATION
    # ----------------------------------------
    player_totals = (
        scored_df
        .groupby(["owner_name", "player_name"])["player_points"]
        .sum()
        .reset_index()
    )

    player_totals["category"] = player_totals["player_points"].apply(
        lambda x: "Dead (<10 points)" if x < 10 else "Active (≥10 points)"
    )

    stack_df = (
        player_totals
        .groupby(["owner_name", "category"])["player_name"]
        .count()
        .reset_index(name="count")
    )

    # ----------------------------------------
    # CHARTS
    # ----------------------------------------
    col1, col2 = st.columns(2)

    # Owner Points
    fig1 = px.bar(team_df, x="Owner", y="Points")
    fig1.update_layout(template="plotly_dark")
    col1.plotly_chart(fig1, use_container_width=True)

    # Franchise Contribution
    franchise_df = (
        scored_df
        .groupby("franchise")["player_points"]
        .sum()
        .reset_index()
    )

    fig2 = px.pie(franchise_df, names="franchise", values="player_points")
    fig2.update_layout(template="plotly_dark")
    col2.plotly_chart(fig2, use_container_width=True)

    # Squad Quality
    fig3 = px.bar(
        stack_df,
        x="owner_name",
        y="count",
        color="category",
        text_auto=True,
        barmode="stack",
        color_discrete_map={
            "Dead (<10 points)": "#ef4444",
            "Active (≥10 points)": "#22c55e"
        }
    )

    fig3.update_layout(
        template="plotly_dark",
        title="📊 Squad Quality (Dead vs Active Players)",
        xaxis_title="Owner",
        yaxis_title="No. of Players",
        legend_title=""
    )

    st.plotly_chart(fig3, use_container_width=True)