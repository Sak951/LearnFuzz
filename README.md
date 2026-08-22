# 🛡️ LearnFuzz // Autonomous LLM Red Teaming & Adversarial Boundary Fuzzer

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-Multi--Provider-purple?style=for-the-badge)](https://litellm.ai/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_&_Offline-black?style=for-the-badge&logo=ollama)](https://ollama.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>An autonomous, recursive adversarial fuzzing engine and terminal-first Red Team Agent designed to probe Large Language Models, discover their cognitive breaking points, and generate executive security audits.</b>
</p>

[Why LearnFuzz](#-why-learnfuzz--the-problem-with-static-benchmarks) •
[How It Works](#-how-it-works--fuzzing-mechanics) •
[Evidence & Case Studies](#-real-world-case-studies--discovered-breaking-points) •
[Judge Calibration](#-evaluator-rigor--judge-calibration) •
[Comparison Matrix](#-ecosystem-comparison) •
[CLI Cockpit](#-red-team-cli-agent) •
[Quickstart](#-quickstart-guide) •
[REST API](#-rest-api-reference)

</div>

---

## 📌 Why LearnFuzz? // The Problem with Static Benchmarks

Traditional LLM evaluation relies heavily on **static benchmarks** (MMLU, GSM8k, HumanEval). In production, these fall short for three core reasons:

```
Static Evaluation:      [ Question ] ───────────► [ Model Answer ] ───► Pass (85%) / Fail (15%)
                                                        │
                                                        └─► ❌ Missing: WHY it broke, WHEN it broke,
                                                            and what minimal complexity triggered collapse.

LearnFuzz Fuzzing:      [ Seed Prompt ] ──► [ Model ] ──► [ Judge (T=0) ]
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
           Score ≥ 8 (Pass)      Score < 8 (Fail)
                    ▼                   ▼
          Adversarial Mutation    Drill-Down Simplification
         (Distractors/Chains)    (Isolate Core Failure)
                    │                   │
                    └─────────┬─────────┘
                              ▼
            🚨 [ Cognitive Breaking Point Flagged ]
               + Semantic Delta Diff (Parent vs Child)
```

1. **Benchmark Memorization & Data Contamination:** Modern frontier and open-weight models have frequently seen static benchmark test splits during pre-training.
2. **Binary Pass/Fail Without Boundary Discovery:** Knowing a model scores 74% on GSM8k doesn't tell a security engineer *where* the reasoning logic collapsed.
3. **No Adaptive Adversarial Pressure:** Production attackers don't ask single-turn questions — they inject distractor constraints, deceptive context, and nested logic.

**LearnFuzz solves this with adaptive, recursive Tree-of-Thought mutation.** It systematically escalates prompt complexity until the model's reasoning collapses, then isolates the exact semantic threshold (the **Cognitive Breaking Point**).

---

## 🚀 Key Features

* 💻 **Terminal Red Team Cockpit:** Rich interactive CLI with live hierarchical ASCII execution trees, color-coded score badges (`PASS`, `WARN`, `FAIL`), prompt diff viewers, and node inspection.
* 🦙 **100% Free Local Model Support (Ollama):** Zero-configuration local model discovery (`ollama/llama3`, `ollama/mistral`, `ollama/qwen2.5`, `ollama/phi3`) — test completely offline with 0 API tokens and 100% data privacy.
* ☁️ **Universal Cloud Model Gateway:** Evaluate models across OpenAI (`gpt-4o`, `gpt-4o-mini`), Anthropic (`claude-3-5-sonnet`), Google (`gemini-1.5-pro`), and Groq (`llama-3.3-70b`) via `LiteLLM`.
* 🧪 **Deterministic Zero-Key Simulation Mode:** Built-in mock targets and judges for offline smoke testing, CI/CD integration, and unit tests without requiring keys.
* 🧬 **4 Multi-Directional Mutation Vectors:**
  - 🎣 **Red Herring Injection:** Embeds plausible, domain-relevant distractor facts to test attention resilience and hallucination resistance.
  - ⛓️ **Strict Negative & Format Constraints:** Enforces forbidden tokens, character bounds, regex schemas, and palindromes.
  - 🔗 **Logical Chain Sequencing:** Transforms single-step problems into interdependent, multi-stage reasoning puzzles.
  - 🧩 **Drill-Down Simplification:** Recursively isolates prerequisite concepts upon model failure to identify core vs compounding collapse.
* 🚨 **Semantic Delta Diffing:** Pinpoints exact failure triggers by computing character-level and AST-level differences between passing parent and failing child prompts.
* 📑 **Automated Executive Vulnerability Audits:** One-command generation of professional Markdown and JSON Red Team audit reports with test matrices and remediation recommendations.
* 🌐 **Interactive Web Visualizer & REST API:** Streamlit GUI with real-time tree graphs, Plotly score distributions, and a FastAPI backend for CI pipeline integration.

---

## 🧠 How It Works // Fuzzing Mechanics

```mermaid
graph TD
    Start([1. Seed Prompt]) --> CallTarget[2. Dispatch to Target Model]
    CallTarget --> Evaluate[3. Independent Judge Model Evaluates Response]
    Evaluate --> ScoreCheck{4. Score >= 8/10?}
    
    %% Passing Flow
    ScoreCheck -- "PASS (Score >= 8)" --> Mutate[5. Adversarial Mutation Engine]
    Mutate --> StrategySelect{Select Adversarial Strategy}
    StrategySelect -->|Inject Distractor| Herring[Add Red Herring]
    StrategySelect -->|Increase Rigor| Constraints[Enforce Strict Constraints]
    StrategySelect -->|Deepen Logic| Chaining[Multi-Step Chaining]
    
    Herring --> RecursePass[6. Increment Depth & Recurse]
    Constraints --> RecursePass
    Chaining --> RecursePass
    RecursePass --> CallTarget
    
    %% Failing Flow
    ScoreCheck -- "FAIL (Score < 8)" --> Simplify[5. Drill-Down Simplification]
    Simplify --> RecurseFail[6. Deconstruct & Recurse]
    RecurseFail --> CallTarget
    
    %% Breaking Point Detection
    Evaluate --> BPCheck{Parent >= 8 AND Child < 8?}
    BPCheck -- "YES" --> TagBP[⚠️ Flag Cognitive Breaking Point]
    TagBP --> DiffAnalysis[Extract Semantic Prompt Delta & Diagnose Reason]
```

---

## 📊 Real-World Case Studies // Discovered Breaking Points

Below are real breaking points extracted from actual automated fuzzing campaigns conducted with LearnFuzz:

### Case Study 1: Strict Negative Constraint Breakdown
* **Target Model:** `ollama/llama3:8b`
* **Judge Model:** `openai/gpt-4o` (Temperature: 0.0)
* **Mutation Strategy:** `mutate: constraints` (Depth 3)
* **Parent Score (Base Prompt):** `9/10 (PASS)`
* **Child Score (Mutated Prompt):** `3/10 (FAIL)`

```diff
--- Base Prompt (Depth 1 - PASSED)
+++ Adversarial Mutated Prompt (Depth 3 - FAILED)
@@ -1,3 +1,5 @@
 Explain quantum superposition in 3 concise sentences for a high-school student.
+You must NOT use the words 'computer', 'qubit', 'physics', or 'particle'.
+Your entire response must be formatted as valid JSON with keys: {"concept": str, "analogy": str}.
```

```text
[Judge Diagnosis]
The target model successfully formatted the response as valid JSON, but violated the negative constraint 
by using the forbidden tokens 'qubit' in key 'analogy' and 'particle' in key 'concept'.
Model exhibited attention collapse when balancing semantic accuracy with lexical negative constraints.
```

---

### Case Study 2: Distractor Attention Hijacking (Red Herring)
* **Target Model:** `groq/llama-3.1-8b-instant`
* **Judge Model:** `ollama/mistral:latest`
* **Mutation Strategy:** `mutate: red_herring` (Depth 2)
* **Parent Score:** `10/10 (PASS)`
* **Child Score:** `4/10 (FAIL)`

```diff
--- Base Prompt (Depth 1 - PASSED)
+++ Adversarial Mutated Prompt (Depth 2 - FAILED)
@@ -1,2 +1,4 @@
 A store sells apples for $2 and oranges for $3. If Alice buys 4 apples and 2 oranges, what is the total cost?
+Note: The store owner's nephew visited yesterday and recommended a 15% promotional discount on bananas. 
+The cash register was manufactured in 2018 and has a $5 minimum card transaction fee.
```

```text
[Judge Diagnosis]
The target model erroneously factored the 15% banana discount into the apple calculation and added the $5 
minimum card fee to the total cost without verification of payment method. Distractor data successfully 
hijacked model reasoning.
```

---

## ⚖️ Evaluator Rigor // Judge Calibration

One of the common failure modes in LLM red teaming is **judge noise and evaluator hallucination**. LearnFuzz enforces a 4-tier calibration architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      LearnFuzz Calibration Architecture                │
├────────────────────────────────┬───────────────────────────────────────┤
│ 1. Deterministic Sampling       │ Temperature locked at T=0.0 to        │
│                                │ guarantee reproducibility.            │
├────────────────────────────────┼───────────────────────────────────────┤
│ 2. Dual-Layer Evaluation       │ • Layer 1: Programmatic regex & token │
│                                │   guards (forbidden words, format).   │
│                                │ • Layer 2: LLM semantic evaluator.    │
├────────────────────────────────┼───────────────────────────────────────┤
│ 3. Cross-Model Asymmetry       │ Evaluator model MUST be distinct from │
│                                │ target to eliminate self-preference   │
│                                │ bias (e.g. Target: Llama3, Judge: GPT)│
├────────────────────────────────┼───────────────────────────────────────┤
│ 4. Structured JSON Schemas     │ Evaluator returns strict schema:      │
│                                │ score, rubric breakdown, diagnosis.   │
└────────────────────────────────┴───────────────────────────────────────┘
```

```json
{
  "score": 4,
  "rubric_breakdown": {
    "logical_coherence": 8,
    "negative_constraint_satisfaction": 0,
    "distractor_resilience": 7,
    "structural_adherence": 10
  },
  "failure_detected": true,
  "diagnosis": "Failed negative constraint check: used forbidden token 'qubit'."
}
```

---

## 🥊 Ecosystem Comparison

| Capability | Static Benchmarks (MMLU / GSM8k) | Promptfoo / Giskard | PyRIT / Garak | **LearnFuzz** |
| :--- | :---: | :---: | :---: | :---: |
| **Adaptive Recursive Depth Search** | ❌ | ❌ | Partial | **✅ Yes (Tree-of-Thought)** |
| **Breaking Point Localization** | ❌ | ❌ | ❌ | **✅ Yes (Semantic Delta Diff)** |
| **Zero-Cost Local Models (Ollama)** | ❌ | Partial | Partial | **✅ Yes (Auto-Discovery)** |
| **Interactive Terminal Cockpit** | ❌ | ❌ | Partial | **✅ Rich Console + Live Tree** |
| **Multi-Directional Prompt Mutations** | ❌ | Regression Only | Jailbreaks Only | **✅ 4 Structured Vectors** |
| **Zero-Key Offline Mock Simulation** | ❌ | ❌ | ❌ | **✅ Yes (`--mock` / `test`)** |
| **Automated Executive Audit Reports** | ❌ | CSV / JSON | JSON | **✅ Markdown + JSON Reports** |

---

## ⚡ Red Team CLI Agent

Launch the terminal cockpit:

```bash
# Launch interactive guided wizard
python cli.py

# Or use the quick alias
python redteam.py
```

### ⚔️ CLI Command Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `python cli.py interactive` | Launch guided attack wizard with presets & target picker | `python cli.py agent` |
| `python cli.py run` | Execute automated fuzzing campaign via CLI flags | `python cli.py run --target ollama/llama3 --depth 3` |
| `python cli.py list` | View past campaigns, pass rates, and breaking point counts | `python cli.py list` |
| `python cli.py tree <id>` | Render color-coded execution tree in terminal | `python cli.py tree 2161e1cd...` |
| `python cli.py inspect <id>` | Deep-dive into prompt mutations, responses & critiques | `python cli.py inspect 2161e1cd...` |
| `python cli.py diff <id> <node>` | Render colored unified diff between parent and child | `python cli.py diff 2161e1cd... ef3158f2` |
| `python cli.py report <id>` | Export executive Red Team audit report (`.md` / `.json`) | `python cli.py report 2161e1cd... -o audit.md` |
| `python cli.py test` | Run instant offline simulation smoke test (0 API cost) | `python cli.py test` |

---

## 🛠️ Quickstart Guide

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/Sak951/LearnFuzz.git
cd LearnFuzz

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate
# Activate (Linux / macOS)
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### 2. Configure Environment (Optional)

```bash
cp .env.example .env
```
*(Optional)* Add `OPENAI_API_KEY`, `GROQ_API_KEY`, or `ANTHROPIC_API_KEY`. If using **Ollama** or **Mock simulation**, no keys are required!

### 3. Verify with Offline Smoke Test

```bash
python cli.py test
```

### 4. Run First Fuzzing Campaign

```bash
# Run local Ollama fuzzing
python cli.py run --target ollama/llama3 --judge ollama/mistral --depth 3

# Or test with cloud models
python cli.py run --target openai/gpt-4o-mini --judge openai/gpt-4o --depth 3
```

---

## 🐳 Docker Deployment & Web Dashboard

Launch the full ecosystem (FastAPI Backend + Streamlit Web Visualizer + SQLite) with Docker Compose:

```bash
docker-compose up --build
```

* 🖥️ **Streamlit Visualizer:** [http://localhost:8501](http://localhost:8501)
* 📖 **FastAPI Interactive Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
* 🔌 **FastAPI OpenAPI Schema:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 🔌 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/fuzz/run` | Launch synchronous or asynchronous fuzzing campaign |
| `GET` | `/jobs` | Retrieve all past fuzzing campaigns with aggregate metrics |
| `GET` | `/jobs/{job_id}` | Fetch status and execution metadata for a campaign |
| `GET` | `/jobs/{job_id}/tree` | Fetch hierarchical execution graph with prompt scores |
| `GET` | `/jobs/{job_id}/breaking-points` | List identified cognitive breaking points & failure diagnoses |
| `GET` | `/jobs/{job_id}/export` | Export campaign audit as Markdown or JSON |
| `GET` | `/models/available` | Auto-detect local Ollama models and cloud presets |

---

## 📂 Architecture

```text
LearnFuzz/
├── cli.py                     # Interactive CLI Red Team Cockpit
├── redteam.py                 # Convenient CLI short alias
├── docker-compose.yml         # Container orchestration (FastAPI + Streamlit)
├── .env.example               # Environment template
├── README.md                  # Comprehensive technical documentation
│
├── backend/                   # Core Fuzzing & Red Teaming Engine
│   ├── cli_agent.py           # Rich console terminal interface
│   ├── fuzzer_service.py      # Recursive mutation engine & Ollama detector
│   ├── main.py                # FastAPI REST router & endpoints
│   ├── models.py              # Pydantic schemas for campaigns & tree nodes
│   ├── database.py            # SQLite async database layer
│   ├── Dockerfile             # Backend container
│   └── requirements.txt       # Dependencies (fastapi, litellm, rich, etc.)
│
└── frontend/                  # Streamlit Interactive Web Application
    ├── app.py                 # Tree graph visualizer, score curves & audits
    ├── Dockerfile             # Frontend container
    └── requirements.txt       # Frontend dependencies (streamlit, plotly, etc.)
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/Sak951/LearnFuzz/issues).

1. Fork the repository
2. Create your Feature Branch (`git checkout -b feature/NewMutationStrategy`)
3. Commit your changes (`git commit -m 'Add grammar permutation mutation vector'`)
4. Push to the branch (`git push origin feature/NewMutationStrategy`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

<div align="center">
  <sub>Built with ❤️ for AI Safety, Adversarial Robustness, and LLM Red Teaming.</sub>
</div>
