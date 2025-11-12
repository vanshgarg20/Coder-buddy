# agent/graph.py
import os
from pathlib import Path
from typing import Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph

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
    # NOTE: keep key name 'filepath' (matches LLM/tool schema used earlier)
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
# LLM (Groq) - configurable via env
# -------------------------
llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=float(os.getenv("GROQ_TEMPERATURE", "0.2")),
)

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
# Graph nodes
# -------------------------
def planner_agent(state: AppState) -> AppState:
    user_prompt = state["user_prompt"]
    plan = llm.with_structured_output(Plan).invoke(planner_prompt(user_prompt))
    out: AppState = dict(state)
    out["plan"] = plan
    logs = out.get("logs", [])
    logs.append("planner: generated Plan")
    out["logs"] = logs
    return out

def architect_agent(state: AppState) -> AppState:
    plan: Plan = state["plan"]
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
    """
    Writes files described by TaskPlan. Creates parent directories as needed.
    Files are written under the PROJECT_OUTPUT_DIR (default: ./output).
    """
    output_dir = os.getenv("PROJECT_OUTPUT_DIR", "output")
    task_plan: TaskPlan = state["task_plan"]
    built: Dict[str, str] = {}

    for step in task_plan.implementation_steps:
        # filepath is relative inside the output_dir
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
# Build and export agent
# -------------------------
def build_app():
    graph = StateGraph(AppState)
    graph.add_node("planner", planner_agent)
    graph.add_node("architect", architect_agent)
    graph.add_node("coder", coder_agent)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "architect")
    graph.add_edge("architect", "coder")
    return graph.compile()

# compile once on import and export the compiled agent object
_agent_instance = build_app()

# Exported name that main.py expects
agent = _agent_instance

# If you run graph.py directly, run an example (safe for dev)
if __name__ == "__main__":
    user_prompt = "Build a colourful modern todo app in html css and js"
    result = agent.invoke({"user_prompt": user_prompt}, config={"recursion_limit": 100})
    plan = result.get("plan")
    task_plan = result.get("task_plan")
    built = result.get("built_files", {})
    logs = result.get("logs", [])

    print("\n=== PLAN ===")
    if plan:
        print(plan.model_dump_json(indent=2))
    print("\n=== TASK PLAN ===")
    if task_plan:
        print(task_plan.model_dump_json(indent=2))
    print("\n=== BUILT FILES ===")
    for k, v in built.items():
        print(f"- {k}: {v}")
    print("\n=== LOGS ===")
    for line in logs:
        print("*", line)
