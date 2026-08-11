"""Runtime dashboard for the Day 13 observability lab.

Run with: streamlit run dashboard.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml


REPO_ROOT = Path(__file__).resolve().parent
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"


@st.cache_data(ttl=30)
def load_dashboard_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]


@st.cache_data(ttl=30)
def load_logs() -> pd.DataFrame:
    if not LOG_PATH.exists():
        return pd.DataFrame()

    records: list[dict] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not records:
        return pd.DataFrame()

    frame = pd.DataFrame(records)
    if "ts" not in frame:
        return pd.DataFrame()
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True, errors="coerce")
    return frame.dropna(subset=["ts"]).sort_values("ts")


def threshold_message(value: float, *, operator: str, threshold: float) -> str:
    passed = value <= threshold if operator == "lte" else value >= threshold
    state = "ĐẠT" if passed else "VƯỢT NGƯỠNG"
    sign = "≤" if operator == "lte" else "≥"
    return f"{state} · ngưỡng {sign} {threshold:g}"


def event_frame(logs: pd.DataFrame, event: str) -> pd.DataFrame:
    if logs.empty or "event" not in logs:
        return pd.DataFrame()
    return logs.loc[logs["event"] == event].copy()


def numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame.empty or column not in frame:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").dropna()


def render_dashboard() -> None:
    config = load_dashboard_config()
    logs = load_logs()
    minutes = config["time_range_minutes"]
    now = pd.Timestamp.now(tz="UTC")
    if not logs.empty:
        logs = logs.loc[logs["ts"] >= now - pd.Timedelta(minutes=minutes)]

    st.title(config["title"])
    st.caption(
        f"Nguồn: `{LOG_PATH.relative_to(REPO_ROOT)}` · cửa sổ: {minutes} phút · "
        f"tự làm mới mỗi {config['refresh_seconds']} giây"
    )

    if logs.empty:
        st.warning(
            "Chưa có request trong 60 phút gần nhất. Hãy chạy API, sau đó chạy "
            "`python scripts/load_test.py --concurrency 5`."
        )
        return

    panels = {panel["id"]: panel for panel in config["panels"]}
    responses = event_frame(logs, "response_sent")
    requests = event_frame(logs, "request_received")
    failures = event_frame(logs, "request_failed")

    latency_values = numeric(responses, "latency_ms")
    latency_panel = panels["latency"]
    st.subheader("1. Latency percentiles")
    if latency_values.empty:
        st.info("Chưa có event response_sent để tính latency.")
    else:
        percentiles = latency_values.quantile([0.50, 0.95, 0.99])
        p50, p95, p99 = (float(percentiles.loc[p]) for p in (0.50, 0.95, 0.99))
        c1, c2, c3 = st.columns(3)
        c1.metric("P50", f"{p50:.0f} ms")
        c2.metric("P95", f"{p95:.0f} ms")
        c3.metric("P99", f"{p99:.0f} ms")
        threshold = latency_panel["threshold"]
        st.caption(threshold_message(p95, operator=threshold["operator"], threshold=threshold["value"]))
        latency_frame = responses.copy()
        latency_frame["latency_ms"] = pd.to_numeric(latency_frame["latency_ms"], errors="coerce")
        st.line_chart(latency_frame.set_index("ts")["latency_ms"].resample("1min").mean(), y_label="ms")

    left, right = st.columns(2)
    with left:
        traffic_panel = panels["traffic"]
        rate = len(requests) / max(minutes, 1)
        st.subheader("2. Request traffic")
        st.metric("Requests per minute", f"{rate:.2f}", help="Số event request_received / 60 phút")
        st.caption(threshold_message(rate, operator=traffic_panel["threshold"]["operator"], threshold=traffic_panel["threshold"]["value"]))
        if not requests.empty:
            st.bar_chart(requests.set_index("ts").resample("1min").size(), y_label="requests/min")

    with right:
        errors_panel = panels["errors"]
        error_rate = (len(failures) / len(requests) * 100) if len(requests) else 0.0
        st.subheader("3. Error rate and breakdown")
        st.metric("Error rate", f"{error_rate:.2f}%")
        st.caption(threshold_message(error_rate, operator=errors_panel["threshold"]["operator"], threshold=errors_panel["threshold"]["value"]))
        if not failures.empty and "error_type" in failures:
            st.bar_chart(failures["error_type"].fillna("Unknown").value_counts(), y_label="errors")
        else:
            st.success("Không có request_failed trong cửa sổ hiện tại.")

    left, right = st.columns(2)
    with left:
        cost_panel = panels["cost"]
        costs = numeric(responses, "cost_usd")
        total_cost = float(costs.sum())
        st.subheader("4. Cost over time")
        st.metric("Total cost", f"${total_cost:.4f}")
        st.caption(threshold_message(total_cost, operator=cost_panel["threshold"]["operator"], threshold=cost_panel["threshold"]["value"]))
        if not costs.empty:
            cost_frame = responses.copy()
            cost_frame["cost_usd"] = pd.to_numeric(cost_frame["cost_usd"], errors="coerce")
            st.line_chart(cost_frame.set_index("ts")["cost_usd"].resample("1min").sum(), y_label="USD/min")

    with right:
        tokens_panel = panels["tokens"]
        tokens_in = numeric(responses, "tokens_in")
        tokens_out = numeric(responses, "tokens_out")
        total_tokens = float(tokens_in.sum() + tokens_out.sum())
        st.subheader("5. Input and output tokens")
        st.metric("Total tokens", f"{total_tokens:,.0f}")
        st.caption(threshold_message(total_tokens, operator=tokens_panel["threshold"]["operator"], threshold=tokens_panel["threshold"]["value"]))
        if not responses.empty:
            token_frame = responses.set_index("ts").copy()
            for column in ("tokens_in", "tokens_out"):
                if column in token_frame:
                    token_frame[column] = pd.to_numeric(token_frame[column], errors="coerce").fillna(0)
                else:
                    token_frame[column] = 0
            st.bar_chart(token_frame[["tokens_in", "tokens_out"]].resample("1min").sum(), y_label="tokens/min")

    quality_panel = panels["quality"]
    quality = numeric(responses, "quality_score")
    st.subheader("6. Quality proxy")
    if quality.empty:
        st.info("Chưa có quality_score trong event response_sent.")
    else:
        average_quality = float(quality.mean())
        st.metric("Average quality", f"{average_quality:.2f}")
        st.caption(threshold_message(average_quality, operator=quality_panel["threshold"]["operator"], threshold=quality_panel["threshold"]["value"]))
        quality_frame = responses.copy()
        quality_frame["quality_score"] = pd.to_numeric(quality_frame["quality_score"], errors="coerce")
        st.line_chart(quality_frame.set_index("ts")["quality_score"].resample("1min").mean(), y_label="score (0-1)")


st.set_page_config(page_title="Day 13 AI Observability", layout="wide")


@st.fragment(run_every=30)
def live_dashboard() -> None:
    """Refresh dashboard data every 30 seconds without a manual reload."""
    render_dashboard()


live_dashboard()
