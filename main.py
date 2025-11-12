# main.py - Streamlit front-end for your agent (calculator/todo writer)
import os
import time
import json
import traceback as _tb
import logging
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

# -------- flexible import: agent.graph (preferred) OR graph.py at repo root --------
agent = None
_import_traceback = None
try:
    from agent.graph import agent  # if you later move graph.py into agent/, this will work
except Exception:
    try:
        from graph import agent  # fallback: your current layout (graph.py at repo root)
    except Exception:
        _import_traceback = _tb.format_exc()
        logging.exception("Failed to import agent from agent.graph or graph")

# ---------------- helper functions (same invocation compatibility as before) ----------------
def call_agent(agent_obj: Any, payload: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Any:
    """Try multiple invocation styles to be compatible with different agent exports."""
    config = config or {}

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

    raise TypeError(
        "agent is not invokable. Expected an object with .invoke(...) or a callable. "
        "Check your graph.py export (should define `agent = build_app()` at module level)."
    )


def list_recent_files(base_dir: str, since_seconds: int = 300, max_files: int = 50) -> List[Dict[str, str]]:
    cutoff = time.time() - since_seconds
    found: List[tuple[float, str]] = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            path = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime >= cutoff:
                found.append((mtime, path))
    found.sort(reverse=True, key=lambda x: x[0])
    return [{"path": p, "mtime": time.ctime(m)} for m, p in found[:max_files]]


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
st.set_page_config(page_title="Coder-buddy — Agent Runner", layout="wide")
st.title("Coder-buddy — Run agent to generate project files")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Prompt")
    template = st.selectbox("Choose a template (or 'Custom')", ["Todo app", "Calculator app", "Custom"])
    if template == "Todo app":
        default_prompt = "Create a to-do list application using html, css, and javascript."
    elif template == "Calculator app":
        default_prompt = "Create a modern calculator web app in HTML, CSS and JavaScript."
    else:
        default_prompt = ""

    user_prompt = st.text_area("Project prompt", value=default_prompt, height=120)
    recursion_limit = st.number_input("Recursion limit (graph)", min_value=10, max_value=1000, value=100, step=10)
    run_button = st.button("Run agent and generate files")

with col2:
    st.subheader("Agent status")
    if agent is None:
        st.error(
            "agent import failed. Looking for `agent` in either `agent/graph.py` or `graph.py`."
        )
        if st.checkbox("Show import traceback (if any)"):
            if _import_traceback:
                st.code(_import_traceback)
            else:
                st.write("No traceback captured. Check server logs.")
    else:
        st.success("Agent module imported OK")
        st.write("Agent type:", type(agent))

st.markdown("---")
out_col1, out_col2 = st.columns([1, 1])

with out_col1:
    st.subheader("Logs / Final state")
    logs_area = st.empty()

with out_col2:
    st.subheader("Files written / Preview")
    files_area = st.empty()
    preview_area = st.empty()

# run the agent when button clicked
if run_button:
    if agent is None:
        st.error("Cannot run — `agent` is not available. Ensure your `graph.py` defines `agent = build_app()`.")
    else:
        payload = {"user_prompt": user_prompt}
        config = {"recursion_limit": recursion_limit}

        try:
            with st.spinner("Running agent — this may take a while depending on LLM..."):
                result = call_agent(agent, payload, config=config)

            if result is None:
                base_dir = os.getcwd()
                recent = list_recent_files(base_dir, since_seconds=60 * 10)
                final_state = {
                    "status": "done",
                    "returned_value": None,
                    "recent_files_count": len(recent),
                    "recent_files": recent,
                    "message": "Agent returned None — likely wrote files to disk. Showing files modified recently."
                }
            else:
                final_state = {"status": "done", "returned_value": to_serializable(result)}

            logs_area.code(json.dumps(final_state, indent=2, ensure_ascii=False))
            st.success("Agent finished")

            output_dir = os.path.join(os.getcwd(), "output")
            if os.path.isdir(output_dir):
                files = []
                for root, _, filenames in os.walk(output_dir):
                    for fn in filenames:
                        full = os.path.join(root, fn)
                        rel = os.path.relpath(full, os.getcwd())
                        files.append(rel)
                if files:
                    files_area.write(f"Files written to `{output_dir}`:")
                    for f in sorted(files):
                        st.write("-", f)
                    chosen = st.selectbox("Preview a file", ["(none)"] + sorted(files))
                    if chosen and chosen != "(none)":
                        chosen_path = os.path.join(os.getcwd(), chosen)
                        try:
                            text = open(chosen_path, "r", encoding="utf-8").read()
                            if chosen.lower().endswith(".html"):
                                st.markdown("Previewing HTML file (rendered below). If it looks blank, try viewing source.")
                                components.html(text, height=700, scrolling=True)
                                st.markdown("**Source**")
                                st.code(text)
                            else:
                                st.markdown("**File contents**")
                                st.code(text, language="text")
                        except Exception as e:
                            st.error(f"Failed to open file: {e}")
                else:
                    files_area.info(f"No files found in `{output_dir}` — agent may not have written files.")
            else:
                files_area.info("No `output/` directory found (agent may write to a different path).")

        except Exception:
            st.error("Agent execution raised an exception — see traceback below.")
            st.exception(_tb.format_exc())

# helpful footer
st.markdown("---")
st.markdown(
    """
    **Notes / tips**
    - Ensure your `graph.py` (repo root) or `agent/graph.py` defines `agent = build_app()` at module level.
    - Avoid heavy imports or secret-dependent initialization at top-level of graph code (use lazy init if needed).
    - On Streamlit Cloud, add required secrets (GROQ, API keys) in App settings (do NOT commit `.env` to git).
    """
)
