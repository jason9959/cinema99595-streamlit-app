from __future__ import annotations

from datetime import date, timedelta

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(page_title="달러 스위칭 백테스터", page_icon="USD", layout="wide")

USD_KRW_TICKER = "KRW=X"
DOLLAR_INDEX_TICKER = "DX-Y.NYB"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #172033;
            --muted: #667085;
            --line: #d8e0ea;
            --panel: #f7fafc;
            --accent: #0f766e;
            --danger: #b42318;
            --danger-soft: #fee4e2;
            --ok: #067647;
            --ok-soft: #dcfae6;
        }
        .main .block-container {
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }
        section[data-testid="stSidebar"] {
            display: none;
        }
        div[data-testid="stAppViewContainer"] > .main {
            margin-left: 0;
        }
        h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
        .hero {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 28px;
            background:
                linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(255,255,255,0.72)),
                linear-gradient(0deg, #ffffff, #ffffff);
            margin-bottom: 18px;
        }
        .hero-title {
            font-size: 35px;
            line-height: 1.16;
            font-weight: 760;
            margin: 0 0 8px 0;
        }
        .hero-copy {
            color: var(--muted);
            font-size: 16px;
            line-height: 1.65;
            max-width: 820px;
            margin: 0;
        }
        .note {
            border-left: 4px solid var(--accent);
            background: var(--panel);
            padding: 12px 14px;
            color: var(--ink);
            border-radius: 6px;
            margin: 12px 0 18px 0;
        }
        .metric-card, .status-card, .nav-card, .settings-panel {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 15px;
            background: #ffffff;
            min-height: 112px;
        }
        .metric-label, .status-label {
            color: var(--muted);
            font-size: 13px;
            margin-bottom: 6px;
        }
        .metric-value {
            color: var(--ink);
            font-size: 25px;
            font-weight: 760;
            line-height: 1.2;
        }
        .metric-help, .status-help {
            color: var(--muted);
            font-size: 12px;
            margin-top: 6px;
            line-height: 1.45;
        }
        .status-ok, .status-no {
            border-radius: 999px;
            padding: 4px 10px;
            display: inline-block;
            font-size: 13px;
            font-weight: 700;
        }
        .status-ok { color: var(--ok); background: var(--ok-soft); }
        .status-no { color: var(--danger); background: var(--danger-soft); }
        .small-title {
            color: var(--ink);
            font-size: 18px;
            font-weight: 740;
            margin-bottom: 6px;
        }
        div.stButton > button {
            border-radius: 8px;
            min-height: 62px;
            font-weight: 700;
            justify-content: flex-start;
            text-align: left;
            padding: 12px 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <section class="hero">
            <p class="hero-title">{title}</p>
            <p class="hero-copy">{copy}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, help_text: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_card(label: str, ok: bool, value: str, standard: str, help_text: str) -> None:
    badge = "충족" if ok else "미충족"
    klass = "status-ok" if ok else "status-no"
    st.markdown(
        f"""
        <div class="status-card">
            <div class="status-label">{label}</div>
            <span class="{klass}">{badge}</span>
            <div class="metric-value" style="font-size:22px;margin-top:8px;">{value}</div>
            <div class="metric-help">기준: {standard}</div>
            <div class="status-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_krw(value: float) -> str:
    return f"{value:,.0f}원"


def format_pct(value: float) -> str:
    return f"{value * 100:,.2f}%"


def krw_axis(title: str) -> alt.Axis:
    return alt.Axis(
        title=title,
        labelExpr=(
            "datum.value >= 100000000 ? format(datum.value / 100000000, '.2f') + '억원' : "
            "format(datum.value / 10000000, '.2f') + '천만원'"
        ),
    )


def make_sample_market_data() -> pd.DataFrame:
    dates = pd.date_range(date.today() - timedelta(days=365 * 6), date.today(), freq="B")
    rng = np.random.default_rng(99595)
    dxy = 101 + 5.5 * np.sin(np.linspace(0, 9 * np.pi, len(dates))) + np.cumsum(rng.normal(0, 0.05, len(dates)))
    usdkrw = 1190 + 95 * np.sin(np.linspace(0.6, 8.8 * np.pi, len(dates))) + np.cumsum(rng.normal(0, 1.1, len(dates)))
    usdkrw = np.clip(usdkrw, 1030, 1520)
    return pd.DataFrame({"date": dates, "usdkrw": usdkrw.round(2), "dxy": dxy.round(2), "source": "sample"})


@st.cache_data(ttl=60 * 60 * 4)
def load_market_data() -> pd.DataFrame:
    try:
        import yfinance as yf

        start = date.today() - timedelta(days=365 * 7)
        end = date.today() + timedelta(days=1)
        raw = yf.download(
            [USD_KRW_TICKER, DOLLAR_INDEX_TICKER],
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,
            group_by="ticker",
            threads=False,
        )
        fx = raw[USD_KRW_TICKER]["Close"].rename("usdkrw")
        dxy = raw[DOLLAR_INDEX_TICKER]["Close"].rename("dxy")
        data = pd.concat([fx, dxy], axis=1).dropna().reset_index()
        data.columns = ["date", "usdkrw", "dxy"]
        data["date"] = pd.to_datetime(data["date"]).dt.tz_localize(None)
        data["source"] = "yfinance"
        if len(data) < 260:
            raise ValueError("not enough market data")
        return data.sort_values("date").reset_index(drop=True)
    except Exception:
        return make_sample_market_data()


def add_indicators(data: pd.DataFrame) -> pd.DataFrame:
    out = data.copy().sort_values("date").reset_index(drop=True)
    out["gap_ratio"] = out["dxy"] / out["usdkrw"] * 100
    out["usdkrw_52w_avg"] = out["usdkrw"].rolling(252, min_periods=60).mean()
    out["dxy_52w_avg"] = out["dxy"].rolling(252, min_periods=60).mean()
    out["gap_52w_avg"] = out["gap_ratio"].rolling(252, min_periods=60).mean()
    out["current_dollar_index"] = out["dxy"]
    out["fair_rate"] = out["dxy"] / out["gap_52w_avg"] * 100
    out["cond_fx_below_avg"] = out["usdkrw"] < out["usdkrw_52w_avg"]
    out["cond_dxy_below_avg"] = out["dxy"] < out["dxy_52w_avg"]
    out["cond_gap_above_avg"] = out["gap_ratio"] > out["gap_52w_avg"]
    out["cond_fx_below_fair"] = out["usdkrw"] < out["fair_rate"]
    condition_cols = ["cond_fx_below_avg", "cond_dxy_below_avg", "cond_gap_above_avg", "cond_fx_below_fair"]
    out["signal_score"] = out[condition_cols].sum(axis=1)
    return out.dropna().reset_index(drop=True)


def backtest_switching(
    data: pd.DataFrame,
    start_date: date,
    end_date: date,
    initial_krw: float,
    recurring_enabled: bool,
    monthly_krw: float,
    buy_score: int,
    sell_score: int,
    fee_pct: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    view = data[(data["date"].dt.date >= start_date) & (data["date"].dt.date <= end_date)].copy()
    view = view.sort_values("date").reset_index(drop=True)
    cash = float(initial_krw)
    usd = 0.0
    state = "KRW"
    total_contribution = float(initial_krw)
    last_contribution_month = None
    curve = []
    switches = []

    for row in view.itertuples(index=False):
        current_date = pd.Timestamp(row.date)
        current_month = (current_date.year, current_date.month)
        rate = float(row.usdkrw)

        if recurring_enabled and current_month != last_contribution_month:
            cash += float(monthly_krw)
            total_contribution += float(monthly_krw)
            last_contribution_month = current_month

        score = int(row.signal_score)
        action = "보유"

        if state == "KRW" and score >= buy_score and cash > 0:
            usd = cash * (1 - fee_pct) / rate
            cash = 0.0
            state = "USD"
            action = "달러 매수"
            switches.append(
                {
                    "date": current_date,
                    "action": action,
                    "rate": rate,
                    "score": score,
                    "total_value": usd * rate * (1 - fee_pct),
                }
            )
        elif state == "USD" and score <= sell_score and usd > 0:
            cash = usd * rate * (1 - fee_pct)
            usd = 0.0
            state = "KRW"
            action = "원화 전환"
            switches.append(
                {
                    "date": current_date,
                    "action": action,
                    "rate": rate,
                    "score": score,
                    "total_value": cash,
                }
            )

        usd_value = usd * rate * (1 - fee_pct)
        total_value = cash + usd_value
        curve.append(
            {
                "date": current_date,
                "usdkrw": rate,
                "dxy": float(row.dxy),
                "gap_ratio": float(row.gap_ratio),
                "fair_rate": float(row.fair_rate),
                "signal_score": score,
                "position": state,
                "action": action,
                "cash_krw": cash,
                "usd_amount": usd,
                "total_value": total_value,
                "total_contribution": total_contribution,
                "return": total_value / total_contribution - 1,
                "cond_fx_below_avg": bool(row.cond_fx_below_avg),
                "cond_dxy_below_avg": bool(row.cond_dxy_below_avg),
                "cond_gap_above_avg": bool(row.cond_gap_above_avg),
                "cond_fx_below_fair": bool(row.cond_fx_below_fair),
            }
        )

    return pd.DataFrame(curve), pd.DataFrame(switches)


def max_drawdown(series: pd.Series) -> float:
    peak = series.cummax()
    return float((series / peak - 1).min())


def set_page(page: str) -> None:
    st.session_state["page"] = page


def render_home() -> None:
    st.title("🧭 달러 환율 나침반")
    st.caption("Dollar Compass · 최신 환율 조건을 이해하고, 원화/달러 스위칭을 데이터로 확인하세요.")
    st.write("어떤 분석을 해볼까요?")
    st.button(
        "📖  포트폴리오 계산기 개요\n\n최신 원/달러 환율, 달러지수, 달러 갭 비율, 적정 환율 4가지 조건을 확인합니다.",
        use_container_width=True,
        on_click=set_page,
        args=("overview",),
    )
    st.button(
        "📈  거치식 · 적립식 계산\n\n입력한 기간과 금액으로 원화/달러 스위칭 전략을 백테스트합니다.",
        use_container_width=True,
        on_click=set_page,
        args=("calculator",),
    )
    latest_note = date.today().strftime("%Y.%m.%d")
    st.caption(f"달러 환율 나침반 · {latest_note} 기준 연구 앱 | 과거 성과를 분석하는 도구이며 미래 수익을 보장하지 않습니다.")


def render_overview(data: pd.DataFrame) -> None:
    hero(
        "오늘의 달러 투자 환경",
        "최신 거래일 기준으로 네 가지 조건이 달러 매수에 우호적인지 확인합니다. 각 조건은 52주 이동 평균과 달러 갭 비율로 계산합니다.",
    )
    st.button("첫 화면으로", on_click=set_page, args=("home",))
    latest = data.iloc[-1]
    latest_date = pd.Timestamp(latest["date"]).date()
    source = "Yahoo Finance" if latest["source"] == "yfinance" else "샘플 데이터"
    st.markdown(
        f"""
        <div class="note">
            기준일: {latest_date} · 데이터 출처: {source}<br>
            달러 갭 비율은 <b>달러지수 / 원달러환율 * 100</b>으로 계산했고,
            적정 환율은 <b>현재 달러지수 / 52주 평균 달러 갭 비율 * 100</b>으로 추정했습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    with cols[0]:
        status_card("원/달러 환율", bool(latest["cond_fx_below_avg"]), f"{latest['usdkrw']:,.2f}원", f"52주 평균 {latest['usdkrw_52w_avg']:,.2f}원보다 낮음", "환율이 52주 평균보다 낮으면 달러를 상대적으로 싸게 살 수 있는 구간으로 봅니다.")
    with cols[1]:
        status_card("달러 지수", bool(latest["cond_dxy_below_avg"]), f"{latest['dxy']:,.2f}", f"52주 평균 {latest['dxy_52w_avg']:,.2f}보다 낮음", "달러 자체의 힘이 평균보다 약하면 달러 매수 부담이 낮아졌다고 해석합니다.")
    with cols[2]:
        status_card("달러 갭 비율", bool(latest["cond_gap_above_avg"]), f"{latest['gap_ratio']:,.3f}", f"52주 평균 {latest['gap_52w_avg']:,.3f}보다 높음", "달러지수 대비 환율이 낮게 평가될수록 이 비율이 높아집니다.")
    with cols[3]:
        status_card("적정 환율", bool(latest["cond_fx_below_fair"]), f"{latest['fair_rate']:,.2f}원", f"현재 환율 {latest['usdkrw']:,.2f}원이 적정 환율보다 낮음", "달러지수와 52주 평균 갭 비율로 계산한 추정 환율보다 실제 환율이 낮은지 봅니다.")

    score = int(latest["signal_score"])
    st.subheader("종합 판정")
    if score >= 3:
        st.success(f"4개 중 {score}개 조건이 충족됩니다. 현재 기준으로는 달러 매수 환경이 우호적인 편입니다.")
    elif score == 2:
        st.info(f"4개 중 {score}개 조건이 충족됩니다. 중립 구간에 가까워 추가 확인이 필요합니다.")
    else:
        st.warning(f"4개 중 {score}개 조건이 충족됩니다. 현재 기준으로는 적극 매수 신호가 약합니다.")

    chart_data = data.tail(252).melt(id_vars=["date"], value_vars=["usdkrw", "fair_rate"], var_name="구분", value_name="환율")
    chart_data["구분"] = chart_data["구분"].replace({"usdkrw": "원/달러 환율", "fair_rate": "적정 환율"})
    chart = (
        alt.Chart(chart_data)
        .mark_line()
        .encode(
            x=alt.X("date:T", title="날짜"),
            y=alt.Y("환율:Q", title="환율", scale=alt.Scale(zero=False)),
            color=alt.Color("구분:N", title="", legend=alt.Legend(orient="bottom")),
            tooltip=["date:T", "구분:N", alt.Tooltip("환율:Q", format=",.2f")],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, use_container_width=True)


def render_calculator(data: pd.DataFrame) -> None:
    hero(
        "거치식 / 월 적립식 스위칭 테스트",
        "과거 일별 데이터에서 네 조건을 매일 판정하고, 조건 점수에 따라 원화와 달러를 전환했을 때의 변화를 확인합니다.",
    )
    st.button("첫 화면으로", on_click=set_page, args=("home",))
    min_date = pd.Timestamp(data["date"].min()).date()
    max_date = pd.Timestamp(data["date"].max()).date()

    st.subheader("백테스트 설정")
    st.markdown(
        """
        <div class="note">
            거치 금액을 먼저 투입하고, 월 적립식 옵션을 켜면 매월 첫 거래일에 적립 금액이 추가됩니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    row1 = st.columns(4)
    with row1[0]:
        start_date = st.date_input("시작일", value=max(min_date, max_date - timedelta(days=365 * 3)), min_value=min_date, max_value=max_date)
    with row1[1]:
        end_date = st.date_input("종료일", value=max_date, min_value=min_date, max_value=max_date)
    with row1[2]:
        initial_krw = st.number_input("거치 금액", min_value=100_000, value=10_000_000, step=100_000)
    with row1[3]:
        fee_pct = st.slider("환전 수수료", min_value=0.0, max_value=1.0, value=0.15, step=0.01) / 100

    row2 = st.columns(4)
    with row2[0]:
        recurring_enabled = st.toggle("월 적립식 옵션", value=False)
    monthly_krw = 0
    with row2[1]:
        if recurring_enabled:
            monthly_krw = st.number_input("월 적립 금액", min_value=10_000, value=500_000, step=10_000)
        else:
            st.number_input("월 적립 금액", min_value=0, value=0, step=10_000, disabled=True)
    with row2[2]:
        buy_score = st.slider("달러 전환 조건 수", min_value=1, max_value=4, value=3)
    with row2[3]:
        sell_score = st.slider("원화 전환 조건 수", min_value=0, max_value=3, value=1)

    if start_date >= end_date:
        st.warning("시작일은 종료일보다 빨라야 합니다.")
        return

    curve, switches = backtest_switching(data, start_date, end_date, float(initial_krw), bool(recurring_enabled), float(monthly_krw), int(buy_score), int(sell_score), float(fee_pct))
    if curve.empty:
        st.warning("선택한 기간에 계산 가능한 데이터가 없습니다.")
        return

    final = curve.iloc[-1]
    mdd = max_drawdown(curve["total_value"])
    cols = st.columns(5)
    with cols[0]:
        metric_card("최종 평가금액", format_krw(float(final["total_value"])), f"총 납입 {format_krw(float(final['total_contribution']))}")
    with cols[1]:
        metric_card("누적 수익률", format_pct(float(final["return"])), "납입 원금 대비")
    with cols[2]:
        metric_card("최대 낙폭", format_pct(mdd), "평가금액 기준")
    with cols[3]:
        metric_card("전환 횟수", f"{len(switches)}회", f"현재 포지션 {final['position']}")
    with cols[4]:
        metric_card("최근 조건 점수", f"{int(final['signal_score'])}/4", f"최근 환율 {float(final['usdkrw']):,.2f}원")

    st.subheader("평가금액 변화와 스위칭 지점")
    base_chart = (
        alt.Chart(curve)
        .mark_line(color="#0f766e", strokeWidth=3)
        .encode(
            x=alt.X("date:T", title="날짜"),
            y=alt.Y("total_value:Q", title="평가금액", axis=krw_axis("평가금액"), scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("date:T", title="날짜"), alt.Tooltip("total_value:Q", title="평가금액", format=",.0f"), alt.Tooltip("position:N", title="포지션"), alt.Tooltip("signal_score:Q", title="조건 점수")],
        )
    )
    chart = base_chart
    if not switches.empty:
        points = (
            alt.Chart(switches)
            .mark_point(size=95, filled=True)
            .encode(
                x="date:T",
                y=alt.Y("total_value:Q", axis=krw_axis("평가금액"), scale=alt.Scale(zero=False)),
                color=alt.Color("action:N", title="스위칭", legend=alt.Legend(orient="bottom")),
                shape=alt.Shape("action:N", title="스위칭", legend=alt.Legend(orient="bottom")),
                tooltip=[alt.Tooltip("date:T", title="날짜"), alt.Tooltip("action:N", title="전환"), alt.Tooltip("rate:Q", title="환율", format=",.2f"), alt.Tooltip("score:Q", title="조건 점수")],
            )
        )
        chart = base_chart + points
    st.altair_chart(chart.properties(height=420), use_container_width=True)

    st.subheader("원/달러 환율과 적정 환율")
    rate_chart_data = curve.melt(id_vars=["date"], value_vars=["usdkrw", "fair_rate"], var_name="구분", value_name="환율")
    rate_chart_data["구분"] = rate_chart_data["구분"].replace({"usdkrw": "원/달러 환율", "fair_rate": "적정 환율"})
    rate_chart = (
        alt.Chart(rate_chart_data)
        .mark_line()
        .encode(x=alt.X("date:T", title="날짜"), y=alt.Y("환율:Q", title="환율", scale=alt.Scale(zero=False)), color=alt.Color("구분:N", title="", legend=alt.Legend(orient="bottom")), tooltip=["date:T", "구분:N", alt.Tooltip("환율:Q", format=",.2f")])
        .properties(height=330)
    )
    st.altair_chart(rate_chart, use_container_width=True)

    st.subheader("일별 4조건 판정")
    table = curve[["date", "usdkrw", "dxy", "gap_ratio", "fair_rate", "signal_score", "position", "action", "cond_fx_below_avg", "cond_dxy_below_avg", "cond_gap_above_avg", "cond_fx_below_fair"]].copy()
    table.columns = ["날짜", "원/달러", "달러지수", "달러갭비율", "적정환율", "조건점수", "포지션", "액션", "환율<52주평균", "달러지수<52주평균", "갭비율>52주평균", "환율<적정환율"]
    for col in ["환율<52주평균", "달러지수<52주평균", "갭비율>52주평균", "환율<적정환율"]:
        table[col] = table[col].map(lambda x: "O" if x else "X")
    st.dataframe(table.sort_values("날짜", ascending=False), use_container_width=True, hide_index=True)


def main() -> None:
    inject_css()
    if "page" not in st.session_state:
        st.session_state["page"] = "home"
    market_data = add_indicators(load_market_data())
    if st.session_state["page"] == "overview":
        render_overview(market_data)
    elif st.session_state["page"] == "calculator":
        render_calculator(market_data)
    else:
        render_home()


if __name__ == "__main__":
    main()
