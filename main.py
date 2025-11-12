# main.py — Coder-buddy (modern UI, toolbar, preview download)
import os
import re
import html
import traceback
from typing import Any, Optional

import streamlit as st
import streamlit.components.v1 as components

# Optional agent import (fallback)
try:
    from agent.graph import agent
except Exception:
    try:
        from graph import agent
    except Exception:
        agent = None

st.set_page_config(page_title="Coder-buddy — Live Generator", layout="wide", initial_sidebar_state="collapsed")

# ---------- Styles & Hero ----------
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
    :root{
      --bg:#0b1020; --card:#0f1724; --muted:#94a3b8; --accent1:#6c5ce7; --accent2:#0b79ff;
      --glass: rgba(255,255,255,0.04);
    }
    html,body { background: var(--bg); color: #e6eef8; font-family: Inter, Arial, sans-serif; }
    .hero { display:flex; gap:20px; align-items:center; padding:28px; border-radius:14px;
            background: linear-gradient(90deg, rgba(12,40,90,0.20), rgba(80,28,120,0.12));
            box-shadow: 0 8px 30px rgba(2,6,23,0.6); margin-bottom:18px; }
    .logo { font-weight:800; font-size:22px; color: var(--accent2); letter-spacing:0.3px; }
    .logo .heart { color:#5be0ff; margin-left:8px; font-size:18px; }
    .tag { color:var(--muted); margin-top:6px; }
    .hero-right { margin-left:auto; color:var(--muted); font-size:13px }
    .panel { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.03); }
    .form-title { font-size:20px; font-weight:700; color:#fff; margin-bottom:6px; }
    .muted { color:var(--muted); }
    .primary-btn { background: linear-gradient(90deg,var(--accent2),var(--accent1)); color:white; border:none; padding:10px 16px; border-radius:10px; font-weight:700; cursor:pointer; }
    .secondary { background: transparent; border:1px solid rgba(255,255,255,0.06); color:var(--muted); padding:8px 10px; border-radius:8px; }
    .preview-frame { width:100%; border-radius:12px; overflow:hidden; border:1px solid rgba(255,255,255,0.04); background:#fff; padding:10px; }
    .toolbar { display:flex; gap:8px; align-items:center; justify-content:space-between; margin-bottom:10px; }
    .toolbar-left { display:flex; gap:8px; align-items:center; }
    .small-muted { color: #677487; font-size:13px }
    /* inputs */
    .stTextArea > label { color:#fff !important; }
    .stSelectbox > label { color:#fff !important; }
    .stCheckbox > label { color:#fff !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Hero
st.markdown(
    f"""
    <div class="hero">
      <div>
        <div class="logo">Coder-buddy <span class="heart">💙</span></div>
        <div class="tag">Ask a question, or generate a small working web app — preview runs inline, no disk writes by default.</div>
      </div>
      <div class="hero-right">Fast • Modern • Interactive</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- helper functions (LLM & preview cleaning) ----------
def extract_text_from_llm_output(out: Any) -> str:
    try:
        if out is None:
            return ""
        if isinstance(out, str):
            return out
        if isinstance(out, dict):
            for k in ("text", "content", "output", "answer"):
                if k in out and out[k] is not None:
                    return str(out[k])
            for v in out.values():
                if isinstance(v, str) and v.strip():
                    return v
            return str(out)
        if hasattr(out, "content") and getattr(out, "content"):
            return str(getattr(out, "content"))
        if hasattr(out, "text") and getattr(out, "text"):
            return str(getattr(out, "text"))
        # fallback heuristics
        s = str(out)
        m = re.search(r"content=(?:'|\")(.+?)(?:'|\")", s)
        if m:
            return m.group(1)
        return s
    except Exception:
        return str(out)

def call_llm_and_get_text(llm, prompt: str) -> str:
    errors = []
    if llm is None:
        raise RuntimeError("LLM is None")
    try:
        if hasattr(llm, "invoke"):
            return extract_text_from_llm_output(llm.invoke(prompt))
    except Exception as e:
        errors.append("invoke:" + str(e))
    try:
        return extract_text_from_llm_output(llm(prompt))
    except Exception as e:
        errors.append("call:" + str(e))
    try:
        if hasattr(llm, "generate"):
            return extract_text_from_llm_output(llm.generate([prompt]))
    except Exception as e:
        errors.append("generate:" + str(e))
    raise RuntimeError("LLM invocation failed: " + " | ".join(errors))

# preview cleaning & CSS injection
INJECTED_CSS = """
html, body { background: #ffffff !important; color: #0f172a !important; }
body { font-family: Inter, Arial, sans-serif; -webkit-font-smoothing:antialiased; }
"""

def strip_triple_backticks_and_lang(s: str) -> str:
    if not s:
        return s
    s = s.strip()
    m = re.match(r"^```(?:\w+)?\s*(.*)\s*```$", s, flags=re.S)
    if m:
        return m.group(1).strip()
    s = re.sub(r"^```[\w-]*\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s

def extract_inner_html_from_markdown(s: str) -> str:
    if not s:
        return s
    m = re.search(r"```(?:html)?\s*(<[^`]+>)\s*```", s, flags=re.S | re.I)
    if m:
        return m.group(1).strip()
    return strip_triple_backticks_and_lang(s)

def inject_css_into_html(html_text: str, css: str) -> str:
    if not html_text:
        return f"<!doctype html><html><head><style>{css}</style></head><body></body></html>"
    s = html_text.strip()
    if s.lower().startswith("<!doctype") or s.lower().startswith("<html"):
        if "</head>" in s.lower():
            return re.sub(r"(?i)</head>", f"<style>{css}</style></head>", s, count=1)
        else:
            return re.sub(r"(?i)<html([^>]*)>", r"<html\1><head><style>" + css + "</style></head>", s, count=1)
    return f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>{css}</style></head><body>{s}</body></html>"

def clean_preview_html(raw: str) -> str:
    if raw is None:
        return ""
    s = raw.strip()
    s = extract_inner_html_from_markdown(s)
    s = s.replace("```html", "").replace("```", "").strip()
    cleaned = inject_css_into_html(s, INJECTED_CSS)
    return cleaned

# ---------- small templates ----------
def todo_inline_html() -> str:
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>
body{font-family:Inter,Arial,sans-serif;background:#f6f8fb;padding:24px}
.card{max-width:720px;margin:18px auto;background:#fff;padding:16px;border-radius:12px;box-shadow:0 8px 30px rgba(2,6,23,0.06)}
.input{width:70%;padding:8px;border-radius:8px;border:1px solid #e6eef8}
.btn{padding:8px 12px;border-radius:8px;border:none;background:#0b79ff;color:#fff}
.list{margin-top:12px}
</style></head><body><div class='card'><h3>Todo</h3><div><input id='t' class='input' placeholder='Add task'><button id='a' class='btn'>Add</button></div><ul id='l' class='list'></ul></div><script>
const LKEY='cb_todos_v4';let l=JSON.parse(localStorage.getItem(LKEY)||'[]');function r(){const el=document.getElementById('l');el.innerHTML='';l.forEach((t,i)=>{const li=document.createElement('li');li.innerText=t;li.onclick=()=>{l.splice(i,1);localStorage.setItem(LKEY,JSON.stringify(l));r()};el.appendChild(li)})}document.getElementById('a').onclick=()=>{const v=document.getElementById('t').value.trim();if(!v) return; l.unshift(v); localStorage.setItem(LKEY,JSON.stringify(l)); document.getElementById('t').value=''; r()};r();
</script></body></html>"""

def calc_inline_html() -> str:
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>
body{font-family:Inter,Arial,sans-serif;background:#eef6ff;display:flex;align-items:center;justify-content:center;height:100vh}
.calc-card{width:320px;background:#fff;padding:18px;border-radius:14px;box-shadow:0 12px 40px rgba(2,6,23,0.06)}
#display{width:100%;height:54px;border-radius:10px;border:1px solid #eef2ff;margin-bottom:12px;padding:10px;font-size:20px;text-align:right}
.keys{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.key{padding:12px;border-radius:10px;border:none;background:#f6f7fb;font-size:16px;cursor:pointer}
.key.op{background:linear-gradient(90deg,#6c5ce7,#0b79ff);color:white}
</style></head><body><div class='calc-card'><input id='display' disabled /><div id='keys' class='keys'></div></div><script>
const keys=['7','8','9','/','4','5','6','*','1','2','3','-','0','.','=','+'];const keysEl=document.getElementById('keys');const display=document.getElementById('display');let expr='';function render(){display.value=expr;}keys.forEach(k=>{const b=document.createElement('button');b.className='key'+(['/','*','-','+','='].includes(k)?' op':'');b.textContent=k;b.onclick=()=>{if(k==='='){try{expr=String(eval(expr))}catch(e){expr='Error'}}else{expr+=k}render()};keysEl.appendChild(b)});render();
</script></body></html>"""

def local_custom_generator(prompt: str) -> str:
    p = (prompt or "").strip().lower()
    if any(k in p for k in ["note", "notes", "note-taking", "notes app", "notes maker"]):
        return todo_inline_html()
    if "snake" in p:
        return "<!doctype html><html><body><h3>Snake game placeholder</h3></body></html>"
    if "tic" in p and "toe" in p:
        return "<!doctype html><html><body><h3>Tic Tac Toe placeholder</h3></body></html>"
    if any(k in p for k in ["calc", "calculator", "stopwatch", "timer"]):
        # prefer calculator / stopwatch; use calc template for simplicity
        return calc_inline_html()
    if any(k in p for k in ["todo", "task", "todo list"]):
        return todo_inline_html()
    safe = html.escape(prompt or "Generated App")
    return f"<!doctype html><html><head><meta charset='utf-8'></head><body style='font-family:Inter,Arial,sans-serif;padding:24px'><h3>{safe}</h3><p>Light scaffold generated from your prompt.</p></body></html>"

# ---------- form UI (left column) ----------
col1, col2 = st.columns([1.1, 1])
with col1:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="form-title">Enter your prompt or question</div>', unsafe_allow_html=True)
    mode = st.selectbox("Mode", ["Ask (question)", "Generate app (build)"])
    prompt = st.text_area("Prompt / Question", value="", height=140, placeholder="e.g. Create a stopwatch with start/stop/reset or How does Python list comprehension work?")
    use_groq = st.checkbox("Use GROQ LLM (requires GROQ_API_KEY env var)", value=bool(os.getenv("GROQ_API_KEY")))
    run_btn = st.button("Run", key="run", help="Generate / Ask")
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    # right column: quick CTA / examples
    st.markdown('<div style="padding:12px;border-radius:12px">', unsafe_allow_html=True)
    st.markdown("<div style='font-weight:700;font-size:16px;margin-bottom:6px'>Examples</div>", unsafe_allow_html=True)
    st.markdown("<div class='muted'>Try prompts like:</div>", unsafe_allow_html=True)
    st.markdown("""
    <ul class='muted'>
      <li><code>Create a stopwatch web app with start, stop, and reset</code></li>
      <li><code>Build a todo list with localStorage and search</code></li>
      <li><code>Explain how Python's map() works</code></li>
      <li><code>Create a snake game in plain JavaScript</code></li>
    </ul>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='muted'>Preview toolbar appears once generation finishes. Use Download to save the preview.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- run logic ----------
preview_html: Optional[str] = None
answer_text: Optional[str] = None
_internal_logs = []

def looks_like_question_text(s: str) -> bool:
    s = (s or "").strip().lower()
    if not s:
        return False
    if s.endswith("?"):
        return True
    for w in ("what", "who", "how", "why", "when", "where", "explain", "difference", "compare"):
        if s.startswith(w + " ") or (" " + w + " ") in s:
            return True
    return False

# ---------- run logic (REPLACE existing `if run_btn:` block with this) ----------
preview_html: Optional[str] = None
answer_text: Optional[str] = None
_internal_logs = []

if run_btn:
    user_text = (prompt or "").strip()
    if not user_text:
        st.warning("Please enter a prompt or question.")
    else:
        # init LLM only if user asked for GROQ
        llm = None
        if use_groq:
            try:
                from langchain_groq import ChatGroq
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    raise RuntimeError("GROQ_API_KEY not set in environment")
                llm = ChatGroq(
                    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                    temperature=float(os.getenv("GROQ_TEMPERATURE", "0.2")),
                    api_key=api_key
                )
                _internal_logs.append("GROQ initialized")
            except Exception as e:
                llm = None
                _internal_logs.append("GROQ init failed: " + str(e))

        try:
            # ---------- ASK (question) mode ----------
            if mode == "Ask (question)":
                if llm is not None:
                    try:
                        final_prompt = f"You are a helpful assistant. Answer concisely.\nUser: {user_text}\n"
                        raw = call_llm_and_get_text(llm, final_prompt)
                        answer_text = extract_text_from_llm_output(raw)
                        _internal_logs.append("Answered with GROQ")
                    except Exception as e:
                        _internal_logs.append("GROQ answer failed: " + str(e))
                        answer_text = "GROQ error. Try again or disable GROQ to use local/agent fallback."
                else:
                    # try agent fallback
                    if agent is not None:
                        try:
                            payload = {"user_prompt": user_text}
                            res = agent.invoke(payload, config={"recursion_limit": 50}) if hasattr(agent, "invoke") else agent(payload)
                            answer_text = extract_text_from_llm_output(res)
                            _internal_logs.append("Answered with agent fallback")
                        except Exception as e:
                            _internal_logs.append("Agent failed for question: " + str(e))
                            answer_text = "Agent failed to answer. Enable GROQ or try a different prompt."
                    else:
                        answer_text = "No GROQ and no agent available. Enable GROQ or use Generate mode."

            # ---------- GENERATE (app) mode ----------
            else:
                # Priority: GROQ -> agent -> local fallback
                generated = False

                # 1) Try GROQ if we have it
                if llm is not None:
                    try:
                        gen_prompt = f"Produce a single self-contained HTML document implementing: {user_text}\nReturn only the HTML document."
                        raw = call_llm_and_get_text(llm, gen_prompt)
                        gen_text = extract_text_from_llm_output(raw)
                        preview_html = clean_preview_html(gen_text)
                        generated = True
                        _internal_logs.append("Generated app via GROQ")
                    except Exception as e:
                        _internal_logs.append("GROQ generation failed: " + str(e))

                # 2) If not generated yet, try agent if available
                if not generated and agent is not None:
                    try:
                        payload = {"user_prompt": user_text}
                        res = agent.invoke(payload, config={"recursion_limit": 200}) if hasattr(agent, "invoke") else agent(payload)
                        # agent may return built_files dict or a raw HTML string
                        if isinstance(res, dict) and res.get("built_files"):
                            raw_bf = res.get("built_files", {})
                            normalized = {}
                            for p, meta in (raw_bf.items() if isinstance(raw_bf, dict) else []):
                                if isinstance(meta, dict) and meta.get("content") is not None:
                                    normalized[p] = {"content": meta["content"]}
                            # pick index.html if present, else combine css/js/html into single doc
                            if normalized:
                                if any(k.lower().endswith("index.html") for k in normalized.keys()):
                                    for k, v in normalized.items():
                                        if k.lower().endswith("index.html"):
                                            preview_html = clean_preview_html(v["content"])
                                            break
                                else:
                                    css = "".join(v["content"] for p, v in normalized.items() if p.lower().endswith(".css"))
                                    js = "".join(v["content"] for p, v in normalized.items() if p.lower().endswith(".js"))
                                    body = next((v["content"] for p, v in normalized.items() if p.lower().endswith(".html")), "<div>Preview</div>")
                                    preview_html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}<script>{js}</script></body></html>"
                                generated = True
                                _internal_logs.append("Used agent-built files for preview")
                        elif isinstance(res, str):
                            preview_html = clean_preview_html(res)
                            generated = True
                            _internal_logs.append("Agent returned raw HTML string")
                        else:
                            _internal_logs.append("Agent returned no usable built_files")
                    except Exception as e:
                        _internal_logs.append("Agent generation failed: " + str(e))

                # 3) Local fallback (always reliable)
                if not generated:
                    preview_html = clean_preview_html(local_custom_generator(user_text))
                    generated = True
                    _internal_logs.append("Used local generator fallback")

        except Exception as e:
            _internal_logs.append("Unexpected error in run_btn handler: " + str(e))
            _internal_logs.append(traceback.format_exc())
            preview_html = clean_preview_html(f"<pre>{html.escape(traceback.format_exc())}</pre>")


# ---------- render results ----------
st.markdown("---")
if mode == "Ask (question)":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Answer")
    if answer_text:
        # render simple plain text or code nicely
        if "\n" in answer_text and len(answer_text) > 300:
            st.code(answer_text)
        else:
            # allow small HTML returns to be shown as text or rendered if HTML-like
            if answer_text.strip().startswith("<") and "<html" in answer_text.lower():
                st.info("HTML returned — rendering below.")
                # show inside white preview card
                st.markdown("<div class='preview-frame'>", unsafe_allow_html=True)
                components.html(clean_preview_html(answer_text), height=420, scrolling=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(answer_text)
    else:
        st.info("No answer produced yet. Try Generate mode or enable GROQ for live answers.")
    st.markdown("</div>", unsafe_allow_html=True)
else:
    # toolbar + preview area
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Live preview")
    toolbar_col1, toolbar_col2 = st.columns([3,1])
    with toolbar_col1:
        st.markdown('<div class="toolbar"><div class="toolbar-left">', unsafe_allow_html=True)
        st.markdown('<div class="small-muted">Preview</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with toolbar_col2:
        if preview_html:
            # Download button (keeps)
            b = preview_html.encode("utf-8")
            st.download_button("Download HTML", b, file_name="preview.html", mime="text/html")
            # NOTE: Open-in-new-tab removed intentionally (data URLs are unreliable / blocked)
    st.markdown('</div>', unsafe_allow_html=True)

    if preview_html:
        st.markdown("<div class='preview-frame'>", unsafe_allow_html=True)
        # fixed, readable height for preview
        components.html(preview_html, height=700, scrolling=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No preview yet. Run generation to see an interactive preview.")
    st.markdown("</div>", unsafe_allow_html=True)

# (no visible logs or quick checks shown — internal logs stored in _internal_logs variable)
