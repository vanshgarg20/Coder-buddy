# main.py - Custom generator improved (recognizes "snake", "tic tac toe", etc.)
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
st.title("Coder-buddy — Enter prompt and generate a working app")

# --- templates / app generators ---

def snake_game_html() -> str:
    style = """
:root{--bg:#f7fafc}
body{margin:0;font-family:Inter,Arial,sans-serif;background:var(--bg);display:flex;align-items:center;justify-content:center;height:100vh}
.card{background:#fff;padding:18px;border-radius:12px;box-shadow:0 10px 40px rgba(2,6,23,0.06)}
canvas{background:#0f172a;border-radius:8px;display:block}
.info{margin-top:10px;color:#475569;text-align:center}
.btn{margin-top:8px;padding:8px 12px;border-radius:8px;border:none;background:linear-gradient(90deg,#0b79ff,#6c5ce7);color:white;cursor:pointer}
"""
    script = r"""
const root = document.getElementById('app-root');
root.innerHTML = `<div class="card" style="text-align:center"><h3>Snake (Use arrow keys)</h3><canvas id="c" width="400" height="400"></canvas><div class="info">Score: <span id="score">0</span></div><button id="restart" class="btn">Restart</button></div>`;
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const cell = 20;
let w = canvas.width, h = canvas.height;
let cols = w / cell, rows = h / cell;

function rnd(min, max){ return Math.floor(Math.random()*(max-min))+min; }

let snake, dir, food, score, running;

function reset() {
  snake = [{x:Math.floor(cols/2), y:Math.floor(rows/2)}];
  dir = {x:1, y:0};
  placeFood();
  score = 0;
  running = true;
  document.getElementById('score').innerText = score;
}

function placeFood(){
  food = {x: rnd(1, cols-1), y: rnd(1, rows-1)};
}

function tick(){
  if(!running) return;
  const head = {x: snake[0].x + dir.x, y: snake[0].y + dir.y};
  // wrap
  if(head.x < 0) head.x = cols - 1;
  if(head.x >= cols) head.x = 0;
  if(head.y < 0) head.y = rows - 1;
  if(head.y >= rows) head.y = 0;
  // collision
  for(let i=0;i<snake.length;i++){
    if(snake[i].x === head.x && snake[i].y === head.y){
      running = false;
      return;
    }
  }
  snake.unshift(head);
  // eat
  if(head.x === food.x && head.y === food.y){
    score += 1;
    document.getElementById('score').innerText = score;
    placeFood();
  } else {
    snake.pop();
  }
}

function draw(){
  ctx.fillStyle = '#071024';
  ctx.fillRect(0,0,w,h);
  // food
  ctx.fillStyle = '#ff4d6d';
  ctx.fillRect(food.x*cell + 2, food.y*cell + 2, cell-4, cell-4);
  // snake
  for(let i=0;i<snake.length;i++){
    ctx.fillStyle = i===0 ? '#6c5ce7' : '#9aa7ff';
    ctx.fillRect(snake[i].x*cell + 1, snake[i].y*cell + 1, cell-2, cell-2);
  }
  if(!running){
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(0,0,w,h);
    ctx.fillStyle = '#fff';
    ctx.font = '20px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Game Over — press Restart', w/2, h/2);
  }
}

document.addEventListener('keydown', (e)=>{
  if(e.key.includes('Arrow')){
    if(e.key === 'ArrowUp' && dir.y === 0) dir = {x:0,y:-1};
    if(e.key === 'ArrowDown' && dir.y === 0) dir = {x:0,y:1};
    if(e.key === 'ArrowLeft' && dir.x === 0) dir = {x:-1,y:0};
    if(e.key === 'ArrowRight' && dir.x === 0) dir = {x:1,y:0};
  }
});

document.getElementById('restart').onclick = ()=>{ reset(); };

reset();
let last = 0;
function loop(ts){
  if(ts - last > 120){
    tick();
    last = ts;
  }
  draw();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
"""
    return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{style}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

