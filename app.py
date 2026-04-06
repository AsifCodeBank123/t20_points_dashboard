import streamlit as st
import pandas as pd

from utils.data_loader import load_data, load_matches, load_captains
from utils.standings import prepare_team_standings

from tabs.tab1_rankings import render_tab1
from tabs.tab2_players import render_tab2
from tabs.tab3_insights import render_tab3
from tabs.tab4_squad import render_tab4
from tabs.tab5_replacement import render_tab5
from tabs.tab6_match_points import render_tab6

# ----------------------------------------
# CONFIG
# ----------------------------------------
st.set_page_config(layout="wide", page_title="IPL Dashboard-Core Group")
TOTAL_MATCHES = 74

# ----------------------------------------
# LOAD CSS
# ----------------------------------------
with open("style/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ----------------------------------------
# LOAD DATA
# ----------------------------------------
df = load_data()
matches_df = load_matches()
cap_df = load_captains()

# ----------------------------------------
# DAYS
# ----------------------------------------
day_cols = [c for c in df.columns if c.startswith("day")]
day_numbers = sorted([int(c.replace("day","")) for c in day_cols])

selected_day = st.sidebar.selectbox(
    "📅 Select Day",
    day_numbers,
    index=len(day_numbers)-1
)

effective_day = max(selected_day - 1, 1)

# ----------------------------------------
# SIDEBAR
# ----------------------------------------

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

matches_left = TOTAL_MATCHES - selected_day + 1

st.sidebar.markdown(f"""
### 📌 Match Info
• Current Day: **{selected_day}**  
• Matches Left: **{matches_left}**
""")

st.sidebar.markdown("---")

st.sidebar.markdown("""
### 🧠 Rules
• Captain = 2×  
• Vice Captain = 1.5×  
• Max 2 changes allowed  
""")

st.sidebar.markdown("---")

st.sidebar.markdown("""
### 🔍 Tips
• Track captain impact  
• Focus on active franchises  
""")

team_df, scored_df, top_owner, low_owner, max_points, min_points = prepare_team_standings(
    df, cap_df, matches_df, selected_day, effective_day
)

# ----------------------------------------
# VISITOR COUNTER
# ----------------------------------------
st.markdown("""
<style>
.top-counter {
    display:flex;
    justify-content:flex-end;
    align-items:center;
    margin-top:-10px;
    margin-bottom:8px;
}

.top-counter img {
    height:24px;
}

/* Mobile */
@media (max-width:768px) {
    .top-counter {
        justify-content:center;
        margin-top:0px;
    }
}
</style>

<div class="top-counter">
    <img src="https://hitscounter.dev/api/hit?url=https%3A%2F%2Fipl-dashboard-fe.streamlit.app%2F&label=Visits&icon=github&color=%230d6efd&message=&style=plastic&tz=UTC">
</div>
""", unsafe_allow_html=True)

# ----------------------------------------
# HEADER
# ----------------------------------------
st.markdown(f"""
<div class="header">
    <div>
        <div class="title">🏏 IPL Fantasy Dashboard - Core Group</div>
        <div class="subtitle">Live standings till Day {selected_day - 1}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------
# PROGRESS BAR
# ----------------------------------------
matches_completed = max(selected_day - 1, 0)
progress = matches_completed / TOTAL_MATCHES
percent = int(progress * 100)

st.markdown(f"""
<div style="font-size:0.9rem;color:#94a3b8;margin-bottom:4px;margin-top:10px">
📊 Season Progress: <b>{matches_completed}</b> / {TOTAL_MATCHES} matches ({percent}%)
</div>
""", unsafe_allow_html=True)

st.progress(progress)

# ----------------------------------------
# KPI CARDS
# ----------------------------------------
k1, k2, k3, k4 = st.columns(4)

k1.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(148,163,184,0.12), rgba(100,116,139,0.05));
    padding:16px;
    border-radius:16px;
    border:1px solid rgba(148,163,184,0.2);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align:center;
">
    <div style="font-size:13px; color:#94a3b8; margin-bottom:6px;">
        📊 Teams
    </div>
    <div style="font-size:22px; font-weight:700;">
        {len(team_df)}
    </div>
</div>
""", unsafe_allow_html=True)


k2.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(251,191,36,0.18), rgba(245,158,11,0.08));
    padding:16px;
    border-radius:16px;
    border:1px solid rgba(251,191,36,0.3);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align:center;
">
    <div style="font-size:13px; color:#94a3b8; margin-bottom:6px;">
        🏆 Leader
    </div>
    <div style="font-size:22px; font-weight:700;">
        {team_df.iloc[0]['Owner']}
    </div>
</div>
""", unsafe_allow_html=True)

k3.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(16,185,129,0.08));
    padding:16px;
    border-radius:16px;
    border:1px solid rgba(34,197,94,0.25);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align:center;
">
    <div style="font-size:13px; color:#94a3b8; margin-bottom:6px;">
        🔥 Highest Gainer
    </div>
    <div style="font-size:22px; font-weight:700;">
        {top_owner}
    </div>
    <div style="font-size:13px; color:#22c55e;">
        {int(max_points)} pts
    </div>
</div>
""", unsafe_allow_html=True)


k4.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(37,99,235,0.08));
    padding:16px;
    border-radius:16px;
    border:1px solid rgba(59,130,246,0.25);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align:center;
">
    <div style="font-size:13px; color:#94a3b8; margin-bottom:6px;">
        🧊 Lowest Gainer
    </div>
    <div style="font-size:22px; font-weight:700;">
        {low_owner}
    </div>
    <div style="font-size:13px; color:#3b82f6;">
        {int(min_points)} pts
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ----------------------------------------
# TABS
# ----------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏆 Rankings",
    "👥 Players",
    "📊 Insights",
    "🎯 Squad Composition",
    "🤝 Replacement",
    "📅 Match Points"
])

# ----------------------------------------
# HELPER FUNCTION
# ----------------------------------------
def get_c_vc_points(owner, role="captain"):
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

# ----------------------------------------
# TAB RENDERING
# ----------------------------------------
with tab1:
    render_tab1(df, team_df, cap_df, selected_day, get_c_vc_points)

with tab2:
    render_tab2(df, scored_df, cap_df, selected_day)

with tab3:
    render_tab3(df, scored_df, team_df, selected_day)

with tab4:
    render_tab4(df, cap_df, selected_day)

with tab5:
    render_tab5(df, selected_day)

with tab6:
    render_tab6(df, matches_df, selected_day)

# ----------------------------------------
# FOOTER
# ----------------------------------------
st.markdown(
    "<div style='text-align:center;color:#94a3b8;margin-top:20px;'>Built for IPL 🚀</div>",
    unsafe_allow_html=True
)