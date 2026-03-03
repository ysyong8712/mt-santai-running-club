"""
╔══════════════════════════════════════════╗
║   MT SANTAI RUNNING CLUB                ║
║   Powered by Strava API + Streamlit     ║
╚══════════════════════════════════════════╝

Setup:
  1. streamlit/secrets.toml:
       STRAVA_CLIENT_ID = "your_id"
       STRAVA_CLIENT_SECRET = "your_secret"
  2. pip install -r requirements.txt
  3. streamlit run app.py
"""

import time
import math
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

try:
    import folium
    from streamlit_folium import st_folium
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

from stravalib.client import Client

# ═══════════════════════════════════════════
#  APP CONFIG
# ═══════════════════════════════════════════
CLUB_NAME    = "MT Santai Running Club"
CLUB_EMOJI   = "🏔️"
ACCENT       = "#FF4D00"
GOLD         = "#FFD600"

st.set_page_config(
    page_title=f"{CLUB_NAME}",
    page_icon=CLUB_EMOJI,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════
#  CREDENTIALS  (from Streamlit Secrets)
# ═══════════════════════════════════════════
try:
    CLIENT_ID     = st.secrets["STRAVA_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
except Exception:
    CLIENT_ID     = ""
    CLIENT_SECRET = ""

# Auto-detect deployed URL vs localhost
try:
    REDIRECT_URI = st.secrets.get("REDIRECT_URI", "http://localhost:8501")
except Exception:
    REDIRECT_URI = "http://localhost:8501"

SCOPE = "read,activity:read_all,profile:read_all"

# ═══════════════════════════════════════════
#  CSS  — Trail / Forest Night aesthetic
#  Deep greens + burnt orange + cream
# ═══════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;700&display=swap');

:root {
    --orange:  #FF4D00;
    --dark:    #080E08;
    --card:    #101810;
    --muted:   #1E2A1E;
    --border:  #2A3D2A;
    --cream:   #F2EDD7;
    --green:   #3A6B35;
    --gold:    #FFD600;
    --blue:    #4FC3F7;
}

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background: var(--dark) !important;
    color: var(--cream) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #050C05 !important;
    border-right: 1px solid var(--border);
}

/* ── Typography ── */
h1 {
    font-family: 'Bebas Neue', sans-serif !important;
    color: var(--orange) !important;
    font-size: 3rem !important;
    letter-spacing: 2px !important;
    line-height: 1 !important;
}
h2 {
    font-family: 'Bebas Neue', sans-serif !important;
    color: var(--cream) !important;
    letter-spacing: 1px !important;
    font-size: 1.8rem !important;
}
h3 {
    font-family: 'DM Sans', sans-serif !important;
    color: #7A9E7A !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 3px !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 16px !important;
}
[data-testid="metric-container"] label {
    color: #5A7A5A !important;
    font-size: 0.68rem !important;
    text-transform: uppercase;
    letter-spacing: 2px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Bebas Neue', sans-serif !important;
    color: var(--orange) !important;
    font-size: 2.2rem !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    color: var(--gold) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--orange) !important;
    color: white !important;
    border: none !important;
    border-radius: 5px !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.05rem !important;
    letter-spacing: 1.5px !important;
    padding: 8px 20px !important;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background: #CC3D00 !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(255,77,0,0.3);
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--card) !important;
    border-radius: 8px 8px 0 0 !important;
    border-bottom: 2px solid var(--orange) !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #4A6A4A !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1rem !important;
    letter-spacing: 1.5px !important;
}
.stTabs [aria-selected="true"] {
    color: var(--orange) !important;
    background: transparent !important;
}

/* ── Cards ── */
.run-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-left: 4px solid var(--orange);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: transform 0.15s;
}
.run-card:hover { transform: translateX(3px); }

.stat-pill {
    display: inline-block;
    background: var(--muted);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.82rem;
    margin-right: 6px;
    margin-top: 4px;
    color: var(--cream);
}
.badge-me {
    display: inline-block;
    background: var(--gold);
    color: #000;
    border-radius: 4px;
    padding: 1px 8px;
    font-size: 0.72rem;
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 1px;
}
.badge-rank {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.4rem;
    min-width: 32px;
    display: inline-block;
    text-align: center;
}

/* ── Strava login button ── */
.strava-connect {
    display: inline-block;
    background: #FC4C02;
    color: white !important;
    text-decoration: none !important;
    padding: 14px 32px;
    border-radius: 8px;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.3rem;
    letter-spacing: 2px;
    transition: all 0.2s;
    box-shadow: 0 4px 20px rgba(252,76,2,0.4);
}
.strava-connect:hover {
    background: #D43E00;
    box-shadow: 0 6px 25px rgba(252,76,2,0.5);
}

/* ── Dividers ── */
hr { border-color: var(--border) !important; }

