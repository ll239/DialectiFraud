import math
import os
import re

import pandas as pd
import streamlit as st
from anthropic import Anthropic

MODEL = "claude-sonnet-5"

st.set_page_config(
    page_title="DialectiFraud",
    page_icon="⚖️",
    layout="wide",
)

# ---------- styling ----------
st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; }
    .df-title { font-size: 2.6rem; font-weight: 800; text-align: center;
                margin-bottom: 0; color: #f0f2f6; letter-spacing: 0.5px; }
    .df-subtitle { text-align: center; color: #9aa4b2; font-size: 1.05rem;
                   margin-top: 0.2rem; margin-bottom: 1.8rem; }
    .df-panel { border-radius: 10px; padding: 1.1rem 1.3rem; height: 100%;
                border: 1px solid rgba(255,255,255,0.08); }
    .df-thesis { background: rgba(220, 38, 38, 0.10); border-top: 3px solid #dc2626; }
    .df-antithesis { background: rgba(22, 163, 74, 0.10); border-top: 3px solid #16a34a; }
    .df-synthesis { background: rgba(37, 99, 235, 0.12); border-top: 3px solid #2563eb; }
    .df-panel-title { font-weight: 700; font-size: 1.05rem; margin-bottom: 0.6rem; }
    .df-thesis .df-panel-title { color: #f87171; }
    .df-antithesis .df-panel-title { color: #4ade80; }
    .df-synthesis .df-panel-title { color: #60a5fa; }
    .df-panel-body { color: #d1d5db; font-size: 0.92rem; line-height: 1.5; white-space: pre-wrap; }
    .df-verdict { font-size: 1.3rem; font-weight: 800; margin-bottom: 0.4rem; }
    .df-footer { text-align: center; color: #6b7280; font-size: 0.78rem;
                 margin-top: 2.5rem; font-style: italic; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="df-title">DialectiFraud</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="df-subtitle">Dialectical Reasoning for Fraud Detection</div>',
    unsafe_allow_html=True,
)

# ---------- API key ----------
with st.sidebar:
    st.subheader("Configuration")
    default_key = os.environ.get("ANTHROPIC_API_KEY", "")
    api_key = st.text_input(
        "Anthropic API key",
        value=default_key,
        type="password",
        help="Reads from ANTHROPIC_API_KEY env var if set. Never stored.",
    )
    st.caption(f"Model: `{MODEL}`")

# ---------- shared engine ----------
THESIS_PROMPT = (
    "You are a fraud analyst reviewing a flagged transaction. Argue specifically why this "
    "transaction is suspicious and likely fraudulent. Give 3-4 specific reasons."
)

ANTITHESIS_PROMPT = (
    "You are a customer advocate reviewing the same transaction. Argue specifically why "
    "this transaction is legitimate and likely a false positive. Give 3-4 specific reasons."
)

SYNTHESIS_PROMPT = (
    "You are a senior risk officer. You have heard both arguments. Give a final verdict. "
    "Output in this exact structure:\n"
    "RISK: HIGH, MEDIUM, or LOW\n"
    "CONFIDENCE: a number 0-100 followed by a percent sign\n"
    "FALSE POSITIVE LIKELIHOOD: a number 0-100 followed by a percent sign\n"
    "ACTION: one line recommended action"
)


def call_claude(client: Anthropic, system_prompt: str, user_content: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def extract_percent(text: str, label: str, default: int = 50) -> int:
    match = re.search(rf"{label}[:\s]*([0-9]{{1,3}})\s*%", text, re.IGNORECASE)
    if match:
        return max(0, min(100, int(match.group(1))))
    return default


def extract_risk(text: str) -> str:
    match = re.search(r"RISK[:\s]*(HIGH|MEDIUM|LOW)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    upper = text.upper()
    for level in ("HIGH", "MEDIUM", "LOW"):
        if level in upper:
            return level
    return "MEDIUM"


def extract_action(text: str) -> str:
    match = re.search(r"ACTION[:\s]*(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().splitlines()[0]
    return ""


def run_dialectic(client: Anthropic, transaction_description: str):
    user_content = f"Transaction:\n{transaction_description}"
    thesis = call_claude(client, THESIS_PROMPT, user_content)
    antithesis = call_claude(client, ANTITHESIS_PROMPT, user_content)
    synthesis = call_claude(
        client,
        SYNTHESIS_PROMPT,
        f"{user_content}\n\nTHESIS (fraud analyst):\n{thesis}\n\nANTITHESIS (customer advocate):\n{antithesis}",
    )
    risk = extract_risk(synthesis)
    confidence = extract_percent(synthesis, "CONFIDENCE")
    fp_likelihood = extract_percent(synthesis, "FALSE POSITIVE LIKELIHOOD")
    action = extract_action(synthesis)
    return thesis, antithesis, synthesis, risk, confidence, fp_likelihood, action


RISK_COLORS = {"HIGH": "#f87171", "MEDIUM": "#facc15", "LOW": "#4ade80", "ERROR": "#9ca3af"}


def render_panels(thesis, antithesis, synthesis, risk, confidence, fp_likelihood, action, cols=None):
    col1, col2, col3 = cols if cols else st.columns(3)
    with col1:
        st.markdown(
            f'<div class="df-panel df-thesis"><div class="df-panel-title">⚠ THESIS — Fraud Analyst</div>'
            f'<div class="df-panel-body">{thesis}</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="df-panel df-antithesis"><div class="df-panel-title">✓ ANTITHESIS — Customer Advocate</div>'
            f'<div class="df-panel-body">{antithesis}</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        risk_color = RISK_COLORS.get(risk, "#9ca3af")
        action_html = f'<div class="df-panel-body"><b>Action:</b> {action}</div>' if action else ""
        st.markdown(
            f'<div class="df-panel df-synthesis"><div class="df-panel-title">⚖ SYNTHESIS — Final Verdict</div>'
            f'<div class="df-verdict" style="color:{risk_color}">{risk} RISK</div>'
            f'<div class="df-panel-body">{synthesis}</div>{action_html}</div>',
            unsafe_allow_html=True,
        )
        st.progress(confidence / 100, text=f"Confidence: {confidence}%")
        st.progress(fp_likelihood / 100, text=f"False positive likelihood: {fp_likelihood}%")


tab1, tab2 = st.tabs(["Single Transaction", "Batch Analysis (CSV)"])

# ================= TAB 1: single transaction =================
with tab1:
    example = (
        "$1,847.32 charged at an electronics retailer in Lagos, Nigeria at 3:47 AM. "
        "Cardholder's last transaction was 18 days ago, $42 at a grocery store in Denver, CO. "
        "This is an online, card-not-present transaction."
    )
    transaction_description = st.text_area(
        "Flagged transaction description",
        placeholder=example,
        height=110,
    )
    analyze = st.button("Run Dialectical Analysis", type="primary")

    if analyze:
        if not api_key:
            st.error("Enter your Anthropic API key in the sidebar first.")
        elif not transaction_description.strip():
            st.error("Enter a transaction description first.")
        else:
            client = Anthropic(api_key=api_key)
            with st.spinner("Running thesis → antithesis → synthesis..."):
                thesis, antithesis, synthesis, risk, confidence, fp_likelihood, action = run_dialectic(
                    client, transaction_description
                )
            render_panels(thesis, antithesis, synthesis, risk, confidence, fp_likelihood, action)

# ================= TAB 2: batch CSV =================
with tab2:
    st.caption(
        "Upload a transaction CSV. A naive baseline rule-flagger (mimics a legacy fraud "
        "system) flags a subset of rows. The dialectical engine re-analyzes a sample of "
        "those flags. If you map a ground-truth fraud column, you get a measured "
        "false-positive-reduction number instead of just plausible-sounding text."
    )

    uploaded = st.file_uploader("Transaction CSV", type=["csv"])

    def guess_column(columns, keyword_groups):
        lower_map = {c.lower(): c for c in columns}
        for keywords in keyword_groups:
            for kw in keywords:
                for lc, orig in lower_map.items():
                    if kw in lc:
                        return orig
        return None

    def haversine_miles(lat1, lon1, lat2, lon2):
        r = 3958.8
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
        return 2 * r * math.asin(math.sqrt(a))

    def bucket_hour(h):
        if 5 <= h < 12:
            return "morning"
        if 12 <= h < 18:
            return "afternoon"
        if 18 <= h < 24:
            return "night"
        return "midnight"

    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Couldn't read that CSV: {e}")
            df = None

        if df is not None and len(df) == 0:
            st.error("That CSV has no rows.")
            df = None

        if df is not None:
            st.success(f"Loaded {len(df):,} rows, {len(df.columns)} columns.")
            cols = list(df.columns)
            none_opt = "— none —"
            options = [none_opt] + cols

            st.markdown("**Map your columns** (best guesses pre-selected — check them)")
            m1, m2, m3 = st.columns(3)
            with m1:
                amount_col = st.selectbox(
                    "Amount *", cols,
                    index=cols.index(guess_column(cols, [["amt"], ["amount"], ["value"]]) or cols[0]),
                )
                merchant_col = st.selectbox(
                    "Merchant", options,
                    index=options.index(guess_column(cols, [["merchant"]]) or none_opt),
                )
                category_col = st.selectbox(
                    "Category / type", options,
                    index=options.index(guess_column(cols, [["category"], ["mcc"]]) or none_opt),
                )
            with m2:
                time_col = st.selectbox(
                    "Timestamp", options,
                    index=options.index(
                        guess_column(cols, [["trans_date_trans_time"], ["timestamp"], ["date"]]) or none_opt
                    ),
                )
                card_col = st.selectbox(
                    "Cardholder ID", options,
                    index=options.index(
                        guess_column(cols, [["cc_num"], ["card"], ["customer_id"], ["account"]]) or none_opt
                    ),
                )
                label_col = st.selectbox(
                    "Ground-truth fraud label (optional but recommended)", options,
                    index=options.index(guess_column(cols, [["is_fraud"], ["fraud"], ["label"], ["target"]]) or none_opt),
                )
            with m3:
                lat_col = st.selectbox("Cardholder lat (optional)", options,
                                        index=options.index(guess_column(cols, [["lat"]]) or none_opt))
                long_col = st.selectbox("Cardholder long (optional)", options,
                                         index=options.index(guess_column(cols, [["long"]]) or none_opt))
                merch_lat_col = st.selectbox("Merchant lat (optional)", options,
                                              index=options.index(guess_column(cols, [["merch_lat"]]) or none_opt))
                merch_long_col = st.selectbox("Merchant long (optional)", options,
                                               index=options.index(guess_column(cols, [["merch_long"]]) or none_opt))

            sample_size = st.slider("Sample size to run through the dialectical engine", 5, 50, 15)
            run_batch = st.button("Run Batch Dialectical Analysis", type="primary")

            if run_batch:
                if not api_key:
                    st.error("Enter your Anthropic API key in the sidebar first.")
                else:
                    work = df.copy()

                    work["_amount"] = pd.to_numeric(work[amount_col], errors="coerce")
                    work = work.dropna(subset=["_amount"])

                    if time_col != none_opt:
                        work["_ts"] = pd.to_datetime(work[time_col], errors="coerce")
                        work["_hour"] = work["_ts"].dt.hour
                        work["_bucket"] = work["_hour"].apply(lambda h: bucket_hour(h) if pd.notna(h) else None)
                    else:
                        work["_ts"] = pd.NaT
                        work["_bucket"] = None

                    if card_col != none_opt and time_col != none_opt:
                        work = work.sort_values([card_col, "_ts"])
                        work["_days_since_last"] = work.groupby(card_col)["_ts"].diff().dt.total_seconds() / 86400
                    else:
                        work["_days_since_last"] = None

                    has_geo = none_opt not in (lat_col, long_col, merch_lat_col, merch_long_col)
                    if has_geo:
                        for c in (lat_col, long_col, merch_lat_col, merch_long_col):
                            work[c] = pd.to_numeric(work[c], errors="coerce")
                        work["_distance"] = work.apply(
                            lambda r: haversine_miles(r[lat_col], r[long_col], r[merch_lat_col], r[merch_long_col])
                            if pd.notna(r[lat_col]) and pd.notna(r[merch_lat_col])
                            else None,
                            axis=1,
                        )
                    else:
                        work["_distance"] = None

                    if label_col != none_opt:
                        work["_ground_truth_fraud"] = work[label_col].astype(str).str.strip().isin(
                            ["1", "1.0", "true", "True", "TRUE", "Y", "yes"]
                        )
                    else:
                        work["_ground_truth_fraud"] = None

                    amt_threshold = work["_amount"].quantile(0.95)
                    flag_amount = work["_amount"] > amt_threshold
                    flag_time = work["_bucket"].isin(["night", "midnight"])
                    flag_recency = work["_days_since_last"].isna() | (work["_days_since_last"] > 20)
                    flag_distance = work["_distance"] > 100 if has_geo else pd.Series(False, index=work.index)

                    risk_score = (
                        flag_amount.astype(int)
                        + flag_time.fillna(False).astype(int)
                        + flag_recency.astype(int)
                        + flag_distance.fillna(False).astype(int)
                    )
                    work["_baseline_flag"] = risk_score >= 2
                    flagged = work[work["_baseline_flag"]]

                    st.info(
                        f"Baseline naive flagger caught {len(flagged):,} of {len(work):,} transactions "
                        f"({len(flagged) / max(1, len(work)):.1%}). Sampling {min(sample_size, len(flagged))} for re-analysis."
                    )

                    if len(flagged) == 0:
                        st.warning("No rows tripped the baseline flag rules — nothing to re-analyze.")
                    else:
                        if label_col != none_opt:
                            fp_pool = flagged[flagged["_ground_truth_fraud"] == False]
                            tp_pool = flagged[flagged["_ground_truth_fraud"] == True]
                            half = sample_size // 2
                            sample = pd.concat([
                                fp_pool.sample(min(half, len(fp_pool)), random_state=42) if len(fp_pool) else fp_pool,
                                tp_pool.sample(min(sample_size - half, len(tp_pool)), random_state=42) if len(tp_pool) else tp_pool,
                            ])
                            remaining = sample_size - len(sample)
                            if remaining > 0:
                                leftover = flagged.drop(sample.index)
                                sample = pd.concat([sample, leftover.sample(min(remaining, len(leftover)), random_state=42)])
                        else:
                            sample = flagged.sample(min(sample_size, len(flagged)), random_state=42)

                        client = Anthropic(api_key=api_key)
                        results = []
                        progress = st.progress(0, text="Starting batch analysis...")

                        for i, (idx, row) in enumerate(sample.iterrows()):
                            merchant_desc = str(row[merchant_col]) if merchant_col != none_opt else "unspecified merchant"
                            if category_col != none_opt:
                                merchant_desc += f" (category: {row[category_col]})"

                            bucket = row["_bucket"] if row["_bucket"] else "unknown time of day"
                            hour_str = f"{int(row['_hour']):02d}:00" if pd.notna(row.get("_hour")) else "unknown time"

                            if has_geo and pd.notna(row["_distance"]):
                                loc_desc = f"{row['_distance']:.0f} miles from cardholder's typical location"
                            else:
                                loc_desc = "distance from cardholder's typical location unknown"

                            days = row["_days_since_last"]
                            days_desc = "first known transaction on record for this cardholder" if pd.isna(days) else f"{days:.1f} days"

                            summary = (
                                f"Amount: ${row['_amount']:,.2f}\n"
                                f"Merchant: {merchant_desc}\n"
                                f"Time: {hour_str} ({bucket})\n"
                                f"Location: {loc_desc}\n"
                                f"Days since cardholder's last transaction: {days_desc}"
                            )

                            progress.progress((i) / len(sample), text=f"Analyzing row {i + 1}/{len(sample)}...")
                            try:
                                thesis, antithesis, synthesis, risk, confidence, fp_likelihood, action = run_dialectic(
                                    client, summary
                                )
                            except Exception as e:
                                if i == 0:
                                    progress.empty()
                                    st.error(f"API call failed on the first row — check your API key. Details: {e}")
                                    st.stop()
                                thesis = antithesis = synthesis = f"Error: {e}"
                                risk, confidence, fp_likelihood, action = "ERROR", 0, 0, ""

                            results.append({
                                "row": idx,
                                "amount": row["_amount"],
                                "merchant": merchant_desc,
                                "ground_truth_fraud": row["_ground_truth_fraud"] if label_col != none_opt else None,
                                "risk": risk,
                                "confidence": confidence,
                                "fp_likelihood": fp_likelihood,
                                "action": action,
                                "thesis": thesis,
                                "antithesis": antithesis,
                                "synthesis": synthesis,
                                "summary": summary,
                            })
                            progress.progress((i + 1) / len(sample), text=f"Analyzed {i + 1}/{len(sample)}")

                        progress.empty()
                        results_df = pd.DataFrame(results)
                        if (results_df["risk"] == "ERROR").any():
                            n_err = (results_df["risk"] == "ERROR").sum()
                            st.warning(f"{n_err} row(s) failed mid-batch (see detail below) — results for the rest are still valid.")
                        st.session_state["batch_results"] = results_df
                        st.session_state["batch_has_labels"] = label_col != none_opt

    if "batch_results" in st.session_state:
        results_df = st.session_state["batch_results"]
        has_labels = st.session_state.get("batch_has_labels", False)

        st.markdown("### Results")

        if has_labels:
            fp_mask = results_df["ground_truth_fraud"] == False
            tp_mask = results_df["ground_truth_fraud"] == True
            fp_total = fp_mask.sum()
            tp_total = tp_mask.sum()
            fp_cleared = ((fp_mask) & (results_df["risk"] == "LOW")).sum()
            tp_retained = ((tp_mask) & (results_df["risk"].isin(["HIGH", "MEDIUM"]))).sum()
            tp_missed = ((tp_mask) & (results_df["risk"] == "LOW")).sum()

            k1, k2, k3 = st.columns(3)
            k1.metric(
                "False positives correctly cleared",
                f"{fp_cleared}/{fp_total}" if fp_total else "n/a",
                f"{fp_cleared / fp_total:.0%}" if fp_total else None,
            )
            k2.metric(
                "True fraud still caught",
                f"{tp_retained}/{tp_total}" if tp_total else "n/a",
                f"{tp_retained / tp_total:.0%}" if tp_total else None,
            )
            k3.metric(
                "True fraud wrongly cleared",
                f"{tp_missed}/{tp_total}" if tp_total else "n/a",
                f"-{tp_missed / tp_total:.0%}" if tp_total else None,
                delta_color="inverse",
            )
            st.caption(
                "'False positives correctly cleared' is the headline number: of the baseline "
                "flagger's false alarms in this sample, how many did the dialectical re-score "
                "correctly downgrade to LOW risk."
            )

        st.dataframe(
            results_df[["row", "amount", "merchant", "ground_truth_fraud", "risk", "confidence", "fp_likelihood", "action"]],
            use_container_width=True,
        )

        st.download_button(
            "Download results as CSV",
            results_df.drop(columns=["thesis", "antithesis", "synthesis", "summary"]).to_csv(index=False),
            file_name="dialectifraud_batch_results.csv",
            mime="text/csv",
        )

        st.markdown("**Row-by-row detail**")
        for _, r in results_df.iterrows():
            label = f"Row {r['row']} — ${r['amount']:,.2f} at {r['merchant']} — {r['risk']} risk ({r['confidence']}%)"
            with st.expander(label):
                render_panels(
                    r["thesis"], r["antithesis"], r["synthesis"],
                    r["risk"], r["confidence"], r["fp_likelihood"], r["action"],
                )

st.markdown(
    '<div class="df-footer">Based on Microsoft Research Hegelian Dialectic Framework (ICML 2025)</div>',
    unsafe_allow_html=True,
)
