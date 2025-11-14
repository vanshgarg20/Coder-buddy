# main.py — Coder-buddy (modern UI, responsive, animated, gradient)
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

# ---------- Styles & Hero (enhanced modern design) ----------
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
    :root{
      --bg-grad-1: #081029;
      --bg-grad-2: #2b0442;
      --card-glass: rgba(255,255,255,0.04);
      --muted: #9aa8c3;
      --accent1: #6c5ce7;
      --accent2: #00b4ff;
      --white: #ffffff;
      --glass-border: rgba(255,255,255,0.06);
    }

    /* page background + animated gradient blob */
    html,body,section { height:100%; margin:0; padding:0; font-family: Inter, Arial, sans-serif; }
    body {
      background: radial-gradient(1000px 500px at 10% 20%, rgba(108,92,231,0.10), transparent 10%),
                  radial-gradient(800px 400px at 90% 80%, rgba(0,180,255,0.06), transparent 10%),
                  linear-gradient(180deg, var(--bg-grad-1), var(--bg-grad-2));
      color: #e6eef8;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      padding: 28px 18px;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
    }

    /* hero */
    .hero {
      display:flex; gap:20px; align-items:center; padding:22px; border-radius:14px;
      background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
      border: 1px solid rgba(255,255,255,0.03);
      box-shadow: 0 20px 60px rgba(2,6,23,0.45);
      backdrop-filter: blur(6px);
      transform: translateZ(0);
      overflow: hidden;
    }
    .logo {
      display:flex; align-items:center; gap:12px;
    }
    .logo-badge {
      width:56px; height:56px; border-radius:12px;
      background: linear-gradient(135deg, var(--accent1), var(--accent2));
      display:flex; align-items:center; justify-content:center; font-weight:800; font-size:20px;
      box-shadow: 0 8px 30px rgba(11,121,255,0.12), inset 0 -6px 18px rgba(0,0,0,0.12);
      animation: float 6s ease-in-out infinite;
    }
    @keyframes float {
      0% { transform: translateY(0px); }
      50% { transform: translateY(-6px); }
      100% { transform: translateY(0px); }
    }
    .brand-title { font-weight:800; font-size:20px; color:var(--white); }
    .brand-sub { color:var(--muted); margin-top:4px; font-size:13px; }

    .hero-right { margin-left:auto; text-align:right; }
    .chip { display:inline-block; padding:6px 10px; border-radius:999px; background: rgba(255,255,255,0.03); color:var(--muted); font-size:13px; border:1px solid rgba(255,255,255,0.02); }

    /* panels */
    .panel { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); padding:18px; border-radius:12px; border:1px solid var(--glass-border); }
    .form-title { font-size:18px; font-weight:700; color:var(--white); margin-bottom:6px; }
    .muted { color:var(--muted); }

    /* controls styling (improve appearance of streamlit inputs) */
    .stTextArea > label, .stSelectbox > label, .stCheckbox > label { color:var(--white) !important; }
    .primary-btn { background: linear-gradient(90deg,var(--accent2),var(--accent1)); color:white; border:none; padding:10px 16px; border-radius:10px; font-weight:700; cursor:pointer; box-shadow: 0 8px 30px rgba(108,92,231,0.14); }

    /* preview frame white */
    .preview-frame {
      width:100%;
      border-radius:12px;
      overflow:hidden;
      border:1px solid rgba(0,0,0,0.06);
      background:#ffffff; /* white preview area */
      padding:12px;
      box-shadow: 0 10px 40px rgba(2,6,23,0.08);
    }

    .toolbar { display:flex; gap:8px; align-items:center; justify-content:space-between; margin-bottom:10px; }
    .toolbar-left { display:flex; gap:8px; align-items:center; }
    .small-muted { color: #677487; font-size:13px }

    /* responsive grid layout */
    .grid {
      display:grid;
      grid-template-columns: 1fr 460px;
      gap:18px;
      align-items:start;
    }

    /* mobile responsiveness */
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      .hero { flex-direction: column; align-items:flex-start; gap:12px; }
      .hero-right { margin-left:0; text-align:left; }
    }

    /* subtle enter animations for cards */
    .panel { animation: cardIn 420ms cubic-bezier(.2,.9,.2,1); }
    @keyframes cardIn {
      from { transform: translateY(8px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    /* footer small */
    .credits { font-size:12px; color:var(--muted); margin-top:8px; }

    /* example chips */
    .example { background: rgba(255,255,255,0.02); padding:8px 10px; border-radius:8px; display:inline-block; margin:4px; color:var(--muted); font-size:13px; border:1px solid rgba(255,255,255,0.02); }
    </style>
    """,
    unsafe_allow_html=True,
)

# Hero markup
st.markdown(
    """
    <div class="container">
      <div class="hero">
        <div class="logo">
          <div class="logo-badge">CB</div>
          <div>
            <div class="brand-title">Coder-buddy <span style="font-weight:600;color: #bfe9ff; font-size:14px">💙</span></div>
            <div class="brand-sub">AI-powered app generator • Live preview • Auto-debug</div>
          </div>
        </div>
        <div class="hero-right">
          <div class="chip">Fast • Modern • Interactive</div>
          <div style="height:6px"></div>
          <div class="credits">Built with Streamlit • LangChain • GROQ (optional)</div>
        </div>
      </div>
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

# preview cleaning & CSS injection (keeps preview white)
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
        return calc_inline_html()
    if any(k in p for k in ["todo", "task", "todo list"]):
        return todo_inline_html()
    safe = html.escape(prompt or "Generated App")
    return f"<!doctype html><html><head><meta charset='utf-8'></head><body style='font-family:Inter,Arial,sans-serif;padding:24px'><h3>{safe}</h3><p>Light scaffold generated from your prompt.</p></body></html>"

# ---------- form UI (left column) ----------
st.markdown('<div class="container">', unsafe_allow_html=True)
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
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("<div style='font-weight:700;font-size:16px;margin-bottom:6px'>Examples</div>", unsafe_allow_html=True)
    st.markdown("<div class='muted'>Try prompts like:</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;flex-wrap:wrap;margin-top:8px">
      <div class="example">Create a stopwatch</div>
      <div class="example">Build a todo with search</div>
      <div class="example">Explain Python map()</div>
      <div class="example">Create a calculator</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='muted'>Preview appears on the right. Use Download to save the preview.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

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

if run_btn:
    user_text = (prompt or "").strip()
    if not user_text:
        st.warning("Please enter a prompt or question.")
    else:
        llm = None
        if use_groq:
            try:
                from langchain_groq import ChatGroq
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    raise RuntimeError("GROQ_API_KEY not set in env")
                llm = ChatGroq(model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), temperature=float(os.getenv("GROQ_TEMPERATURE", "0.2")), api_key=api_key)
                _internal_logs.append("GROQ initialized")
            except Exception as e:
                llm = None
                _internal_logs.append("GROQ init failed: " + str(e))
        else:
            _internal_logs.append("GROQ not selected; using local/agent fallback")

        try:
            if mode == "Ask (question)":
                if llm is not None:
                    final_prompt = f"You are a helpful assistant. Answer concisely.\nUser: {user_text}\n"
                    raw = call_llm_and_get_text(llm, final_prompt)
                    answer_text = extract_text_from_llm_output(raw)
                    _internal_logs.append("Answered with GROQ")
                else:
                    if agent is not None:
                        try:
                            payload = {"user_prompt": user_text}
                            res = agent.invoke(payload, config={"recursion_limit": 50}) if hasattr(agent, "invoke") else agent(payload)
                            answer_text = extract_text_from_llm_output(res)
                            _internal_logs.append("Answered with agent")
                        except Exception as e:
                            _internal_logs.append("Agent failed: " + str(e))
                            answer_text = "No GROQ available. Enable GROQ_API_KEY for live answers, or try Generate app mode."
                    else:
                        answer_text = "No GROQ available. Enable GROQ_API_KEY for live answers, or try Generate app mode."
            else:
                # generate app
                if llm is not None:
                    try:
                        gen_prompt = f"Produce a single self-contained HTML document implementing: {user_text}\nReturn only the HTML document."
                        raw = call_llm_and_get_text(llm, gen_prompt)
                        gen_text = extract_text_from_llm_output(raw)
                        preview_html = clean_preview_html(gen_text)
                        _internal_logs.append("Generated app via GROQ")
                    except Exception as e:
                        _internal_logs.append("GROQ generation failed: " + str(e))
                        # try agent or local
                        if agent is not None:
                            try:
                                payload = {"user_prompt": user_text}
                                res = agent.invoke(payload, config={"recursion_limit": 200}) if hasattr(agent, "invoke") else agent(payload)
                                if isinstance(res, dict) and res.get("built_files"):
                                    raw_bf = res.get("built_files", {})
                                    normalized = {}
                                    for p, meta in (raw_bf.items() if isinstance(raw_bf, dict) else []):
                                        if isinstance(meta, dict) and meta.get("content") is not None:
                                            normalized[p] = {"content": meta["content"]}
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
                                        _internal_logs.append("Used agent-built files for preview")
                                    else:
                                        preview_html = clean_preview_html(local_custom_generator(user_text))
                                        _internal_logs.append("Agent returned no in-memory files; used local generator")
                                else:
                                    preview_html = clean_preview_html(local_custom_generator(user_text))
                                    _internal_logs.append("Agent returned no usable output; used local generator")
                            except Exception as e2:
                                _internal_logs.append("Agent fallback error: " + str(e2))
                                preview_html = clean_preview_html(local_custom_generator(user_text))
                        else:
                            preview_html = clean_preview_html(local_custom_generator(user_text))
                            _internal_logs.append("No agent; used local generator")
                else:
                    if agent is not None:
                        try:
                            payload = {"user_prompt": user_text}
                            res = agent.invoke(payload, config={"recursion_limit": 200}) if hasattr(agent, "invoke") else agent(payload)
                            if isinstance(res, dict) and res.get("built_files"):
                                raw_bf = res.get("built_files", {})
                                normalized = {}
                                for p, meta in (raw_bf.items() if isinstance(raw_bf, dict) else []):
                                    if isinstance(meta, dict) and meta.get("content") is not None:
                                        normalized[p] = {"content": meta["content"]}
                                if normalized:
                                    if any(k.lower().endswith("index.html") for k in normalized.keys()):
                                        for k, v in normalized.items():
                                            if k.lower().endswith("index.html"):
                                                preview_html = clean_preview_html(v["content"]); break
                                    else:
                                        css = "".join(v["content"] for p, v in normalized.items() if p.lower().endswith(".css"))
                                        js = "".join(v["content"] for p, v in normalized.items() if p.lower().endswith(".js"))
                                        body = next((v["content"] for p, v in normalized.items() if p.lower().endswith(".html")), "<div>Preview</div>")
                                        preview_html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}<script>{js}</script></body></html>"
                                    _internal_logs.append("Used agent-built files for preview")
                                else:
                                    preview_html = clean_preview_html(local_custom_generator(user_text))
                                    _internal_logs.append("Agent returned no in-memory files; used local generator")
                            else:
                                preview_html = clean_preview_html(local_custom_generator(user_text))
                                _internal_logs.append("Agent returned no usable output; used local generator")
                        except Exception as e:
                            _internal_logs.append("Agent failed: " + str(e))
                            preview_html = clean_preview_html(local_custom_generator(user_text))
                    else:
                        preview_html = clean_preview_html(local_custom_generator(user_text))
                        _internal_logs.append("Generated from prompt locally (no LLM or agent)")
        except Exception as e:
            _internal_logs.append("Unexpected error: " + str(e))
            _internal_logs.append(traceback.format_exc())
            preview_html = clean_preview_html(f"<pre>{html.escape(traceback.format_exc())}</pre>")

# ---------- render results (right column) ----------
st.markdown("---")
st.markdown('<div class="container">', unsafe_allow_html=True)
if mode == "Ask (question)":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Answer")
    if answer_text:
        if "\n" in answer_text and len(answer_text) > 300:
            st.code(answer_text)
        else:
            if answer_text.strip().startswith("<") and "<html" in answer_text.lower():
                st.info("HTML returned — rendering below.")
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
            b = preview_html.encode("utf-8")
            st.download_button("Download HTML", b, file_name="preview.html", mime="text/html")
    st.markdown('</div>', unsafe_allow_html=True)

    if preview_html:
        st.markdown("<div class='preview-frame'>", unsafe_allow_html=True)
        components.html(preview_html, height=700, scrolling=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No preview yet. Run generation to see an interactive preview.")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# (internal logs kept but not shown)
