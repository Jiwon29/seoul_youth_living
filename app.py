import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px
import json

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="서울 1인가구 주거환경 대시보드",
    page_icon="🏙️",
    layout="wide",
)

# ─────────────────────────────────────────────
# 커스텀 CSS (초록 계열 테마)
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }

    /* 배경 */
    .stApp {
        background: linear-gradient(135deg, #f0faf4 0%, #e8f5e9 100%);
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 60%, #388e3c 100%);
    }
    section[data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] p {
        color: #c8e6c9 !important;
        font-size: 0.9rem;
    }

    /* 헤더 */
    .dashboard-header {
        background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 50%, #43a047 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(27,94,32,0.25);
    }
    .dashboard-title {
        font-size: 1.75rem;
        font-weight: 900;
        color: #ffffff;
        line-height: 1.3;
        margin: 0;
    }
    .dashboard-subtitle {
        font-size: 0.95rem;
        color: #a5d6a7;
        margin-top: 0.4rem;
    }

    /* 카드 */
    .metric-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 4px 16px rgba(46,125,50,0.10);
        border-left: 5px solid #43a047;
        margin-bottom: 0.8rem;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #66bb6a;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 900;
        color: #1b5e20;
        line-height: 1.1;
    }
    .metric-unit {
        font-size: 0.85rem;
        color: #81c784;
        font-weight: 400;
    }

    /* 섹션 타이틀 */
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1b5e20;
        border-left: 4px solid #43a047;
        padding-left: 0.7rem;
        margin: 1.2rem 0 0.8rem 0;
    }

    /* 차트 컨테이너 */
    .chart-container {
        background: #ffffff;
        border-radius: 14px;
        padding: 1rem;
        box-shadow: 0 4px 16px rgba(46,125,50,0.08);
        margin-bottom: 1rem;
    }

    /* 구분선 */
    hr { border-color: #c8e6c9; }

    /* Top5 배지 */
    .top5-badge {
        display: inline-block;
        background: linear-gradient(135deg, #43a047, #66bb6a);
        color: white;
        border-radius: 20px;
        padding: 0.2rem 0.8rem;
        font-size: 0.78rem;
        font-weight: 700;
        margin-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    conn = sqlite3.connect("seoul_youth.db")

    score_df = pd.read_sql("SELECT * FROM score ORDER BY 총점 DESC", conn)

    safety_df = pd.read_sql("""
        SELECT 시설명, 시설유형, 자치구명, 위도, 경도
        FROM safety
        WHERE 위도 IS NOT NULL AND 경도 IS NOT NULL
    """, conn)

    conv_df = pd.read_sql("""
        SELECT 시설명, 시설유형, 자치구명, 위도, 경도
        FROM convenience
        WHERE 위도 IS NOT NULL AND 경도 IS NOT NULL
    """, conn)

    rent_df = pd.read_sql("""
        SELECT 자치구명, ROUND(AVG(임대료),1) AS 평균월세
        FROM monthly_rent
        WHERE 임대료 > 0
        GROUP BY 자치구명
    """, conn)

    conn.close()
    return score_df, safety_df, conv_df, rent_df

score_df, safety_df, conv_df, rent_df = load_data()

# 서울 25개 구 중심 좌표
GU_CENTERS = {
    "강남구": [37.5172, 127.0473], "강동구": [37.5301, 127.1238],
    "강북구": [37.6396, 127.0257], "강서구": [37.5509, 126.8495],
    "관악구": [37.4784, 126.9516], "광진구": [37.5384, 127.0822],
    "구로구": [37.4954, 126.8874], "금천구": [37.4519, 126.9017],
    "노원구": [37.6542, 127.0568], "도봉구": [37.6688, 127.0471],
    "동대문구": [37.5744, 127.0397], "동작구": [37.5124, 126.9393],
    "마포구": [37.5638, 126.9084], "서대문구": [37.5791, 126.9368],
    "서초구": [37.4837, 127.0324], "성동구": [37.5634, 127.0369],
    "성북구": [37.5894, 127.0167], "송파구": [37.5145, 127.1050],
    "양천구": [37.5270, 126.8561], "영등포구": [37.5264, 126.8962],
    "용산구": [37.5324, 126.9901], "은평구": [37.6026, 126.9291],
    "종로구": [37.5729, 126.9794], "중구":  [37.5641, 126.9979],
    "중랑구": [37.6063, 127.0927],
}

TOP5 = score_df.head(5)["자치구명"].tolist()

# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗺️ 구 선택")
    st.markdown("구를 선택하면 지도와 차트가 업데이트됩니다.")

    gu_list = sorted(GU_CENTERS.keys())
    selected_gu = st.selectbox("자치구 선택", gu_list, index=gu_list.index("강서구"))

    st.markdown("---")
    st.markdown("### 📌 지도 레이어")
    show_safety  = st.checkbox("🚔 지구대 · 파출소", value=True)
    show_conv    = st.checkbox("🏪 편의점 · 마트",   value=True)

    st.markdown("---")

    # 선택 구 요약 카드
    gu_score = score_df[score_df["자치구명"] == selected_gu].iloc[0]
    rank = score_df[score_df["자치구명"] == selected_gu].index[0] + 1
    badge = '<span class="top5-badge">TOP 5 🏆</span>' if selected_gu in TOP5 else ""

    st.markdown(f"### 📊 {selected_gu} 요약 {badge}", unsafe_allow_html=True)
    st.markdown(f"""
    | 항목 | 값 |
    |------|-----|
    | 전체 순위 | **{rank}위 / 25위** |
    | 총점 | **{gu_score['총점']}점** |
    | 안전점수 | {gu_score['안전점수']}점 |
    | 생활점수 | {gu_score['생활점수']}점 |
    | 가격점수 | {gu_score['가격점수']}점 |
    | 평균 월세 | {gu_score['평균_월세']}만원 |
    """)

# ─────────────────────────────────────────────
# 헤더
# ─────────────────────────────────────────────
st.markdown("""
<div class="dashboard-header">
    <div class="dashboard-title">🏙️ 청년 1인가구, 서울 어디에서 살면 좋을까?</div>
    <div class="dashboard-subtitle">서울특별시 1인가구 주거환경 인프라 대시보드 | 안전 · 생활 · 가격 점수 기반 구별 분석</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 상단 지표 카드
# ─────────────────────────────────────────────
rent_val = rent_df[rent_df["자치구명"] == selected_gu]["평균월세"].values
avg_rent = rent_val[0] if len(rent_val) > 0 else "-"

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">선택 구</div>
        <div class="metric-value">{selected_gu}</div>
        <div class="metric-unit">전체 {rank}위</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">인프라 총점</div>
        <div class="metric-value">{gu_score['총점']}</div>
        <div class="metric-unit">/ 100점</div>
    </div>""", unsafe_allow_html=True)
with col3:
    cnt_safety = len(safety_df[safety_df["자치구명"] == selected_gu])
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">🚔 안전시설 수</div>
        <div class="metric-value">{cnt_safety}</div>
        <div class="metric-unit">지구대 · 파출소</div>
    </div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">💰 평균 월세</div>
        <div class="metric-value">{avg_rent}</div>
        <div class="metric-unit">만원</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────
# [차트 1] 지도
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">📍 Chart 1. 서울시 구별 인프라 지도</div>', unsafe_allow_html=True)
st.caption(f"🔍 선택된 구: **{selected_gu}** | 호버 시 평균 월세 표시 | 사이드바에서 레이어 ON/OFF 가능")

# score + rent 병합
map_df = score_df.merge(rent_df, on="자치구명", how="left")

# Folium 지도 생성
m = folium.Map(
    location=[37.5665, 126.9780],
    zoom_start=11,
    tiles="CartoDB positron",
    min_zoom=10,
    max_zoom=14,
)

# 구별 원형 마커 (호버 시 월세 표시)
for _, row in map_df.iterrows():
    gu = row["자치구명"]
    if gu not in GU_CENTERS:
        continue
    lat, lng = GU_CENTERS[gu]
    is_selected = (gu == selected_gu)
    is_top5 = (gu in TOP5)

    color = "#1b5e20" if is_selected else ("#43a047" if is_top5 else "#a5d6a7")
    radius = 18 if is_selected else (14 if is_top5 else 10)
    weight = 3 if is_selected else 1

    folium.CircleMarker(
        location=[lat, lng],
        radius=radius,
        color="#ffffff",
        weight=weight,
        fill=True,
        fill_color=color,
        fill_opacity=0.85,
        tooltip=folium.Tooltip(
            f"""<div style='font-family:sans-serif; font-size:13px; min-width:140px'>
                <b style='color:#1b5e20'>{gu}</b><br>
                💰 평균 월세: <b>{row['평균월세']}만원</b><br>
                🏆 총점: <b>{row['총점']}점</b><br>
                {'⭐ TOP 5' if is_top5 else ''}
            </div>""",
            sticky=True
        ),
    ).add_to(m)

    # 구 이름 텍스트
    folium.Marker(
        location=[lat, lng],
        icon=folium.DivIcon(
            html=f"""<div style='
                font-size:{"11px" if is_selected else "9px"};
                font-weight:{"700" if is_selected else "500"};
                color:{"#1b5e20" if is_selected else "#333"};
                white-space:nowrap;
                margin-top:20px;
                text-shadow: 1px 1px 2px white, -1px -1px 2px white;
            '>{gu}</div>""",
            icon_size=(60, 20),
            icon_anchor=(30, 0),
        )
    ).add_to(m)

# 선택된 구의 안전시설 마커
if show_safety:
    gu_safety = safety_df[safety_df["자치구명"] == selected_gu]
    for _, row in gu_safety.iterrows():
        icon_color = "blue" if row["시설유형"] == "지구대" else "lightblue"
        icon_name  = "shield" if row["시설유형"] == "지구대" else "info-sign"
        folium.Marker(
            location=[row["위도"], row["경도"]],
            icon=folium.Icon(color=icon_color, icon=icon_name, prefix="glyphicon"),
            tooltip=f"🚔 {row['시설유형']} | {row['시설명']}",
        ).add_to(m)

# 선택된 구의 편의시설 마커
if show_conv:
    gu_conv = conv_df[conv_df["자치구명"] == selected_gu]
    # 편의점/마트 개수가 많을 경우 샘플링 (최대 100개)
    if len(gu_conv) > 100:
        gu_conv = gu_conv.sample(100, random_state=42)

    for _, row in gu_conv.iterrows():
        icon_color = "green" if row["시설유형"] == "편의점" else "orange"
        icon_name  = "shopping-cart"
        folium.Marker(
            location=[row["위도"], row["경도"]],
            icon=folium.Icon(color=icon_color, icon=icon_name, prefix="glyphicon"),
            tooltip=f"{'🏪' if row['시설유형']=='편의점' else '🛒'} {row['시설유형']} | {row['시설명']}",
        ).add_to(m)

# 범례
legend_html = """
<div style='position:fixed; bottom:20px; right:20px; z-index:1000;
     background:white; padding:12px 16px; border-radius:10px;
     box-shadow:0 2px 12px rgba(0,0,0,0.15); font-size:12px; font-family:sans-serif;'>
  <b style='color:#1b5e20'>범례</b><br>
  <span style='color:#1b5e20'>●</span> 선택된 구<br>
  <span style='color:#43a047'>●</span> TOP 5 구<br>
  <span style='color:#a5d6a7'>●</span> 일반 구<br>
  🔵 지구대 &nbsp; 🔷 파출소<br>
  🟢 편의점 &nbsp; 🟠 마트
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

st_folium(m, width="100%", height=480, returned_objects=[])

st.markdown("---")

# ─────────────────────────────────────────────
# [차트 2] 선택 구 시설 개수 막대그래프
# ─────────────────────────────────────────────
st.markdown(f'<div class="section-title">📊 Chart 2. {selected_gu} 시설 현황</div>', unsafe_allow_html=True)

col_bar, col_radar = st.columns([1, 1])

with col_bar:
    # 데이터 집계
    cnt_jiguidae  = len(safety_df[(safety_df["자치구명"] == selected_gu) & (safety_df["시설유형"] == "지구대")])
    cnt_pachulso  = len(safety_df[(safety_df["자치구명"] == selected_gu) & (safety_df["시설유형"] == "파출소")])
    cnt_geonuijeom = len(conv_df[(conv_df["자치구명"] == selected_gu) & (conv_df["시설유형"] == "편의점")])
    cnt_mart      = len(conv_df[(conv_df["자치구명"] == selected_gu) & (conv_df["시설유형"] == "슈퍼마켓")])

    categories = ["지구대", "파출소", "편의점", "슈퍼마켓"]
    counts     = [cnt_jiguidae, cnt_pachulso, cnt_geonuijeom, cnt_mart]
    colors     = ["#1b5e20", "#388e3c", "#66bb6a", "#a5d6a7"]

    fig2 = go.Figure(go.Bar(
        x=categories,
        y=counts,
        marker_color=colors,
        text=counts,
        textposition="outside",
        textfont=dict(size=14, color="#1b5e20"),
        hovertemplate="%{x}: %{y}개<extra></extra>",
    ))
    fig2.update_layout(
        title=dict(text=f"{selected_gu} 시설 유형별 개수", font=dict(size=14, color="#1b5e20")),
        yaxis=dict(title="개수", gridcolor="#e8f5e9"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=50, b=20, l=20, r=20),
        height=340,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # SQL 인사이트
    with st.expander("📝 사용된 SQL 및 인사이트"):
        st.code(f"""
-- 안전시설 개수
SELECT 시설유형, COUNT(*) AS 개수
FROM safety
WHERE 자치구명 = '{selected_gu}'
GROUP BY 시설유형;

-- 편의시설 개수
SELECT 시설유형, COUNT(*) AS 개수
FROM convenience
WHERE 자치구명 = '{selected_gu}'
GROUP BY 시설유형;
        """, language="sql")
        total_safe = cnt_jiguidae + cnt_pachulso
        total_conv = cnt_geonuijeom + cnt_mart
        st.markdown(f"""
**💡 인사이트**
- **{selected_gu}**의 안전시설(지구대+파출소)은 총 **{total_safe}개**, 편의시설(편의점+슈퍼마켓)은 총 **{total_conv}개**입니다.
- 안전시설 수가 많을수록 야간 체감 안전도가 높아, 청년 1인가구에게 유리한 환경입니다.
        """)

# ─────────────────────────────────────────────
# [차트 3] 레이더 차트
# ─────────────────────────────────────────────
with col_radar:
    st.markdown(f'<div class="section-title">📡 Chart 3. {selected_gu} 인프라 점수 레이더</div>', unsafe_allow_html=True)

    gu_row = score_df[score_df["자치구명"] == selected_gu].iloc[0]
    radar_categories = ["안전점수", "생활점수", "가격점수"]
    radar_values     = [gu_row["안전점수"], gu_row["생활점수"], gu_row["가격점수"]]
    radar_values_closed = radar_values + [radar_values[0]]
    radar_cats_closed   = radar_categories + [radar_categories[0]]

    fig3 = go.Figure()
    fig3.add_trace(go.Scatterpolar(
        r=radar_values_closed,
        theta=radar_cats_closed,
        fill="toself",
        fillcolor="rgba(67,160,71,0.25)",
        line=dict(color="#2e7d32", width=2.5),
        marker=dict(size=8, color="#1b5e20"),
        name=selected_gu,
        hovertemplate="%{theta}: %{r:.1f}점<extra></extra>",
    ))
    fig3.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=10), gridcolor="#c8e6c9"),
            angularaxis=dict(tickfont=dict(size=12, color="#1b5e20")),
            bgcolor="white",
        ),
        showlegend=False,
        paper_bgcolor="white",
        margin=dict(t=30, b=30, l=40, r=40),
        height=340,
    )
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("📝 사용된 SQL 및 인사이트"):
        st.code(f"""
SELECT 자치구명, 안전점수, 생활점수, 가격점수
FROM score
WHERE 자치구명 = '{selected_gu}';
        """, language="sql")
        best = radar_categories[radar_values.index(max(radar_values))]
        worst = radar_categories[radar_values.index(min(radar_values))]
        st.markdown(f"""
**💡 인사이트**
- **{selected_gu}**의 가장 강한 점수는 **{best}({max(radar_values):.1f}점)** 입니다.
- 상대적으로 보완이 필요한 영역은 **{worst}({min(radar_values):.1f}점)** 입니다.
- 점수는 안전(×3) + 생활(×3) + 가격(×4) 가중 합산으로 산출됩니다.
        """)

st.markdown("---")

# ─────────────────────────────────────────────
# [차트 4] TOP 5 막대 차트 (사이드바 독립)
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">🏆 Chart 4. 인프라 점수 TOP 5 구</div>', unsafe_allow_html=True)

top5_df = score_df.head(5).copy()
top5_df["색상"] = top5_df["자치구명"].apply(
    lambda x: "#1b5e20" if x == selected_gu else "#43a047"
)

fig4 = go.Figure()
for i, row in top5_df.iterrows():
    fig4.add_trace(go.Bar(
        x=[row["자치구명"]],
        y=[row["총점"]],
        marker_color=row["색상"],
        text=[f"{row['총점']}점"],
        textposition="outside",
        textfont=dict(size=13, color="#1b5e20"),
        name=row["자치구명"],
        hovertemplate=(
            f"<b>{row['자치구명']}</b><br>"
            f"총점: {row['총점']}점<br>"
            f"안전: {row['안전점수']}점 | 생활: {row['생활점수']}점 | 가격: {row['가격점수']}점"
            "<extra></extra>"
        ),
        width=0.5,
    ))

fig4.update_layout(
    showlegend=False,
    yaxis=dict(title="인프라 총점", range=[0, 100], gridcolor="#e8f5e9"),
    xaxis=dict(title="자치구"),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(t=30, b=20, l=20, r=20),
    height=380,
    bargap=0.3,
)
st.plotly_chart(fig4, use_container_width=True)

with st.expander("📝 사용된 SQL 및 인사이트"):
    st.code("""
SELECT 자치구명, 안전점수, 생활점수, 가격점수, 총점
FROM score
ORDER BY 총점 DESC
LIMIT 5;
    """, language="sql")
    st.markdown(f"""
**💡 인사이트**
- 1위 **강서구(72.11점)**는 안전·생활·가격 세 항목이 균형 있게 높아 청년 1인가구에 가장 적합한 환경입니다.
- **구로구(5위)**는 월세가 낮아 가격점수(9.88)가 매우 높고, 전체 대비 저렴한 주거 비용이 강점입니다.
- **종로구(3위)**는 안전점수 1위(10.0점)이지만 편의시설이 상대적으로 적어 생활점수에서 약점이 있습니다.
- 현재 선택된 **{selected_gu}**는 {'TOP 5에 포함된 구입니다! 🎉' if selected_gu in TOP5 else 'TOP 5에 포함되지 않습니다.'}
    """)

st.markdown("---")

# ─────────────────────────────────────────────
# [차트 5] 히트맵 — 전체 구 × 항목별 점수
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">🌡️ Chart 5. 서울 25개 구 항목별 점수 히트맵</div>', unsafe_allow_html=True)

heatmap_df = score_df[["자치구명", "안전점수", "생활점수", "가격점수"]].set_index("자치구명")

fig5 = go.Figure(go.Heatmap(
    z=heatmap_df.values,
    x=["안전점수", "생활점수", "가격점수"],
    y=heatmap_df.index.tolist(),
    colorscale=[
        [0.0, "#f1f8e9"],
        [0.3, "#a5d6a7"],
        [0.6, "#43a047"],
        [1.0, "#1b5e20"],
    ],
    text=[[f"{v:.1f}" for v in row] for row in heatmap_df.values],
    texttemplate="%{text}",
    textfont=dict(size=11, color="white"),
    hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}점<extra></extra>",
    showscale=True,
    colorbar=dict(
        title="점수",
        tickfont=dict(size=11),
        len=0.8,
    ),
    zmin=1, zmax=10,
))
fig5.update_layout(
    xaxis=dict(side="top", tickfont=dict(size=13, color="#1b5e20")),
    yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(t=60, b=20, l=20, r=20),
    height=700,
)
st.plotly_chart(fig5, use_container_width=True)

with st.expander("📝 사용된 SQL 및 인사이트"):
    st.code("""
SELECT 자치구명, 안전점수, 생활점수, 가격점수
FROM score
ORDER BY 총점 DESC;
    """, language="sql")
    st.markdown("""
**💡 인사이트**
- **생활점수**: 강남구(10.0점)가 압도적이지만, 가격점수가 낮아 총점에서 불리합니다.
- **가격점수**: 중랑구·구로구·금천구가 10점에 가까워 저렴한 주거비가 강점입니다.
- **안전점수**: 종로구가 유일하게 10점으로, 지구대·파출소 밀도가 가장 높습니다.
- **패턴**: 강남·서초·용산은 생활점수는 높지만 가격점수가 매우 낮은 반면, 노원·도봉·강북은 가격점수가 높아 청년 1인가구에 실질적으로 유리한 구가 뚜렷이 구분됩니다.
    """)

# ─────────────────────────────────────────────
# 푸터
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#81c784; font-size:0.8rem; padding:1rem 0'>
    📊 데이터 출처: 공공데이터포털 · 국토교통부 실거래가 · 소상공인진흥공단 상가정보 · 경찰청<br>
    서울특별시 1인가구 주거환경 인프라 대시보드 | 안전×3 + 생활×3 + 가격×4 = 총점 100점 만점
</div>
""", unsafe_allow_html=True)
