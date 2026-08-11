import streamlit as st
import pandas as pd
import json
from pathlib import Path
import os

# --- Configuration ---
st.set_page_config(page_title="AI Observability Dashboard", layout="wide")
st.title("Day 13 AI Observability Dashboard")
st.markdown("Dashboard for Monitoring RAG System (6 Panels)")

if st.button("Refresh Data"):
    st.rerun()

# --- Load Data ---
@st.cache_data(ttl=5) # Cache data for 5 seconds to simulate auto-refresh if re-run
def load_data():
    log_file = Path("data/logs.jsonl")
    if not log_file.exists():
        return pd.DataFrame()
    
    data = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except:
                    pass
    
    if not data:
        return pd.DataFrame()
        
    df = pd.DataFrame(data)
    df['ts'] = pd.to_datetime(df['ts'])
    return df

df = load_data()

if df.empty:
    st.warning("No data found in data/logs.jsonl")
    st.stop()

# Filter last 60 minutes based on the max timestamp in the dataset
max_ts = df['ts'].max()
last_60m = max_ts - pd.Timedelta(minutes=60)
df = df[df['ts'] >= last_60m].copy()

# Add a minute column for aggregations
df['minute'] = df['ts'].dt.floor('min')

# --- 1. Latency (P50, P95, P99) ---
st.subheader("1. Latency Percentiles (SLO P95 <= 3000ms)")
df_resp = df[df['event'] == 'response_sent'].copy()

if not df_resp.empty:
    latency_stats = df_resp.groupby('minute')['latency_ms'].quantile([0.50, 0.95, 0.99]).unstack()
    latency_stats.columns = ['P50', 'P95', 'P99']
    latency_stats['SLO (3000ms)'] = 3000
    st.line_chart(latency_stats)
else:
    st.info("No response_sent events found.")

# --- 2. Traffic ---
st.subheader("2. Request Traffic (SLO >= 1 req/min)")
df_req = df[df['event'] == 'request_received'].copy()
if not df_req.empty:
    traffic = df_req.groupby('minute').size().rename("Requests/min").to_frame()
    traffic['SLO (1 req/min)'] = 1
    st.line_chart(traffic)
else:
    st.info("No request_received events found.")

# --- 3. Errors ---
st.subheader("3. Error Rate & Breakdown (SLO <= 2%)")
req_count = len(df_req)
df_fail = df[df['event'] == 'request_failed'].copy()
fail_count = len(df_fail)

col1, col2 = st.columns(2)
with col1:
    error_rate = (fail_count / req_count * 100) if req_count > 0 else 0
    st.metric(label="Error Rate (%)", value=f"{error_rate:.2f}%", delta=f"{error_rate - 2:.2f}% vs SLO", delta_color="inverse")
    
with col2:
    if not df_fail.empty and 'error_type' in df_fail.columns:
        breakdown = df_fail['error_type'].value_counts()
        st.write("Error Breakdown:")
        st.dataframe(breakdown)
    else:
        st.write("No errors recorded.")

# --- 4. Cost ---
st.subheader("4. Cost Over Time (SLO Total <= $2.5)")
if not df_resp.empty and 'cost_usd' in df_resp.columns:
    cost_total = df_resp['cost_usd'].sum()
    st.metric(label="Total Cost (USD)", value=f"${cost_total:.4f}", delta=f"{cost_total - 2.5:.4f} USD vs SLO", delta_color="inverse")
    
    cost_series = df_resp.groupby('minute')['cost_usd'].sum().cumsum().rename("Cumulative Cost")
    st.line_chart(cost_series)
else:
    st.info("No cost data available.")

# --- 5. Tokens ---
st.subheader("5. Input & Output Tokens (SLO Total <= 50,000)")
if not df_resp.empty and 'tokens_in' in df_resp.columns and 'tokens_out' in df_resp.columns:
    total_in = df_resp['tokens_in'].sum()
    total_out = df_resp['tokens_out'].sum()
    total_tokens = total_in + total_out
    
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Total Tokens", f"{total_tokens:,.0f}", delta=f"{total_tokens - 50000:,.0f} vs SLO", delta_color="inverse")
    col_t2.metric("Tokens In", f"{total_in:,.0f}")
    col_t3.metric("Tokens Out", f"{total_out:,.0f}")
else:
    st.info("No token data available.")

# --- 6. Quality Proxy ---
st.subheader("6. Quality Proxy (SLO Mean >= 0.75)")
if not df_resp.empty and 'quality_score' in df_resp.columns:
    mean_quality = df_resp['quality_score'].mean()
    st.metric("Mean Quality Score", f"{mean_quality:.2f}", delta=f"{mean_quality - 0.75:.2f} vs SLO", delta_color="normal")
    
    quality_series = df_resp.groupby('minute')['quality_score'].mean().rename("Mean Quality")
    quality_series = quality_series.to_frame()
    quality_series['SLO (0.75)'] = 0.75
    st.line_chart(quality_series)
else:
    st.info("No quality score data available.")
