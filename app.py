from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="달러 스위칭 백테스터",
    page_icon="USD",
    layout="wide",
)


@dataclass
class Lot:
    id: int
    buy_date: pd.Timestamp
    buy_rate: float
    usd_amount: float
    krw_cost: float
    target_rate: float


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #1e293b;
            --muted: #64748b;
            --line: #dbe3ee;
            --panel: #f8fafc;
            --accent: #0f766e;
            --accent-soft: #ccfbf1;
            --warn: #b45309;
            --warn-soft: #fef3c7;
        }
        .main .block-container {
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }
        h1, h2, h3 {
            color: var(--ink);
            letter-spacing: 0;
        }
        .hero {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 26px 28px;
            background:
                linear-gradient(135deg, rgba(15, 118, 110, 0.10), rgba(255,255,255,0.70)),
                linear-gradient(0deg, #ffffff, #ffffff);
            margin-bottom: 18px;
        }
        .hero-title {
            font-size: 34px;
            line-height: 1.16;
            font-weight: 760;
            margin: 0 0 8px 0;
        }
        .hero-copy {
            color: var(--muted);
            font-size: 16px;
            line-height: 1.6;
            max-width: 760px;
            margin: 0;
        }
        .note {
            border-left: 4px solid var(--accent);
            background: var(--panel);
            padding: 12px 14px;
            color: var(--ink);
            border-radius: 6px;
            margin: 10px 0 18px 0;
        }
        .metric-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 14px 15px;
            background: #ffffff;
            min-height: 106px;
        }
        .metric-label {
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
        .metric-help {
            color: var(--muted);
            font-size: 12px;
            margin-top: 6px;
        }
        div[data-testid="stMetricValue"] {
            font-size: 25px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def make_sample_data() -> pd.DataFrame:
    dates = pd.date_range("2019-01-02", "2026-09-11", freq="B")
    rng = np.random.default_rng(99595)
    shocks = rng.normal(0, 4.2, len(dates))
    cycle = 70 * np.sin(np.linspace(0, 9.5 * np.pi, len(dates)))
    trend = np.linspace(0, 135, len(dates))
    rates = 1130 + trend + cycle + np.cumsum(shocks * 0.18)
    rates = np.clip(rates, 1030, 1510)
    return pd.DataFrame({"date": dates, "rate": rates.round(2)})


def load_uploaded_csv(uploaded_file) -> pd.DataFrame | None:
    if uploaded_file is None:
        return None

    raw = uploaded_file.getvalue().decode("utf-8-sig")
    df = pd.read_csv(StringIO(raw))
    normalized = {col.lower().strip(): col for col in df.columns}

    date_col = normalized.get("date") or normalized.get("날짜")
    rate_col = (
        normalized.get("rate")
        or normalized.get("close")
        or normalized.get("usdkrw")
        or normalized.get("exchange_rate")
        or normalized.get("환율")
    )

    if not date_col or not rate_col:
        st.error("CSV에는 date/날짜 열과 rate/close/usdkrw/환율 중 하나의 환율 열이 필요합니다.")
        return None

    out = df[[date_col, rate_col]].copy()
    out.columns = ["date", "rate"]
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["rate"] = pd.to_numeric(out["rate"], errors="coerce")
    out = out.dropna().sort_values("date").drop_duplicates("date")

    if out.empty:
        st.error("읽을 수 있는 환율 데이터가 없습니다.")
        return None

    return out.reset_index(drop=True)


def backtest_switching(
    data: pd.DataFrame,
    initial_krw: float,
    lot_krw: float,
    max_lots: int,
    anchor_rate: float,
    buy_gap: float,
    target_profit_pct: float,
    fee_pct: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cash = initial_krw
    lots: list[Lot] = []
    closed_trades: list[dict] = []
    curve: list[dict] = []
    next_lot_id = 1

    for row in data.itertuples(index=False):
        date = pd.Timestamp(row.date)
        rate = float(row.rate)

        remaining_lots: list[Lot] = []
        for lot in lots:
            if rate >= lot.target_rate:
                sell_value = lot.usd_amount * rate * (1 - fee_pct)
                profit = sell_value - lot.krw_cost
                cash += sell_value
                closed_trades.append(
                    {
                        "회차": lot.id,
                        "매수일": lot.buy_date,
                        "매도일": date,
                        "매수환율": lot.buy_rate,
                        "매도환율": rate,
                        "목표환율": lot.target_rate,
                        "투입원화": lot.krw_cost,
                        "회수원화": sell_value,
                        "실현손익": profit,
                        "수익률": profit / lot.krw_cost,
                        "보유일": (date - lot.buy_date).days,
                    }
                )
            else:
                remaining_lots.append(lot)
        lots = remaining_lots

        while len(lots) < max_lots:
            buy_level = anchor_rate - buy_gap * len(lots)
            if rate > buy_level or cash < lot_krw:
                break

            usd_amount = lot_krw * (1 - fee_pct) / rate
            target_rate = rate * (1 + target_profit_pct + fee_pct)
            lots.append(
                Lot(
                    id=next_lot_id,
                    buy_date=date,
                    buy_rate=rate,
                    usd_amount=usd_amount,
                    krw_cost=lot_krw,
                    target_rate=target_rate,
                )
            )
            cash -= lot_krw
            next_lot_id += 1

        usd_value = sum(lot.usd_amount for lot in lots) * rate * (1 - fee_pct)
        total_value = cash + usd_value
        invested = sum(lot.krw_cost for lot in lots)
        curve.append(
            {
                "date": date,
                "rate": rate,
                "total_value": total_value,
                "cash_krw": cash,
                "usd_value": usd_value,
                "open_lots": len(lots),
                "open_cost": invested,
                "realized_profit": sum(trade["실현손익"] for trade in closed_trades),
            }
        )

    curve_df = pd.DataFrame(curve)
    trades_df = pd.DataFrame(closed_trades)
    open_df = pd.DataFrame(
        [
            {
                "회차": lot.id,
                "매수일": lot.buy_date,
                "매수환율": lot.buy_rate,
                "목표환율": lot.target_rate,
                "보유달러": lot.usd_amount,
                "투입원화": lot.krw_cost,
                "평가원화": lot.usd_amount * float(data.iloc[-1]["rate"]) * (1 - fee_pct),
            }
            for lot in lots
        ]
    )
    return curve_df, trades_df, open_df


def max_drawdown(series: pd.Series) -> float:
    peak = series.cummax()
    drawdown = series / peak - 1
    return float(drawdown.min())


def format_krw(value: float) -> str:
    return f"{value:,.0f}원"


def format_pct(value: float) -> str:
    return f"{value * 100:,.2f}%"


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


def main() -> None:
    inject_css()

    st.markdown(
        """
        <section class="hero">
            <p class="hero-title">달러 스위칭 백테스터</p>
            <p class="hero-copy">
                원화와 달러 사이를 오가는 분할 매수·분할 매도 전략을 환율 데이터로 시험합니다.
                각 매수 회차를 독립 포지션으로 보고, 목표 환율에 닿으면 해당 회차만 원화로 전환합니다.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("전략 설정")
        uploaded_file = st.file_uploader("환율 CSV 업로드", type=["csv"])
        uploaded_data = load_uploaded_csv(uploaded_file)
        data = uploaded_data if uploaded_data is not None else make_sample_data()

        min_date = data["date"].min().date()
        max_date = data["date"].max().date()
        date_range = st.date_input("백테스트 기간", (min_date, max_date), min_value=min_date, max_value=max_date)

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            data = data[(data["date"].dt.date >= start_date) & (data["date"].dt.date <= end_date)]

        latest_rate = float(data.iloc[-1]["rate"])
        median_rate = float(data["rate"].median())

        initial_krw = st.number_input("초기 원화 자금", min_value=1_000_000, value=10_000_000, step=500_000)
        max_lots = st.slider("최대 분할 회차", min_value=2, max_value=12, value=7)
        lot_krw = st.number_input("1회 매수 금액", min_value=100_000, value=1_000_000, step=100_000)
        anchor_rate = st.number_input("기준 환율", min_value=800.0, value=round(median_rate, 1), step=5.0)
        buy_gap = st.number_input("추가 매수 간격", min_value=1.0, value=15.0, step=1.0)
        target_profit_pct = st.slider("회차별 목표 수익률", min_value=0.1, max_value=10.0, value=2.0, step=0.1) / 100
        fee_pct = st.slider("환전 수수료", min_value=0.0, max_value=1.0, value=0.15, step=0.01) / 100

    if data.empty:
        st.warning("선택한 기간에 데이터가 없습니다.")
        return

    curve_df, trades_df, open_df = backtest_switching(
        data=data,
        initial_krw=float(initial_krw),
        lot_krw=float(lot_krw),
        max_lots=int(max_lots),
        anchor_rate=float(anchor_rate),
        buy_gap=float(buy_gap),
        target_profit_pct=float(target_profit_pct),
        fee_pct=float(fee_pct),
    )

    final_value = float(curve_df.iloc[-1]["total_value"])
    total_return = final_value / float(initial_krw) - 1
    realized_profit = float(curve_df.iloc[-1]["realized_profit"])
    mdd = max_drawdown(curve_df["total_value"])
    closed_count = len(trades_df)
    open_count = int(curve_df.iloc[-1]["open_lots"])

    buy_hold_usd = float(initial_krw) * (1 - fee_pct) / float(data.iloc[0]["rate"])
    buy_hold_value = buy_hold_usd * latest_rate * (1 - fee_pct)
    buy_hold_return = buy_hold_value / float(initial_krw) - 1

    st.markdown(
        """
        <div class="note">
            이 화면은 투자 조언이 아니라 전략 검증용 계산기입니다. 환율 데이터, 수수료, 세금, 실제 체결 조건에 따라 결과가 달라질 수 있습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(5)
    with cols[0]:
        metric_card("최종 평가금액", format_krw(final_value), f"초기 {format_krw(float(initial_krw))}")
    with cols[1]:
        metric_card("총 수익률", format_pct(total_return), f"달러 보유 {format_pct(buy_hold_return)}")
    with cols[2]:
        metric_card("실현손익", format_krw(realized_profit), f"청산 거래 {closed_count}건")
    with cols[3]:
        metric_card("최대 낙폭", format_pct(mdd), "평가금액 기준")
    with cols[4]:
        metric_card("미청산 회차", f"{open_count}개", f"최근 환율 {latest_rate:,.2f}원")

    view = st.radio("보기", ["전략 차트", "거래 내역", "데이터"])

    if view == "전략 차트":
        comparison = pd.DataFrame(
            {
                "스위칭 전략": curve_df["total_value"].values,
                "달러 단순 보유 비교": (curve_df["rate"] / curve_df.iloc[0]["rate"] * float(initial_krw)).values,
            },
            index=curve_df["date"],
        )
        st.line_chart(comparison, height=430)

        rate_view = pd.DataFrame({"USD/KRW": data["rate"].values}, index=data["date"])
        st.line_chart(rate_view, height=330)

        buy_levels = pd.DataFrame(
            {
                "회차": [f"{idx + 1}차" for idx in range(max_lots)],
                "매수 기준 환율": [anchor_rate - buy_gap * idx for idx in range(max_lots)],
            }
        )
        st.markdown("현재 설정의 회차별 매수 기준")
        st.dataframe(buy_levels)

    elif view == "거래 내역":
        left, right = st.columns(2)
        with left:
            st.subheader("청산 거래")
            if trades_df.empty:
                st.info("선택한 조건에서 청산된 거래가 없습니다.")
            else:
                display = trades_df.copy()
                display["수익률"] = display["수익률"].map(lambda x: f"{x * 100:.2f}%")
                for col in ["투입원화", "회수원화", "실현손익"]:
                    display[col] = display[col].map(lambda x: f"{x:,.0f}")
                st.dataframe(display)
        with right:
            st.subheader("미청산 포지션")
            if open_df.empty:
                st.success("미청산 포지션이 없습니다.")
            else:
                display_open = open_df.copy()
                for col in ["보유달러", "투입원화", "평가원화"]:
                    display_open[col] = display_open[col].map(lambda x: f"{x:,.2f}")
                st.dataframe(display_open)

    else:
        st.subheader("사용한 환율 데이터")
        st.dataframe(data.tail(800))
        st.markdown("샘플 CSV가 필요하면 아래 내용을 `sample_usdkrw.csv`로 저장해서 업로드 테스트에 사용할 수 있습니다.")
        st.code(make_sample_data().head(20).to_csv(index=False), language="csv")


if __name__ == "__main__":
    main()
