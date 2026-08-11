# Alert and Runbook

Each alert is symptom-based: it detects a user-facing or SLO-related problem first, then uses metrics, traces, and logs to identify the cause.

## Alert 1: High chat latency

- Severity: Warning.
- Related SLI/SLO: P95 latency <= 3000 ms; 99.5% target over 28 days.
- Condition and duration: P95 chat latency exceeds 3000 ms for 5 consecutive minutes.
- User impact: Requests in the slowest 5% take more than three seconds to receive an answer.
- First checks:
  1. Identify when P95/P99 increased and compare it with traffic.
  2. Open a slow Langfuse trace and compare `retrieve-context` and `generate-response` duration.
  3. Locate log records with the same correlation ID to confirm feature, input context, and any error.
- Temporary mitigation: Disable the incident or slow feature, reduce concurrency, or use a faster fallback if available.
- Owner: Dashboard, SLO & Alert owner.

## Alert 2: Elevated chat error rate

- Severity: Critical.
- Related SLI/SLO: Error rate <= 2%; 99.0% target over 28 days.
- Condition and duration: Chat error rate exceeds 2% for 5 consecutive minutes.
- User impact: Users receive no answer or an HTTP 500 response.
- First checks:
  1. Inspect the Errors panel to identify the dominant `error_type`.
  2. Open a recent failing trace to identify the failed observation.
  3. Find the `request_failed` log record using its correlation ID.
- Temporary mitigation: Disable the failing incident or external dependency, use the local fallback, or roll back the recent change.
- Owner: Dashboard, SLO & Alert owner.

## Alert 3: Daily LLM cost budget exceeded

- Severity: Warning.
- Related SLI/SLO: Daily LLM cost <= 2.5 USD.
- Condition and duration: Total `cost_usd` for the current day exceeds 2.5 USD.
- User impact: No immediate functional failure, but the service risks exceeding its operating budget and may need usage limits.
- First checks:
  1. Compare Cost and Traffic to see whether cost grew faster than demand.
  2. Inspect input and output token totals, especially `tokens_out`.
  3. Open a generation trace to check model, prompt version, and usage details.
- Temporary mitigation: Limit output length, reduce retrieved context, or roll back the prompt/model change that increased tokens.
- Owner: Dashboard, SLO & Alert owner.
