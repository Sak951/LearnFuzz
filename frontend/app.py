import os
import time
import requests
import streamlit as st
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(
    page_title="Learn Fuzz",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Set up styles for premium appearance
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10B981, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #9CA3AF;
        margin-bottom: 2rem;
    }
    .metric-box {
        background-color: #1F2937;
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #F9FAFB;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 5px;
    }
    .breaking-point-card {
        background: rgba(239, 68, 68, 0.1);
        border-left: 5px solid #EF4444;
        padding: 12px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Configurations
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# 5 base seed prompts
SEED_PROMPTS = {
    "Math Word Problem (Algebraic/Lateral)": (
        "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?"
    ),
    "Logic Puzzle (Constraint Satisfaction)": (
        "Three boxes are labeled 'Apples', 'Oranges', and 'Apples and Oranges'. All labels are incorrect. "
        "You can pick one fruit from one box. How do you label them all correctly?"
    ),
    "Multi-step Instruction (Strict Constraints)": (
        "Write a short paragraph about space exploration. Every sentence must start with the consecutive "
        "letters of the alphabet starting with 'A' (e.g. sentence 1 starts with A, sentence 2 with B, etc.), "
        "and you must mention Mars at least twice."
    ),
    "Spatial/Logic Reasoning (Sock Problem)": (
        "If a drawer contains 10 red socks and 10 blue socks, what is the minimum number of socks you must "
        "pull out in the dark to guarantee you have a matching pair?"
    ),
    "Conditional Execution (Rules-based Coding)": (
        "A code has input variables X and Y. If X is prime, return X * Y. If X is even but not prime, "
        "return X + Y. If X is odd and composite, return X - Y. Under these rules, calculate the output for X = 9 and Y = 4."
    )
}

# Sidebar - Settings & Keys
st.sidebar.markdown("### 🔑 API Keys Configuration")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Needed if using OpenAI models (e.g. gpt-4o-mini)")
anthropic_key = st.sidebar.text_input("Anthropic API Key", type="password", help="Needed if using Anthropic models")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", help="Needed if using Gemini models")
groq_key = st.sidebar.text_input("Groq API Key", type="password", help="Needed if using Groq models (e.g. groq/llama-3.1-8b-instant)")
openrouter_key = st.sidebar.text_input("OpenRouter API Key", type="password", help="Needed if using OpenRouter models")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 Model Setup")

target_model = st.sidebar.text_input(
    "Target Model",
    value="groq/llama-3.1-8b-instant",
    help="LiteLLM model string (e.g., groq/llama-3.1-8b-instant, openrouter/meta-llama/llama-3.1-8b-instruct:free, openai/gpt-4o-mini)."
)

judge_model = st.sidebar.text_input(
    "Judge Model",
    value="groq/llama-3.3-70b-versatile",
    help="Model used to score responses and generate mutations. Defaults to groq/llama-3.3-70b-versatile."
)

max_depth = st.sidebar.slider(
    "Max Exploration Depth",
    min_value=1,
    max_value=5,
    value=4,
    help="Maximum depth for the recursive fuzzer tree."
)

# Header
st.markdown("<div class='main-title'>🎯 Learn Fuzz</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='subtitle'>Probing LLM reasoning boundaries using dynamic branching and prompt fuzzing.</div>",
    unsafe_allow_html=True
)

# Helper function to fetch jobs
def fetch_jobs():
    try:
        response = requests.get(f"{BACKEND_URL}/jobs")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []

# Fetch active jobs list
jobs_list = fetch_jobs()

# Split page into tabs
tab_run, tab_history = st.tabs(["🚀 Launch Campaign", "📜 History & Analysis"])

with tab_run:
    st.markdown("### Launch a New Fuzzing Campaign")
    
    col_prompt_select, col_prompt_custom = st.columns([1, 1])
    
    with col_prompt_select:
        seed_choice = st.selectbox(
            "Choose a Pre-defined Seed Prompt Template:",
            options=["Custom Prompt"] + list(SEED_PROMPTS.keys())
        )
    
    with col_prompt_custom:
        if seed_choice != "Custom Prompt":
            selected_prompt = SEED_PROMPTS[seed_choice]
        else:
            selected_prompt = ""
            
        seed_prompt_input = st.text_area(
            "Prompt Input (Seed):",
            value=selected_prompt,
            placeholder="Type your initial challenge here..."
        )
    
    if st.button("Start Fuzzing Campaign", type="primary"):
        if not seed_prompt_input.strip():
            st.error("Please enter a valid seed prompt.")
        else:
            payload = {
                "seed_prompt": seed_prompt_input,
                "target_model": target_model,
                "judge_model": judge_model,
                "max_depth": max_depth,
                "openai_api_key": openai_key if openai_key else None,
                "anthropic_api_key": anthropic_key if anthropic_key else None,
                "gemini_api_key": gemini_key if gemini_key else None,
                "groq_api_key": groq_key if groq_key else None,
                "openrouter_api_key": openrouter_key if openrouter_key else None
            }
            try:
                res = requests.post(f"{BACKEND_URL}/start-fuzz", json=payload)
                if res.status_code == 201:
                    st.success("Campaign launched! Check the 'History & Analysis' tab to see it run.")
                    st.balloons()
                    # Trigger rerun to show job in history
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to start campaign: {res.text}")
            except Exception as e:
                st.error(f"Could not connect to FastAPI backend: {e}")

with tab_history:
    if not jobs_list:
        st.info("No fuzzing campaigns run yet. Launch one in the first tab!")
    else:
        # Layout: Job selector and refresh option
        col_select, col_refresh = st.columns([3, 1])
        
        with col_select:
            # Format job display
            job_options = {
                j["job_id"]: f"{j['target_model']} | {j['created_at'][:19]} | Seed: {j['seed_prompt'][:40]}..."
                for j in jobs_list
            }
            selected_job_id = st.selectbox(
                "Select Fuzzing Campaign:",
                options=list(job_options.keys()),
                format_func=lambda x: job_options[x]
            )
            
        with col_refresh:
            auto_refresh = st.checkbox("Auto-refresh running jobs", value=True)
            if st.button("Refresh Manually"):
                st.rerun()

        # Fetch job status and nodes
        try:
            status_res = requests.get(f"{BACKEND_URL}/job/{selected_job_id}/status")
            tree_res = requests.get(f"{BACKEND_URL}/job/{selected_job_id}/tree")
            
            if status_res.status_code == 200 and tree_res.status_code == 200:
                job_status = status_res.json()
                nodes = tree_res.json()
                
                # Check if we should auto-refresh
                if job_status["status"] in ["PENDING", "RUNNING"] and auto_refresh:
                    time.sleep(2)
                    st.rerun()
                
                # Render Metrics
                st.markdown("#### Campaign Stats")
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                
                total_nodes = len(nodes)
                passed_nodes = len([n for n in nodes if n["score"] is not None and n["score"] >= 8])
                failed_nodes = len([n for n in nodes if n["score"] is not None and n["score"] < 8])
                max_depth_reached = max([n["depth"] for n in nodes]) if nodes else 0

                with m_col1:
                    st.markdown(
                        f"<div class='metric-box'><div class='metric-value'>{total_nodes}</div>"
                        f"<div class='metric-label'>Total Nodes</div></div>",
                        unsafe_allow_html=True
                    )
                with m_col2:
                    st.markdown(
                        f"<div class='metric-box'><div class='metric-value'>{passed_nodes}</div>"
                        f"<div class='metric-label'>Passed (≥8)</div></div>",
                        unsafe_allow_html=True
                    )
                with m_col3:
                    st.markdown(
                        f"<div class='metric-box'><div class='metric-value'>{failed_nodes}</div>"
                        f"<div class='metric-label'>Failed (<8)</div></div>",
                        unsafe_allow_html=True
                    )
                with m_col4:
                    st.markdown(
                        f"<div class='metric-box'><div class='metric-value'>{max_depth_reached}</div>"
                        f"<div class='metric-label'>Max Depth Reached</div></div>",
                        unsafe_allow_html=True
                    )
                
                st.markdown("---")
                
                # Plotly Heatmap Tree
                if nodes:
                    st.markdown("### 🗺️ Reasoning Boundary Heatmap (Fuzzing Tree)")
                    st.caption("Green represents success (Score >= 8), Red/Orange indicates breakdown. The boundary text is annotated on failure nodes.")
                    
                    ids = []
                    labels = []
                    parents = []
                    scores = []
                    hover_texts = []
                    
                    for n in nodes:
                        n_id = n["id"]
                        p_id = n["parent_id"] if n["parent_id"] else ""
                        score = n["score"] if n["score"] is not None else 0
                        strategy = n["strategy"]
                        bp = n["breaking_point"]
                        
                        # Shorten strategy name for cleaner labels
                        strat_clean = strategy.replace("mutate: ", "M: ").replace("simplify", "S: Simplify")
                        
                        if bp:
                            label_text = f"❌ <b>Broke at Depth {n['depth']}</b><br>{bp}"
                        elif score < 8:
                            label_text = f"⚠️ <b>Failed at Depth {n['depth']}</b><br>Score: {score}/10<br>({strat_clean})"
                        else:
                            label_text = f"✅ <b>Passed at Depth {n['depth']}</b><br>Score: {score}/10<br>({strat_clean})"
                            
                        ids.append(n_id)
                        parents.append(p_id)
                        labels.append(label_text)
                        scores.append(score)
                        
                        # Hover details
                        hover = (
                            f"<b>Strategy:</b> {strategy}<br>"
                            f"<b>Depth:</b> {n['depth']}<br>"
                            f"<b>Score:</b> {score}/10<br>"
                            f"<b>Prompt:</b> {n['prompt'][:100]}...<br>"
                        )
                        if bp:
                            hover += f"<br>⚠️ <b>Breaking Point:</b> {bp}"
                        hover_texts.append(hover)
                        
                    df_tree = pd.DataFrame({
                        "id": ids,
                        "parent": parents,
                        "label": labels,
                        "score": scores,
                        "hover": hover_texts
                    })
                    
                    # Create Treemap
                    try:
                        fig = px.treemap(
                            df_tree,
                            ids="id",
                            parents="parent",
                            names="label",
                            color="score",
                            color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"], # Red -> Yellow -> Green
                            range_color=[0, 10],
                            hover_name=None,
                            custom_data=["hover"]
                        )
                        fig.update_traces(
                            hovertemplate="%{customdata[0]}<extra></extra>",
                            texttemplate="%{label}",
                            textposition="middle center"
                        )
                        fig.update_layout(
                            margin=dict(t=10, l=10, r=10, b=10),
                            height=500
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as tree_err:
                        st.error(f"Error drawing visualization: {tree_err}")
                
                # Breaking Points Highlight
                if job_status["breaking_points"]:
                    st.markdown("### ⚠️ Identified Reasoning Boundaries (Breaking Points)")
                    for bp in job_status["breaking_points"]:
                        st.markdown(
                            f"<div class='breaking-point-card'>🚨 <b>{bp}</b></div>",
                            unsafe_allow_html=True
                        )
                    st.markdown("---")
                
                # Detailed Node Inspector & Failure Autopsy Tabs
                if nodes:
                    inspector_tab, autopsy_tab = st.tabs(["🔍 Node Inspector", "🩺 Failure Autopsy"])
                    
                    with inspector_tab:
                        st.caption("Select a prompt node below to inspect its detailed evaluation trail.")
                        
                        # Create selectbox options from nodes list
                        node_map = {n["id"]: n for n in nodes}
                        
                        def get_node_label(n):
                            return f"Depth {n['depth']} | {n['strategy']} | Score: {n['score']}/10 | {n['prompt'][:50]}..."
                            
                        inspected_node_id = st.selectbox(
                            "Select Node to Inspect:",
                            options=list(node_map.keys()),
                            format_func=lambda x: get_node_label(node_map[x])
                        )
                        
                        n_select = node_map[inspected_node_id]
                        
                        col_p, col_r = st.columns(2)
                        with col_p:
                            st.subheader("Prompt Text")
                            st.code(n_select["prompt"], language="text")
                            
                            st.subheader("Target LLM Response")
                            st.code(n_select["response"] if n_select["response"] else "No response recorded.", language="text")
                            
                        with col_r:
                            st.subheader("Judge Assessment")
                            st.markdown(f"**Score:** {n_select['score']} / 10")
                            st.markdown(f"**Strategy Used:** `{n_select['strategy']}`")
                            st.markdown(f"**Depth:** {n_select['depth']}")
                            
                            st.markdown("**Judge Reasoning:**")
                            st.info(n_select["reasoning"] if n_select["reasoning"] else "No reasoning provided.")
                            
                            if n_select["breaking_point"]:
                                st.error(f"🚨 **Breaking Point identified:** {n_select['breaking_point']}")
                                
                    with autopsy_tab:
                        st.caption("Algorithmic aggregation of failed evaluation nodes to discover common breakdown patterns.")
                        
                        # Get all failed nodes
                        failed_nodes_list = [n for n in nodes if n["score"] is not None and n["score"] < 8]
                        total_failed = len(failed_nodes_list)
                        
                        if total_failed == 0:
                            st.success("🎉 No failed nodes detected in this campaign! The model passed all complexity branches.")
                        else:
                            st.markdown(f"**Diagnostic Summary:** An autopsy of the **{total_failed}** failed evaluation nodes was conducted to isolate failure patterns.")
                            
                            # Analyze strategies
                            strategy_counts = {}
                            for fn in failed_nodes_list:
                                strat = fn["strategy"]
                                strat_name = strat.replace("mutate: ", "Mutation: ").title()
                                strategy_counts[strat_name] = strategy_counts.get(strat_name, 0) + 1
                                
                            # Analyze keywords/categories in failed prompts
                            categories = {
                                "Arithmetic & Quantitative reasoning": ["decimal", "subtraction", "minus", "cost", "bat", "calculate", "prime", "number", "even", "odd", "math"],
                                "Negative & positive constraints": ["letter", "sentence", "alphabet", "word", "length", "start with", "formatting", "constraint"],
                                "Lateral Logic & Deductive puzzles": ["box", "apples", "oranges", "socks", "drawer", "matching", "labeled", "incorrect"]
                            }
                            
                            category_failures = {}
                            for fn in failed_nodes_list:
                                prompt_lower = fn["prompt"].lower()
                                matched = False
                                for cat, keywords in categories.items():
                                    if any(kw in prompt_lower for kw in keywords):
                                        category_failures[cat] = category_failures.get(cat, 0) + 1
                                        matched = True
                                if not matched:
                                    category_failures["Complex Context Following"] = category_failures.get("Complex Context Following", 0) + 1
                                    
                            # Find dominant failure category
                            dominant_cat = max(category_failures, key=category_failures.get) if category_failures else "Complex Context Following"
                            dominant_count = category_failures[dominant_cat]
                            
                            # Recommendation engine
                            recommendations = {
                                "Arithmetic & Quantitative reasoning": (
                                    "Fine-tune the model on arithmetic and multi-step quantitative reasoning datasets. "
                                    "Strengthen token representation for numbers and mathematical operators, and ensure system instructions mandate step-by-step scratchpad calculations."
                                ),
                                "Negative & positive constraints": (
                                    "Train the model on negative constraint instruction-following sets. "
                                    "Consider wrapping the model API with runtime validator guardrails (such as Llama Guard or custom regex filters) to verify negative constraints before outputting."
                                ),
                                "Lateral Logic & Deductive puzzles": (
                                    "Incorporate Chain-of-Thought (CoT) system prompt guidelines (e.g. 'Let's think step-by-step') to enforce logical ordering. "
                                    "Additionally, fine-tune the model on logic grid and lateral deduction datasets."
                                ),
                                "Complex Context Following": (
                                    "Fine-tune the target model on long-context instruction-following benchmarks "
                                    "(e.g., UltraFeedback, OpenOrca) to improve distraction-resistance and attention retention."
                                )
                            }
                            
                            rec_text = recommendations.get(dominant_cat, recommendations["Complex Context Following"])
                            
                            # Display the Autopsy findings in a beautiful card
                            st.markdown(f"""
                            <div style="background-color: #1F2937; padding: 20px; border-radius: 8px; border: 1px solid #374151; margin-bottom: 20px;">
                                <h4 style="margin-top:0; color:#EF4444;">🚨 Dominant Failure Pattern Detected</h4>
                                <p>Of the <b>{total_failed}</b> failed nodes, <b>{dominant_count}</b> broke when the prompt involved <b>{dominant_cat}</b>.</p>
                                <hr style="border: 0; border-top: 1px solid #374151; margin: 15px 0;">
                                <h5 style="color:#10B981; margin-top:0;">💡 Actionable Recommendation:</h5>
                                <p style="font-size:0.95rem; line-height:1.5; margin-bottom:0;">{rec_text}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Show breakdown of categories and strategies
                            col_cat, col_strat = st.columns(2)
                            with col_cat:
                                st.markdown("**By Evaluation Category:**")
                                for cat, count in category_failures.items():
                                    pct = int((count / total_failed) * 100)
                                    st.write(f"- **{cat}**: {count} failures ({pct}%)")
                            with col_strat:
                                st.markdown("**By Applied Strategy:**")
                                for strat, count in strategy_counts.items():
                                    pct = int((count / total_failed) * 100)
                                    st.write(f"- **{strat}**: {count} failures ({pct}%)")

                # Delete Job option
                st.markdown("---")
                if st.button("Delete Campaign Data", type="secondary"):
                    res = requests.delete(f"{BACKEND_URL}/job/{selected_job_id}")
                    if res.status_code == 200:
                        st.success("Campaign data deleted successfully.")
                        time.sleep(1)
                        st.rerun()
            else:
                st.error("Failed to load campaign data.")
        except Exception as e:
            st.error(f"Failed to fetch job data from backend: {e}")
