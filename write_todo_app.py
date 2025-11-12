#!/usr/bin/env python3
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
  <title>Colourful Todo App</title>
  <link rel="stylesheet" href="static/style.css" />
</head>
<body>
  <main class="app">
    <header class="app-header">
      <h1>My Todos</h1>
      <p class="subtitle">A colourful, modern todo — built with HTML/CSS/JS</p>
    </header>

    <section class="composer">
      <input id="new-todo" type="text" placeholder="Add a new task and press Enter" aria-label="New todo" />
      <button id="add-btn" aria-label="Add todo">Add</button>
    </section>

    <section class="controls">
      <div class="stats">
        <span id="total-count">0</span> tasks • <span id="done-count">0</span> done
      </div>
      <div class="filters">
        <button data-filter="all" class="active">All</button>
        <button data-filter="active">Active</button>
        <button data-filter="done">Done</button>
      </div>
    </section>

    <ul id="todo-list" class="todo-list" aria-live="polite"></ul>

    <footer class="app-footer">
      <small>Saved locally in your browser • Try it on mobile</small>
    </footer>
  </main>

  <script src="static/script.js" defer></script>
</body>
</html>
"""

style_css = """:root{
  --bg: #0f1724;
  --card: #0b1220;
  --muted: #94a3b8;
  --accent1: #ff6b6b;
  --accent2: #7c5cff;
  --accent3: #00d4ff;
  --glass: rgba(255,255,255,0.04);
  --radius: 14px;
  --gap: 12px;
  --maxw: 820px;
  --text: #e6eef8;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;
  font-family:Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
  background: linear-gradient(180deg, #071024 0%, #071422 60%);
  color:var(--text);
  display:flex;
  align-items:center;
  justify-content:center;
  padding:40px 20px;
}
.app{
  width:100%;
  max-width:var(--maxw);
  background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  border-radius:var(--radius);
  padding:28px;
  box-shadow: 0 10px 30px rgba(2,6,23,0.6);
  border: 1px solid rgba(255,255,255,0.03);
}
.app-header{ display:flex; align-items:flex-start; gap:16px; margin-bottom:12px; }
.app-header h1{ margin:0; font-size:1.9rem; }
.subtitle{ margin:6px 0 0 0; color:var(--muted); font-size:0.95rem; }
.composer{ display:flex; gap:10px; margin-top:10px; }
#new-todo{ flex:1; padding:12px 14px; border-radius:12px; background:var(--glass); border:1px solid rgba(255,255,255,0.03); color:var(--text); outline:none; font-size:1rem; }
#add-btn{ background: linear-gradient(90deg,var(--accent2),var(--accent3)); border:none; padding:10px 14px; border-radius:12px; color:white; font-weight:600; cursor:pointer; }
.controls{ display:flex; justify-content:space-between; align-items:center; margin:14px 0; gap:12px; }
.stats{ color:var(--muted); font-size:0.95rem; }
.filters button{ background:transparent; border:1px solid rgba(255,255,255,0.03); color:var(--muted); padding:8px 10px; border-radius:10px; cursor:pointer; }
.filters button.active{ color:white; border-color:transparent; background: linear-gradient(90deg, rgba(124,92,255,0.12), rgba(0,212,255,0.06)); }
.todo-list{ list-style:none; margin:0; padding:0; display:grid; gap:12px; }
.todo-item{ display:flex; align-items:center; gap:12px; padding:12px; border-radius:12px; background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.00)); border:1px solid rgba(255,255,255,0.02); }
.todo-item .check{ width:44px; height:44px; border-radius:10px; display:flex; align-items:center; justify-content:center; background:linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.00)); border:1px solid rgba(255,255,255,0.03); cursor:pointer; }
.todo-item.done .text{ text-decoration:line-through; color:var(--muted); }
.text{ flex:1; font-size:1rem; }
.actions{ display:flex; gap:8px; align-items:center; }
.icon-btn{ background:transparent; border:1px solid rgba(255,255,255,0.03); padding:8px; border-radius:10px; cursor:pointer; color:var(--muted); }
.app-footer{ margin-top:16px; color:var(--muted); text-align:center; font-size:0.85rem; }
@media (max-width:600px){
  .app{ padding:18px; border-radius:12px; }
  .app-header h1{ font-size:1.4rem; }
  .composer{ flex-direction:column; }
  #add-btn{ width:100%; }
}
"""

script_js = """(function(){
  const STORAGE_KEY = "todo_app_v1";
  let todos = [];
  let filter = "all";

  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));

  const input = $("#new-todo");
  const addBtn = $("#add-btn");
  const list = $("#todo-list");
  const totalCount = $("#total-count");
  const doneCount = $("#done-count");
  const filterBtns = $$(".filters button");

  function load(){ try{ const raw = localStorage.getItem(STORAGE_KEY); todos = raw ? JSON.parse(raw) : []; }catch(e){ todos = []; } }
  function save(){ localStorage.setItem(STORAGE_KEY, JSON.stringify(todos)); }
  function uid(){ return Date.now().toString(36) + Math.random().toString(36).slice(2,8); }

  function addTodo(text){ if(!text||!text.trim()) return; todos.unshift({ id: uid(), text: text.trim(), done:false, createdAt: Date.now() }); save(); render(); }
  function removeTodo(id){ todos = todos.filter(t=>t.id!==id); save(); render(); }
  function toggleDone(id){ todos = todos.map(t=> t.id===id ? {...t, done: !t.done} : t); save(); render(); }
  function setFilter(f){ filter=f; filterBtns.forEach(b=> b.classList.toggle('active', b.dataset.filter===f)); render(); }
  function filtered(){ if(filter==='active') return todos.filter(t=>!t.done); if(filter==='done') return todos.filter(t=>t.done); return todos; }

  function escapeHtml(s){ return s.replace(/[&<>"']/g, m=> ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":\"&#39;\"}[m])); }

  function render(){
    list.innerHTML = '';
    const items = filtered();
    for(const t of items){
      const li = document.createElement('li');
      li.className = 'todo-item' + (t.done ? ' done' : '');
      li.innerHTML = `
        <div class="check" role="button" data-id="${t.id}"><div class="dot"></div></div>
        <div class="text">${escapeHtml(t.text)}</div>
        <div class="actions">
          <button class="icon-btn delete" data-id="${t.id}">🗑</button>
        </div>
      `;
      li.querySelector('.check').addEventListener('click', e=> toggleDone(e.currentTarget.dataset.id));
      li.querySelector('.delete').addEventListener('click', e=> removeTodo(e.currentTarget.dataset.id));
      list.appendChild(li);
    }
    totalCount.textContent = todos.length;
    doneCount.textContent = todos.filter(t=>t.done).length;
  }

  function boot(){
    load();
    render();
    addBtn.addEventListener('click', ()=> { addTodo(input.value); input.value=''; input.focus(); });
    input.addEventListener('keydown', e=> { if(e.key==='Enter'){ addTodo(input.value); input.value=''; }});
    filterBtns.forEach(b=> b.addEventListener('click', ()=> setFilter(b.dataset.filter)));
  }

  document.addEventListener('DOMContentLoaded', boot);
})();"""

# write files
(BASE / "index.html").write_text(index_html, encoding="utf-8")
(STATIC / "style.css").write_text(style_css, encoding="utf-8")
(STATIC / "script.js").write_text(script_js, encoding="utf-8")

print("Wrote files:")
print(" -", (BASE / "index.html").resolve())
print(" -", (STATIC / "style.css").resolve())
print(" -", (STATIC / "script.js").resolve())
print("\nNow open the file in your browser:")
print("  file://" + str((BASE / 'index.html').resolve()))
print("Or serve with: python3 -m http.server 5500  (then open http://localhost:5500/output/index.html)")