# main.py - Coder-buddy: GROQ-enabled Q&A + app generator (single-file)
import os
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

# ------------------ UI header ------------------
st.markdown(
    """
    <style>
    .header { display:flex; gap:16px; align-items:center; padding:18px;
      background: linear-gradient(90deg, rgba(11,121,255,0.10), rgba(108,92,231,0.06));
      border-radius:12px; box-shadow: 0 6px 24px rgba(2,6,23,0.04); }
    .brand { font-weight:700; font-size:20px; color:#0b79ff; }
    .sub { color:#475569; margin-top:4px; }
    .muted { color:#64748b; font-size:13px; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="header">
      <div>
        <div class="brand">Coder-buddy 💙</div>
        <div class="sub">Ask a question or generate a small web app — preview runs inline.</div>
      </div>
      <div style="margin-left:auto" class="muted">No disk writes by default • Use GROQ for live answers</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------ helper: LLM factory + caller ------------------
def get_groq_llm():
    """Lazily create a ChatGroq instance using GROQ_API_KEY env var."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    try:
        # lazy import to avoid import errors when package missing
        from langchain_groq import ChatGroq
    except Exception as e:
        raise RuntimeError(f"langchain_groq not available: {e}")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    temperature = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
    # try to construct; some client versions will pick key from env, some accept api_key param
    try:
        return ChatGroq(model=model, temperature=temperature, api_key=api_key)
    except TypeError:
        # older/newer API might ignore api_key param; rely on env var and construct without param
        return ChatGroq(model=model, temperature=temperature)

def call_llm_and_get_text(llm, prompt: str) -> str:
    """Try several common invocation styles and return a text answer (best-effort)."""
    if llm is None:
        raise RuntimeError("LLM is None")
    errors = []
    # 1) .invoke(prompt)
    try:
        if hasattr(llm, "invoke"):
            out = llm.invoke(prompt)
            # if returns dict-like or object, try to extract
            if isinstance(out, str):
                return out
            if isinstance(out, dict):
                # common field names
                for k in ("text", "output", "answer"):
                    if k in out:
                        return str(out[k])
                return str(out)
            return str(out)
    except Exception as e:
        errors.append(f"invoke failed: {e}")
    # 2) direct call llm(prompt)
    try:
        out = llm(prompt)
        if isinstance(out, str):
            return out
        if isinstance(out, dict):
            for k in ("text", "output", "answer"):
                if k in out:
                    return str(out[k])
            return str(out)
        return str(out)
    except Exception as e:
        errors.append(f"call failed: {e}")
    # 3) .generate([prompt]) -> check .generations structure
    try:
        if hasattr(llm, "generate"):
            gen = llm.generate([prompt])
            # Attempt to extract textual generation (depends on library)
            if hasattr(gen, "generations"):
                gens = getattr(gen, "generations")
                if gens and len(gens[0]) > 0:
                    first = gens[0][0]
                    if hasattr(first, "text"):
                        return first.text
                    return str(first)
            # fallback convert to string
            return str(gen)
    except Exception as e:
        errors.append(f"generate failed: {e}")
    # nothing worked — return combined errors
    raise RuntimeError("LLM invocation failed. Attempts:\n" + "\n".join(errors))

# ------------------ inline app templates ------------------
# (todo, calc, snake, tic-tac-toe, notes) - inline HTML strings
def todo_inline_html():
    # same as before - minimal fresh inline todo
    return """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{font-family:Arial;background:#f6f8fb;padding:24px} .card{max-width:720px;margin:18px auto;background:#fff;padding:16px;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.05)} .input{width:70%;padding:8px;border-radius:8px;border:1px solid #e6eef8} .btn{padding:8px 12px;border-radius:8px;border:none;background:#0b79ff;color:#fff} .list{margin-top:12px}
</style></head><body><div class="card"><h3>Todo</h3><div><input id="t" class="input" placeholder="Add task"><button id="a" class="btn">Add</button></div><ul id="l" class="list"></ul></div><script>
const l=localStorage.getItem('cb_todos')?JSON.parse(localStorage.getItem('cb_todos')):[];function r(){const el=document.getElementById('l');el.innerHTML='';l.forEach((t,i)=>{const li=document.createElement('li');li.innerText=t;li.onclick=()=>{l.splice(i,1);localStorage.setItem('cb_todos',JSON.stringify(l));r()};el.appendChild(li)})}document.getElementById('a').onclick=()=>{const v=document.getElementById('t').value.trim();if(!v) return; l.unshift(v); localStorage.setItem('cb_todos',JSON.stringify(l)); document.getElementById('t').value=''; r()};r();
</script></body></html>"""

def calc_inline_html():
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{font-family:Arial;display:flex;height:100vh;align-items:center;justify-content:center;background:#eef2f7}.card{background:#fff;padding:16px;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.05)} #d{width:220px;height:44px;font-size:20px;text-align:right;padding:6px;margin-bottom:8px}</style></head><body><div class='card'><input id='d' disabled /><div id='k'></div></div><script>const keys=['7','8','9','/','4','5','6','*','1','2','3','-','0','.','=','+'];const k=document.getElementById('k'),d=document.getElementById('d');keys.forEach(t=>{const b=document.createElement('button');b.innerText=t;b.style.margin='4px';b.onclick=()=>{if(t==='='){try{d.value=eval(d.value)}catch(e){d.value='Error'}}else d.value+=t};k.appendChild(b)});</script></body></html>"""

def snake_game_html():
    # a playable snake game (kept concise)
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{margin:0;display:flex;align-items:center;justify-content:center;height:100vh;background:#f7fafc}.card{padding:12px;background:#fff;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.05)}canvas{background:#071024;border-radius:8px}</style></head><body><div class='card'><h4>Snake (arrows)</h4><canvas id='c' width='360' height='360'></canvas><div>Score: <span id='s'>0</span></div><button id='r'>Restart</button></div><script>
const c=document.getElementById('c'),ctx=c.getContext('2d');const cell=18;const cols=c.width/cell,rows=c.height/cell;let snake=[],dir={x:1,y:0},food,score=0,alive=true;function rnd(a,b){return Math.floor(Math.random()*(b-a))+a}function place(){food={x:rnd(0,cols),y:rnd(0,rows)}}function reset(){snake=[{x:Math.floor(cols/2),y:Math.floor(rows/2)}];dir={x:1,y:0};place();score=0;alive=true;document.getElementById('s').innerText=score}document.addEventListener('keydown',e=>{if(e.key.includes('Arrow')){if(e.key==='ArrowUp'&&dir.y==0)dir={x:0,y:-1};if(e.key==='ArrowDown'&&dir.y==0)dir={x:0,y:1};if(e.key==='ArrowLeft'&&dir.x==0)dir={x:-1,y:0};if(e.key==='ArrowRight'&&dir.x==0)dir={x:1,y:0}}});document.getElementById('r').onclick=reset;function tick(){if(!alive)return;const head={x:snake[0].x+dir.x,y:snake[0].y+dir.y};if(head.x<0)head.x=cols-1;if(head.y<0)head.y=rows-1;if(head.x>=cols)head.x=0;if(head.y>=rows)head.y=0;for(let s of snake)if(s.x===head.x&&s.y===head.y){alive=false;return}snake.unshift(head);if(head.x===food.x&&head.y===food.y){score++;document.getElementById('s').innerText=score;place()}else snake.pop()}function draw(){ctx.fillStyle='#071024';ctx.fillRect(0,0,c.width,c.height);ctx.fillStyle='#ff6b6b';ctx.fillRect(food.x*cell+2,food.y*cell+2,cell-4,cell-4);for(let i=0;i<snake.length;i++){ctx.fillStyle=i==0? '#6c5ce7':'#9aa7ff';ctx.fillRect(snake[i].x*cell+1,snake[i].y*cell+1,cell-2,cell-2)}if(!alive){ctx.fillStyle='rgba(0,0,0,0.5)';ctx.fillRect(0,0,c.width,c.height);ctx.fillStyle='#fff';ctx.font='18px Arial';ctx.textAlign='center';ctx.fillText('Game Over — Restart',c.width/2,c.height/2)}}reset();let last=0;function loop(t){if(t-last>120){tick();last=t}draw();requestAnimationFrame(loop)}requestAnimationFrame(loop);
</script></body></html>"""

def tic_tac_toe_html():
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{font-family:Arial;display:flex;height:100vh;align-items:center;justify-content:center;background:#f6f9fc}.card{padding:12px;background:#fff;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.05)} .b{display:grid;grid-template-columns:repeat(3,80px);gap:6px}.c{width:80px;height:80px;background:#f8fafc;display:flex;align-items:center;justify-content:center;font-size:28px;cursor:pointer;border-radius:8px}</style></head><body><div class='card'><h4>Tic Tac Toe</h4><div id='b' class='b'></div><div id='s'></div><button id='r'>Restart</button></div><script>
const b=document.getElementById('b'),s=document.getElementById('s');let cells=Array(9).fill(null),turn='X';function check(){const wins=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];for(const w of wins){const[a,b,c]=w; if(cells[a]&&cells[a]===cells[b]&&cells[b]===cells[c]) return cells[a]} if(cells.every(Boolean)) return 'Draw'; return null}function render(){b.innerHTML='';cells.forEach((v,i)=>{const el=document.createElement('div');el.className='c';el.textContent=v||'';el.onclick=()=>{ if(cells[i]||check()) return; cells[i]=turn; turn=turn==='X'?'O':'X'; render() }; b.appendChild(el)}); const w=check(); s.innerText=w? (w==='Draw'?'Draw!':w+' wins!') : 'Turn: '+turn }document.getElementById('r').onclick=()=>{cells=Array(9).fill(null);turn='X';render()};render();
</script></body></html>"""

# Notes generator (local) used by fallback
def notes_inline_html():
    # kept concise; local_custom_generator uses more featureful version
    return local_notes_html_small()

def local_notes_html_small():
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{font-family:Arial;background:#f6f8fb;padding:24px}.card{max-width:900px;margin:0 auto;background:#fff;padding:12px;border-radius:12px}.note{padding:8px;border-bottom:1px solid #eee}</style></head><body><div class='card'><h3>Notes</h3><input id='t' placeholder='title'><br><textarea id='b' placeholder='body'></textarea><br><button id='s'>Save</button><div id='list'></div></div><script>const key='cb_notes_sm';let arr=JSON.parse(localStorage.getItem(key)||'[]');function r(){const el=document.getElementById('list');el.innerHTML='';arr.forEach(a=>{const d=document.createElement('div');d.className='note';d.innerHTML='<b>'+a.t+'</b><div>'+a.b+'</div>';el.appendChild(d)})}document.getElementById('s').onclick=()=>{arr.unshift({t:document.getElementById('t').value,b:document.getElementById('b').value});localStorage.setItem(key,JSON.stringify(arr));document.getElementById('t').value='';document.getElementById('b').value='';r()};r();</script></body></html>"""

# combine files helper (used when agent returns in-memory files)
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

# ------------------ smart local generator ------------------
def local_custom_generator(prompt: str) -> str:
    p = (prompt or "").strip().lower()
    if any(k in p for k in ["note", "notes", "note-taking", "notes app", "notes maker"]):
        # better notes UI (from earlier helper)
        return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{font-family:Inter,Arial,sans-serif;background:#f6f8fb;padding:28px}.card{max-width:960px;margin:0 auto;background:#fff;padding:16px;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.04)} .input{width:100%;padding:8px;border-radius:8px;border:1px solid #eef2ff} .note{padding:8px;border-bottom:1px solid #f1f5f9}</style></head><body><div class='card'><h3>Notes</h3><input id='t' class='input' placeholder='Title'><br><textarea id='b' class='input' style='height:120px;margin-top:8px' placeholder='Write your note...'></textarea><br><button id='s' style='margin-top:8px;padding:8px 10px;border-radius:8px;background:linear-gradient(90deg,#0b79ff,#6c5ce7);color:#fff;border:none'>Save</button><div id='list' style='margin-top:12px'></div></div><script>const K='cb_notes_v2';let arr=JSON.parse(localStorage.getItem(K)||'[]');function r(){const L=document.getElementById('list');L.innerHTML='';arr.forEach(a=>{const d=document.createElement('div');d.className='note';d.innerHTML='<b>'+a.t+'</b><div>'+a.b+'</div>';L.appendChild(d)})}document.getElementById('s').onclick=()=>{arr.unshift({t:document.getElementById('t').value,b:document.getElementById('b').value});localStorage.setItem(K,JSON.stringify(arr));document.getElementById('t').value='';document.getElementById('b').value='';r()};r();</script></body></html>"""
    if "snake" in p:
        return snake_game_html()
    if "tic" in p and "toe" in p:
        return tic_tac_toe_html()
    if any(k in p for k in ["calc", "calculator", "+", "-", "*", "/"]):
        return calc_inline_html()
    if any(k in p for k in ["todo", "task", "todo list"]):
        return todo_inline_html()
    # default scaffold
    safe = html.escape(prompt or "Generated App")
    return f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{{font-family:Inter,Arial,sans-serif;background:#fff;padding:28px}}.card{{max-width:900px;margin:0 auto;padding:18px;border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,0.04)}}.btn{{padding:8px 12px;border-radius:8px;border:none;background:linear-gradient(90deg,#0b79ff,#6c5ce7);color:#fff}}</style></head><body><div class='card'><h2>{safe}</h2><p>This is a lightweight scaffold generated from your prompt.</p><button class='btn' id='d'>Run demo</button><div id='out' style='margin-top:12px'></div></div><script>document.getElementById('d').onclick=()=>document.getElementById('out').innerText='Demo for: {html.escape(prompt or "")}';</script></body></html>"

# ------------------ UI form ------------------
with st.form("gen", clear_on_submit=False):
    st.subheader("Enter your prompt or question")
    template = st.selectbox("Mode", ["Ask (question)", "Generate app (build)"])
    prompt = st.text_area("Prompt / Question", value="", height=120, placeholder="e.g. create a snake game OR how does map() work in Python?")
    use_groq = st.checkbox("Use GROQ LLM (requires GROQ_API_KEY env var)", value=bool(os.getenv("GROQ_API_KEY")))
    submit = st.form_submit_button("Run")

preview_html: Optional[str] = None
logs = []
answer_text: Optional[str] = None

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

# ------------------ run logic ------------------
if submit:
    user_text = (prompt or "").strip()
    if not user_text:
        st.warning("Please enter a prompt or question.")
    else:
        if use_groq:
            # initialize LLM
            try:
                llm = get_groq_llm()
                logs.append("GROQ LLM initialized.")
            except Exception as e:
                llm = None
                logs.append("GROQ init failed: " + str(e))
        else:
            llm = None
            logs.append("GROQ not selected; using local generator/agent fallback.")

        # Decide action:
        # If Mode == Ask (question) -> prefer LLM answer; else if Generate -> produce HTML
        if template == "Ask (question)":
            # try to answer using LLM if available
            if llm is not None:
                try:
                    final_prompt = f"You are a helpful assistant. Answer concisely.\nUser: {user_text}\n"
                    raw = call_llm_and_get_text(llm, final_prompt)
                    answer_text = str(raw).strip()
                    logs.append("Answered using GROQ LLM.")
                except Exception as e:
                    logs.append("LLM answer failed: " + str(e))
                    logs.append("Falling back to agent/local.")
                    # fallback: try agent if available (agent may not answer text, but try)
                    if agent is not None:
                        try:
                            payload = {"user_prompt": user_text}
                            res = agent.invoke(payload, config={"recursion_limit": 50}) if hasattr(agent, "invoke") else agent(payload)
                            answer_text = str(res)
                            logs.append("Agent provided fallback response.")
                        except Exception as e2:
                            logs.append("Agent fallback failed: " + str(e2))
                            answer_text = "Sorry — I couldn't fetch a live answer. Try enabling GROQ or check logs."
                    else:
                        answer_text = "GROQ not available and no agent fallback. Enable GROQ_API_KEY or check agent."
            else:
                # no GROQ -> try agent -> else show local helper
                if agent is not None:
                    try:
                        payload = {"user_prompt": user_text}
                        res = agent.invoke(payload, config={"recursion_limit": 50}) if hasattr(agent, "invoke") else agent(payload)
                        answer_text = str(res)
                        logs.append("Answer from local agent.")
                    except Exception as e:
                        logs.append("Agent failed: " + str(e))
                        answer_text = "No GROQ and agent failed. Try enabling GROQ_API_KEY."
                else:
                    # local quick heuristic: if question about templates / code, give simple canned help
                    if "how" in user_text.lower() or "what" in user_text.lower() or "explain" in user_text.lower():
                        answer_text = "I don't have GROQ enabled. Enable GROQ_API_KEY to get live LLM answers. Meanwhile, ask about generating apps (choose 'Generate app') or use local templates."
                    else:
                        answer_text = "No LLM available. Enable GROQ_API_KEY for live answers."

        else:  # Generate app (build)
            # If GROQ available, ask it to produce a single HTML doc (preferred)
            if llm is not None:
                try:
                    gen_prompt = f"Produce a single self-contained HTML document implementing: {user_text}\nReturn only the HTML document."
                    raw = call_llm_and_get_text(llm, gen_prompt)
                    raw = str(raw).strip()
                    # If model returned non-HTML, we will try to wrap it, else show as HTML
                    if ("<html" in raw.lower()) or raw.lower().startswith("<!doctype"):
                        preview_html = raw
                    else:
                        # wrap plain output into a pre block so user sees it
                        preview_html = "<!doctype html><html><body style='font-family:Inter,Arial,sans-serif;padding:20px'><pre>" + html.escape(raw) + "</pre></body></html>"
                    logs.append("Generated app via GROQ LLM.")
                except Exception as e:
                    logs.append("GROQ generation failed: " + str(e))
                    logs.append("Falling back to agent/local generator.")
                    # fallback chain: agent -> local generator
                    try:
                        if agent is not None:
                            payload = {"user_prompt": user_text}
                            res = agent.invoke(payload, config={"recursion_limit": 200}) if hasattr(agent, "invoke") else agent(payload)
                            if isinstance(res, dict) and res.get("built_files"):
                                raw_bf = res.get("built_files", {})
                                normalized = {}
                                for p, meta in (raw_bf.items() if isinstance(raw_bf, dict) else []):
                                    if isinstance(meta, dict) and meta.get("content") is not None:
                                        normalized[p] = {"written": False, "content": meta["content"]}
                                if normalized:
                                    preview_html = combine_files_to_html(normalized)
                                    logs.append("Used agent-built files for preview.")
                                else:
                                    preview_html = local_custom_generator(user_text)
                                    logs.append("Agent returned no in-memory files; used local generator.")
                            else:
                                preview_html = local_custom_generator(user_text)
                                logs.append("Agent returned no usable output; used local generator.")
                        else:
                            preview_html = local_custom_generator(user_text)
                            logs.append("No agent; used local generator.")
                    except Exception as e2:
                        logs.append("Agent fallback error: " + str(e2))
                        preview_html = local_custom_generator(user_text)
            else:
                # no LLM -> try agent -> else local generator
                if agent is not None:
                    try:
                        payload = {"user_prompt": user_text}
                        res = agent.invoke(payload, config={"recursion_limit": 200}) if hasattr(agent, "invoke") else agent(payload)
                        if isinstance(res, dict) and res.get("built_files"):
                            raw_bf = res.get("built_files", {})
                            normalized = {}
                            for p, meta in (raw_bf.items() if isinstance(raw_bf, dict) else []):
                                if isinstance(meta, dict) and meta.get("content") is not None:
                                    normalized[p] = {"written": False, "content": meta["content"]}
                            if normalized:
                                preview_html = combine_files_to_html(normalized)
                                logs.append("Used agent-built files for preview.")
                            else:
                                preview_html = local_custom_generator(user_text)
                                logs.append("Agent returned no in-memory files; used local generator.")
                        else:
                            preview_html = local_custom_generator(user_text)
                            logs.append("Agent returned no usable output; used local generator.")
                    except Exception as e:
                        logs.append("Agent failed: " + str(e))
                        preview_html = local_custom_generator(user_text)
                else:
                    preview_html = local_custom_generator(user_text)
                    logs.append("Generated from prompt locally (no LLM or agent).")

# ------------------ render output ------------------
st.markdown("---")
if template == "Ask (question)":
    st.subheader("Answer")
    if answer_text:
        # render as markdown when possible
        try:
            st.markdown(answer_text)
        except Exception:
            st.text(answer_text)
    else:
        st.info("No answer produced yet. Try enabling GROQ or check logs below.")
else:
    st.subheader("Live preview")
    if preview_html:
        components.html(preview_html, height=720, scrolling=True)
    else:
        st.info("No preview yet. Run generation.")

st.markdown("----")
st.subheader("Logs")
if logs:
    for l in logs:
        st.write("-", l)
else:
    st.write("No logs yet.")

# developer note / quick checks
st.markdown("---")
st.markdown("**Quick checks:**")
if os.getenv("GROQ_API_KEY"):
    st.success("GROQ_API_KEY detected in environment.")
else:
    st.warning("GROQ_API_KEY not found. If you want live LLM answers, set GROQ_API_KEY in your environment or Streamlit secrets.")

if agent is None:
    st.info("Local `agent` not found — that's fine; local generators will be used as fallback.")
else:
    st.info("Local `agent` detected — will be used as fallback for generation when selected.")
