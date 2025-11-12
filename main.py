# main.py - Coder-buddy — improved preview cleaning + nicer UI
import os
import re
import html
import traceback
from typing import Any, Dict, Optional

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

st.set_page_config(page_title="Coder-buddy — Live Generator & Assistant", layout="wide")

# ---------------- UI header / styling ----------------
st.markdown(
    """
    <style>
    /* page header */
    .cb-header { display:flex; gap:16px; align-items:center; padding:20px; 
                background: linear-gradient(90deg, rgba(11,121,255,0.08), rgba(108,92,231,0.04));
                border-radius:14px; margin-bottom:18px; }
    .cb-brand { font-weight:800; font-size:20px; color:#58a6ff; }
    .cb-sub { color:#94a3b8; margin-top:4px; }
    /* nice card for form */
    .cb-card { padding:18px; background: linear-gradient(180deg,#0f172a00,#0000); border-radius:12px; box-shadow:0 8px 30px rgba(2,6,23,0.06); }
    /* preview container improvements - Streamlit page background is dark so force inner white card */
    .preview-frame { width:100%; border-radius:12px; overflow:hidden; border:1px solid rgba(15,23,42,0.08); box-shadow: 0 12px 40px rgba(2,6,23,0.08); background: #ffffff; }
    .muted { color:#94a3b8; font-size:13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="cb-header">
      <div>
        <div class="cb-brand">Coder-buddy 💙</div>
        <div class="cb-sub">Ask a question or generate a small web app — preview runs inline (no disk writes by default).</div>
      </div>
      <div style="margin-left:auto" class="muted">Use GROQ for live answers • Agent fallback available</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- helpers (LLM extraction left as before) ----------------
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
        if hasattr(out, "generations"):
            gens = getattr(out, "generations")
            if isinstance(gens, (list, tuple)) and len(gens) > 0:
                first_group = gens[0]
                if isinstance(first_group, (list, tuple)) and len(first_group) > 0:
                    first = first_group[0]
                    if hasattr(first, "text") and getattr(first, "text"):
                        return str(first.text)
                    return str(first)
            return str(out)
        if hasattr(out, "choices"):
            choices = getattr(out, "choices")
            if isinstance(choices, (list, tuple)) and len(choices) > 0:
                first = choices[0]
                if isinstance(first, dict):
                    for k in ("text", "message", "content"):
                        if k in first and first[k]:
                            return str(first[k])
                if hasattr(first, "text") and getattr(first, "text"):
                    return str(first.text)
                return str(first)
        s = str(out)
        m = re.search(r"content=(?:'|\")(.+?)(?:'|\")", s)
        if m:
            return m.group(1)
        return s
    except Exception:
        return str(out)


def call_llm_and_get_text(llm, prompt: str) -> str:
    if llm is None:
        raise RuntimeError("LLM is None")
    errors = []
    try:
        if hasattr(llm, "invoke"):
            out = llm.invoke(prompt)
            return extract_text_from_llm_output(out)
    except Exception as e:
        errors.append(f"invoke failed: {e}")
    try:
        out = llm(prompt)
        return extract_text_from_llm_output(out)
    except Exception as e:
        errors.append(f"call failed: {e}")
    try:
        if hasattr(llm, "generate"):
            gen = llm.generate([prompt])
            return extract_text_from_llm_output(gen)
    except Exception as e:
        errors.append(f"generate failed: {e}")
    raise RuntimeError("LLM invocation failed. Attempts:\n" + "\n".join(errors))


# ---------------- preview cleaning helpers (NEW) ----------------
def strip_triple_backticks_and_lang(s: str) -> str:
    """Remove leading/trailing triple backticks and optional language tag (```html)."""
    if not s:
        return s
    # remove leading/trailing whitespace
    s = s.strip()
    # if entire response wrapped in triple backticks, remove them
    m = re.match(r"^```(?:\w+)?\s*(.*)\s*```$", s, flags=re.S)
    if m:
        return m.group(1).strip()
    # remove any leading ```lang or ``` and trailing ``` that sometimes appear
    s = re.sub(r"^```[\w-]*\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s

def extract_inner_html_from_markdown(s: str) -> str:
    """
    If the generator returned a markdown block that contains an HTML code block,
    this will attempt to extract the raw HTML inside the fenced block.
    """
    if not s:
        return s
    # find first fenced block that looks like html (```html ... ``` or ``` ... ``` with html)
    m = re.search(r"```(?:html)?\s*(<[^`]+>)\s*```", s, flags=re.S | re.I)
    if m:
        return m.group(1).strip()
    # fallback: remove triple backticks only
    return strip_triple_backticks_and_lang(s)

def clean_preview_html(raw: str) -> str:
    """
    Make sure the string passed to components.html is a bare HTML document or
    at least a fragment. Strip markdown fences, remove stray leading ticks,
    and ensure there's a <html> wrapper if missing.
    """
    if raw is None:
        return ""
    s = raw.strip()
    # remove markdown fences and language tags
    s = extract_inner_html_from_markdown(s)
    # If result still starts with a ``` anywhere, remove them
    s = s.replace("```html", "").replace("```", "")
    s = s.strip()
    # If the string looks like partial HTML fragment (starts with '<'), keep it.
    if s.lower().startswith("<!doctype") or s.lower().startswith("<html") or s.startswith("<"):
        return s
    # If it's plain text or code (not html), render it inside a minimal safe HTML page
    safe = html.escape(s)
    return f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1' /><style>body{{font-family:Inter,Arial,sans-serif;background:#fff;color:#0f172a;padding:20px}}.card{{max-width:900px;margin:0 auto}}</style></head><body><div class='card'><pre style='white-space:pre-wrap;word-break:break-word'>{safe}</pre></div></body></html>"


# ---------------- inline simple templates ----------------
def todo_inline_html() -> str:
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>
body{font-family:Inter,Arial,sans-serif;background:#f6f8fb;padding:24px}
.card{max-width:720px;margin:18px auto;background:#fff;padding:16px;border-radius:12px;box-shadow:0 8px 30px rgba(2,6,23,0.06)}
.input{width:70%;padding:8px;border-radius:8px;border:1px solid #e6eef8}
.btn{padding:8px 12px;border-radius:8px;border:none;background:#0b79ff;color:#fff}
.list{margin-top:12px}
</style></head><body><div class='card'><h3>Todo</h3><div><input id='t' class='input' placeholder='Add task'><button id='a' class='btn'>Add</button></div><ul id='l' class='list'></ul></div><script>
const LKEY='cb_todos_v3';let l=JSON.parse(localStorage.getItem(LKEY)||'[]');function r(){const el=document.getElementById('l');el.innerHTML='';l.forEach((t,i)=>{const li=document.createElement('li');li.innerText=t;li.onclick=()=>{l.splice(i,1);localStorage.setItem(LKEY,JSON.stringify(l));r()};el.appendChild(li)})}document.getElementById('a').onclick=()=>{const v=document.getElementById('t').value.trim();if(!v) return; l.unshift(v); localStorage.setItem(LKEY,JSON.stringify(l)); document.getElementById('t').value=''; r()};r();
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

# ---------------- local fallback generator (same as before, simple) ----------------
def local_custom_generator(prompt: str) -> str:
    p = (prompt or "").strip().lower()
    if any(k in p for k in ["note", "notes", "note-taking", "notes app", "notes maker"]):
        return todo_inline_html()  # reuse todo UI as simple notes fallback
    if "snake" in p:
        return "<!doctype html><html><body><h3>Snake game placeholder</h3></body></html>"
    if "tic" in p and "toe" in p:
        return "<!doctype html><html><body><h3>Tic Tac Toe placeholder</h3></body></html>"
    if any(k in p for k in ["calc", "calculator"]):
        return calc_inline_html()
    if any(k in p for k in ["todo", "task", "todo list"]):
        return todo_inline_html()
    safe = html.escape(prompt or "Generated App")
    return f"<!doctype html><html><head><meta charset='utf-8'></head><body style='font-family:Inter,Arial,sans-serif;padding:24px'><h3>{safe}</h3><p>This is a lightweight scaffold generated from your prompt.</p></body></html>"

# ---------------- form UI ----------------
with st.form("gen", clear_on_submit=False):
    st.subheader("Enter your prompt or question")
    template = st.selectbox("Mode", ["Ask (question)", "Generate app (build)"])
    prompt = st.text_area("Prompt / Question", value="", height=120, placeholder="e.g. create a snake game OR how does map() work in Python?")
    use_groq = st.checkbox("Use GROQ LLM (requires GROQ_API_KEY env var)", value=bool(os.getenv("GROQ_API_KEY")))
    submit = st.form_submit_button("Run")

preview_html: Optional[str] = None
logs = []
answer_text: Optional[str] = None

# helper to detect questions (simple)
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

# ---------------- run logic ----------------
if submit:
    user_text = (prompt or "").strip()
    if not user_text:
        st.warning("Please enter a prompt or question.")
    else:
        # initialize LLM if requested
        llm = None
        if use_groq:
            try:
                # lazy import to avoid top-level heavy imports if not used
                from langchain_groq import ChatGroq
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    raise RuntimeError("GROQ_API_KEY not set in env")
                llm = ChatGroq(model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), temperature=float(os.getenv("GROQ_TEMPERATURE", "0.2")), api_key=api_key)
                logs.append("GROQ LLM initialized.")
            except Exception as e:
                llm = None
                logs.append("GROQ init failed: " + str(e))
        else:
            logs.append("GROQ not selected; using local generator/agent fallback.")

        try:
            if template == "Ask (question)":
                if llm is not None:
                    final_prompt = f"You are a helpful assistant. Answer concisely.\nUser: {user_text}\n"
                    raw = call_llm_and_get_text(llm, final_prompt)
                    answer_text = extract_text_from_llm_output(raw)
                    logs.append("Answered using GROQ LLM.")
                else:
                    # try agent fallback
                    if agent is not None:
                        try:
                            payload = {"user_prompt": user_text}
                            res = agent.invoke(payload, config={"recursion_limit": 50}) if hasattr(agent, "invoke") else agent(payload)
                            answer_text = extract_text_from_llm_output(res)
                            logs.append("Answered using local agent.")
                        except Exception as e:
                            logs.append("Agent failed: " + str(e))
                            if looks_like_question_text(user_text):
                                answer_text = "No GROQ available. Enable GROQ_API_KEY for live answers, or try Generate app mode."
                            else:
                                answer_text = "No LLM available. Enable GROQ_API_KEY for live answers."
                    else:
                        if looks_like_question_text(user_text):
                            answer_text = "No GROQ available. Enable GROQ_API_KEY for live answers, or try Generate app mode."
                        else:
                            answer_text = "No LLM available. Enable GROQ_API_KEY for live answers."
            else:
                # Generate app
                if llm is not None:
                    try:
                        gen_prompt = f"Produce a single self-contained HTML document implementing: {user_text}\nReturn only the HTML document."
                        raw = call_llm_and_get_text(llm, gen_prompt)
                        gen_text = extract_text_from_llm_output(raw)
                        preview_html = clean_preview_html(gen_text)
                        logs.append("Generated app via GROQ LLM.")
                    except Exception as e:
                        logs.append("GROQ generation failed: " + str(e))
                        logs.append("Falling back to agent/local generator.")
                        # agent fallback or local
                        if agent is not None:
                            try:
                                payload = {"user_prompt": user_text}
                                res = agent.invoke(payload, config={"recursion_limit": 200}) if hasattr(agent, "invoke") else agent(payload)
                                if isinstance(res, dict) and res.get("built_files"):
                                    raw_bf = res.get("built_files", {})
                                    # normalize to content mapping if available
                                    normalized = {}
                                    for p, meta in (raw_bf.items() if isinstance(raw_bf, dict) else []):
                                        if isinstance(meta, dict) and meta.get("content") is not None:
                                            normalized[p] = {"content": meta["content"]}
                                    # prefer an index.html
                                    if normalized:
                                        # combine into HTML
                                        # simple: if index.html present, use it, else try to merge css/js
                                        if any(k.lower().endswith("index.html") for k in normalized.keys()):
                                            for k, v in normalized.items():
                                                if k.lower().endswith("index.html"):
                                                    preview_html = clean_preview_html(v["content"])
                                                    break
                                        else:
                                            # basic combine: put CSS/JS in a wrapper
                                            css = "".join(v["content"] for p,v in normalized.items() if p.lower().endswith(".css"))
                                            js = "".join(v["content"] for p,v in normalized.items() if p.lower().endswith(".js"))
                                            body = next((v["content"] for p,v in normalized.items() if p.lower().endswith(".html")), "<div>Preview</div>")
                                            preview_html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}<script>{js}</script></body></html>"
                                        logs.append("Used agent-built files for preview.")
                                    else:
                                        preview_html = clean_preview_html(local_custom_generator(user_text))
                                        logs.append("Agent returned no in-memory files; used local generator.")
                                else:
                                    preview_html = clean_preview_html(local_custom_generator(user_text))
                                    logs.append("Agent returned no usable output; used local generator.")
                            except Exception as e2:
                                logs.append("Agent fallback error: " + str(e2))
                                preview_html = clean_preview_html(local_custom_generator(user_text))
                        else:
                            preview_html = clean_preview_html(local_custom_generator(user_text))
                            logs.append("No agent; used local generator.")
                else:
                    # no LLM, try agent or local
                    if agent is not None:
                        try:
                            payload = {"user_prompt": user_text}
                            res = agent.invoke(payload, config={"recursion_limit": 200}) if hasattr(agent, "invoke") else agent(payload)
                            # handle agent output similar to above
                            if isinstance(res, dict) and res.get("built_files"):
                                raw_bf = res.get("built_files", {})
                                normalized = {}
                                for p, meta in (raw_bf.items() if isinstance(raw_bf, dict) else []):
                                    if isinstance(meta, dict) and meta.get("content") is not None:
                                        normalized[p] = {"content": meta["content"]}
                                if normalized:
                                    if any(k.lower().endswith("index.html") for k in normalized.keys()):
                                        for k,v in normalized.items():
                                            if k.lower().endswith("index.html"):
                                                preview_html = clean_preview_html(v["content"]); break
                                    else:
                                        css = "".join(v["content"] for p,v in normalized.items() if p.lower().endswith(".css"))
                                        js = "".join(v["content"] for p,v in normalized.items() if p.lower().endswith(".js"))
                                        body = next((v["content"] for p,v in normalized.items() if p.lower().endswith(".html")), "<div>Preview</div>")
                                        preview_html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}<script>{js}</script></body></html>"
                                    logs.append("Used agent-built files for preview.")
                                else:
                                    preview_html = clean_preview_html(local_custom_generator(user_text))
                                    logs.append("Agent returned no in-memory files; used local generator.")
                            else:
                                preview_html = clean_preview_html(local_custom_generator(user_text))
                                logs.append("Agent returned no usable output; used local generator.")
                        except Exception as e:
                            logs.append("Agent failed: " + str(e))
                            preview_html = clean_preview_html(local_custom_generator(user_text))
                    else:
                        preview_html = clean_preview_html(local_custom_generator(user_text))
                        logs.append("Generated from prompt locally (no LLM or agent).")
        except Exception as e:
            logs.append("Unexpected error: " + str(e))
            logs.append(traceback.format_exc())
            preview_html = clean_preview_html(f"Error: {str(e)}\n\n{traceback.format_exc()}")

# ---------------- render output ----------------
st.markdown("---")
if template == "Ask (question)":
    st.subheader("Answer")
    if answer_text:
        # prefer markdown for readable answers, code block for long text or code
        if answer_text.strip().startswith("<") and "<html" in answer_text.lower():
            # if LLM returned an HTML snippet by mistake, show an explained notice + preview
            st.info("LLM returned an HTML snippet — rendering below.")
            components.html(clean_preview_html(answer_text), height=480, scrolling=True)
        elif "\n" in answer_text and len(answer_text) > 240:
            st.code(answer_text)
        else:
            st.markdown(answer_text)
    else:
        st.info("No answer produced yet. Try enabling GROQ or check logs below.")
else:
    st.subheader("Live preview")
    if preview_html:
        # wrap preview in a white card so dark-mode Streamlit doesn't hide content
        st.markdown("<div class='preview-frame'>", unsafe_allow_html=True)
        components.html(preview_html, height=680, scrolling=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No preview yet. Run generation.")

st.markdown("----")
st.subheader("Logs")
if logs:
    for l in logs:
        st.write("-", l)
else:
    st.write("No logs yet.")

st.markdown("---")
st.markdown("**Quick checks:**")
if os.getenv("GROQ_API_KEY"):
    st.success("GROQ_API_KEY detected in environment.")
else:
    st.warning("GROQ_API_KEY not found. To get live LLM answers set GROQ_API_KEY in your environment or Streamlit secrets.")

if agent is None:
    st.info("Local `agent` not found — local generators will be used as fallback.")
else:
    st.info("Local `agent` detected — it will be used as fallback for generation.")
