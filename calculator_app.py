#!/usr/bin/env python3
# app.py — write a small calculator web app to output/
from pathlib import Path

BASE = Path.cwd() / "output"
STATIC = BASE / "static"
BASE.mkdir(parents=True, exist_ok=True)
STATIC.mkdir(parents=True, exist_ok=True)

index_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Calculator</title>
  <link rel="stylesheet" href="static/style.css" />
</head>
<body>
  <main class="calc">
    <header class="top">
      <h1>Calculator</h1>
    </header>

    <section class="screen">
      <div id="history" class="history"></div>
      <input id="display" class="display" type="text" readonly aria-label="Calculator display" />
    </section>

    <section class="keys" role="group" aria-label="Calculator keys">
      <button data-action="clear" class="btn wide">C</button>
      <button data-action="del" class="btn">⌫</button>
      <button data-action="op" data-value="/" class="btn op">÷</button>

      <button data-value="7" class="btn">7</button>
      <button data-value="8" class="btn">8</button>
      <button data-value="9" class="btn">9</button>
      <button data-action="op" data-value="*" class="btn op">×</button>

      <button data-value="4" class="btn">4</button>
      <button data-value="5" class="btn">5</button>
      <button data-value="6" class="btn">6</button>
      <button data-action="op" data-value="-" class="btn op">−</button>

      <button data-value="1" class="btn">1</button>
      <button data-value="2" class="btn">2</button>
      <button data-value="3" class="btn">3</button>
      <button data-action="op" data-value="+" class="btn op">+</button>

      <button data-value="0" class="btn wide">0</button>
      <button data-value="." class="btn">.</button>
      <button data-action="equals" class="btn equals">=</button>
    </section>

    <footer class="foot">
      <small>Simple offline calculator • Works in your browser</small>
    </footer>
  </main>

  <script src="static/script.js" defer></script>
</body>
</html>
"""

# Larger, modern style (bigger width, larger buttons, nicer spacing)
style_css = """:root {
  --bg: #0f1724;
  --card: #0b1220;
  --accent: #7c5cff;
  --accent2: #00d4ff;
  --green: #22c55e;
  --muted: #9aa7b8;
  --text: #e6eef8;
  --btn: #121a2b;
  --btn-hover: #1b2437;
  --radius: 18px;
  --shadow: 0 20px 60px rgba(2, 6, 23, 0.8);
}

* {
  box-sizing: border-box;
}

html, body {
  height: 100%;
  margin: 0;
  background: radial-gradient(circle at top left, #071422 0%, #050c16 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Arial;
  color: var(--text);
}

.calc {
  width: 420px;
  max-width: 95vw;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
  border-radius: var(--radius);
  padding: 30px;
  box-shadow: var(--shadow);
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: transform 0.25s ease;
}

.calc:hover {
  transform: scale(1.02);
}

.top h1 {
  margin: 0 0 12px 0;
  text-align: center;
  font-size: 1.6rem;
  font-weight: 600;
  color: white;
}

.screen {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.history {
  color: var(--muted);
  font-size: 1rem;
  min-height: 22px;
  text-align: right;
  padding: 0 10px;
}

.display {
  width: 100%;
  padding: 18px;
  font-size: 2rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--text);
  text-align: right;
  outline: none;
}

.keys {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 10px;
}

.btn {
  background: var(--btn);
  border: 1px solid rgba(255, 255, 255, 0.05);
  color: var(--text);
  padding: 20px 0;
  font-size: 1.3rem;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: inset 0 -3px 0 rgba(0, 0, 0, 0.25);
}

.btn:hover {
  background: var(--btn-hover);
  transform: translateY(-2px);
}

.btn:active {
  transform: translateY(1px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.btn.wide {
  grid-column: span 2;
}

.btn.op {
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  color: white;
  font-weight: 600;
  border: none;
}

.btn.equals {
  background: linear-gradient(90deg, #16a34a, var(--green));
  color: white;
  font-weight: 600;
  border: none;
}

.foot {
  margin-top: 20px;
  text-align: center;
  color: var(--muted);
  font-size: 0.95rem;
}

/* Responsive */
@media (max-width: 500px) {
  .calc {
    width: 90vw;
    padding: 20px;
  }
  .display {
    font-size: 1.6rem;
  }
  .btn {
    padding: 16px 0;
    font-size: 1.1rem;
  }
}
"""

script_js = """(function(){
  const display = document.getElementById('display');
  const historyEl = document.getElementById('history');
  const keys = document.querySelectorAll('.btn');
  let expr = '';

  function update(){
    display.value = expr || '0';
  }

  function pushValue(v){
    // prevent multiple leading zeros or invalid sequences
    if (v === '.' && expr.slice(-1) === '.') return;
    expr += v;
    update();
  }

  function pushOp(op){
    if (!expr) {
      if (op === '-') { expr = '-'; update(); }
      return;
    }
    // replace trailing operator if last char is operator
    if (/[+\\-*/]$/.test(expr)) {
      expr = expr.slice(0,-1) + op;
    } else {
      expr += op;
    }
    update();
  }

  function clearAll(){ expr = ''; historyEl.textContent = ''; update(); }
  function del(){ expr = expr.slice(0,-1); update(); }

  function evaluateExpr(){
    if (!expr) return;
    // sanitize: only allow digits, operators, dot and parentheses
    const sanitized = expr.replace(/[^0-9.+\\-*/()%]/g, '');
    try {
      // Use Function to evaluate; wrap safely and force numeric result
      // (This is fine for a simple local app)
      // eslint-disable-next-line no-new-func
      const result = Function('"use strict"; return (' + sanitized + ')')();
      historyEl.textContent = sanitized + ' =';
      expr = (typeof result === 'number' && isFinite(result)) ? String(result) : '0';
    } catch (e) {
      expr = 'ERR';
      setTimeout(()=> { expr=''; update(); }, 900);
    }
    update();
  }

  keys.forEach(k => {
    const val = k.dataset.value;
    const action = k.dataset.action;
    if (val) {
      k.addEventListener('click', () => pushValue(val));
    } else if (action) {
      if (action === 'op') {
        k.addEventListener('click', ()=> pushOp(k.dataset.value));
      } else if (action === 'clear') {
        k.addEventListener('click', clearAll);
      } else if (action === 'del') {
        k.addEventListener('click', del);
      } else if (action === 'equals') {
        k.addEventListener('click', evaluateExpr);
      }
    }
  });

  // keyboard input support
  window.addEventListener('keydown', (e) => {
    if (e.key >= '0' && e.key <= '9') pushValue(e.key);
    else if (e.key === '.' ) pushValue('.');
    else if (['+','-','*','/','%','(',')'].includes(e.key)) pushOp(e.key);
    else if (e.key === 'Enter' || e.key === '=') { e.preventDefault(); evaluateExpr(); }
    else if (e.key === 'Backspace') del();
    else if (e.key === 'Escape') clearAll();
  });

  update();
})();"""

# write files
(BASE / "index.html").write_text(index_html, encoding="utf-8")
(STATIC / "style.css").write_text(style_css, encoding="utf-8")
(STATIC / "script.js").write_text(script_js, encoding="utf-8")

print("Calculator app written to:")
print(" -", (BASE / "index.html").resolve())
print(" -", (STATIC / "style.css").resolve())
print(" -", (STATIC / "script.js").resolve())
print()
print("Open file://"+str((BASE / "index.html").resolve()))
print("Or serve project root with: python3 -m http.server 5500")
print("Then open: http://localhost:5500/output/index.html")
