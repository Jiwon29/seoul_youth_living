import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="서울 1인가구 주거환경 대시보드",
    page_icon="🏠",
    layout="wide",
)

# ─────────────────────────────────────────────
# 커스텀 CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

    .stApp { background: linear-gradient(135deg, #f0faf4 0%, #e8f5e9 100%); }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 60%, #388e3c 100%);
    }
    section[data-testid="stSidebar"] * { color: #ffffff !important; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] p { color: #c8e6c9 !important; font-size: 0.9rem; }

    .dashboard-header {
        background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 50%, #43a047 100%);
        padding: 2rem 2.5rem; border-radius: 16px; margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(27,94,32,0.25);
    }
    .dashboard-title  { font-size: 1.75rem; font-weight: 900; color: #ffffff; line-height: 1.3; margin: 0; }
    .dashboard-subtitle { font-size: 0.95rem; color: #a5d6a7; margin-top: 0.4rem; }

    .metric-card {
        background: #ffffff; border-radius: 14px; padding: 1.2rem 1.5rem;
        box-shadow: 0 4px 16px rgba(46,125,50,0.10); border-left: 5px solid #43a047;
        margin-bottom: 0.8rem;
    }
    .metric-label { font-size: 0.8rem; color: #66bb6a; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { font-size: 2rem; font-weight: 900; color: #1b5e20; line-height: 1.1; }
    .metric-unit  { font-size: 0.85rem; color: #81c784; font-weight: 400; }

    .section-title {
        font-size: 1.1rem; font-weight: 700; color: #1b5e20;
        border-left: 4px solid #43a047; padding-left: 0.7rem;
        margin: 1.2rem 0 0.8rem 0;
    }

    .insight-box {
        background: #ffffff; border-radius: 12px;
        padding: 1.4rem 1.8rem; margin-top: 0.5rem;
        box-shadow: 0 4px 16px rgba(46,125,50,0.08);
        border-top: 4px solid #43a047;
    }
    .insight-title { font-size: 1rem; font-weight: 700; color: #1b5e20; margin-bottom: 0.8rem; }
    .insight-item  { font-size: 0.9rem; color: #333; line-height: 2.1; }

    .top5-badge {
        display: inline-block; background: linear-gradient(135deg, #43a047, #66bb6a);
        color: white; border-radius: 20px; padding: 0.2rem 0.8rem;
        font-size: 0.78rem; font-weight: 700; margin-left: 0.5rem;
    }
    hr { border-color: #c8e6c9; }
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
        FROM safety WHERE 위도 IS NOT NULL AND 경도 IS NOT NULL
    """, conn)
    conv_df = pd.read_sql("""
        SELECT 시설명, 시설유형, 자치구명, 위도, 경도
        FROM convenience WHERE 위도 IS NOT NULL AND 경도 IS NOT NULL
    """, conn)
    rent_df = pd.read_sql("""
        SELECT 자치구명, ROUND(AVG(임대료),1) AS 평균월세
        FROM monthly_rent WHERE 임대료 > 0 GROUP BY 자치구명
    """, conn)
    conn.close()
    return score_df, safety_df, conv_df, rent_df

score_df, safety_df, conv_df, rent_df = load_data()

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

TOP5    = score_df.head(5)["자치구명"].tolist()
BOTTOM5 = score_df.tail(5)["자치구명"].tolist()

# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗺️ 구 선택")
    st.markdown("구를 선택하면 지도와 차트가 업데이트됩니다.")
    gu_list     = sorted(GU_CENTERS.keys())
    selected_gu = st.selectbox("자치구 선택", gu_list, index=gu_list.index("강서구"))

    st.markdown("---")
    st.markdown("### 📌 지도 레이어")
    show_safety = st.checkbox("🚔 지구대 · 파출소", value=True)
    show_conv   = st.checkbox("🏪 편의점 · 마트",   value=True)

    st.markdown("---")
    gu_score = score_df[score_df["자치구명"] == selected_gu].iloc[0]
    rank     = score_df[score_df["자치구명"] == selected_gu].index[0] + 1
    badge    = '<span class="top5-badge">TOP 5 🏆</span>' if selected_gu in TOP5 else ""

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
    <div class="dashboard-title">🏠 청년 1인가구, 서울 어디에서 살면 좋을까?</div>
    <div class="dashboard-subtitle">서울특별시 1인가구 주거환경 인프라 대시보드 | 안전 · 생활 · 가격 점수 기반 구별 분석</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 상단 지표 카드
# ─────────────────────────────────────────────
rent_val         = rent_df[rent_df["자치구명"] == selected_gu]["평균월세"].values
avg_rent         = rent_val[0] if len(rent_val) > 0 else "-"
cnt_safety_total = len(safety_df[safety_df["자치구명"] == selected_gu])

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">선택 구</div>
        <div class="metric-value">{selected_gu}</div>
        <div class="metric-unit">전체 {rank}위</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">인프라 총점</div>
        <div class="metric-value">{gu_score['총점']}</div>
        <div class="metric-unit">/ 100점</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">🚔 안전시설 수</div>
        <div class="metric-value">{cnt_safety_total}</div>
        <div class="metric-unit">지구대 · 파출소</div>
    </div>""", unsafe_allow_html=True)
with c4:
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

map_df = score_df.merge(rent_df, on="자치구명", how="left")

m = folium.Map(
    location=[37.5665, 126.9780], zoom_start=11,
    tiles="CartoDB positron", min_zoom=10, max_zoom=14,
)

for _, row in map_df.iterrows():
    gu = row["자치구명"]
    if gu not in GU_CENTERS:
        continue
    lat, lng = GU_CENTERS[gu]
    is_sel   = (gu == selected_gu)
    is_top5  = (gu in TOP5)
    color    = "#1b5e20" if is_sel else ("#43a047" if is_top5 else "#a5d6a7")
    radius   = 18 if is_sel else (14 if is_top5 else 10)

    folium.CircleMarker(
        location=[lat, lng], radius=radius,
        color="#ffffff", weight=3 if is_sel else 1,
        fill=True, fill_color=color, fill_opacity=0.85,
        tooltip=folium.Tooltip(
            f"""<div style='font-family:sans-serif;font-size:13px;min-width:140px'>
                <b style='color:#1b5e20'>{gu}</b><br>
                💰 평균 월세: <b>{row['평균월세']}만원</b><br>
                🏆 총점: <b>{row['총점']}점</b><br>
                {'⭐ TOP 5' if is_top5 else ''}
            </div>""", sticky=True),
    ).add_to(m)

    folium.Marker(
        location=[lat, lng],
        icon=folium.DivIcon(
            html=f"""<div style='font-size:{"11px" if is_sel else "9px"};
                font-weight:{"700" if is_sel else "500"};
                color:{"#1b5e20" if is_sel else "#333"};
                white-space:nowrap; margin-top:20px;
                text-shadow:1px 1px 2px white,-1px -1px 2px white;'>{gu}</div>""",
            icon_size=(60,20), icon_anchor=(30,0),
        )
    ).add_to(m)

if show_safety:
    for _, row in safety_df[safety_df["자치구명"] == selected_gu].iterrows():
        folium.Marker(
            location=[row["위도"], row["경도"]],
            icon=folium.Icon(
                color="blue" if row["시설유형"]=="지구대" else "lightblue",
                icon="shield" if row["시설유형"]=="지구대" else "info-sign",
                prefix="glyphicon"
            ),
            tooltip=f"🚔 {row['시설유형']} | {row['시설명']}",
        ).add_to(m)

if show_conv:
    gu_conv = conv_df[conv_df["자치구명"] == selected_gu]
    if len(gu_conv) > 100:
        gu_conv = gu_conv.sample(100, random_state=42)
    for _, row in gu_conv.iterrows():
        folium.Marker(
            location=[row["위도"], row["경도"]],
            icon=folium.Icon(
                color="green" if row["시설유형"]=="편의점" else "orange",
                icon="shopping-cart", prefix="glyphicon"
            ),
            tooltip=f"{'🏪' if row['시설유형']=='편의점' else '🛒'} {row['시설유형']} | {row['시설명']}",
        ).add_to(m)

legend_html = """
<div style='position:fixed;bottom:20px;right:20px;z-index:1000;background:white;
     padding:12px 16px;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,0.15);
     font-size:12px;font-family:sans-serif;'>
  <b style='color:#1b5e20'>범례</b><br>
  <span style='color:#1b5e20'>●</span> 선택된 구<br>
  <span style='color:#43a047'>●</span> TOP 5 구<br>
  <span style='color:#a5d6a7'>●</span> 일반 구<br>
  🔵 지구대 &nbsp; 🔷 파출소<br>
  🟢 편의점 &nbsp; 🟠 마트
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))
st_folium(m, width="100%", height=480, returned_objects=[])

st.markdown("---")

# ─────────────────────────────────────────────
# [차트 2 + 3 + 파이] 3열 동일 높이로 줄 맞춤
# ─────────────────────────────────────────────
st.markdown(
    f'<div class="section-title">📊 Chart 2 & 3. {selected_gu} 시설 현황 · 인프라 레이더 · 점수 구성</div>',
    unsafe_allow_html=True
)

CHART_H = 370   # 세 차트 공통 높이 → 줄 맞춤 핵심

col_bar, col_radar, col_pie = st.columns([1, 1, 1])

# ── Chart 2: 막대그래프 ──────────────────────────────────────────────
with col_bar:
    cnt_jiguidae   = len(safety_df[(safety_df["자치구명"]==selected_gu) & (safety_df["시설유형"]=="지구대")])
    cnt_pachulso   = len(safety_df[(safety_df["자치구명"]==selected_gu) & (safety_df["시설유형"]=="파출소")])
    cnt_geonuijeom = len(conv_df[(conv_df["자치구명"]==selected_gu)   & (conv_df["시설유형"]=="편의점")])
    cnt_mart       = len(conv_df[(conv_df["자치구명"]==selected_gu)   & (conv_df["시설유형"]=="슈퍼마켓")])

    fig2 = go.Figure(go.Bar(
        x=["지구대", "파출소", "편의점", "슈퍼마켓"],
        y=[cnt_jiguidae, cnt_pachulso, cnt_geonuijeom, cnt_mart],
        marker_color=["#1b5e20", "#388e3c", "#66bb6a", "#a5d6a7"],
        text=[cnt_jiguidae, cnt_pachulso, cnt_geonuijeom, cnt_mart],
        textposition="outside",
        textfont=dict(size=13, color="#1b5e20"),
        hovertemplate="%{x}: %{y}개<extra></extra>",
    ))
    fig2.update_layout(
        title=dict(text=f"{selected_gu} 시설 유형별 개수", font=dict(size=13, color="#1b5e20")),
        yaxis=dict(title="개수", gridcolor="#e8f5e9"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=50, b=10, l=10, r=10),
        height=CHART_H,
    )
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("📝 SQL · 인사이트"):
        st.code(f"""
SELECT 시설유형, COUNT(*) AS 개수
FROM safety
WHERE 자치구명 = '{selected_gu}'
GROUP BY 시설유형;

SELECT 시설유형, COUNT(*) AS 개수
FROM convenience
WHERE 자치구명 = '{selected_gu}'
GROUP BY 시설유형;
        """, language="sql")
        st.markdown(
            f"**💡** {selected_gu}의 안전시설 **{cnt_jiguidae+cnt_pachulso}개**, "
            f"편의시설 **{cnt_geonuijeom+cnt_mart}개**"
        )

# ── Chart 3: 레이더 차트 ────────────────────────────────────────────
with col_radar:
    gu_row = score_df[score_df["자치구명"] == selected_gu].iloc[0]
    r_cats = ["안전점수", "생활점수", "가격점수"]
    r_vals = [gu_row["안전점수"], gu_row["생활점수"], gu_row["가격점수"]]

    fig3 = go.Figure(go.Scatterpolar(
        r=r_vals + [r_vals[0]],
        theta=r_cats + [r_cats[0]],
        fill="toself",
        fillcolor="rgba(67,160,71,0.25)",
        line=dict(color="#2e7d32", width=2.5),
        marker=dict(size=8, color="#1b5e20"),
        hovertemplate="%{theta}: %{r:.1f}점<extra></extra>",
    ))
    fig3.update_layout(
        title=dict(text=f"{selected_gu} 인프라 레이더", font=dict(size=13, color="#1b5e20")),
        polar=dict(
            radialaxis=dict(visible=True, range=[0,10], tickfont=dict(size=9), gridcolor="#c8e6c9"),
            angularaxis=dict(tickfont=dict(size=12, color="#1b5e20")),
            bgcolor="white",
        ),
        showlegend=False,
        paper_bgcolor="white",
        margin=dict(t=50, b=10, l=30, r=30),
        height=CHART_H,
    )
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("📝 SQL · 인사이트"):
        st.code(f"""
SELECT 자치구명, 안전점수, 생활점수, 가격점수
FROM score WHERE 자치구명 = '{selected_gu}';
        """, language="sql")
        best  = r_cats[r_vals.index(max(r_vals))]
        worst = r_cats[r_vals.index(min(r_vals))]
        st.markdown(f"**💡** 가장 강한 항목 **{best}({max(r_vals):.1f}점)**, 보완 필요 **{worst}({min(r_vals):.1f}점)**")

# ── 추가: 파이차트 (점수 구성 비율) ─────────────────────────────────
with col_pie:
    weighted   = [gu_row["안전점수"]*3, gu_row["생활점수"]*3, gu_row["가격점수"]*4]
    pie_labels = ["안전점수 (×3)", "생활점수 (×3)", "가격점수 (×4)"]

    fig_pie = go.Figure(go.Pie(
        labels=pie_labels,
        values=weighted,
        hole=0.45,
        marker=dict(
            colors=["#1b5e20", "#43a047", "#a5d6a7"],
            line=dict(color="white", width=2)
        ),
        textinfo="label+percent",
        textfont=dict(size=11),
        hovertemplate="%{label}<br>기여점수: %{value:.1f}점<br>비율: %{percent}<extra></extra>",
        pull=[0.04, 0.04, 0.04],
    ))
    fig_pie.update_layout(
        title=dict(text=f"{selected_gu} 점수 구성 비율", font=dict(size=13, color="#1b5e20")),
        showlegend=False,
        paper_bgcolor="white",
        margin=dict(t=50, b=10, l=10, r=10),
        height=CHART_H,
        annotations=[dict(
            text=f"<b>{gu_row['총점']}</b><br>총점",
            x=0.5, y=0.5, font_size=14, font_color="#1b5e20", showarrow=False
        )],
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    with st.expander("📝 인사이트"):
        dominant = pie_labels[weighted.index(max(weighted))]
        st.markdown(
            f"**💡** 총점에서 가장 큰 비중을 차지하는 항목은 **{dominant}**입니다. "
            "가격 가중치(×4)가 가장 크기 때문에 월세가 낮은 구일수록 총점에서 유리합니다."
        )

st.markdown("---")

# ─────────────────────────────────────────────
# [차트 4] TOP 5 + BOTTOM 5 막대차트
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title">🏆 Chart 4. 인프라 점수 상위 TOP 5 · 하위 BOTTOM 5</div>',
    unsafe_allow_html=True
)

top5_df    = score_df.head(5).copy()
bottom5_df = score_df.tail(5).copy()

def bar_colors(df, base_color, sel_color="#ff8f00"):
    return [sel_color if gu == selected_gu else base_color for gu in df["자치구명"]]

fig4 = make_subplots(
    rows=2, cols=1,
    subplot_titles=("🏆 상위 TOP 5", "⚠️ 하위 BOTTOM 5"),
    vertical_spacing=0.16,
)

fig4.add_trace(go.Bar(
    x=top5_df["자치구명"], y=top5_df["총점"],
    marker_color=bar_colors(top5_df, "#1b5e20"),
    text=[f"{v}점" for v in top5_df["총점"]],
    textposition="outside", textfont=dict(size=12),
    customdata=top5_df[["안전점수","생활점수","가격점수"]].values,
    hovertemplate="<b>%{x}</b><br>총점: %{y}점<br>안전: %{customdata[0]} | 생활: %{customdata[1]} | 가격: %{customdata[2]}<extra></extra>",
    width=0.5,
), row=1, col=1)

fig4.add_trace(go.Bar(
    x=bottom5_df["자치구명"], y=bottom5_df["총점"],
    marker_color=bar_colors(bottom5_df, "#ef9a9a"),
    text=[f"{v}점" for v in bottom5_df["총점"]],
    textposition="outside", textfont=dict(size=12),
    customdata=bottom5_df[["안전점수","생활점수","가격점수"]].values,
    hovertemplate="<b>%{x}</b><br>총점: %{y}점<br>안전: %{customdata[0]} | 생활: %{customdata[1]} | 가격: %{customdata[2]}<extra></extra>",
    width=0.5,
), row=2, col=1)

fig4.update_yaxes(range=[0, 100], gridcolor="#e8f5e9", title_text="총점")
fig4.update_xaxes(tickfont=dict(size=12))
fig4.update_layout(
    showlegend=False,
    plot_bgcolor="white", paper_bgcolor="white",
    margin=dict(t=60, b=20, l=20, r=20),
    height=580,
)
st.plotly_chart(fig4, use_container_width=True)

with st.expander("📝 사용된 SQL · 인사이트"):
    st.code("""
-- 상위 TOP 5
SELECT 자치구명, 안전점수, 생활점수, 가격점수, 총점
FROM score ORDER BY 총점 DESC LIMIT 5;

-- 하위 BOTTOM 5
SELECT 자치구명, 안전점수, 생활점수, 가격점수, 총점
FROM score ORDER BY 총점 ASC LIMIT 5;
    """, language="sql")
    st.markdown(f"""
**💡 인사이트**
- **TOP 1 강서구(72.11점)**: 안전·생활·가격 세 항목이 균형 잡혀 청년 1인가구에 최적입니다.
- **BOTTOM 1 용산구(13.60점)**: 평균 월세 138만원(서울 1위)으로 가격점수 1.0점, 총점 꼴찌입니다.
- 주황색 막대는 현재 선택된 **{selected_gu}**입니다. (현재 {rank}위)
    """)

st.markdown("---")

# ─────────────────────────────────────────────
# [차트 5] 히트맵
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title">🌡️ Chart 5. 서울 25개 구 항목별 점수 히트맵</div>',
    unsafe_allow_html=True
)

heatmap_df = score_df[["자치구명","안전점수","생활점수","가격점수"]].set_index("자치구명")

fig5 = go.Figure(go.Heatmap(
    z=heatmap_df.values,
    x=["안전점수", "생활점수", "가격점수"],
    y=heatmap_df.index.tolist(),
    colorscale=[[0.0,"#f1f8e9"],[0.3,"#a5d6a7"],[0.6,"#43a047"],[1.0,"#1b5e20"]],
    text=[[f"{v:.1f}" for v in row] for row in heatmap_df.values],
    texttemplate="%{text}",
    textfont=dict(size=11, color="white"),
    hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}점<extra></extra>",
    showscale=True,
    colorbar=dict(title="점수", tickfont=dict(size=11), len=0.8),
    zmin=1, zmax=10,
))
fig5.update_layout(
    xaxis=dict(side="top", tickfont=dict(size=13, color="#1b5e20")),
    yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
    plot_bgcolor="white", paper_bgcolor="white",
    margin=dict(t=60, b=20, l=20, r=20),
    height=700,
)
st.plotly_chart(fig5, use_container_width=True)

with st.expander("📝 사용된 SQL · 인사이트"):
    st.code("""
SELECT 자치구명, 안전점수, 생활점수, 가격점수
FROM score ORDER BY 총점 DESC;
    """, language="sql")
    st.markdown("""
**💡 인사이트**
- **생활점수**: 강남구(10.0점) 압도적 1위이나, 높은 월세로 가격점수가 낮아 총점은 10위에 그칩니다.
- **가격점수**: 중랑구·구로구·금천구가 10점에 근접, 저렴한 주거비가 핵심 강점입니다.
- **안전점수**: 종로구가 유일하게 10점으로 지구대·파출소 밀도가 서울 최고 수준입니다.
    """)

st.markdown("---")

# ─────────────────────────────────────────────
# 전체 인사이트 요약 (맨 아래 고정)
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">💡 전체 인사이트 요약</div>', unsafe_allow_html=True)

st.markdown("""
<div class="insight-box">
<div class="insight-title">📌 서울 25개 구 주거환경 — 주목할 포인트</div>
<div class="insight-item">
🥇 <b>강서구</b>는 안전·생활·가격 세 항목이 모두 평균 이상으로, 특정 항목에 치우치지 않은 <b>균형형 1위</b> 자치구입니다.<br>
🏙️ <b>강남구</b>는 편의시설 개수 서울 1위(생활점수 10.0점)이지만, 평균 월세 131만원으로 가격점수가 1.71점에 불과해 총점은 10위에 그칩니다.<br>
🚔 <b>종로구</b>는 지구대·파출소 수가 서울 최다(안전점수 10.0점)이지만 편의시설이 적어 생활점수(2.52점)가 뚜렷한 약점입니다.<br>
💸 <b>용산구</b>는 평균 월세 138만원으로 서울 1위를 기록, 가격점수 1.0점으로 인프라 총점 꼴찌(13.60점)입니다.<br>
🏘️ <b>서초구</b>도 월세(136만원)가 용산구 다음으로 높아 가격점수 1.21점에 불과, 총점 하위권(22위)에 위치합니다.<br>
💚 <b>구로구·중랑구·금천구</b>는 가격점수 최상위권(9~10점)으로, 청년 1인가구의 주거비 부담이 가장 낮은 <b>실속형 자치구</b>입니다.<br>
📊 전반적으로 <b>가격점수(가중치 ×4)</b>가 총점에 가장 큰 영향을 미쳐, 강남권(강남·서초·용산)은 높은 생활 인프라에도 불구하고 하위권에 위치합니다.
</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style='text-align:center;color:#81c784;font-size:0.8rem;padding:1.5rem 0 0.5rem'>
    📊 데이터 출처: 공공데이터포털 · 국토교통부 실거래가 · 소상공인진흥공단 상가정보 · 경찰청<br>
    서울특별시 1인가구 주거환경 인프라 대시보드 | 안전×3 + 생활×3 + 가격×4 = 총점 100점 만점
</div>
""", unsafe_allow_html=True)
