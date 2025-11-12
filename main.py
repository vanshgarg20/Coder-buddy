# main.py - Streamlit front-end (no disk writes for Todo/Calculator; agent optional for Custom)
import os
import time
import json
import traceback
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

# try import agent but it's optional for Custom prompts (we won't show status)
try:
    from agent.graph import agent
except Exception:
    try:
        from graph import agent
    except Exception:
        agent = None

# ---------------- helper functions ----------------
def call_agent(agent_obj: Any, payload: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Any:
    """Try multiple invocation styles to be compatible with different agent exports."""
    config = config or {}

    if agent_obj is None:
        raise RuntimeError("No agent available")

    # .invoke(...)
    if hasattr(agent_obj, "invoke") and callable(getattr(agent_obj, "invoke")):
        try:
            return agent_obj.invoke(payload, config=config)
        except TypeError:
            try:
                return agent_obj.invoke(payload, config)
            except TypeError:
                pass
        except Exception:
            raise

    # callable(agent_obj)(...)
    if callable(agent_obj):
        try:
            return agent_obj(payload, config=config)
        except TypeError:
            pass
        except Exception:
            raise
        try:
            return agent_obj(payload, config)
        except TypeError:
            pass
        except Exception:
            raise
        try:
            return agent_obj(payload)
        except TypeError:
            pass
        except Exception:
            raise
        try:
            return agent_obj()
        except TypeError:
            pass
        except Exception:
            raise

    raise TypeError("agent is not invokable. Expected .invoke(...) or callable.")

def todo_template() -> Dict[str, str]:
    html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>TodoApp</title>
  <link rel="stylesheet" href="static/style.css">
</head>
<body>
  <div class="app">
    <h1>TodoApp</h1>
    <div class="new-task">
      <input id="task-input" placeholder="Add a new task..." />
      <button id="add-btn">Add</button>
    </div>
    <ul id="tasks"></ul>
  </div>
  <script src="static/script.js"></script>
</body>
</html>"""
    css = """body { font-family: Arial, sans-serif; background:#f7f7f8; color:#222; padding:20px; }
.app { max-width:600px; margin:30px auto; background:white; padding:20px; border-radius:8px; box-shadow:0 3px 8px rgba(0,0,0,0.06); }
.new-task { display:flex; gap:8px; margin-bottom:12px; }
#task-input { flex:1; padding:8px; border:1px solid #ddd; border-radius:4px; }
#add-btn { padding:8px 12px; border:none; background:#0b79ff; color:white; border-radius:4px; cursor:pointer; }
#tasks { list-style:none; padding:0; margin:0; }
.task { display:flex; justify-content:space-between; gap:8px; padding:8px; border-bottom:1px solid #eee; }
.task .left { display:flex; gap:8px; align-items:center; }
.complete { text-decoration:line-through; color:#999; }"""
    js = """const input = document.getElementById('task-input');
const addBtn = document.getElementById('add-btn');
const tasksEl = document.getElementById('tasks');

let tasks = [];

function render() {
  tasksEl.innerHTML = '';
  tasks.forEach((t, i) => {
    const li = document.createElement('li');
    li.className = 'task';
    li.innerHTML = `
      <div class="left">
        <input type="checkbox" ${t.done ? 'checked' : ''} data-i="${i}" />
        <span class="${t.done ? 'complete' : ''}">${escapeHtml(t.text)}</span>
      </div>
      <div>
        <button data-del="${i}">Delete</button>
      </div>
    `;
    tasksEl.appendChild(li);
  });
}

function escapeHtml(s){ return s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }

addBtn.onclick = () => {
  const v = input.value.trim();
  if(!v) return;
  tasks.unshift({ text: v, done: false });
  input.value = '';
  render();
};

tasksEl.onclick = (e) => {
  const c = e.target;
  if(c.dataset.i !== undefined){
    const i = Number(c.dataset.i);
    tasks[i].done = !tasks[i].done;
    render();
  } else if(c.dataset.del !== undefined){
    const i = Number(c.dataset.del);
    tasks.splice(i,1);
    render();
  }
};

render();"""
    return {"index.html": html, "static/style.css": css, "static/script.js": js}

def calculator_template() -> Dict[str, str]:
    html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Calculator</title>
  <link rel="stylesheet" href="static/style.css">
</head>
<body>
  <div class="calc">
    <input id="display" disabled />
    <div id="keys"></div>
  </div>
  <script src="static/script.js"></script>
</body>
</html>"""
    css = """body { display:flex; height:100vh; align-items:center; justify-content:center; background:#eef2f7; font-family:Arial; }
.calc { width:260px; background:#fff; padding:16px; border-radius:8px; box-shadow:0 6px 18px rgba(0,0,0,0.07); }
#display { width:100%; height:40px; font-size:18px; margin-bottom:8px; padding:6px; text-align:right; border:1px solid #ddd; border-radius:4px; }
#keys { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
button { padding:12px; font-size:16px; border-radius:6px; border:none; background:#f1f3f5; cursor:pointer; }"""
    js = """const display = document.getElementById('display');
const keys = ['7','8','9','/','4','5','6','*','1','2','3','-','0','.','=','+'];
const keysEl = document.getElementById('keys');
let expr = '';
function render(){ display.value = expr; }
keys.forEach(k => {
  const b = document.createElement('button');
  b.textContent = k;
  b.onclick = () => {
    if(k === '='){
      try{ expr = String(eval(expr)); }catch(e){ expr = 'Error'; }
    } else {
      expr += k;
    }
    render();
  };
  keysEl.appendChild(b);
});
render();"""
    return {"index.html": html, "static/style.css": css, "static/script.js": js}

def to_serializable(obj: Any) -> Any:
    try:
        from pydantic import BaseModel
        if isinstance(obj, BaseModel):
            return to_serializable(obj.model_dump())
    except Exception:
        pass
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_serializable(v) for v in obj]
    return obj

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="Coder-buddy — Generator", layout="wide")
st.title("Coder-buddy — Generate HTML/CSS/JS (no disk write)")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Prompt / Template")
    template = st.selectbox("Choose a template (or 'Custom')", ["Todo app", "Calculator app", "Custom"])
    if template == "Todo app":
        default_prompt = "Create a to-do list application using html, css, and javascript."
    elif template == "Calculator app":
        default_prompt = "Create a modern calculator web app in HTML, CSS and JavaScript."
    else:
        default_prompt = ""
    user_prompt = st.text_area("Project prompt (used only for Custom)", value=default_prompt, height=120)
    recursion_limit = st.number_input("Recursion limit (graph)", min_value=10, max_value=1000, value=100, step=10)
    run_button = st.button("Generate (in-memory preview)")

with col2:
    st.subheader("Quick controls")
    st.write("No files will be written to disk when using Todo/Calculator.")
    if st.checkbox("Allow agent for Custom (if available)", value=False):
        allow_agent_for_custom = True
    else:
        allow_agent_for_custom = False
    st.write("If you want to save to disk later, set WRITE_OUTPUT=1 in env and re-run the app.")

st.markdown("---")
out_col1, out_col2 = st.columns([1, 1])

with out_col1:
    st.subheader("Logs / Final state")
    logs_area = st.empty()

with out_col2:
    st.subheader("Files generated / Preview")
    files_area = st.empty()
    preview_area = st.empty()

# run the generator when button clicked
if run_button:
    final_state = {"status": "started", "returned_value": None}
    try:
        if template == "Todo app":
            built = todo_template()
            returned = {
                "user_prompt": user_prompt,
                "plan": {"name":"TodoApp","description":"Generated TodoApp","techstack":"HTML/CSS/JS"},
                "task_plan": None,
                "built_files": {p: {"written": False, "content": c} for p, c in built.items()},
                "logs": ["local-generator: created todo templates in-memory"],
            }
        elif template == "Calculator app":
            built = calculator_template()
            returned = {
                "user_prompt": user_prompt,
                "plan": {"name":"Calculator","description":"Generated Calculator","techstack":"HTML/CSS/JS"},
                "task_plan": None,
                "built_files": {p: {"written": False, "content": c} for p, c in built.items()},
                "logs": ["local-generator: created calculator templates in-memory"],
            }
        else:  # Custom
            if allow_agent_for_custom and agent is not None:
                # call agent but expect it to return built_files in-memory (no write)
                payload = {"user_prompt": user_prompt}
                cfg = {"recursion_limit": recursion_limit}
                result = call_agent(agent, payload, config=cfg)
                # try to normalize built_files into our structure (path -> {written:False, content:...})
                bf = None
                if isinstance(result, dict):
                    bf = result.get("built_files")
                if bf:
                    normalized = {}
                    # bf entries might be old "path": "written (...)" or new dict form
                    for p, meta in bf.items():
                        if isinstance(meta, dict) and meta.get("written") is False and "content" in meta:
                            normalized[p] = {"written": False, "content": meta["content"]}
                        elif isinstance(meta, str):
                            # we can't read content from disk (we avoid disk). Mark as note.
                            normalized[p] = {"written": True, "note": meta}
                        else:
                            # fallback: try to stringify
                            normalized[p] = {"written": False, "content": str(meta)}
                    returned = {
                        "user_prompt": user_prompt,
                        "plan": result.get("plan"),
                        "task_plan": result.get("task_plan"),
                        "built_files": normalized,
                        "logs": result.get("logs", []),
                    }
                else:
                    returned = {
                        "user_prompt": user_prompt,
                        "plan": None,
                        "task_plan": None,
                        "built_files": {},
                        "logs": ["agent returned no built_files"],
                    }
            else:
                returned = {
                    "user_prompt": user_prompt,
                    "plan": None,
                    "task_plan": None,
                    "built_files": {},
                    "logs": ["Custom generation skipped (agent missing or disabled)"],
                }

        final_state = {"status": "done", "returned_value": returned}
        logs_area.code(json.dumps(final_state, indent=2, ensure_ascii=False))
        st.success("Generation finished (in-memory).")

        # Show in-memory files if present
        built_files = returned.get("built_files", {}) if isinstance(returned, dict) else {}
        in_memory_files = {p: meta.get("content") for p, meta in built_files.items() if isinstance(meta, dict) and meta.get("written") is False and "content" in meta}

        if in_memory_files:
            files_area.write("Files generated (in-memory preview):")
            for p in sorted(in_memory_files.keys()):
                st.write("-", p)
            chosen = st.selectbox("Preview a file", ["(none)"] + sorted(in_memory_files.keys()))
            if chosen and chosen != "(none)":
                text = in_memory_files[chosen]
                if chosen.lower().endswith(".html"):
                    st.markdown("Previewing generated HTML (in-memory).")
                    components.html(text, height=700, scrolling=True)
                    st.markdown("**Source**")
                    st.code(text)
                else:
                    st.markdown("**File contents**")
                    st.code(text, language="text")
        else:
            files_area.info("No in-memory files available to preview.")

    except Exception:
        st.error("Generation raised an exception — see traceback below.")
        st.exception(traceback.format_exc())
