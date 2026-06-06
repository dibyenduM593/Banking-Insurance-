"""
DAGOAT Bank & Insurance – Customer Service Chatbot
Run: streamlit run app.py
"""
from __future__ import annotations

import uuid
import streamlit as st
from src.chatbot import BankingChatbot
from src.schemas import (
    ChatSession,
    IntentCategory,
    GuardrailStatus,
    ChatResponse,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DAGOAT Bank & Insurance | ARIA Chatbot",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Main background */
.stApp { background: #f0f4f8; }

/* Chat container */
.chat-message {
    padding: 1rem 1.25rem;
    border-radius: 12px;
    margin-bottom: 0.75rem;
    max-width: 85%;
    line-height: 1.6;
    font-size: 0.95rem;
}
.chat-message.user {
    background: #1a56db;
    color: white;
    margin-left: auto;
    border-bottom-right-radius: 4px;
}
.chat-message.assistant {
    background: white;
    color: #1f2937;
    margin-right: auto;
    border-bottom-left-radius: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

/* Intent badge */
.intent-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Sidebar header */
.sidebar-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a56db;
    border-bottom: 2px solid #1a56db;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}

/* Alert boxes */
.guardrail-alert {
    background: #fef3cd;
    border-left: 4px solid #f59e0b;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    font-size: 0.875rem;
    color: #92400e;
}
.guardrail-danger {
    background: #fee2e2;
    border-left: 4px solid #ef4444;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    font-size: 0.875rem;
    color: #991b1b;
}
.guardrail-info {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    font-size: 0.875rem;
    color: #1e40af;
}

/* Sample question button */
.stButton > button {
    border-radius: 8px;
    font-size: 0.82rem;
    padding: 0.35rem 0.75rem;
    text-align: left;
    white-space: normal;
    height: auto;
}

/* Confidence bar track */
.conf-bar-track {
    background: #e5e7eb;
    border-radius: 4px;
    height: 6px;
    width: 100%;
}
.conf-bar-fill {
    border-radius: 4px;
    height: 6px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Intent display helpers ────────────────────────────────────────────────────
INTENT_META: dict[str, dict] = {
    "account_inquiry":     {"label": "Account",     "color": "#3b82f6", "emoji": "🏦"},
    "loan_credit":         {"label": "Loan/Credit",  "color": "#8b5cf6", "emoji": "💳"},
    "complaint_resolution":{"label": "Complaint",   "color": "#ef4444", "emoji": "📋"},
    "kyc_compliance":      {"label": "KYC",          "color": "#10b981", "emoji": "🔐"},
    "insurance":           {"label": "Insurance",    "color": "#f59e0b", "emoji": "🛡️"},
    "general":             {"label": "General",      "color": "#6b7280", "emoji": "💬"},
    "off_topic":           {"label": "Off-Topic",    "color": "#9ca3af", "emoji": "🚫"},
    "blocked":             {"label": "Blocked",      "color": "#dc2626", "emoji": "⛔"},
}

SAMPLE_QUESTIONS: list[tuple[str, str]] = [
    ("🏦", "What savings account types do you offer?"),
    ("💳", "I earn ₹70,000/month. Can I get a personal loan of ₹3 lakhs?"),
    ("📋", "I was charged twice for the same UPI transaction of ₹1,500."),
    ("🔐", "What documents are needed for KYC verification?"),
    ("🛡️", "How do I file a health insurance claim after hospitalization?"),
    ("🏠", "What is the current home loan interest rate?"),
    ("💰", "What is the EMI for a ₹10 lakh loan at 12% for 5 years?"),
    ("⚠️",  "My debit card was used without my permission!"),
    ("📄", "How do I open an NRI savings account?"),
    ("🔄", "How long does a NEFT transfer take?"),
]


def _get_intent_meta(intent_value: str) -> dict:
    return INTENT_META.get(intent_value, INTENT_META["general"])


# ── Session state initialization ──────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "chat_session" not in st.session_state:
    st.session_state.chat_session = ChatSession(session_id=st.session_state.session_id)

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []  # list of dicts: {role, content, response}

if "chatbot" not in st.session_state:
    try:
        st.session_state.chatbot = BankingChatbot()
        st.session_state.bot_error = None
    except ValueError as e:
        st.session_state.chatbot = None
        st.session_state.bot_error = str(e)

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center; padding: 1rem 0;'>
            <div style='font-size:2.5rem;'>🏦</div>
            <div style='font-size:1.1rem; font-weight:800; color:#1a56db;'>DAGOAT Bank</div>
            <div style='font-size:0.78rem; color:#6b7280;'>& Insurance Services</div>
            <hr style='margin:0.75rem 0;'>
            <div style='font-size:0.9rem; font-weight:600; color:#374151;'>
                ARIA — AI Resolution & Inquiry Assistant
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Try a sample question:**")
    for emoji, question in SAMPLE_QUESTIONS:
        if st.button(f"{emoji} {question}", key=f"sample_{question[:20]}", use_container_width=True):
            st.session_state.pending_question = question

    st.divider()

    # Last response metadata
    if st.session_state.display_messages:
        last = st.session_state.display_messages[-1]
        if last["role"] == "assistant" and last.get("response"):
            resp: ChatResponse = last["response"]
            meta = _get_intent_meta(resp.intent.value)

            st.markdown("**Last Response Details**")
            st.markdown(
                f"<span class='intent-badge' style='background:{meta['color']}22; color:{meta['color']};'>"
                f"{meta['emoji']} {meta['label']}</span>",
                unsafe_allow_html=True,
            )

            conf = resp.confidence
            conf_color = "#10b981" if conf >= 0.85 else "#f59e0b" if conf >= 0.65 else "#ef4444"
            st.markdown(f"**Confidence:** {conf:.0%}")
            st.markdown(
                f"<div class='conf-bar-track'><div class='conf-bar-fill' "
                f"style='width:{conf*100:.0f}%; background:{conf_color};'></div></div>",
                unsafe_allow_html=True,
            )

            if resp.requires_human_agent:
                st.warning("🔴 **Human Agent Required**")

            if resp.follow_up_questions:
                st.markdown("**Suggested follow-ups:**")
                for q in resp.follow_up_questions[:2]:
                    if st.button(f"→ {q}", key=f"followup_{q[:20]}", use_container_width=True):
                        st.session_state.pending_question = q

    st.divider()
    st.markdown(
        "<div style='font-size:0.72rem; color:#9ca3af;'>"
        "Session ID: " + st.session_state.session_id + "<br>"
        "Guardrails: PII Detection • Injection Defense • Off-Topic Filter<br>"
        "Backend: Ollama (local)"
        "</div>",
        unsafe_allow_html=True,
    )

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.chat_session = ChatSession(session_id=st.session_state.session_id)
        st.session_state.display_messages = []
        st.rerun()


# ── Main header ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style='background: linear-gradient(135deg, #1a56db 0%, #1e40af 100%);
                padding: 1.25rem 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
                display: flex; align-items: center; gap: 1rem;'>
        <div style='font-size: 2rem;'>🏦</div>
        <div>
            <div style='color: white; font-size: 1.3rem; font-weight: 700;'>
                DAGOAT Bank & Insurance
            </div>
            <div style='color: #bfdbfe; font-size: 0.85rem;'>
                ARIA – Customer Service & Complaint Resolution Assistant
            </div>
        </div>
        <div style='margin-left: auto; color: #bfdbfe; font-size: 0.78rem; text-align: right;'>
            🟢 Online<br>24/7 Support
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Bot initialization error ──────────────────────────────────────────────────
if st.session_state.bot_error:
    st.error(
        f"⚠️ **Configuration Error:** {st.session_state.bot_error}\n\n"
        "**Setup:** Make sure Ollama is running, then set `OLLAMA_MODEL` in your `.env` "
        "to a model you have pulled (run `ollama list` to see available models).",
        icon="🚨",
    )
    st.stop()

# ── Welcome message ───────────────────────────────────────────────────────────
if not st.session_state.display_messages:
    st.markdown(
        """
        <div style='background: white; border-radius: 12px; padding: 1.5rem;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 1rem;'>
            <p style='margin:0; color:#374151;'>
                👋 <strong>Hello! I'm ARIA</strong>, your DAGOAT Bank & Insurance assistant.<br><br>
                I can help you with:
            </p>
            <ul style='color:#374151; margin: 0.75rem 0 0 0;'>
                <li>🏦 <strong>Account queries</strong> — account types, opening, balances</li>
                <li>💳 <strong>Loans & credit</strong> — eligibility, EMI, interest rates</li>
                <li>📋 <strong>Complaint resolution</strong> — disputes, fraud, charges</li>
                <li>🔐 <strong>KYC</strong> — document requirements, verification</li>
                <li>🛡️ <strong>Insurance</strong> — policies, claims, coverage</li>
            </ul>
            <p style='margin: 0.75rem 0 0 0; color:#6b7280; font-size:0.85rem;'>
                Pick a sample question from the sidebar or type your own below.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Chat history display ──────────────────────────────────────────────────────
for msg in st.session_state.display_messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div class='chat-message user'>{msg['content']}</div>",
            unsafe_allow_html=True,
        )
    else:
        resp: ChatResponse = msg.get("response")

        # Guardrail alert banner
        if resp and resp.guardrail_result and not resp.guardrail_result.passed:
            gr = resp.guardrail_result
            if gr.status == GuardrailStatus.INJECTION_ATTEMPT:
                st.markdown(
                    f"<div class='guardrail-danger'>⛔ <strong>Security Alert:</strong> "
                    f"Potential prompt injection attempt detected and blocked.</div>",
                    unsafe_allow_html=True,
                )
            elif gr.status == GuardrailStatus.PII_DETECTED:
                st.markdown(
                    f"<div class='guardrail-alert'>🔒 <strong>Privacy Protection:</strong> "
                    f"Sensitive data detected: {', '.join(gr.pii_types)}. "
                    f"Message blocked to protect your information.</div>",
                    unsafe_allow_html=True,
                )
            elif gr.status == GuardrailStatus.OFF_TOPIC:
                st.markdown(
                    "<div class='guardrail-info'>ℹ️ <strong>Out of Scope:</strong> "
                    "Query is outside banking/insurance domain.</div>",
                    unsafe_allow_html=True,
                )

        # Main response bubble
        if resp:
            meta = _get_intent_meta(resp.intent.value)
            badge = (
                f"<span style='font-size:0.7rem; background:{meta['color']}22; "
                f"color:{meta['color']}; padding:2px 8px; border-radius:20px; "
                f"font-weight:600; text-transform:uppercase;'>"
                f"{meta['emoji']} {meta['label']}</span>"
            )
            escalation = (
                " &nbsp;<span style='font-size:0.7rem; background:#fee2e2; color:#dc2626; "
                "padding:2px 8px; border-radius:20px; font-weight:600;'>🔴 ESCALATE</span>"
                if resp.requires_human_agent else ""
            )
            answer_html = resp.answer.replace("\n", "<br>")
            st.markdown(
                f"<div class='chat-message assistant'>"
                f"<div style='margin-bottom:0.5rem;'>{badge}{escalation}</div>"
                f"{answer_html}"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Disclaimer
            if resp.disclaimer:
                st.markdown(
                    f"<div style='font-size:0.75rem; color:#9ca3af; margin:-0.5rem 0 0.5rem 0; "
                    f"padding-left:0.25rem;'>⚠️ {resp.disclaimer}</div>",
                    unsafe_allow_html=True,
                )

            # Structured details expander
            has_details = any([
                resp.structured_data,
                resp.loan_eligibility,
                resp.complaint_data,
                resp.insurance_data,
            ])
            if has_details:
                with st.expander("📊 View Structured Response Details", expanded=False):
                    col1, col2 = st.columns(2)

                    if resp.loan_eligibility:
                        with col1:
                            st.markdown("**Loan Assessment**")
                            le = resp.loan_eligibility
                            if le.monthly_income:
                                st.metric("Monthly Income", f"₹{le.monthly_income:,.0f}")
                            if le.max_eligible_amount:
                                st.metric("Max Eligible", f"₹{le.max_eligible_amount:,.0f}")
                            if le.emi_amount:
                                st.metric("EMI Amount", f"₹{le.emi_amount:,.0f}")
                            if le.eligible is not None:
                                st.metric("Eligible", "✅ Yes" if le.eligible else "❌ No")
                        if le.reasoning_steps:
                            with col2:
                                st.markdown("**Chain-of-Thought Reasoning**")
                                for step in le.reasoning_steps:
                                    st.markdown(f"• {step}")

                    if resp.structured_data and not resp.loan_eligibility:
                        st.markdown("**Key Details**")
                        st.json(resp.structured_data)
        else:
            st.markdown(
                f"<div class='chat-message assistant'>{msg['content']}</div>",
                unsafe_allow_html=True,
            )

# ── Chat input ────────────────────────────────────────────────────────────────
pending = st.session_state.pop("pending_question", None)

user_input = st.chat_input(
    "Ask about accounts, loans, insurance, complaints, KYC...",
    key="chat_input",
)

# Use sample question if clicked
if pending and not user_input:
    user_input = pending

if user_input:
    # Add user message to display
    st.session_state.display_messages.append({
        "role": "user",
        "content": user_input,
    })

    # Get response
    chatbot: BankingChatbot = st.session_state.chatbot
    with st.spinner("ARIA is thinking..."):
        try:
            response = chatbot.chat(user_input, st.session_state.chat_session)
            st.session_state.display_messages.append({
                "role": "assistant",
                "content": response.answer,
                "response": response,
            })
        except RuntimeError as e:
            st.session_state.display_messages.append({
                "role": "assistant",
                "content": f"⚠️ {e}",
                "response": None,
            })

    st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style='text-align:center; margin-top:2rem; padding-top:1rem;
                border-top:1px solid #e5e7eb; color:#9ca3af; font-size:0.75rem;'>
        DAGOAT Bank & Insurance Services | ARIA Chatbot v1.0 |
        Not financial advice. For regulated queries, consult a certified advisor.
        <br>Guardrails: PII Detection · Prompt Injection Defense · Off-Topic Filter
    </div>
    """,
    unsafe_allow_html=True,
)
