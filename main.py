# main.py - Generate & render working apps inline (no disk writes)
import os
import json
import traceback
from typing import Any, Dict, Optional

import streamlit as st
import streamlit.components.v1 as components

# Optional agent import (for Custom)
try:
    from agent.graph import agent
except Exception:
    try:
        from graph import agent
    except Exception:
        agent = None

st.set_page_config(page_title="Coder-buddy — Live Generator", layout="wide")
st.title("Coder-buddy — Enter your prompt and generate a working app")

# ---- helper templates (inline style + script embedded) ----
def todo_inline_html() -> str:
    style = """
body { font-family: Arial, sans-serif; background:#f7f7f8; color:#222; padding:20px; }
.app { max-width:600px; margin:30px auto; background:white; padding:20px; border-radius:8px; box-shadow:0 3px 8px rgba(0,0,0,0.06); }
.new-task { display:flex; gap:8px; margin-bottom:12px; }
#task-input { flex:1; padding:8px; border:1px solid #ddd; border-radius:4px; }
#add-btn { padding:8px 12px; border:none; background:#0b79ff; color:white; border-radius:4px; cursor:pointer; }
#tasks { list-style:none; padding:0; margin:0; }
.task { display:flex; justify-content:space-between; gap:8px; padding:8px; border-bottom:1px solid #eee; }
.task .left { display:flex; gap:8px; align-items:center; }
.complete { text-decoration:line-through; color:#999; }
button.small { padding:6px 8px; border-radius:4px; border:none; background:#eee; cursor:pointer; }
    """
    script = r"""
const appRoot = document.getElementById('app-root');

appRoot.innerHTML = `
  <div class="app">
    <h1>TodoApp</h1>
    <div class="new-task">
      <input id="task-input" placeholder="Add a new task..." />
      <button id="add-btn">Add</button>
    </div>
    <ul id="tasks"></ul>
  </div>
`;

const input = document.getElementById('task-input');
const addBtn = document.getElementById('add-btn');
const tasksEl = document.getElementById('tasks');

let tasks = JSON.parse(localStorage.getItem('cb_todos') || '[]');

function save() { localStorage.setItem('cb_todos', JSON.stringify(tasks)); }
function escapeHtml(s){ return s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }

function render() {
  tasksEl.innerHTML = '';
  tasks.forEach((t, i) => {
    const li = document.createElement('li');
    li.className = 'task';
    const checked = t.done ? 'checked' : '';
    li.innerHTML = `
      <div class="left">
        <input type="checkbox" ${checked} data-i="${i}" />
        <span class="${t.done ? 'complete' : ''}">${escapeHtml(t.text)}</span>
      </div>
      <div>
        <button class="small" data-del="${i}">Delete</button>
      </div>
    `;
    tasksEl.appendChild(li);
  });
  save();
}

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

render();
"""
    html = f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{style}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"
    return html

def calc_inline_html() -> str:
    style = """
body { display:flex; height:100vh; align-items:center; justify-content:center; background:#eef2f7; font-family:Arial; margin:0; }
.wrapper { width:320px; padding:18px; }
.calc { width:100%; background:#fff; padding:16px; border-radius:8px; box-shadow:0 6px 18px rgba(0,0,0,0.07); }
#display { width:100%; height:48px; font-size:20px; margin-bottom:10px; padding:6px; text-align:right; border:1px solid #ddd; border-radius:4px; }
#keys { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
.btn { padding:12px; font-size:16px; border-radius:6px; border:none; background:#f1f3f5; cursor:pointer; }
.btn.op { background:#dfe7ff; }
"""
    script = r"""
const container = document.getElementById('calc-root');
container.innerHTML = `
  <div class="wrapper">
    <div class="calc">
      <input id="display" disabled />
      <div id="keys"></div>
    </div>
  </div>
`;
const display = container.querySelector('#display');
const keysEl = container.querySelector('#keys');
const keys = ['7','8','9','/','4','5','6','*','1','2','3','-','0','.','=','+'];
let expr = '';
function render(){ display.value = expr; }
keys.forEach(k => {
  const b = document.createElement('button');
  b.className = 'btn' + (['/','*','-','+','='].includes(k) ? ' op' : '');
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
render();
"""
    html = f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{style}</style></head><body><div id='calc-root'></div><script>{script}</script></body></html>"
    return html

