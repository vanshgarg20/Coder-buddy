# agent/graph.py
"""
Robust graph module.

- Lazily initializes the LLM (ChatGroq) so missing env/creds/packages don't break import.
- Tries to build a real StateGraph-based agent if `langgraph` is available.
- If dependencies are missing, exports a MockAgent that is safe for UI/dev.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, Any

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

# -------------------------
# Pydantic models
# -------------------------
class FileSpec(BaseModel):
    path: str
    purpose: str

class Plan(BaseModel):
    name: str
    description: str
    techstack: str
    features: List[str]
    files: List[FileSpec]

class TaskStep(BaseModel):
    filepath: str
    task_description: str
    current_file_content: Optional[str] = None

class TaskPlan(BaseModel):
    implementation_steps: List[TaskStep]

# -------------------------
# App state typing
# -------------------------
class AppState(TypedDict, total=False):
    user_prompt: str
    plan: Plan
    task_plan: TaskPlan
    built_files: Dict[str, str]
    logs: List[str]

# -------------------------
# Lazy LLM helper
# -------------------------
_llm: Optional[Any] = None
_llm_init_error: Optional[Exception] = None

def get_llm():
    """
    Lazily import and construct the ChatGroq LLM.
    If langchain_groq is missing, raise ImportError with clear message.
    """
    global _llm, _llm_init_error
    if _llm is not None:
        return _llm
    if _llm_init_error is not None:
        raise _llm_init_error

    try:
        from langchain_groq import ChatGroq
    except Exception as e:
        _llm_init_error = ImportError(
            "Missing optional dependency 'langchain_groq'. Install it to use the real LLM. "
            f"Original error: {e!r}"
        )
        raise _llm_init_error

    try:
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        temperature = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
        _llm = ChatGroq(model=model, temperature=temperature)
        return _llm
    except Exception as e:
        _llm_init_error = RuntimeError(
            "Failed to construct ChatGroq LLM. Check GROQ credentials / env vars. "
            f"Original error: {e!r}"
        )
        raise _llm_init_error

# -------------------------
# Prompts
# -------------------------
def planner_prompt(user_prompt: str) -> str:
    return f"""You are the PLANNING agent.
Produce a strictly structured Plan with the following fields ONLY:
  - name: short app name
  - description: 1–2 lines
  - techstack: single string (e.g., "Flask + HTML/CSS/JS")
  - features: list[str]
  - files: list{{"path": str, "purpose": str}}  # POSIX-like paths

Constraints:
  - Be concise and concrete.
  - Make file paths realistic (e.g., "index.html", "static/style.css", "static/script.js").

User request:
{user_prompt}
"""

def architect_prompt(plan_json: str) -> str:
    return f"""You are the ARCHITECT agent.
Return a TaskPlan via tool/function call ONLY (no free text).

TaskPlan schema (fill EXACT KEYS):
{{
  "implementation_steps": [
    {{
      "filepath": "string (e.g., 'index.html', 'static/style.css')",
      "task_description": "string (clear, actionable change to implement)",
      "current_file_content": "string or null"
    }}
  ]
}}

Rules:
  - Use keys exactly: filepath, task_description, current_file_content.
  - Prefer minimal, working snippets when providing current_file_content.
  - If nothing to write yet, set current_file_content to null (not an empty string).
  - Keep steps ordered so dependencies come first.

