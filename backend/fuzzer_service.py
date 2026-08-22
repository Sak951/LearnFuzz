import os
import json
import random
import logging
import asyncio
import re
import litellm
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Job, Node

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_json_markdown(text: str) -> dict:
    """Robust parser to extract JSON or key-values from LLM responses, even if wrapped in markdown or loose text."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON inside markdown code blocks
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try to find the first '{' and last '}'
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace+1])
        except json.JSONDecodeError:
            pass

    # Fallback heuristic extractor for open-source models
    res = {}
    score_match = re.search(r'"?score"?\s*[:=]\s*(\d+)', text, re.IGNORECASE)
    if score_match:
        res["score"] = int(score_match.group(1))
    
    mutated_match = re.search(r'"?mutated_prompt"?\s*[:=]\s*["\']?(.*?)["\']?(?:,\s*"|\s*})', text, re.DOTALL | re.IGNORECASE)
    if mutated_match:
        res["mutated_prompt"] = mutated_match.group(1).strip()
    elif "mutated" in text.lower() or "prompt" in text.lower():
        res["mutated_prompt"] = text

    simplified_match = re.search(r'"?simplified_prompt"?\s*[:=]\s*["\']?(.*?)["\']?(?:,\s*"|\s*})', text, re.DOTALL | re.IGNORECASE)
    if simplified_match:
        res["simplified_prompt"] = simplified_match.group(1).strip()
    
    reasoning_match = re.search(r'"?reasoning"?\s*[:=]\s*["\']?(.*?)["\']?(?:,\s*"|\s*})', text, re.DOTALL | re.IGNORECASE)
    if reasoning_match:
        res["reasoning"] = reasoning_match.group(1).strip()
    else:
        res["reasoning"] = text[:300]

    if res:
        return res

    raise ValueError(f"Could not parse JSON or attributes from text: {text}")



async def call_llm(model: str, system_prompt: str, user_prompt: str, api_keys: dict) -> str:
    """Invokes the LLM using LiteLLM, dynamically applying API keys or returning a mock response."""
    if model.startswith("mock"):
        await asyncio.sleep(0.3)  # Simulate network latency
        system_lower = system_prompt.lower()
        if "judge" in system_lower:
            # Judge model evaluating target response
            score = random.choice([4, 6, 8, 9, 10])
            return json.dumps({
                "score": score,
                "reasoning": f"This is a mock evaluation. The response was evaluated with score {score}/10.",
                "is_failure": score < 8,
                "identified_weakness": "fails under complex formatting" if score < 8 else ""
            })
        elif "adversarial" in system_lower:
            # Mutation model generating harder prompt
            strategy = "constraints"
            if "red_herring" in system_prompt:
                strategy = "red_herring"
            elif "chain_sequence" in system_prompt:
                strategy = "chain_sequence"
            
            clean_base = user_prompt.replace("Base Prompt:\n", "")
            return json.dumps({
                "mutated_prompt": f"{clean_base} (Mock strategy: {strategy})",
                "applied_strategy": strategy,
                "expected_difficulty": f"Added {strategy} constraint to increase difficulty."
            })
        elif "simplify" in system_lower:
            # Simplification model
            clean_failed = user_prompt.replace("Failed Prompt:\n", "")
            # Remove any mock strategy markers
            simplified = clean_failed
            for term in [" (Mock strategy: red_herring)", " (Mock strategy: constraints)", " (Mock strategy: chain_sequence)"]:
                simplified = simplified.replace(term, "")
            return json.dumps({
                "simplified_prompt": f"{simplified} [Mock Simplified]",
                "simplification_details": "Removed mock constraints to drill down."
            })
        elif "analyst" in system_lower:
            # Breaking point determination
            return "Fails when mock strategies are applied"
        else:
            # General prompt / target model
            return "This is a simulated target model response that satisfies some mock criteria."

    # Ensure keys are injected into environment variables for LiteLLM
    if api_keys:
        for k, v in api_keys.items():
            if v:
                env_key = k.upper()
                os.environ[env_key] = v
                # Mirror gemini key for standard google provider support
                if env_key == "GEMINI_API_KEY":
                    os.environ["GOOGLE_API_KEY"] = v

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Handle local Ollama models
    api_base = None
    timeout = 40.0
    actual_model = model

    if model.startswith("ollama/") or model.startswith("ollama_chat/"):
        api_base = os.getenv("OLLAMA_API_BASE", "http://127.0.0.1:11434")
        timeout = 120.0
    elif model.lower() in ["mistral", "llama2", "qwen3.6", "llama3", "llama3.2", "phi3"]:
        actual_model = f"ollama/{model}:latest"
        api_base = os.getenv("OLLAMA_API_BASE", "http://127.0.0.1:11434")
        timeout = 120.0

    try:
        kwargs = {
            "model": actual_model,
            "messages": messages,
            "timeout": timeout
        }
        if api_base:
            kwargs["api_base"] = api_base

        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling LLM {model}: {e}")
        raise e



async def evaluate_response(prompt: str, response: str, api_keys: dict, judge_model: str) -> dict:
    """Evaluates the target LLM response using the Judge model."""
    system_prompt = (
        "You are an expert AI judge evaluator. Evaluate the correctness, reasoning quality, and constraint satisfaction "
        "of the target LLM's response to the given prompt on a scale of 1 to 10:\n"
        "- 10: Absolutely correct, flawless logic, satisfies all constraints, complete.\n"
        "- 8-9: Correct answer, minor style issues, satisfies constraints.\n"
        "- 5-7: Partially correct, minor reasoning errors, or failed some constraints.\n"
        "- 1-4: Highly incorrect, major reasoning failures, hallucinated details, or ignored instructions.\n\n"
        "You must respond in strict JSON format matching this schema:\n"
        "{\n"
        "  \"score\": int, // 1 to 10\n"
        "  \"reasoning\": \"Detailed justification of the score.\",\n"
        "  \"is_failure\": boolean, // true if score < 8, false otherwise\n"
        "  \"identified_weakness\": \"Short description of why the model struggled, or empty if perfect.\"\n"
        "}\n"
        "Ensure you return ONLY valid JSON. Do not include markdown code block wrappers."
    )
    user_prompt = f"Prompt:\n{prompt}\n\nTarget LLM Response:\n{response}"

    raw_response = await call_llm(judge_model, system_prompt, user_prompt, api_keys)
    return parse_json_markdown(raw_response)


async def mutate_prompt(prompt: str, strategy: str, api_keys: dict, judge_model: str) -> dict:
    """Mutates a prompt to increase complexity based on a strategy."""
    system_prompt = (
        "You are an adversarial prompt engineering expert. Your task is to modify the given base prompt to make it "
        "significantly more challenging for a target LLM, while keeping the core task solvable.\n\n"
        f"Apply this strategy: '{strategy}'\n"
        "- red_herring: Inject plausible but completely irrelevant details/data. The final answer must ignore this distraction.\n"
        "- constraints: Introduce strict positive/negative constraints (e.g. output structure, length, forbidden words).\n"
        "- chain_sequence: Add an additional dependent logical step (e.g. 'Solve X, then use that to calculate Y under condition Z').\n\n"
        "Respond in strict JSON format matching this schema:\n"
        "{\n"
        "  \"mutated_prompt\": \"The new, more complex prompt.\",\n"
        "  \"applied_strategy\": \"Explanation of how the strategy was applied.\",\n"
        "  \"expected_difficulty\": \"Why this makes the prompt harder.\"\n"
        "}\n"
        "Ensure you return ONLY valid JSON."
    )
    user_prompt = f"Base Prompt:\n{prompt}"

    raw_response = await call_llm(judge_model, system_prompt, user_prompt, api_keys)
    return parse_json_markdown(raw_response)


async def simplify_prompt(prompt: str, api_keys: dict, judge_model: str) -> dict:
    """Simplifies a prompt to find the reasoning threshold."""
    system_prompt = (
        "You are a prompt engineering expert. A target LLM has failed to correctly answer the following prompt.\n"
        "Your task is to simplify or decompose the prompt to find the exact capability boundary where the model succeeds.\n\n"
        "Deconstruct the prompt:\n"
        "- Remove or weaken complex constraints.\n"
        "- Remove distracting red herrings.\n"
        "- Break a multi-step logical chain into a simpler or single-step prompt.\n\n"
        "Respond in strict JSON format matching this schema:\n"
        "{\n"
        "  \"simplified_prompt\": \"The new, simplified prompt.\",\n"
        "  \"simplification_details\": \"Explanation of what was simplified or removed.\"\n"
        "}\n"
        "Ensure you return ONLY valid JSON."
    )
    user_prompt = f"Failed Prompt:\n{prompt}"

    raw_response = await call_llm(judge_model, system_prompt, user_prompt, api_keys)
    return parse_json_markdown(raw_response)


async def determine_breaking_point(
    parent_prompt: str,
    child_prompt: str,
    child_response: str,
    child_reasoning: str,
    api_keys: dict,
    judge_model: str
) -> str:
    """Summarizes why a model broke when transitioning from a passing parent node to a failing child node."""
    system_prompt = (
        "You are an AI evaluation analyst. Compare the successful parent prompt and the failing child prompt/response.\n"
        "Identify and summarize the exact breaking point of the model in a single short, punchy sentence (maximum 10 words).\n"
        "Examples:\n"
        "- 'Fails at 3-step reasoning'\n"
        "- 'Hallucinates with negative numbers'\n"
        "- 'Struggles with word length constraints'\n"
        "- 'Distracted by red herring currency data'\n\n"
        "Provide ONLY the short sentence, no extra text, no quotes."
    )
    user_prompt = (
        f"Parent Prompt (Succeeded):\n{parent_prompt}\n\n"
        f"Child Prompt (Failed):\n{child_prompt}\n\n"
        f"Child Response:\n{child_response}\n\n"
        f"Judge Failure Reasoning:\n{child_reasoning}"
    )
    try:
        explanation = await call_llm(judge_model, system_prompt, user_prompt, api_keys)
        return explanation.strip().strip('"').strip("'")
    except Exception as e:
        logger.error(f"Error determining breaking point: {e}")
        return "Fails under increased complexity"


async def fuzz_node_recursive(
    job_id: str,
    prompt: str,
    parent_id: str | None,
    depth: int,
    strategy: str,
    max_depth: int,
    target_model: str,
    judge_model: str,
    api_keys: dict,
    node_callback=None
):
    """Recursively processes a fuzzing node: calling target, evaluation, branching."""
    if depth > max_depth:
        return

    logger.info(f"Fuzzing node at depth {depth} (Job: {job_id}, Strategy: {strategy})")
    
    if node_callback:
        try:
            cb_res = node_callback("node_started", {
                "job_id": job_id,
                "depth": depth,
                "strategy": strategy,
                "prompt": prompt,
                "parent_id": parent_id
            })
            if asyncio.iscoroutine(cb_res):
                await cb_res
        except Exception as cb_err:
            logger.warning(f"node_callback error on node_started: {cb_err}")

    # 1. Call Target LLM
    response_text = ""
    try:
        response_text = await call_llm(target_model, "You are a helpful assistant. Solve the prompt accurately.", prompt, api_keys)
    except Exception as e:
        response_text = f"Error calling target model: {str(e)}"
        score = 0
        reasoning = f"Target model failed to respond: {str(e)}"
        is_failure = True
        identified_weakness = "API connection error"
    
    # 2. Evaluate response if target LLM call succeeded (or failed)
    if "Error calling target model" not in response_text:
        try:
            evaluation = await evaluate_response(prompt, response_text, api_keys, judge_model)
            score = int(evaluation.get("score", 1))
            reasoning = evaluation.get("reasoning", "No reasoning provided.")
            is_failure = evaluation.get("is_failure", score < 8)
            identified_weakness = evaluation.get("identified_weakness", "")
        except Exception as e:
            logger.error(f"Error evaluating response: {e}")
            score = 5  # default neutral score on eval error
            reasoning = f"Judge model evaluation failed: {str(e)}"
            is_failure = False
            identified_weakness = "Evaluation failed"
    else:
        score = 0
        reasoning = "Target model call failed."
        is_failure = True
        identified_weakness = "Target model error"

    # 3. Create Node in Database
    db: Session = SessionLocal()
    node = Node(
        job_id=job_id,
        parent_id=parent_id,
        prompt=prompt,
        response=response_text,
        score=score,
        depth=depth,
        strategy=strategy,
        reasoning=reasoning,
        breaking_point=None
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    # 4. Check if this is a "Breaking Point"
    # A breaking point is defined as: this node failed (Score < 8) and its parent passed (Score >= 8)
    bp_desc = None
    if parent_id and is_failure:
        parent_node = db.query(Node).filter(Node.id == parent_id).first()
        if parent_node and parent_node.score is not None and parent_node.score >= 8:
            bp_desc = await determine_breaking_point(
                parent_prompt=parent_node.prompt,
                child_prompt=prompt,
                child_response=response_text,
                child_reasoning=reasoning,
                api_keys=api_keys,
                judge_model=judge_model
            )
            node.breaking_point = bp_desc
            db.commit()
            db.refresh(node)
            logger.info(f"Identified breaking point: {bp_desc}")
    
    node_id = node.id
    db.close()

    if node_callback:
        try:
            cb_res = node_callback("node_completed", {
                "id": node_id,
                "job_id": job_id,
                "parent_id": parent_id,
                "prompt": prompt,
                "response": response_text,
                "score": score,
                "depth": depth,
                "strategy": strategy,
                "reasoning": reasoning,
                "breaking_point": bp_desc,
                "identified_weakness": identified_weakness
            })
            if asyncio.iscoroutine(cb_res):
                await cb_res
        except Exception as cb_err:
            logger.warning(f"node_callback error on node_completed: {cb_err}")

    # 5. Check if we should branch further
    if depth >= max_depth:
        return

    # Check termination criteria
    if score == 10 and "simplify" in strategy:
        logger.info("Termination reached: Simplified prompt is trivially easy (score 10).")
        return

    child_tasks = []

    # 6. Branching Logic
    if score >= 8:
        # Pass: Mutate to increase difficulty.
        strategies = ["red_herring", "constraints", "chain_sequence"]
        
        if depth < max_depth - 2:
            chosen_strategies = random.sample(strategies, 2)
        else:
            chosen_strategies = [random.choice(strategies)]

        for strat in chosen_strategies:
            try:
                mutation = await mutate_prompt(prompt, strat, api_keys, judge_model)
                mutated_prompt = mutation.get("mutated_prompt")
                if mutated_prompt:
                    child_tasks.append(
                        fuzz_node_recursive(
                            job_id=job_id,
                            prompt=mutated_prompt,
                            parent_id=node_id,
                            depth=depth + 1,
                            strategy=f"mutate: {strat}",
                            max_depth=max_depth,
                            target_model=target_model,
                            judge_model=judge_model,
                            api_keys=api_keys,
                            node_callback=node_callback
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to mutate prompt using strategy '{strat}': {e}")
    else:
        # Fail: Simplify prompt to drill down.
        try:
            simplification = await simplify_prompt(prompt, api_keys, judge_model)
            simplified_prompt = simplification.get("simplified_prompt")
            if simplified_prompt:
                child_tasks.append(
                    fuzz_node_recursive(
                        job_id=job_id,
                        prompt=simplified_prompt,
                        parent_id=node_id,
                        depth=depth + 1,
                        strategy="simplify",
                        max_depth=max_depth,
                        target_model=target_model,
                        judge_model=judge_model,
                        api_keys=api_keys,
                        node_callback=node_callback
                    )
                )
        except Exception as e:
            logger.error(f"Failed to simplify prompt: {e}")

    if child_tasks:
        await asyncio.gather(*child_tasks, return_exceptions=True)


async def run_fuzzing_job_task(
    job_id: str,
    seed_prompt: str,
    target_model: str,
    judge_model: str,
    max_depth: int,
    api_keys: dict,
    node_callback=None
):
    """Task runner wrapper to execute the fuzzing process and update Job status."""
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    job.status = "RUNNING"
    db.commit()
    db.close()

    try:
        # Start recursive fuzzing at depth 0
        await fuzz_node_recursive(
            job_id=job_id,
            prompt=seed_prompt,
            parent_id=None,
            depth=0,
            strategy="seed",
            max_depth=max_depth,
            target_model=target_model,
            judge_model=judge_model,
            api_keys=api_keys,
            node_callback=node_callback
        )

        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "COMPLETED"
            db.commit()
        db.close()
        logger.info(f"Fuzzing job {job_id} COMPLETED successfully.")

    except Exception as e:
        logger.error(f"Error running fuzzing job {job_id}: {e}")
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "FAILED"
            db.commit()
        db.close()

