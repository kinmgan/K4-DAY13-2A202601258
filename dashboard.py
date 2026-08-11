"""Runtime dashboard for the Day 13 observability lab.

Run with: streamlit run dashboard.py
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
import yaml


REPO_ROOT = Path(__file__).resolve().parent
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
CHALLENGE_PATH = REPO_ROOT / "config" / "challenge.json"
API_URL = "http://127.0.0.1:8000"


def apply_theme() -> None:
    """Keep the demo dashboard calm, readable, and projection-friendly."""
    st.markdown(
        """
        <style>
          .stApp { background: #f4f9fc; color: #17324d; }
          [data-testid="stHeader"] { background: rgba(244, 249, 252, 0.9); }
          .block-container { max-width: 1280px; padding-top: 2.2rem; padding-bottom: 3rem; }
          h1, h2, h3 { color: #12395b; letter-spacing: -0.02em; }
          h1 { font-size: 2.15rem !important; margin-bottom: 0.2rem !important; }
          h3 { font-size: 1.05rem !important; margin-top: 1.3rem !important; }
          [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d8e8f2;
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 4px 15px rgba(31, 91, 128, 0.06);
          }
          [data-testid="stMetricLabel"] { color: #57748c; }
          [data-testid="stMetricValue"] { color: #0b6e99; }
          [data-testid="stAlert"] {
            border-radius: 12px;
            border: 1px solid #cfe4f0;
          }
          .demo-banner {
            background: linear-gradient(105deg, #e8f6fc, #f8fcff);
            border: 1px solid #cfe7f5;
            border-radius: 16px;
            color: #315672;
            margin: 0.65rem 0 1.4rem;
            padding: 1rem 1.2rem;
          }
          .demo-banner strong { color: #0b6e99; }
          .stCaption { color: #638197 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


@st.cache_data
def load_demo_cases() -> list[dict[str, str]]:
    """Load the five released challenge requests without modifying the config."""
    if not CHALLENGE_PATH.exists():
        return []
    payload = json.loads(CHALLENGE_PATH.read_text(encoding="utf-8"))
    return list(payload.get("queries", []))


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


def render_chat() -> None:
    """Send demo messages to the FastAPI app that writes the dashboard logs."""
    st.subheader("Chat demo")
    st.caption("Mỗi tin nhắn gửi đến API sẽ tạo log và trace. Sau đó mở tab Dashboard để xem chỉ số cập nhật.")

    demo_cases = load_demo_cases()
    selected_case: dict[str, str] = {
        "user_id": "demo-user",
        "session_id": "dashboard-demo",
        "feature": "qa",
        "message": "",
    }
    send_selected_case = False
    if demo_cases:
        case_index = st.selectbox(
            "Chọn tình huống demo (5 case từ config/challenge.json)",
            options=range(len(demo_cases)),
            format_func=lambda index: f"Case {index + 1} — {demo_cases[index]['message']}",
        )
        selected_case = demo_cases[case_index]
        st.info(
            f"Feature: `{selected_case['feature']}` · User: `{selected_case['user_id']}` · "
            f"Session: `{selected_case['session_id']}`"
        )
        send_selected_case = st.button("Gửi tình huống đã chọn", type="primary")
    else:
        st.warning("Không tìm thấy config/challenge.json; bạn vẫn có thể nhập chat thủ công.")

    settings = st.columns(3)
    user_id = settings[0].text_input("User ID", value=selected_case["user_id"])
    session_id = settings[1].text_input("Session ID", value=selected_case["session_id"])
    feature = settings[2].selectbox(
        "Feature", options=["qa", "summary", "monitoring"], index=0
    )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("metrics"):
                st.caption(message["metrics"])

    prompt = selected_case["message"] if send_selected_case else st.chat_input("Hoặc nhập câu hỏi tùy ý...")
    if not prompt:
        return

    request_user_id = selected_case["user_id"] if send_selected_case else user_id
    request_session_id = selected_case["session_id"] if send_selected_case else session_id
    request_feature = selected_case["feature"] if send_selected_case else feature

    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = httpx.post(
                f"{API_URL}/chat",
                json={
                    "user_id": request_user_id,
                    "session_id": request_session_id,
                    "feature": request_feature,
                    "message": prompt,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            payload = response.json()
            metrics = (
                f"{payload['latency_ms']} ms · {payload['tokens_in']} input tokens · "
                f"{payload['tokens_out']} output tokens · ${payload['cost_usd']:.4f} · "
                f"quality {payload['quality_score']:.2f} · correlation ID: {payload['correlation_id']}"
            )
            st.markdown(payload["answer"])
            st.caption(metrics)
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": payload["answer"], "metrics": metrics}
            )
            load_logs.clear()
        except httpx.HTTPError as exc:
            st.error(
                "Không kết nối được API. Hãy chạy `python -m uvicorn app.main:app --reload --env-file .env` trước. "
                f"Chi tiết: {exc}"
            )

    if st.button("Xóa hội thoại", type="secondary"):
        st.session_state.chat_messages = []
        st.rerun()


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
    st.markdown(
        """
        <div class="demo-banner">
          <strong>Cách demo:</strong> nhìn dashboard để phát hiện chỉ số bất thường,
          mở trace Langfuse để xem bước chậm/lỗi, rồi dùng correlation ID để đối chiếu log.
        </div>
        """,
        unsafe_allow_html=True,
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
apply_theme()


@st.fragment(run_every=30)
def live_dashboard() -> None:
    """Refresh dashboard data every 30 seconds without a manual reload."""
    render_dashboard()


chat_tab, dashboard_tab = st.tabs(["💬 Chat demo", "📊 Dashboard"])
with chat_tab:
    render_chat()
with dashboard_tab:
    live_dashboard()
