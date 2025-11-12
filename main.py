# main.py - Better Custom prompt handling + modern UI
import os
import json
import traceback
import html
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
# --- page header / style tweaks ---
st.markdown(
    """
    <style>
    .header {
      display:flex; gap:20px; align-items:center; padding:18px;
      background: linear-gradient(90deg, rgba(11,121,255,0.12), rgba(102,51,255,0.06));
      border-radius: 12px; box-shadow: 0 6px 20px rgba(15,23,42,0.06);
    }
    .brand {
      font-weight:700; font-size:20px; color:#0b79ff;
    }
    .sub { color:#475569; margin-top:4px; }
    .gen-btn { background: linear-gradient(90deg,#0b79ff,#6c5ce7); color:white; padding:10px 16px; border-radius:10px; border:none; font-weight:600; }
    .small { font-size:12px; color:#64748b; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="header">
      <div>
        <div class="brand">Coder-buddy</div>
        <div class="sub">Enter a prompt and generate a working web app — preview runs inline.</div>
      </div>
      <div style="margin-left:auto" class="small">No disk writes by default • Modern inline preview</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- helper templates (inline) ----
def todo_inline_html() -> str:
    style = """
:root{--bg:#f6f8fb;--card:#ffffff;--accent:#0b79ff;--muted:#64748b}
body{font-family:Inter,Arial,sans-serif;margin:0;background:var(--bg);padding:24px}
.card{max-width:720px;margin:18px auto;background:var(--card);border-radius:12px;padding:20px;box-shadow:0 8px 30px rgba(15,23,42,0.06)}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.h1{font-size:20px;margin:0;color:#0f172a}
.controls{display:flex;gap:8px}
.input{flex:1;padding:10px;border-radius:8px;border:1px solid #e6eef8}
.btn{background:var(--accent);color:#fff;padding:10px 12px;border-radius:8px;border:none;cursor:pointer}
.list{margin-top:12px;padding:0;list-style:none}
.item{display:flex;align-items:center;justify-content:space-between;padding:10px;border-radius:8px;border:1px solid #f1f5f9;margin-bottom:8px}
.item .left{display:flex;gap:10px;align-items:center}
.complete{opacity:.6;text-decoration:line-through}
.small-btn{padding:6px 8px;border-radius:8px;border:none;background:#eef2ff;cursor:pointer}
"""
    script = r"""
const root = document.getElementById('app-root');
root.innerHTML = `<div class="card"><div class="header"><h2 class="h1">TodoApp</h2></div>
<div style="display:flex;gap:10px"><input id="task-input" class="input" placeholder="Add a task..."/><button id="add-btn" class="btn">Add</button></div>
<ul id="list" class="list"></ul></div>`;
const input = document.getElementById('task-input');
const addBtn = document.getElementById('add-btn');
const listEl = document.getElementById('list');
let tasks = JSON.parse(localStorage.getItem('cb_todos_v2')||'[]');
function save(){localStorage.setItem('cb_todos_v2', JSON.stringify(tasks))}
function render(){
  listEl.innerHTML='';
  tasks.forEach((t,i)=> {
    const li = document.createElement('li'); li.className='item';
    li.innerHTML = `<div class="left"><input type="checkbox" ${t.done?'checked':''} data-i="${i}" /><div style="display:flex;flex-direction:column"><strong>${escapeHtml(t.text)}</strong><small style="color:#64748b">${t.when||''}</small></div></div><div><button class="small-btn" data-del="${i}">Delete</button></div>`;
    listEl.appendChild(li);
  });
  save();
}
function escapeHtml(s){ return (s+'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }
addBtn.onclick = ()=>{ const v=input.value.trim(); if(!v) return; tasks.unshift({text:v,done:false,when:new Date().toLocaleString()}); input.value=''; render(); }
listEl.onclick = (e)=>{ const t=e.target; if(t.dataset.i!==undefined){ const i=Number(t.dataset.i); tasks[i].done=!tasks[i].done; render(); } else if(t.dataset.del!==undefined){ tasks.splice(Number(t.dataset.del),1); render(); } };
render();
"""
    return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{style}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

def calc_inline_html() -> str:
    style = """
:root{--bg:#f3f6ff;--card:#fff;--accent:#6c5ce7}
body{margin:0;font-family:Inter,Arial,sans-serif;background:var(--bg);display:flex;align-items:center;justify-content:center;height:100vh}
.calc-card{width:340px;background:var(--card);padding:18px;border-radius:14px;box-shadow:0 12px 40px rgba(12,15,35,0.07)}
#display{width:100%;height:54px;border-radius:10px;border:1px solid #eef2ff;margin-bottom:12px;padding:10px;font-size:20px;text-align:right}
.keys{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.key{padding:14px;border-radius:10px;border:none;background:#f6f7fb;font-size:16px;cursor:pointer}
.key.op{background:linear-gradient(90deg,#6c5ce7,#0b79ff);color:white}
"""
    script = r"""
const root = document.getElementById('app-root');
root.innerHTML = `<div class="calc-card"><input id="display" disabled /><div id="keys" class="keys"></div></div>`;
const display = document.getElementById('display');
const keysEl = document.getElementById('keys');
const keys = ['7','8','9','/','4','5','6','*','1','2','3','-','0','.','=','+'];
let expr = '';
function render(){ display.value = expr; }
keys.forEach(k => {
  const b = document.createElement('button');
  b.className = 'key' + (['/','*','-','+','='].includes(k) ? ' op' : '');
  b.textContent = k;
  b.onclick = () => {
    if(k === '='){ try{ expr = String(eval(expr)); } catch(e){ expr = 'Error' } }
    else { expr += k; }
    render();
  };
  keysEl.appendChild(b);
});
render();
"""
    return f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{style}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

# combine agent-built files
def combine_files_to_html(built_files: Dict[str, Dict[str, Any]]) -> str:
    html_content = None
    css_parts = []
    js_parts = []
    for path, meta in built_files.items():
        if not isinstance(meta, dict): continue
        content = meta.get("content") or ""
        lp = path.lower()
        if lp.endswith(".html") and html_content is None:
            html_content = content
        elif lp.endswith(".css"):
            css_parts.append(content)
        elif lp.endswith(".js"):
            js_parts.append(content)
    if html_content is None:
        head = "<meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' />"
        return f"<!doctype html><html><head>{head}<style>{''.join(css_parts)}</style></head><body><div style='padding:20px'><h2>Preview</h2></div><script>{''.join(js_parts)}</script></body></html>"
    head_insert = ("<style>" + "\n".join(css_parts) + "</style>") if css_parts else ""
    body_insert = ("<script>" + "\n".join(js_parts) + "</script>") if js_parts else ""
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

# Smart local custom generator (works without agent)
def local_custom_generator(prompt: str) -> str:
    p = (prompt or "").strip()
    low = p.lower()
    # intent heuristics
    if any(k in low for k in ["todo", "to-do", "task", "tasks"]):
        return todo_inline_html()
    if any(k in low for k in ["calc", "calculator", "compute", "sum", "add", "multiply", "+", "-", "*", "/"]):
        return calc_inline_html()
    if any(k in low for k in ["form", "signup", "contact", "feedback"]):
        # simple form scaffold
        title = html.escape(p or "Form")
        css = """
body{font-family:Inter,Arial,sans-serif;background:#f8fafc;padding:30px}
.card{max-width:700px;margin:0 auto;background:#fff;padding:20px;border-radius:12px;box-shadow:0 10px 30px rgba(2,6,23,0.06)}
label{display:block;margin-top:10px;font-weight:600}
input,textarea,select{width:100%;padding:10px;border-radius:8px;border:1px solid #e6eef8;margin-top:6px}
.btn{margin-top:12px;padding:10px 12px;border-radius:10px;background:linear-gradient(90deg,#0b79ff,#6c5ce7);color:white;border:none}
"""
        html_body = f"""<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{css}</style></head><body><div class='card'><h2>{title}</h2><form><label>Name<input placeholder='Your name'/></label><label>Email<input placeholder='you@example.com'/></label><label>Message<textarea rows='4'></textarea></label><button class='btn' type='button' onclick='alert(\"Submitted (demo)\")'>Submit</button></form></div></body></html>"""
        return html_body
    # fallback: generate a modern scaffold that embeds the prompt and a small interactive example
    safe = html.escape(p or "Generated App")
    css = """
body{font-family:Inter,Arial,sans-serif;background:linear-gradient(180deg,#f8fafc,#fff);padding:28px}
.wrapper{max-width:900px;margin:0 auto}
.card{background:#fff;padding:20px;border-radius:12px;box-shadow:0 12px 30px rgba(2,6,23,0.06)}
header{display:flex;align-items:center;justify-content:space-between}
h1{margin:0;font-size:20px;color:#0f172a}
.desc{color:#475569;margin-top:8px}
.preview{margin-top:18px;padding:12px;border-radius:8px;border:1px solid #eef2ff;background:#fbfdff}
.btn{padding:8px 12px;border-radius:8px;border:none;background:linear-gradient(90deg,#0b79ff,#6c5ce7);color:#fff;cursor:pointer}
"""
    script = f"""
function esc(s){{return s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}} 
document.addEventListener('DOMContentLoaded',()=>{{
  const root=document.getElementById('app-root');
  root.innerHTML=`<div class="wrapper"><div class="card"><header><h1>{safe}</h1></header><p class="desc">This is a small interactive scaffold generated from your prompt: <strong>{safe}</strong></p><div class="preview"><button class="btn" id="demo">Click me</button><div id="out" style="margin-top:12px"></div></div></div></div>`;
  document.getElementById('demo').onclick = ()=> document.getElementById('out').innerText = 'Hello — this demo responds to your prompt!';
}});
"""
    return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{css}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

# ---- UI form ----
with st.form("gen", clear_on_submit=False):
    st.subheader("Enter your prompt")
    template = st.selectbox("Template", ["Todo app", "Calculator app", "Custom"])
    prompt = st.text_area("Prompt (leave empty to use template defaults)", value="", height=110, placeholder="e.g. Build a simple note-taking app with tags and search")
    use_agent_for_custom = st.checkbox("Use agent for Custom (if available)", value=False)
    submit = st.form_submit_button("Generate", help="Generate and render the app inline")

preview_html: Optional[str] = None
logs = []

if submit:
    try:
        if template == "Todo app":
            preview_html = todo_inline_html()
            logs.append("Generated Todo app locally (inline).")
        elif template == "Calculator app":
            preview_html = calc_inline_html()
            logs.append("Generated Calculator locally (inline).")
        else:  # Custom
            if use_agent_for_custom and agent is not None:
                try:
                    payload = {"user_prompt": prompt or "Create a small web app"}
                    cfg = {"recursion_limit": 200}
                    # safe agent call
                    if hasattr(agent, "invoke"):
                        result = agent.invoke(payload, config=cfg)
                    elif callable(agent):
                        result = agent(payload, config=cfg)
                    else:
                        result = None
                    if isinstance(result, dict) and result.get("built_files"):
                        # normalize and combine
                        raw = result.get("built_files", {})
                        normalized = {}
                        for p, meta in (raw.items() if isinstance(raw, dict) else []):
                            if isinstance(meta, dict) and meta.get("content") is not None:
                                normalized[p] = {"written": False, "content": meta["content"]}
                        if not normalized:
                            logs.append("Agent did not return in-memory file contents; falling back to local generator.")
                            preview_html = local_custom_generator(prompt)
                        else:
                            preview_html = combine_files_to_html(normalized)
                            logs.append("Used agent output for preview.")
                    else:
                        logs.append("Agent returned no usable built_files; using local generator.")
                        preview_html = local_custom_generator(prompt)
                except Exception as e:
                    logs.append("Agent error: " + str(e))
                    logs.append("Falling back to local generator.")
                    preview_html = local_custom_generator(prompt)
            else:
                preview_html = local_custom_generator(prompt)
                logs.append("Generated from prompt locally (no agent).")
    except Exception as e:
        logs.append("Generation failed: " + str(e))
        logs.append(traceback.format_exc())
        preview_html = f"<!doctype html><html><body><pre>{html.escape(traceback.format_exc())}</pre></body></html>"

# --- render logs & preview ---
st.markdown("---")
st.subheader("Preview")
if preview_html:
    # show a compact info bar
    st.markdown(
        "<div style='padding:8px;border-radius:8px;background:linear-gradient(90deg,#f8fafc,#fff);box-shadow:0 6px 18px rgba(15,23,42,0.03);margin-bottom:8px'><strong>Live preview below — interactive.</strong></div>",
        unsafe_allow_html=True,
    )
    components.html(preview_html, height=680, scrolling=True)
else:
    st.info("No preview yet. Enter a prompt and click Generate.")

st.markdown("----")
st.subheader("Logs")
if logs:
    for l in logs:
        st.write("-", l)
else:
    st.write("No logs yet.")