# combine separate files (from agent) into one HTML (inline css and js)
def combine_files_to_html(built_files: Dict[str, Dict[str, Any]]) -> str:
    # built_files: path -> {"written":False,"content":...} or other forms.
    html_content = None
    css_parts = []
    js_parts = []
    for path, meta in built_files.items():
        if not isinstance(meta, dict):
            continue
        content = meta.get("content") or ""
        lower = path.lower()
        if lower.endswith(".html") and html_content is None:
            html_content = content
        elif lower.endswith(".css"):
            css_parts.append(content)
        elif lower.endswith(".js"):
            js_parts.append(content)
    if html_content is None:
        # fallback: create a simple container that shows available parts
        body = "<div><h2>Generated Preview</h2></div>"
        html_head = "<meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' />"
        inlined_css = "<style>" + "\n".join(css_parts) + "</style>" if css_parts else ""
        inlined_js = "<script>" + "\n".join(js_parts) + "</script>" if js_parts else ""
        return f"<!doctype html><html><head>{html_head}{inlined_css}</head><body>{body}{inlined_js}</body></html>"
    # attempt to inject css and js into existing html
    # naive insertion: look for </head> and </body>
    head_insert = ""
    if css_parts:
        head_insert += "<style>" + "\n".join(css_parts) + "</style>"
    body_insert = ""
    if js_parts:
        body_insert += "<script>" + "\n".join(js_parts) + "</script>"
    out = html_content
    if "</head>" in out:
        out = out.replace("</head>", head_insert + "</head>")
    else:
        out = out.replace("<html>", "<html><head>" + head_insert + "</head>", 1)
    if "</body>" in out:
        out = out.replace("</body>", body_insert + "</body>")
    else:
        out = out + body_insert
    return out

# ---- UI ----
with st.form("generator_form", clear_on_submit=False):
    st.subheader("Enter your prompt")
    template = st.selectbox("Template", ["Todo app", "Calculator app", "Custom"])
    prompt = st.text_area("Prompt (for Custom enter instructions; for templates you may leave default)", value="", height=100, placeholder="e.g. Build a simple calculator with + - * / or Build a todo app with add/delete/complete")
    use_agent_for_custom = st.checkbox("Use agent for Custom (if available)", value=False)
    submitted = st.form_submit_button("Generate")

preview_html: Optional[str] = None
logs = []

if submitted:
    try:
        if template == "Todo app":
            preview_html = todo_inline_html()
            logs.append("Generated Todo inline HTML")
        elif template == "Calculator app":
            preview_html = calc_inline_html()
            logs.append("Generated Calculator inline HTML")
        else:  # Custom
            if use_agent_for_custom and agent is not None:
                # call agent and expect built_files as in-memory content
                payload = {"user_prompt": prompt or "Create a small web app"}
                cfg = {"recursion_limit": 100}
                result = None
                # call agent safely
                if hasattr(agent, "invoke"):
                    result = agent.invoke(payload, config=cfg)
                elif callable(agent):
                    result = agent(payload, config=cfg)
                # normalize built_files
                bf = {}
                if isinstance(result, dict):
                    raw_bf = result.get("built_files", {})
                    for p, meta in (raw_bf.items() if isinstance(raw_bf, dict) else []):
                        if isinstance(meta, dict) and meta.get("content") is not None:
                            bf[p] = {"written": False, "content": meta["content"]}
                        elif isinstance(meta, str):
                            # meta string (old style) - attempt to read from disk? we avoid disk => put note
                            bf[p] = {"written": True, "note": meta}
                    if not bf:
                        logs.append("Agent returned no in-memory built files.")
                    else:
                        preview_html = combine_files_to_html(bf)
                        logs.append("Combined agent-built files into preview HTML.")
                else:
                    logs.append("Agent did not return expected dict result.")
            else:
                # simple custom generator: try to infer type from prompt
                low = (prompt or "").lower()
                if "calculator" in low or "calc" in low or "+" in low or "-" in low:
                    preview_html = calc_inline_html()
                    logs.append("Prompt matched 'calculator'; generated local calculator.")
                elif "todo" in low or "to-do" in low or "task" in low:
                    preview_html = todo_inline_html()
                    logs.append("Prompt matched 'todo'; generated local todo.")
                else:
                    # fallback: show a simple HTML preview with the prompt
                    escaped = st.escape(prompt) if hasattr(st, "escape") else (prompt or "")
                    simple = f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>body{{font-family:Arial;padding:20px}}</style></head><body><h2>Preview</h2><pre>{escaped}</pre></body></html>"
                    preview_html = simple
                    logs.append("Fallback preview created for custom prompt.")
    except Exception:
        logs.append("Generation error:\n" + traceback.format_exc())
        preview_html = f"<!doctype html><html><body><pre>{traceback.format_exc()}</pre></body></html>"

# Show logs and preview
st.markdown("---")
st.subheader("Logs")
if logs:
    for line in logs:
        st.write("-", line)
else:
    st.write("No logs yet. Enter a prompt and click Generate.")

st.subheader("Live preview (app will run here)")
if preview_html:
    # render the generated inline app
    components.html(preview_html, height=700, scrolling=True)
else:
    st.info("No preview yet. Enter a prompt and click Generate.")