Plan:
{plan_json}
"""

# -------------------------
# Graph node implementations (use get_llm())
# -------------------------
def planner_agent(state: AppState) -> AppState:
    user_prompt = state.get("user_prompt", "")
    llm = get_llm()
    plan = llm.with_structured_output(Plan).invoke(planner_prompt(user_prompt))
    out: AppState = dict(state)
    out["plan"] = plan
    logs = out.get("logs", [])
    logs.append("planner: generated Plan")
    out["logs"] = logs
    return out

def architect_agent(state: AppState) -> AppState:
    plan: Plan = state["plan"]
    llm = get_llm()
    tp = llm.with_structured_output(TaskPlan).invoke(
        architect_prompt(plan.model_dump_json())
    )
    out: AppState = dict(state)
    out["task_plan"] = tp
    logs = out.get("logs", [])
    logs.append("architect: produced TaskPlan")
    out["logs"] = logs
    return out

def coder_agent(state: AppState) -> AppState:
    output_dir = os.getenv("PROJECT_OUTPUT_DIR", "output")
    task_plan: TaskPlan = state["task_plan"]
    built: Dict[str, str] = {}

    for step in task_plan.implementation_steps:
        rel_path = step.filepath
        content = step.current_file_content or ""
        p = Path(output_dir) / Path(rel_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        built[str(p)] = f"written ({len(content)} bytes)"

    out: AppState = dict(state)
    out["built_files"] = built
    logs = out.get("logs", [])
    logs.append(f"coder: wrote {len(built)} file(s) to '{output_dir}/'")
    out["logs"] = logs
    return out

# -------------------------
# Try to import StateGraph (optional). If missing, we'll expose a MockAgent.
# -------------------------
_StateGraph = None
_stategraph_import_error: Optional[Exception] = None
try:
    from langgraph.graph import StateGraph  # type: ignore
    _StateGraph = StateGraph
except Exception as e:
    _stategraph_import_error = e
    _StateGraph = None

# -------------------------
# Helper: simple MockAgent for dev if dependencies are missing
# -------------------------
class MockAgent:
    """
    Minimal agent that supports:
     - .invoke(payload, config=...)
     - callable(payload, config=...)
    It writes a small index.html into ./output so the UI can preview something.
    """
    def invoke(self, payload: Dict[str, Any] = None, config: Dict[str, Any] = None):
        payload = payload or {}
        cfg = config or {}
        user_prompt = payload.get("user_prompt", "<no prompt>")
        out_dir = Path(os.getenv("PROJECT_OUTPUT_DIR", "output"))
        out_dir.mkdir(parents=True, exist_ok=True)

        html_path = out_dir / "index.html"
        html_content = (
            "<!doctype html>\n<html><head><meta charset='utf-8'><title>Mock Output</title></head>"
            f"<body><h1>Mock Agent Output</h1><p>Prompt: {json.dumps(user_prompt)}</p>"
            "<p>This is a mock file created because the real agent dependencies are missing.</p>"
            "</body></html>"
        )
        html_path.write_text(html_content, encoding="utf-8")

        # minimal structured-like response
        task_step = {
            "filepath": "index.html",
            "task_description": "write basic index.html (mock)",
            "current_file_content": html_content,
        }
        return {
            "plan": {"name": "mock-app", "description": "Mock plan", "techstack": "", "features": [], "files": []},
            "task_plan": {"implementation_steps": [task_step]},
            "built_files": {str(html_path): f"written ({html_path.stat().st_size} bytes)"},
            "logs": ["mock: wrote index.html"],
        }

    def __call__(self, payload=None, config=None):
        return self.invoke(payload, config)

# -------------------------
# Build real graph if possible, otherwise return mock
# -------------------------
def build_app():
    if _StateGraph is None:
        # dependencies missing -> raise helpful error OR fallback to mock
        # We choose to return a MockAgent so UI remains usable for development.
        return MockAgent()

    # build the StateGraph based agent
    graph = _StateGraph(AppState)
    graph.add_node("planner", planner_agent)
    graph.add_node("architect", architect_agent)
    graph.add_node("coder", coder_agent)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "architect")
    graph.add_edge("architect", "coder")
    return graph.compile()

# compile once on import and export the compiled agent object (or mock)
_agent_instance = build_app()
agent = _agent_instance

# -------------------------
# Quick local run - safe
# -------------------------
if __name__ == "__main__":
    # If real StateGraph is present, this will run the compiled graph; otherwise mock runs.
    user_prompt = "Build a colourful modern todo app in html css and js"
    # agent supports invoke(...)
    try:
        result = agent.invoke({"user_prompt": user_prompt}, config={"recursion_limit": 100})
    except AttributeError:
        # fallback to callable usage
        result = agent({"user_prompt": user_prompt})

    print("\n=== RESULT ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
