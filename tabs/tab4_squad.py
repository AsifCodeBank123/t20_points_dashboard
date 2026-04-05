import streamlit as st
import plotly.express as px

def render_tab4(df, cap_df, selected_day):

    squad_df = df.groupby(["owner_name", "franchise"]).size().reset_index(name="player_count")

    fig = px.bar(
        squad_df,
        x="owner_name",
        y="player_count",
        color="franchise",
        text_auto=True
    )

    fig.update_layout(barmode="stack", template="plotly_dark")

    st.plotly_chart(fig, use_container_width=True)