/* ── Input fields ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] > div > div {
    background: var(--card) !important;
    color: var(--cream) !important;
    border-color: var(--border) !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #080E08 0%, #0F1F0F 50%, #131A0A 100%);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 36px 40px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -30px; right: -30px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(255,77,0,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3.5rem;
    color: var(--orange);
    letter-spacing: 3px;
    line-height: 1;
    margin-bottom: 6px;
}
.hero-sub {
    color: #5A7A5A;
    font-size: 0.9rem;
    letter-spacing: 2px;
    text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════
def ss(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

ss("token_data", None)
ss("athlete",    None)
ss("activities", None)
ss("feed",       [])


# ═══════════════════════════════════════════
#  STRAVA HELPERS
# ═══════════════════════════════════════════
def get_auth_url():
    c = Client()
    return c.authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        approval_prompt="auto",
    )

def exchange_code(code: str) -> dict:
    c = Client()
    return c.exchange_code_for_token(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        code=code,
    )

def refresh_if_needed(td: dict) -> dict:
    if td.get("expires_at", 0) < time.time() + 60:
        c = Client()
        new = c.refresh_access_token(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            refresh_token=td["refresh_token"],
        )
        td.update(new)
        st.session_state.token_data = td
    return td

def get_client() -> Client:
    td = refresh_if_needed(st.session_state.token_data)
    return Client(access_token=td["access_token"])


# ═══════════════════════════════════════════
#  DATA FETCHING
# ═══════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def fetch_athlete(token: str) -> dict:
    c = Client(access_token=token)
    a = c.get_athlete()
    return {
        "id":        int(a.id),
        "name":      f"{a.firstname} {a.lastname}",
        "city":      getattr(a, "city", "") or "",
        "country":   getattr(a, "country", "") or "",
        "followers": a.follower_count or 0,
        "following": a.friend_count or 0,
        "photo":     str(a.profile_medium or a.profile or ""),
        "sex":       getattr(a, "sex", "") or "",
    }

@st.cache_data(ttl=300, show_spinner=False)
def fetch_activities(token: str, limit: int = 200) -> pd.DataFrame:
    c = Client(access_token=token)
    rows = []
    run_types = {"Run", "TrailRun", "VirtualRun"}
    for act in c.get_activities(limit=limit):
        if str(act.type) not in run_types:
            continue
        dist_km  = round(float(act.distance) / 1000, 2) if act.distance else 0
        dur_sec  = float(act.moving_time.total_seconds()) if act.moving_time else 0
        dur_min  = round(dur_sec / 60, 1)
        pace     = round(dur_sec / 60 / max(dist_km, 0.01), 2) if dist_km > 0 else 0
        rows.append({
            "id":           int(act.id),
            "name":         str(act.name),
            "type":         str(act.type),
            "date":         act.start_date_local,
            "distance_km":  dist_km,
            "duration_min": dur_min,
            "pace_min_km":  pace,
            "avg_hr":       float(act.average_heartrate) if act.average_heartrate else 0,
            "max_hr":       float(act.max_heartrate)     if act.max_heartrate else 0,
            "elevation_m":  float(act.total_elevation_gain) if act.total_elevation_gain else 0,
            "calories":     int(act.calories) if act.calories else 0,
            "kudos":        int(act.kudos_count) if act.kudos_count else 0,
            "suffer_score": int(act.suffer_score) if act.suffer_score else 0,
            "polyline":     (act.map.summary_polyline if act.map else None) or "",
            "start_lat":    float(act.start_latlng.lat) if act.start_latlng else None,
            "start_lng":    float(act.start_latlng.lng) if act.start_latlng else None,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df

def decode_polyline(s: str):
    """Decode Google encoded polyline string → list of (lat, lng)."""
    idx = lat = lng = 0
    coords = []
    while idx < len(s):
        for is_lng in (False, True):
            shift = result = 0
            while True:
                b = ord(s[idx]) - 63
                idx += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if is_lng: lng += delta
            else:      lat += delta
        coords.append((lat / 1e5, lng / 1e5))
    return coords


# ═══════════════════════════════════════════
#  PLOTLY DARK LAYOUT BASE
# ═══════════════════════════════════════════
def dark_layout(**extra):
    base = dict(
        paper_bgcolor="#101810",
        plot_bgcolor="#101810",
        font_color="#F2EDD7",
        title_font_color="#FF4D00",
        title_font_family="Bebas Neue",
        title_font_size=22,
        legend=dict(bgcolor="#080E08", bordercolor="#2A3D2A", borderwidth=1),
        xaxis=dict(gridcolor="#1E2A1E", zerolinecolor="#1E2A1E"),
        yaxis=dict(gridcolor="#1E2A1E", zerolinecolor="#1E2A1E"),
    )
    base.update(extra)
    return base


# ═══════════════════════════════════════════
#  OAUTH CALLBACK HANDLER
# ═══════════════════════════════════════════
params = st.query_params
if "code" in params and st.session_state.token_data is None:
    try:
        with st.spinner("正在连接 Strava…"):
            token = exchange_code(params["code"])
        st.session_state.token_data = token
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"授权失败：{e}")
        st.stop()


# ═══════════════════════════════════════════
#  LOGIN PAGE
# ═══════════════════════════════════════════
if st.session_state.token_data is None:
    _, mid, _ = st.columns([1, 2.2, 1])
    with mid:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
<div class="hero" style="text-align:center;">
    <div style="font-size:3.5rem;margin-bottom:8px;">{CLUB_EMOJI}</div>
    <div class="hero-title">{CLUB_NAME}</div>
    <div class="hero-sub">跑山 · 放松 · 同行</div>
</div>
""", unsafe_allow_html=True)

        if not CLIENT_ID or not CLIENT_SECRET:
            st.error("⚠️ 尚未配置 Strava API 凭证")
            st.markdown("""
**请在 Streamlit Cloud 的 Secrets 中添加：**
```toml
STRAVA_CLIENT_ID = "你的Client ID"
STRAVA_CLIENT_SECRET = "你的Client Secret"
REDIRECT_URI = "https://你的app地址.streamlit.app"
```
""")
        else:
            auth_url = get_auth_url()
            st.markdown(f"""
<div style="text-align:center; padding:20px 0;">
    <a href="{auth_url}" class="strava-connect">
        🔗 &nbsp;&nbsp;用 Strava 帐号登录
    </a>
    <p style="color:#3A5A3A; font-size:.8rem; margin-top:14px; letter-spacing:1px;">
        仅申请跑步数据读取权限 · 不会修改你的资料
    </p>
</div>
""", unsafe_allow_html=True)

        st.markdown("---")
        cols = st.columns(3)
        feats = [
            ("📊", "完整分析", "配速趋势、心率区间、月度里程"),
            ("🗺️", "路线地图", "GPS 轨迹可视化"),
            ("🏆", "跑友排行", "俱乐部成员实时对比"),
        ]
        for col, (icon, title, desc) in zip(cols, feats):
            col.markdown(f"""
<div style="text-align:center; padding:16px; background:#101810; border-radius:10px; border:1px solid #1E2A1E;">
    <div style="font-size:1.8rem;">{icon}</div>
    <div style="font-family:'Bebas Neue'; font-size:1.1rem; color:#FF4D00; letter-spacing:1px;">{title}</div>
    <div style="font-size:.78rem; color:#5A7A5A; margin-top:4px;">{desc}</div>
</div>
""", unsafe_allow_html=True)
    st.stop()


# ═══════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════
td = refresh_if_needed(st.session_state.token_data)

if st.session_state.athlete is None:
    with st.spinner("⏳ 正在同步你的 Strava 数据…"):
        st.session_state.athlete    = fetch_athlete(td["access_token"])
        st.session_state.activities = fetch_activities(td["access_token"])

athlete: dict         = st.session_state.athlete
df:      pd.DataFrame = st.session_state.activities


# ═══════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════
with st.sidebar:
    # Club logo area
    st.markdown(f"""
<div style="text-align:center; padding:16px 0 8px;">
    <div style="font-size:2.4rem;">{CLUB_EMOJI}</div>
    <div style="font-family:'Bebas Neue'; font-size:1.3rem; color:#FF4D00; letter-spacing:2px;">{CLUB_NAME}</div>
</div>
""", unsafe_allow_html=True)

    # Athlete profile
    if athlete.get("photo") and athlete["photo"].startswith("http"):
        st.image(athlete["photo"], width=56)
    st.markdown(f"""
<div style="margin-bottom:4px;">
    <span style="font-weight:700; font-size:1rem;">{athlete['name']}</span>
</div>
<div style="color:#5A7A5A; font-size:.78rem; letter-spacing:1px;">
    {'📍 ' + athlete['city'] + ', ' + athlete['country'] if athlete['city'] else ''}
</div>
<div style="color:#3A5A3A; font-size:.75rem; margin-top:2px;">
    👥 {athlete['followers']} followers
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio("", [
        "🏠  动态广场",
        "📊  我的分析",
        "🗺️  路线地图",
        "🏆  排行榜",
        "👥  跑友对比",
        "⚙️  设置",
    ], label_visibility="collapsed")

    st.markdown("---")

    # Quick stats
    if df is not None and not df.empty:
        now = datetime.now()
        this_month = df[df["date"].dt.month == now.month]
        prev_month = df[df["date"].dt.month == (now.month - 1 or 12)]
        st.markdown("### 本月概览")
        st.metric("里程",   f"{this_month['distance_km'].sum():.1f} km",
                  delta=f"{this_month['distance_km'].sum() - prev_month['distance_km'].sum():.1f} vs 上月")
        st.metric("跑步",   f"{len(this_month)} 次")
        st.metric("累计里程", f"{df['distance_km'].sum():.0f} km")

    st.markdown("---")
    rcol1, rcol2 = st.columns(2)
    with rcol1:
        if st.button("🔄 刷新"):
            fetch_activities.clear()
            fetch_athlete.clear()
            st.session_state.activities = fetch_activities(td["access_token"])
            st.session_state.athlete    = fetch_athlete(td["access_token"])
            st.rerun()
    with rcol2:
        if st.button("🚪 退出"):
            for k in ["token_data","athlete","activities"]:
                st.session_state[k] = None
            st.session_state.feed = []
            st.rerun()


# ═══════════════════════════════════════════════════════════
#  HELPER: no data guard
# ═══════════════════════════════════════════════════════════
def no_data():
    st.markdown("""
<div style="text-align:center; padding:60px; color:#3A5A3A;">
    <div style="font-size:3rem;">🏃</div>
    <div style="font-family:'Bebas Neue'; font-size:1.5rem; letter-spacing:2px; margin-top:8px;">
        暂无跑步记录
    </div>
    <div style="font-size:.85rem; margin-top:8px;">去跑一步，数据就会出现在这里！</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  PAGE: 动态广场
# ═══════════════════════════════════════════════════════════
if "动态广场" in page:
    st.markdown(f"""
<div class="hero">
    <div class="hero-title">{CLUB_EMOJI} {CLUB_NAME}</div>
    <div class="hero-sub">动态广场 — 分享每一次奔跑</div>
</div>
""", unsafe_allow_html=True)

    if df is not None and not df.empty:
        # Recent runs
        st.markdown("## 你的最近动态")
        recent = df.sort_values("date", ascending=False).head(5)
        for _, row in recent.iterrows():
            pace_str = f"{int(row['pace_min_km'])}'{int((row['pace_min_km']%1)*60)}\""
            st.markdown(f"""
<div class="run-card">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <span style="font-family:'Bebas Neue'; font-size:1.25rem; letter-spacing:1px; color:#F2EDD7;">
      {row['name']}
    </span>
    <span style="color:#3A5A3A; font-size:.8rem;">{row['date'].strftime('%Y-%m-%d  %H:%M')}</span>
  </div>
  <div style="margin-top:10px;">
    <span class="stat-pill">🏃 {row['distance_km']} km</span>
    <span class="stat-pill">⚡ {pace_str} /km</span>
    <span class="stat-pill">⏱ {int(row['duration_min'])} min</span>
    {'<span class="stat-pill">❤️ ' + str(int(row["avg_hr"])) + ' bpm</span>' if row['avg_hr'] > 0 else ''}
    {'<span class="stat-pill">🏔 ' + str(int(row["elevation_m"])) + ' m</span>' if row['elevation_m'] > 0 else ''}
    <span class="stat-pill">👍 {row['kudos']}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # Club feed
    st.markdown("## 跑友圈")
    txt_col, btn_col = st.columns([5, 1])
    with txt_col:
        new_post = st.text_input("", placeholder="分享跑步感受、路线推荐、活动通知…",
                                  label_visibility="collapsed")
    with btn_col:
        if st.button("发布 →"):
            if new_post.strip():
                st.session_state.feed.insert(0, {
                    "user": athlete["name"],
                    "text": new_post,
                    "likes": 0,
                    "time": datetime.now().strftime("%H:%M"),
                })
                st.rerun()

    if not st.session_state.feed:
        st.markdown("""
<div style="text-align:center; color:#3A5A3A; padding:30px; background:#101810;
     border:1px solid #1E2A1E; border-radius:10px;">
    跑友圈空空如也，来发第一条吧！🏃‍♂️
</div>
""", unsafe_allow_html=True)
    else:
        for i, post in enumerate(st.session_state.feed):
            st.markdown(f"""
<div class="run-card">
  <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
    <span style="font-weight:700;">{post['user']}</span>
    <span style="color:#3A5A3A; font-size:.78rem;">{post['time']}</span>
  </div>
  <div style="font-size:.95rem; color:#C8C3B0;">{post['text']}</div>
  <div style="margin-top:10px; color:#FF4D00; font-size:.85rem;">🔥 {post['likes']}</div>
</div>
""", unsafe_allow_html=True)
            if st.button("🔥 加油", key=f"like_{i}"):
                st.session_state.feed[i]["likes"] += 1
                st.rerun()


# ═══════════════════════════════════════════════════════════
#  PAGE: 我的分析
# ═══════════════════════════════════════════════════════════
elif "我的分析" in page:
    st.markdown("# 📊 我的跑步分析")

    if df is None or df.empty:
        no_data()
        st.stop()

    # ── KPI Row ──
    total_km  = df["distance_km"].sum()
    total_runs= len(df)
    best_pace = df[df["distance_km"] > 1]["pace_min_km"].min() if len(df) > 1 else 0
    avg_hr    = df[df["avg_hr"] > 0]["avg_hr"].mean()
    total_elev= df["elevation_m"].sum()
    longest   = df["distance_km"].max()

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("总里程",   f"{total_km:.0f} km")
    c2.metric("总次数",   f"{total_runs} 次")
    c3.metric("最长单跑", f"{longest:.1f} km")
    c4.metric("最快配速", f"{best_pace:.2f} /km")
    c5.metric("平均心率", f"{avg_hr:.0f} bpm" if avg_hr else "—")
    c6.metric("累计爬升", f"{total_elev:.0f} m")

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 月度趋势", "⚡ 配速分析", "❤️ 心率区间", "🏔 爬升统计", "📋 完整记录"
    ])

    # ── Tab 1: Monthly ──
    with tab1:
        monthly = (df.set_index("date")
                     .resample("ME")["distance_km"]
                     .sum()
                     .reset_index())
        monthly["month"] = monthly["date"].dt.strftime("%Y-%m")
        monthly["累计"]  = monthly["distance_km"].cumsum()

        fig = go.Figure()
        fig.add_bar(x=monthly["month"], y=monthly["distance_km"],
                    name="月里程", marker_color="#FF4D00",
                    opacity=0.85, marker_line_width=0)
        fig.add_scatter(x=monthly["month"], y=monthly["累计"],
                        name="累计里程", line_color="#FFD600",
                        line_width=2, yaxis="y2",
                        mode="lines+markers", marker_size=6)
        fig.update_layout(
            **dark_layout(title="月度里程统计"),
            yaxis=dict(title="当月里程 (km)", gridcolor="#1E2A1E"),
            yaxis2=dict(title="累计里程 (km)", overlaying="y", side="right",
                        gridcolor="rgba(0,0,0,0)"),
            legend=dict(bgcolor="#080E08", bordercolor="#2A3D2A"),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Weekly run heatmap
        df["_week"]    = df["date"].dt.isocalendar().week.astype(int)
        df["_weekday"] = df["date"].dt.day_name()
        day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        day_cn    = {"Monday":"一","Tuesday":"二","Wednesday":"三",
                     "Thursday":"四","Friday":"五","Saturday":"六","Sunday":"日"}
        df["_weekday_cn"] = df["_weekday"].map(day_cn)
        heat = df.groupby(["_week","_weekday_cn"])["distance_km"].sum().reset_index()
        cn_order = [day_cn[d] for d in day_order]
        fig2 = px.density_heatmap(
            heat, x="_week", y="_weekday_cn",
            z="distance_km",
            category_orders={"_weekday_cn": cn_order},
            color_continuous_scale=[[0,"#0C1A0C"],[0.3,"#1E4D1E"],[0.7,"#FF4D00"],[1,"#FFD600"]],
            labels={"_week":"周次","_weekday_cn":"星期","distance_km":"里程(km)"},
            title="训练热力日历",
        )
        fig2.update_layout(**dark_layout())
        st.plotly_chart(fig2, use_container_width=True)

    # ── Tab 2: Pace ──
    with tab2:
        sub = df[df["distance_km"] > 1].copy().sort_values("date")
        sub["month_label"] = sub["date"].dt.strftime("%Y-%m")

        fig = px.scatter(
            sub, x="distance_km", y="pace_min_km",
            size="duration_min", color="avg_hr",
            color_continuous_scale=[[0,"#1E4D1E"],[0.5,"#FF4D00"],[1,"#FFD600"]],
            hover_data=["name","date","elevation_m"],
            labels={"distance_km":"距离 (km)","pace_min_km":"配速 (min/km)","avg_hr":"心率"},
            title="距离 vs 配速  （点大小 = 时长，颜色 = 心率）",
        )
        fig.update_layout(**dark_layout())
        st.plotly_chart(fig, use_container_width=True)

        # Rolling avg pace trend
        sub["pace_roll7"] = sub["pace_min_km"].rolling(7, min_periods=1).mean()
        fig2 = go.Figure()
        fig2.add_scatter(x=sub["date"], y=sub["pace_min_km"],
                         mode="markers", name="每次配速",
                         marker=dict(color="#2A3D2A", size=5))
        fig2.add_scatter(x=sub["date"], y=sub["pace_roll7"],
                         mode="lines", name="7次滑动均值",
                         line=dict(color="#FF4D00", width=2.5))
        fig2.update_layout(**dark_layout(title="配速进步趋势"),
                           yaxis=dict(title="配速 (min/km)", autorange="reversed",
                                      gridcolor="#1E2A1E"))
        st.plotly_chart(fig2, use_container_width=True)

        # Personal bests
        st.markdown("### 个人最佳")
        distances = [5, 10, 21.1, 42.2]
        pb_cols = st.columns(4)
        for col, d in zip(pb_cols, distances):
            filt = df[(df["distance_km"] >= d * 0.95) &
                      (df["distance_km"] <= d * 1.05)]
            if not filt.empty:
                best = filt.loc[filt["pace_min_km"].idxmin()]
                pace_fmt = f"{int(best['pace_min_km'])}'{int((best['pace_min_km']%1)*60)}\""
                col.metric(f"最快{d}km", pace_fmt,
                           delta=best["date"].strftime("%Y-%m-%d"))
            else:
                col.metric(f"最快{d}km", "—")

    # ── Tab 3: Heart Rate ──
    with tab3:
        hr_df = df[df["avg_hr"] > 0].copy()
        if hr_df.empty:
            st.info("暂无心率数据（需要佩戴心率带）")
        else:
            def hr_zone(hr):
                if   hr < 115: return "Z1 热身"
                elif hr < 133: return "Z2 有氧基础"
                elif hr < 152: return "Z3 有氧强化"
                elif hr < 171: return "Z4 乳酸阈"
                else:          return "Z5 最大强度"

            hr_df["zone"] = hr_df["avg_hr"].apply(hr_zone)
            zone_colors = {
                "Z1 热身":    "#4FC3F7",
                "Z2 有氧基础":"#66BB6A",
                "Z3 有氧强化":"#FFD600",
                "Z4 乳酸阈":  "#FF7733",
                "Z5 最大强度":"#FF4D00",
            }

            zcol1, zcol2 = st.columns(2)
            with zcol1:
                zone_count = hr_df["zone"].value_counts().reset_index()
                zone_count.columns = ["zone","count"]
                fig = px.pie(zone_count, values="count", names="zone",
                             color="zone", color_discrete_map=zone_colors,
                             title="心率区间分布", hole=0.45)
                fig.update_layout(**dark_layout())
                st.plotly_chart(fig, use_container_width=True)

            with zcol2:
                fig2 = px.box(hr_df, x="zone", y="avg_hr",
                              color="zone", color_discrete_map=zone_colors,
                              category_orders={"zone": list(zone_colors.keys())},
                              labels={"zone":"区间","avg_hr":"心率 (bpm)"},
                              title="各区间心率分布")
                fig2.update_layout(**dark_layout(), showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

            # HR vs pace
            fig3 = px.scatter(hr_df, x="pace_min_km", y="avg_hr",
                              color="zone", color_discrete_map=zone_colors,
                              size="distance_km",
                              labels={"pace_min_km":"配速","avg_hr":"心率","distance_km":"距离"},
                              title="配速 vs 心率（有氧效率分析）")
            fig3.update_layout(**dark_layout())
            st.plotly_chart(fig3, use_container_width=True)

    # ── Tab 4: Elevation ──
    with tab4:
        elev_df = df[df["elevation_m"] > 5].copy()
        if elev_df.empty:
            st.info("暂无显著爬升数据")
        else:
            elev_df["elev_per_km"] = (elev_df["elevation_m"] /
                                      elev_df["distance_km"].clip(lower=0.1))
            elev_sorted = elev_df.sort_values("elevation_m", ascending=False).head(20)

            fig = px.bar(
                elev_sorted.sort_values("date"),
                x="date", y="elevation_m",
                color="elev_per_km",
                color_continuous_scale=[[0,"#1E4D1E"],[0.5,"#FF7733"],[1,"#FFD600"]],
                hover_data=["name","distance_km"],
                labels={"date":"日期","elevation_m":"爬升(m)","elev_per_km":"爬升率(m/km)"},
                title="每次爬升量（Top 20）",
            )
            fig.update_layout(**dark_layout())
            st.plotly_chart(fig, use_container_width=True)

            ec1, ec2 = st.columns(2)
            ec1.metric("最大单跑爬升", f"{elev_df['elevation_m'].max():.0f} m")
            ec2.metric("累计总爬升",   f"{elev_df['elevation_m'].sum():.0f} m")

    # ── Tab 5: Full log ──
    with tab5:
        cols_show = ["date","name","distance_km","pace_min_km",
                     "duration_min","avg_hr","elevation_m","calories","kudos"]
        display = df.sort_values("date", ascending=False)[cols_show].copy()
        display["date"] = display["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "date":         st.column_config.TextColumn("日期"),
                "name":         st.column_config.TextColumn("活动"),
                "distance_km":  st.column_config.NumberColumn("距离(km)",   format="%.2f"),
                "pace_min_km":  st.column_config.NumberColumn("配速(min/km)",format="%.2f"),
                "duration_min": st.column_config.NumberColumn("时长(min)",  format="%.0f"),
                "avg_hr":       st.column_config.NumberColumn("心率",        format="%.0f"),
                "elevation_m":  st.column_config.NumberColumn("爬升(m)",    format="%.0f"),
                "calories":     st.column_config.NumberColumn("卡路里"),
                "kudos":        st.column_config.NumberColumn("👍"),
            },
        )
        csv_bytes = df[cols_show].to_csv(index=False).encode()
        st.download_button("⬇️ 下载 CSV", csv_bytes, "mt_santai_runs.csv", "text/csv")


# ═══════════════════════════════════════════════════════════
#  PAGE: 路线地图
# ═══════════════════════════════════════════════════════════
elif "路线地图" in page:
    st.markdown("# 🗺️ 路线地图")

    if df is None or df.empty:
        no_data()
        st.stop()

    poly_df = df[df["polyline"].str.len() > 10].copy()

    if poly_df.empty:
        st.warning("暂无 GPS 路线数据（活动可能设为私密，或未开 GPS 记录）")
        st.stop()

    if not HAS_FOLIUM:
        st.error("请安装：`pip install folium streamlit-folium`")
        st.stop()

    # Controls
    ctrl1, ctrl2, ctrl3 = st.columns(3)
    with ctrl1:
        n_show = st.slider("显示最近几条路线", 1, min(50, len(poly_df)),
                           min(15, len(poly_df)))
    with ctrl2:
        run_type_filter = st.multiselect("活动类型", poly_df["type"].unique().tolist(),
                                          default=poly_df["type"].unique().tolist())
    with ctrl3:
        map_style = st.selectbox("地图风格", ["深色(推荐)","卫星","街道"])

    tiles_map = {
        "深色(推荐)": "CartoDB dark_matter",
        "卫星":       "Esri.WorldImagery",
        "街道":       "OpenStreetMap",
    }
    tile = tiles_map[map_style]

    filtered_poly = poly_df[poly_df["type"].isin(run_type_filter)].sort_values("date", ascending=False).head(n_show)

    center_lat = filtered_poly["start_lat"].dropna().mean()
    center_lng = filtered_poly["start_lng"].dropna().mean()
    if math.isnan(center_lat): center_lat, center_lng = 3.1, 101.7  # Malaysia default

    m = folium.Map(location=[center_lat, center_lng], zoom_start=12, tiles=tile)

    ROUTE_COLORS = ["#FF4D00","#FFD600","#4FC3F7","#66BB6A",
                    "#FF6AB2","#CE93D8","#FF8A65","#80DEEA"]

    for i, (_, row) in enumerate(filtered_poly.iterrows()):
        if not row["polyline"]:
            continue
        coords = decode_polyline(row["polyline"])
        if not coords:
            continue
        color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
        pace_str = f"{int(row['pace_min_km'])}'{int((row['pace_min_km']%1)*60)}\""
        tooltip_html = (
            f"<b>{row['name']}</b><br>"
            f"{row['date'].strftime('%Y-%m-%d')}<br>"
            f"📏 {row['distance_km']} km &nbsp; ⚡ {pace_str}"
        )
        folium.PolyLine(
            coords, color=color, weight=3.5, opacity=0.85,
            tooltip=folium.Tooltip(tooltip_html)
        ).add_to(m)
        folium.CircleMarker(
            coords[0], radius=5, color=color, fill=True,
            fill_opacity=1.0, tooltip="起点"
        ).add_to(m)

    st_folium(m, use_container_width=True, height=520)

    # Activity selector
    st.markdown("---")
    st.markdown("### 查看单条路线详情")
    act_labels = (filtered_poly["name"] + "  " +
                  filtered_poly["date"].dt.strftime("(%Y-%m-%d)")).values
    chosen = st.selectbox("选择活动", act_labels)
    mask = (filtered_poly["name"] + "  " +
            filtered_poly["date"].dt.strftime("(%Y-%m-%d)")) == chosen
    sel_rows = filtered_poly[mask]
    if not sel_rows.empty:
        r = sel_rows.iloc[0]
        d1,d2,d3,d4,d5 = st.columns(5)
        d1.metric("距离",   f"{r['distance_km']} km")
        d2.metric("时长",   f"{int(r['duration_min'])} min")
        d3.metric("配速",   f"{r['pace_min_km']} min/km")
        d4.metric("爬升",   f"{int(r['elevation_m'])} m")
        d5.metric("心率",   f"{int(r['avg_hr'])} bpm" if r['avg_hr'] else "—")


# ═══════════════════════════════════════════════════════════
#  PAGE: 排行榜
# ═══════════════════════════════════════════════════════════
elif "排行榜" in page:
    st.markdown("# 🏆 俱乐部排行榜")

    if df is None or df.empty:
        no_data()
        st.stop()

    f1, f2 = st.columns(2)
    with f1:
        period = st.selectbox("时间段", ["本月","本季度","本年","全部"])
    with f2:
        metric_opt = st.selectbox("排名指标", [
            "总里程", "跑步次数", "最长单跑", "平均配速（越低越好）",
            "最大爬升", "总消耗卡路里"
        ])

    now = datetime.now()
    filt = df.copy()
    if period == "本月":
        filt = filt[filt["date"].dt.month == now.month]
    elif period == "本季度":
        q = (now.month - 1) // 3
        q_start = now.replace(month=q*3+1, day=1)
        filt = filt[filt["date"] >= pd.Timestamp(q_start)]
    elif period == "本年":
        filt = filt[filt["date"].dt.year == now.year]

    sort_map = {
        "总里程":             ("distance_km", "sum",  False, "km"),
        "跑步次数":           ("distance_km", "count",False, "次"),
        "最长单跑":           ("distance_km", "max",  False, "km"),
        "平均配速（越低越好）":("pace_min_km", "mean", True,  "min/km"),
        "最大爬升":           ("elevation_m", "max",  False, "m"),
        "总消耗卡路里":        ("calories",    "sum",  False, "kcal"),
    }
    col, agg, asc, unit = sort_map[metric_opt]

    # Build leaderboard (you + any future club members)
    if not filt.empty:
        if agg == "sum":   val = round(filt[col].sum(), 1)
        elif agg == "max": val = round(filt[col].max(), 1)
        elif agg == "mean":val = round(filt[filt["distance_km"]>1][col].mean(), 2)
        else:              val = len(filt)

        lb_data = [{"名字": athlete["name"], "数值": val, "是我": True}]
    else:
        lb_data = []

    lb = pd.DataFrame(lb_data).sort_values("数值", ascending=asc).reset_index(drop=True)
    medals = ["🥇","🥈","🥉"] + ["  "]*50

    for i, row in lb.iterrows():
        hi = "border-left:4px solid #FFD600; background:#121C12;" if row["是我"] else ""
        me = "<span class='badge-me'>我</span>" if row["是我"] else ""
        st.markdown(f"""
<div class="run-card" style="{hi}">
  <span class="badge-rank">{medals[i]}</span>
  <span style="font-size:1rem; font-weight:700; margin:0 10px;">{row['名字']}</span>
  {me}
  <span style="font-family:'Bebas Neue'; font-size:1.4rem; color:#FF4D00; margin-left:16px;">
    {row['数值']} {unit}
  </span>
</div>
""", unsafe_allow_html=True)

    if not lb.empty:
        fig = px.bar(lb, x="名字", y="数值",
                     color="是我",
                     color_discrete_map={True: "#FFD600", False: "#FF4D00"},
                     labels={"名字":"","数值": f"{metric_opt} ({unit})"},
                     title=f"{period}  ·  {metric_opt}")
        fig.update_layout(**dark_layout(), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.info("""
💡 **如何加入俱乐部排行榜？**

邀请队友登录此平台后，系统会自动显示每个人的数据对比。
部署到 Streamlit Cloud 后将 App 链接分享给队友即可！
""")


# ═══════════════════════════════════════════════════════════
#  PAGE: 跑友对比
# ═══════════════════════════════════════════════════════════
elif "跑友对比" in page:
    st.markdown("# 👥 跑友对比")

    if df is None or df.empty:
        no_data()
        st.stop()

    st.info("""
**当前显示你自己的数据分析。**
邀请队友通过 Strava 登录后，他们的数据会自动出现在这里进行对比。

目前你可以对比自己不同时期的表现 👇
""")

    # Self comparison: compare two date ranges
    st.markdown("## 自我对比 — 不同时期表现")

    if not df.empty:
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        mid_date = min_date + (max_date - min_date) // 2

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### 时期 A")
            a_start = st.date_input("开始", min_date, key="a_start")
            a_end   = st.date_input("结束", mid_date, key="a_end")
        with col_b:
            st.markdown("#### 时期 B")
            b_start = st.date_input("开始", mid_date, key="b_start")
            b_end   = st.date_input("结束", max_date, key="b_end")

        period_a = df[(df["date"].dt.date >= a_start) & (df["date"].dt.date <= a_end)]
        period_b = df[(df["date"].dt.date >= b_start) & (df["date"].dt.date <= b_end)]

        if not period_a.empty and not period_b.empty:
            # Radar
            metrics_r = ["distance_km","pace_min_km","avg_hr","elevation_m","duration_min"]
            labels_r  = ["平均里程","配速(反转)","心率","爬升","时长"]

            def normalize_for_radar(pa, pb):
                data = []
                for seg, label in [(pa, f"时期 A"), (pb, f"时期 B")]:
                    row = []
                    for col in metrics_r:
                        all_vals = pd.concat([pa[col], pb[col]])
                        val = seg[col].mean()
                        mn, mx = all_vals.min(), all_vals.max()
                        n = (val - mn) / (mx - mn + 1e-9)
                        if col == "pace_min_km":
                            n = 1 - n
                        row.append(round(n, 3))
                    data.append((label, row))
                return data

            radar_data = normalize_for_radar(period_a, period_b)
            fig = go.Figure()
            for label, vals in radar_data:
                color = "#FF4D00" if "A" in label else "#FFD600"
                fig.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]],
                    theta=labels_r + [labels_r[0]],
                    fill="toself", name=label,
                    line_color=color, fillcolor=color, opacity=0.2,
                ))
            fig.update_layout(
                polar=dict(bgcolor="#101810",
                           radialaxis=dict(visible=True, range=[0,1], color="#3A5A3A")),
                **dark_layout(title="两时期综合对比雷达图"),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Comparison table
            comp_df = pd.DataFrame({
                "指标":     ["跑步次数","平均里程(km)","最快配速","平均心率","总爬升(m)"],
                "时期 A":   [
                    len(period_a),
                    round(period_a["distance_km"].mean(),2),
                    f"{period_a[period_a['distance_km']>1]['pace_min_km'].min():.2f}",
                    f"{period_a[period_a['avg_hr']>0]['avg_hr'].mean():.0f}" if period_a['avg_hr'].sum()>0 else "—",
                    f"{period_a['elevation_m'].sum():.0f}",
                ],
                "时期 B":   [
                    len(period_b),
                    round(period_b["distance_km"].mean(),2),
                    f"{period_b[period_b['distance_km']>1]['pace_min_km'].min():.2f}",
                    f"{period_b[period_b['avg_hr']>0]['avg_hr'].mean():.0f}" if period_b['avg_hr'].sum()>0 else "—",
                    f"{period_b['elevation_m'].sum():.0f}",
                ],
            })
            st.dataframe(comp_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
#  PAGE: 设置
# ═══════════════════════════════════════════════════════════
elif "设置" in page:
    st.markdown("# ⚙️ 设置与帮助")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🚀 部署指南", "👥 邀请队友", "🔒 隐私说明"])

    with tab1:
        st.markdown("## Streamlit Cloud 免费部署")
        st.markdown("""
**第一步：上传代码到 GitHub**
```bash
git init
git add .
git commit -m "MT Santai Running Club init"
git remote add origin https://github.com/你的用户名/mt-santai-running-club.git
git push -u origin main
```

**第二步：在 Streamlit Cloud 部署**
1. 前往 [share.streamlit.io](https://share.streamlit.io)
2. 连接你的 GitHub
3. 选择仓库 `mt-santai-running-club`，Main file: `app.py`
4. 点击 **Deploy**

**第三步：配置 Strava Secrets**

在 Streamlit Cloud 的 App Settings → Secrets 中填入：
```toml
STRAVA_CLIENT_ID = "你的Client ID"
STRAVA_CLIENT_SECRET = "你的Client Secret"
REDIRECT_URI = "https://你的app名称.streamlit.app"
```

**第四步：更新 Strava App 回调地址**

回到 [strava.com/settings/api](https://www.strava.com/settings/api)，
把 **Authorization Callback Domain** 改为 `你的app名称.streamlit.app`
""")

    with tab2:
        st.markdown("## 邀请 MT Santai 队友")
        st.markdown("""
**分享方式：**

把部署好的 Streamlit Cloud 链接发给队友：
```
https://你的app名称.streamlit.app
```

**队友操作：**
1. 打开链接
2. 点击「用 Strava 帐号登录」
3. 授权后即可查看自己的数据

**注意事项：**
- 每位队友需要有 Strava 帐号
- 排行榜多人对比需要后端数据库支持
  （可以升级为 Supabase，完全免费）
""")

        if athlete:
            st.markdown("---")
            st.markdown("### 你的 Strava 帐号信息")
            info_col1, info_col2 = st.columns(2)
            info_col1.markdown(f"**姓名：** {athlete['name']}")
            info_col1.markdown(f"**城市：** {athlete.get('city','—')}")
            info_col2.markdown(f"**关注者：** {athlete['followers']}")
            info_col2.markdown(f"**关注中：** {athlete['following']}")

    with tab3:
        st.markdown("## 数据隐私说明")
        st.markdown("""
- ✅ 只申请 **只读权限**，不会修改或删除你的 Strava 数据
- ✅ Token 仅存在当前浏览器 Session，关闭即失效
- ✅ 不收集、不存储任何个人数据到第三方服务器
- ✅ 所有数据处理在你的浏览器内完成

**撤销授权方法：**
Strava → 设置 → 我的应用 → 找到 MT Santai Running Club → 撤销访问
""")

    st.markdown("---")
    st.markdown("### 数据导出")
    if df is not None and not df.empty:
        csv = df.to_csv(index=False).encode()
        st.download_button("⬇️ 导出所有跑步数据 (CSV)",
                           csv, "mt_santai_all_runs.csv", "text/csv")
    st.markdown(f"""
---
<div style="text-align:center; color:#3A5A3A; font-size:.8rem; padding:16px;">
    {CLUB_EMOJI} {CLUB_NAME} &nbsp;·&nbsp; Powered by Strava API + Streamlit
</div>
""", unsafe_allow_html=True)
