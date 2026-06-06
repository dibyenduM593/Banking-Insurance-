# DAGOAT Bank & Insurance — ARIA Chatbot

**ARIA** (Automated Resolution & Inquiry Assistant) is a production-quality banking and insurance customer service chatbot built with Anthropic's Claude API, Streamlit, and Pydantic.

---

## Features

| Feature | Implementation |
|---------|---------------|
| **Prompt Engineering** | Role-setting system prompt with output format, safety rules, regulatory context |
| **Few-Shot Learning** | 5 intent categories × 2 examples each in `config/prompts.yaml` |
| **Chain-of-Thought** | Explicit 6-step loan eligibility reasoning (FOIR, EMI formula, credit score) |
| **Structured Output** | Pydantic v2 `ChatResponse` model with nested schemas |
| **PII Guardrails** | Regex detection for Aadhaar, PAN, credit cards, phone numbers, email |
| **Injection Defense** | Pattern matching for 10+ prompt injection signatures |
| **Off-Topic Filter** | Banking keyword list + greeting bypass |
| **Streamlit UI** | Chat interface with intent badges, confidence bars, structured detail panels |
| **Session History** | Multi-turn conversation with Claude API message history |

---

## Project Structure

```
Insurance-Banking Chatbot/
├── app.py                    # Streamlit application
├── requirements.txt
├── .env.example              # Environment template
├── config/
│   └── prompts.yaml          # System prompt, few-shot examples, CoT template
├── src/
│   ├── __init__.py
│   ├── schemas.py            # Pydantic models (ChatResponse, GuardrailResult, etc.)
│   ├── guardrails.py         # PII detection, injection defense, off-topic filter
│   └── chatbot.py            # BankingChatbot engine (Claude API integration)
└── evaluation/
    └── eval_report.md        # 20-query evaluation report
```

---

## Setup

### 1. Clone the repository
```bash
git clone <repository-url>
cd "Insurance-Banking Chatbot"
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-4-6
MAX_TOKENS=2048
TEMPERATURE=0.3
```

### 5. Run the app
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────────┐
│       Guardrail Layer        │
│  PII Detection (regex)       │
│  Injection Defense (regex)   │
│  Off-Topic Filter (keywords) │
└────────────┬────────────────┘
             │ Clean input
             ▼
┌─────────────────────────────┐
│     BankingChatbot Engine    │
│  - Load prompts.yaml         │
│  - Build system prompt       │
│    (role + few-shot + CoT)   │
│  - Claude API call           │
│  - JSON extraction           │
└────────────┬────────────────┘
             │ Raw JSON
             ▼
┌─────────────────────────────┐
│    Pydantic Validation       │
│  ChatResponse model          │
│  LoanEligibilityData (CoT)   │
│  ComplaintData               │
└────────────┬────────────────┘
             │ Typed response
             ▼
┌─────────────────────────────┐
│       Streamlit UI           │
│  Intent badge + confidence   │
│  Structured detail panels    │
│  Guardrail alert banners     │
│  Follow-up suggestions       │
└─────────────────────────────┘
```

---

## Intent Categories

| Intent | Examples |
|--------|---------|
| `account_inquiry` | Account types, opening, closing, statements |
| `loan_credit` | Personal/home/auto loans, EMI, eligibility, interest rates |
| `complaint_resolution` | Disputes, fraud, unauthorized transactions, charges |
| `kyc_compliance` | KYC documents, verification, AML queries |
| `insurance` | Health/life/motor insurance, claims, premiums |
| `general` | Greetings, help, general queries |

---

## Guardrails

### PII Detection
Detects and blocks: Aadhaar numbers, PAN cards, credit card numbers, phone numbers, email addresses, bank account numbers, IFSC codes, passport numbers.

### Prompt Injection Defense
Blocks patterns including:
- "Ignore previous instructions"
- "Forget your role"
- "Act as a different AI"
- "Reveal your system prompt"
- Jailbreak attempts (DAN mode, etc.)

### Off-Topic Filter
Checks for 80+ banking/insurance keywords. Allows greetings and short queries to pass through without blocking.

---

## Prompt Template Library

The `config/prompts.yaml` file contains:
- **`system_prompt`** — Full role-setting prompt with output format specification
- **`chain_of_thought_template`** — 6-step loan eligibility reasoning chain with standard rates
- **`few_shot_examples`** — 5 categories × 2 examples each (account, loan, complaint, KYC, insurance)
- **`off_topic_response`** — Template for graceful off-topic deflection

---

## Evaluation

See [`evaluation/eval_report.md`](evaluation/eval_report.md) for the full 20-query evaluation.

**Summary results:**
- Average Accuracy: **4.73 / 5**
- JSON Format Score: **5.0 / 5** (100% valid, all fields present)
- Guardrail Pass Rate: **100%** (5/5 blocking tests passed)
- False Positive Rate: **0%** (no legitimate queries blocked)

---

## Sample Queries to Try

```
What types of savings accounts do you offer?
I earn ₹70,000/month. Can I get a personal loan of ₹3 lakhs?
I was charged twice for the same UPI transaction of ₹1,500.
What documents are needed for KYC verification?
How do I file a health insurance claim after hospitalization?
My debit card was used without my permission!
What is the EMI for a ₹10 lakh loan at 12% for 5 years?
How long does a NEFT transfer take?
```

---

## Tech Stack

- **LLM:** Anthropic Claude (claude-sonnet-4-6)
- **UI:** Streamlit 1.32+
- **Validation:** Pydantic v2
- **Config:** PyYAML
- **Environment:** python-dotenv
- **Guardrails:** Python `re` (regex)

---

## License

MIT License. For educational and demonstration purposes.
