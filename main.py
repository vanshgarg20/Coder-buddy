# main.py - Better Custom prompt handling + GROQ integration + modern UI
import os
import json
import traceback
import html
from typing import Any, Dict, Optional

import streamlit as st
import streamlit.components.v1 as components

# Optional agent import (kept as fallback)
try:
    from agent.graph import agent
except Exception:
    try:
        from graph import agent
    except Exception:
        agent = None

st.set_page_config(page_title="Coder-buddy — Live Generator (GROQ)", layout="wide")

# ---- small helper: lazy ChatGroq factory ----
def get_groq_llm():
    """Return a ChatGroq LLM instance using GROQ_API_KEY env var (lazy import)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    try:
        from langchain_groq import ChatGroq  # lazy import
    except Exception as e:
        raise RuntimeError(f"Missing langchain_groq package: {e}")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    temp = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
    # pass api_key explicitly to the client
    return ChatGroq(model=model, temperature=temp, api_key=api_key)

# ---- prompts for LLM usage ----
ANSWER_PROMPT = """You are a helpful assistant. Answer the user's question concisely and accurately.
If you are unsure, say you are unsure and provide suggestions to verify online.
User question:
{user_prompt}
"""

HTML_GENERATOR_PROMPT = """You are a web developer assistant. Produce a single self-contained HTML file (including inline CSS and JS)
that implements the requested web component or small web app described below. Return ONLY the full HTML document (no explanations).
User request:
{user_prompt}