def tic_tac_toe_html() -> str:
    style = """
body{font-family:Inter,Arial,sans-serif;background:#f6f9fc;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.card{background:#fff;padding:18px;border-radius:12px;box-shadow:0 10px 30px rgba(2,6,23,0.06)}
.board{display:grid;grid-template-columns:repeat(3,80px);gap:8px}
.cell{width:80px;height:80px;display:flex;align-items:center;justify-content:center;font-size:28px;border-radius:8px;background:#f8fafc;cursor:pointer}
.status{margin-top:12px;color:#475569}
.btn{margin-top:8px;padding:8px 12px;border-radius:8px;border:none;background:linear-gradient(90deg,#0b79ff,#6c5ce7);color:white;cursor:pointer}
"""
    script = r"""
const root = document.getElementById('app-root');
root.innerHTML = `<div class="card"><h3>Tic Tac Toe</h3><div id="board" class="board"></div><div id="status" class="status"></div><button id="restart" class="btn">Restart</button></div>`;
const board = document.getElementById('board');
const status = document.getElementById('status');
let cells = Array(9).fill(null);
let turn = 'X';
function checkWin() {
  const wins = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
  for(const w of wins){
    const [a,b,c]=w;
    if(cells[a] && cells[a]===cells[b] && cells[b]===cells[c]) return cells[a];
  }
  if(cells.every(Boolean)) return 'Draw';
  return null;
}
function render(){
  board.innerHTML='';
  cells.forEach((v,i)=>{
    const el = document.createElement('div');
    el.className='cell';
    el.textContent = v || '';
    el.onclick = ()=>{ if(cells[i] || checkWin()) return; cells[i]=turn; turn = turn==='X'?'O':'X'; render(); };
    board.appendChild(el);
  });
  const winner = checkWin();
  status.textContent = winner ? (winner==='Draw'?'Draw!': winner+' wins!') : 'Turn: '+turn;
}
document.getElementById('restart').onclick = ()=>{ cells = Array(9).fill(null); turn='X'; render(); };
render();
"""
    return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{style}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

def calc_inline_html() -> str:
    style = """
body{margin:0;font-family:Inter,Arial,sans-serif;background:#eef2f7;display:flex;align-items:center;justify-content:center;height:100vh}
.wrapper{width:320px}
.calc-card{background:#fff;padding:18px;border-radius:14px;box-shadow:0 12px 40px rgba(12,15,35,0.07)}
#display{width:100%;height:48px;border-radius:10px;border:1px solid #eef2ff;margin-bottom:12px;padding:10px;font-size:20px;text-align:right}
.keys{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.key{padding:14px;border-radius:10px;border:none;background:#f6f7fb;font-size:16px;cursor:pointer}
.key.op{background:linear-gradient(90deg,#6c5ce7,#0b79ff);color:white}
"""
    script = r"""
const root = document.getElementById('app-root');
root.innerHTML = `<div class="wrapper"><div class="calc-card"><input id="display" disabled /><div id="keys" class="keys"></div></div></div>`;
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
    return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{style}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

# combine agent-built files (same as before)
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

# improved local generator: detects games & other intents
def local_custom_generator(prompt: str) -> str:
    p = (prompt or "").strip().lower()
    # game detection
    if "snake" in p:
        return snake_game_html()
    if "tic" in p and "toe" in p:
        return tic_tac_toe_html()
    if "calculator" in p or "calc" in p:
        return calc_inline_html()
    if "todo" in p or "task" in p:
        return todo_inline_html()
    # more heuristics: if prompt mentions "game" try to pick a simple game
    if "game" in p:
        # prefer snake if user asked "create a game"
        return snake_game_html()
    # fallback: modern scaffold
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
  root.innerHTML=`<div class="wrapper"><div class="card"><header><h1>{html.escape(prompt or 'Generated App')}</h1></header><p class="desc">This scaffold was generated from your prompt: <strong>{html.escape(prompt or '')}</strong></p><div class="preview"><button class="btn" id="demo">Click me</button><div id="out" style="margin-top:12px"></div></div></div></div>`;
  document.getElementById('demo').onclick = ()=> document.getElementById('out').innerText = 'Hello — demo for: {html.escape(prompt or "")}';
}});
"""
    return f"<!doctype html><html><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width,initial-scale=1' /><style>{css}</style></head><body><div id='app-root'></div><script>{script}</script></body></html>"

# ---- UI ----
with st.form("gen", clear_on_submit=False):
    st.subheader("Enter your prompt")
    template = st.selectbox("Template", ["Todo app", "Calculator app", "Custom"])
    prompt = st.text_area("Prompt (leave empty to use template defaults)", value="", height=110, placeholder="e.g. create a snake game")
    use_agent_for_custom = st.checkbox("Use agent for Custom (if available)", value=False)
    submit = st.form_submit_button("Generate")

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

st.markdown("---")
st.subheader("Preview")
if preview_html:
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