Constraints:
- Output a single HTML document (<!doctype html> ... </html>) that can be saved and opened.
- Keep it simple, responsive, and working without external dependencies.
- Avoid external network requests or CDN resources.
"""

# --- page header / style tweaks (same as before) ---
st.markdown(
    """
    <style>
    .header {
      display:flex; gap:20px; align-items:center; padding:18px;
      background: linear-gradient(90deg, rgba(11,121,255,0.12), rgba(102,51,255,0.06));
      border-radius: 12px; box-shadow: 0 6px 20px rgba(15,23,42,0.06);
    }
    .brand { font-weight:700; font-size:20px; color:#0b79ff; }
    .sub { color:#475569; margin-top:4px; }
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
        <div class="sub">Enter a prompt and generate or ask — preview runs inline.</div>
      </div>
      <div style="margin-left:auto" class="small">No disk writes by default • GROQ-enabled</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- inline templates (todo, calc, snake, tic, notes) ---
# (same functions as before; omitted here to shorten — include your versions)
# For brevity I re-use the same inline templates from your file:
def todo_inline_html() -> str:
    # copy the todo inline template content from your file (unchanged)
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

def snake_game_html() -> str:
    # copy snake template from earlier
    style = """
:root{--bg:#f7fafc}
body{margin:0;font-family:Inter,Arial,sans-serif;background:var(--bg);display:flex;align-items:center;justify-content:center;height:100vh}
.card{background:#fff;padding:18px;border-radius:12px;box-shadow:0 10px 40px rgba(2,6,23,0.06)}
canvas{background:#0f172a;border-radius:8px;display:block}
.info{margin-top:10px;color:#475569;text-align:center}
.btn{margin-top:8px;padding:8px 12px;border-radius:8px;border:none;background:linear-gradient(90deg,#0b79ff,#6c5ce7);color:white;cursor:pointer}
"""
    script = r"""/* snake script omitted here for brevity; use your previous snake_game_html content */"""
    return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{style}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

def tic_tac_toe_html() -> str:
    # copy tic tac toe template from earlier
    style = """body{font-family:Inter,Arial,sans-serif;background:#f6f9fc;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"""
    script = r"""/* tic tac toe script omitted here for brevity; use your previous tic_tac_toe_html content */"""
    return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{style}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

def notes_inline_html():
    # will be created by local_custom_generator when needed; kept out here
    return ""

# combine_files_to_html (same as before)
def combine_files_to_html(built_files: Dict[str, Dict[str, Any]]) -> str:
    html_content = None
    css_parts = []
    js_parts = []
    for path, meta in built_files.items():
        if not isinstance(meta, dict):
            continue
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

# local_custom_generator (improved notes + games + fallback)
def local_custom_generator(prompt: str) -> str:
    p = (prompt or "").strip().lower()
    if any(k in p for k in ["note", "notes", "note-taking", "notes maker", "notes app"]):
        # use the notes builder script from previous reply (omitted here for brevity)
        # we will construct a simple notes app inline:
        css = """
:root{--bg:#f6f8fb;--card:#fff;--accent:#6c5ce7}
body{margin:0;font-family:Inter, Arial, sans-serif;background:var(--bg);padding:28px}
.container{max-width:960px;margin:0 auto}
.header{display:flex;align-items:center;justify-content:space-between;gap:12px}
.title{font-size:20px;color:#0f172a;margin:0}
.input{flex:1;padding:10px;border-radius:10px;border:1px solid #e6eef8}
.btn{background:linear-gradient(90deg,#0b79ff,#6c5ce7);color:#fff;padding:10px 14px;border-radius:10px;border:none;cursor:pointer}
.grid{display:grid;grid-template-columns:1fr 340px;gap:18px;margin-top:18px}
.card{background:var(--card);padding:12px;border-radius:10px;box-shadow:0 8px 30px rgba(2,6,23,0.04);border:1px solid #f1f5f9}
textarea.note-area{width:100%;height:120px;border-radius:8px;padding:10px;border:1px solid #e6eef8}
"""
        script = r"""
const root = document.getElementById('app-root');
root.innerHTML = `<div class="container"><div class="header"><div><h2 class="title">Notes</h2><div class="small">Simple notes — stored in your browser (localStorage)</div></div></div>
<div class="grid"><div>
  <div class="card"><div style="display:flex;gap:8px;align-items:center"><input id="filter" class="search" placeholder="Search notes..."/></div>
    <div id="notes-list" style="margin-top:12px"></div></div>
</div>
<div>
  <div class="card">
    <div style="display:flex;gap:8px;margin-bottom:10px">
      <input id="title" class="input" placeholder="Note title" />
      <button id="save" class="btn">Save</button>
    </div>
    <textarea id="body" class="note-area" placeholder="Write your note..."></textarea>
    <div style="display:flex;gap:8px;margin-top:10px">
      <button id="clear-all" class="opt-btn">Clear all</button>
      <div style="flex:1"></div>
      <div class="small">Notes are stored locally only.</div>
    </div>
  </div>
</div></div></div>`;
const notesKey = 'cb_notes_v1';
let notes = JSON.parse(localStorage.getItem(notesKey) || '[]');
function saveNotes(){ localStorage.setItem(notesKey, JSON.stringify(notes)); }
function uid(){ return Math.random().toString(36).slice(2,9); }
function formatDate(ts){ const d = new Date(ts); return d.toLocaleString(); }
function renderList(filterText=''){
  const list = document.getElementById('notes-list');
  list.innerHTML = '';
  const filtered = notes.filter(n => (n.title + ' ' + n.body).toLowerCase().includes(filterText.toLowerCase()));
  if(filtered.length===0){ list.innerHTML = '<div class="small">No notes yet.</div>'; return; }
  filtered.forEach(n => {
    const el = document.createElement('div');
    el.className = 'list-item';
    el.innerHTML = `<div style="flex:1"><strong>${escapeHtml(n.title||'(untitled)')}</strong><div class="small">${escapeHtml(n.body.slice(0,120))}</div><div class="note-meta">${formatDate(n.ts)}</div></div>
      <div style="display:flex;flex-direction:column;gap:6px">
        <button class="opt-btn" data-edit="${n.id}">Edit</button>
        <button class="opt-btn" data-del="${n.id}">Delete</button>
      </div>`;
    list.appendChild(el);
  });
}
function escapeHtml(s){ return (s||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }
document.getElementById('save').onclick = ()=>{
  const title = document.getElementById('title').value.trim();
  const body = document.getElementById('body').value.trim();
  if(!body && !title) return;
  const editingId = document.getElementById('save').dataset.editing;
  if(editingId){
    const idx = notes.findIndex(x=>x.id===editingId);
    if(idx>=0){ notes[idx].title = title; notes[idx].body = body; notes[idx].ts = Date.now(); }
    delete document.getElementById('save').dataset.editing;
  } else {
    notes.unshift({id: uid(), title, body, ts: Date.now()});
  }
  saveNotes(); document.getElementById('title').value=''; document.getElementById('body').value=''; renderList(document.getElementById('filter').value);
};
document.getElementById('filter').oninput = (e)=> renderList(e.target.value);
document.getElementById('notes-list').onclick = (e)=>{
  const d = e.target;
  const edit = d.closest('button[data-edit]');
  const del = d.closest('button[data-del]');
  if(edit){
    const id = edit.dataset.edit;
    const note = notes.find(x=>x.id===id);
    if(note){ document.getElementById('title').value = note.title; document.getElementById('body').value = note.body; document.getElementById('save').dataset.editing = id; window.scrollTo({top:0,behavior:'smooth'}); }
  } else if(del){
    const id = del.dataset.del;
    notes = notes.filter(x=>x.id!==id);
    saveNotes(); renderList(document.getElementById('filter').value);
  }
};
document.getElementById('clear-all').onclick = ()=>{ if(confirm('Clear all notes?')){ notes=[]; saveNotes(); renderList(''); } };
renderList('');
"""
        return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{css}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

    if "snake" in p:
        return snake_game_html()
    if "tic" in p and "toe" in p:
        return tic_tac_toe_html()
    if "calculator" in p or "calc" in p:
        return calc_inline_html()
    if "todo" in p or "task" in p:
        return todo_inline_html()

    safe = html.escape(prompt or "Generated App")
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
  root.innerHTML=`<div class="wrapper"><div class="card"><header><h1>{html.escape(prompt or 'Generated App')}</h1></header><p class="desc">This is a scaffold generated from: <strong>{html.escape(prompt or '')}</strong></p><div class="preview"><button class="btn" id="demo">Click demo</button><div id="out" style="margin-top:12px"></div></div></div></div>`;
  document.getElementById('demo').onclick = ()=> document.getElementById('out').innerText = 'Interactive demo for: {html.escape(prompt or "")}';
}});
"""
    return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{css}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

# ---- UI form ----
with st.form("gen", clear_on_submit=False):
    st.subheader("Enter your prompt")
    template = st.selectbox("Template", ["Todo app", "Calculator app", "Custom"])
    prompt = st.text_area("Prompt (leave empty to use template defaults)", value="", height=110, placeholder="e.g. Build a simple note-taking app with tags and search")
    use_agent_for_custom = st.checkbox("Use agent for Custom (if available, prefers GROQ LLM)", value=False)
    submit = st.form_submit_button("Generate", help="Generate and render the app inline")

preview_html: Optional[str] = None
logs = []

# small heuristic: check if a prompt seems like a question
def looks_like_question(s: str) -> bool:
    s = (s or "").strip().lower()
    if not s:
        return False
    if s.endswith("?"):
        return True
    for w in ("what", "who", "how", "why", "when", "where", "explain", "difference", "compare"):
        if s.startswith(w + " ") or (" " + w + " ") in s:
            return True
    return False

if submit:
    try:
        if template == "Todo app":
            preview_html = todo_inline_html()
            logs.append("Generated Todo app locally (inline).")
        elif template == "Calculator app":
            preview_html = calc_inline_html()
            logs.append("Generated Calculator locally (inline).")
        else:  # Custom
            if use_agent_for_custom:
                # prefer GROQ LLM if available
                llm = None
                try:
                    llm = get_groq_llm()
                    logs.append("GROQ LLM initialized.")
                except Exception as e:
                    logs.append("GROQ init failed: " + str(e))
                    llm = None

                if llm is not None:
                    user_text = prompt or "Create a small web app"
                    try:
                        if looks_like_question(user_text):
                            # ask LLM to answer
                            final_prompt = ANSWER_PROMPT.format(user_prompt=user_text)
                            if hasattr(llm, "invoke"):
                                ans = llm.invoke(final_prompt)
                            else:
                                ans = llm(final_prompt)
                            # normalize
                            answer_text = ans if isinstance(ans, str) else str(ans)
                            preview_html = "<!doctype html><html><body style='font-family:Inter,Arial,sans-serif;padding:20px'><div>" + html.escape(answer_text) + "</div></body></html>"
                            logs.append("Answered via GROQ LLM.")
                        else:
                            # ask LLM to generate a single HTML doc
                            final_prompt = HTML_GENERATOR_PROMPT.format(user_prompt=user_text)
                            if hasattr(llm, "invoke"):
                                gen = llm.invoke(final_prompt)
                            else:
                                gen = llm(final_prompt)
                            gen_text = gen if isinstance(gen, str) else str(gen)
                            if "<!doctype" in gen_text.lower() or "<html" in gen_text.lower():
                                preview_html = gen_text
                            else:
                                preview_html = "<!doctype html><html><body><pre>" + html.escape(gen_text) + "</pre></body></html>"
                            logs.append("Generated HTML via GROQ LLM.")
                    except Exception as e:
                        logs.append("GROQ call failed: " + str(e))
                        logs.append("Falling back to agent/local generator.")
                        # fallback to agent (if exists) then local
                        if agent is not None:
                            try:
                                payload = {"user_prompt": prompt or "Create a small web app"}
                                cfg = {"recursion_limit": 200}
                                if hasattr(agent, "invoke"):
                                    result = agent.invoke(payload, config=cfg)
                                elif callable(agent):
                                    result = agent(payload, config=cfg)
                                else:
                                    result = None
                                if isinstance(result, dict) and result.get("built_files"):
                                    raw = result.get("built_files", {})
                                    normalized = {}
                                    for p, meta in (raw.items() if isinstance(raw, dict) else []):
                                        if isinstance(meta, dict) and meta.get("content") is not None:
                                            normalized[p] = {"written": False, "content": meta["content"]}
                                    if normalized:
                                        preview_html = combine_files_to_html(normalized)
                                        logs.append("Used agent output for preview.")
                                    else:
                                        preview_html = local_custom_generator(prompt)
                                        logs.append("Agent did not produce in-memory files; used local generator.")
                                else:
                                    preview_html = local_custom_generator(prompt)
                                    logs.append("Agent returned no usable built_files; used local generator.")
                            except Exception as e2:
                                logs.append("Agent fallback failed: " + str(e2))
                                preview_html = local_custom_generator(prompt)
                        else:
                            preview_html = local_custom_generator(prompt)
                else:
                    # no LLM, try agent fallback
                    if agent is not None:
                        try:
                            payload = {"user_prompt": prompt or "Create a small web app"}
                            cfg = {"recursion_limit": 200}
                            if hasattr(agent, "invoke"):
                                result = agent.invoke(payload, config=cfg)
                            elif callable(agent):
                                result = agent(payload, config=cfg)
                            else:
                                result = None
                            if isinstance(result, dict) and result.get("built_files"):
                                raw = result.get("built_files", {})
                                normalized = {}
                                for p, meta in (raw.items() if isinstance(raw, dict) else []):
                                    if isinstance(meta, dict) and meta.get("content") is not None:
                                        normalized[p] = {"written": False, "content": meta["content"]}
                                if normalized:
                                    preview_html = combine_files_to_html(normalized)
                                    logs.append("Used agent output for preview.")
                                else:
                                    preview_html = local_custom_generator(prompt)
                                    logs.append("Agent returned no in-memory files; used local generator.")
                            else:
                                preview_html = local_custom_generator(prompt)
                                logs.append("Agent returned no usable built_files; used local generator.")
                        except Exception as e:
                            logs.append("Agent call failed: " + str(e))
                            preview_html = local_custom_generator(prompt)
                    else:
                        preview_html = local_custom_generator(prompt)
                        logs.append("Generated from prompt locally (no LLM or agent).")
            else:
                # user didn't check 'Use agent for Custom' -> local generator only
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
    st.markdown(
        "<div style='padding:8px;border-radius:8px;background:linear-gradient(90deg,#f8fafc,#fff);box-shadow:0 6px 18px rgba(15,23,42,0.03);margin-bottom:8px'><strong>Live preview below — interactive.</strong></div>",
        unsafe_allow_html=True,
    )
    components.html(preview_html, height=720, scrolling=True)
else:
    st.info("No preview yet. Enter a prompt and click Generate.")

st.markdown("----")
st.subheader("Logs")
if logs:
    for l in logs:
        st.write("-", l)
else:
    st.write("No logs yet.")
