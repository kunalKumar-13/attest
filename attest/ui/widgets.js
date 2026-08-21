/* Widget system — §5, §6, §9, §15, §56.
 *
 * The dashboard is data, not markup. A layout is an array of records; the board
 * renders whatever the array says, and rearranging it is editing the array. That
 * is the difference between a workspace and a report, and it is why the layout
 * can be persisted, shared, preset and reset without any of those being a
 * separate feature.
 *
 * Drag and resize are hand-written against pointer events rather than pulled
 * from a library, because this page has no build step and no CDN reachable, and
 * a grid reorder is a few hundred lines of honest arithmetic. What matters for
 * the feel is stated in §8: no jitter, no layout jump, a visible drop target,
 * and no accidental drag when the pointer was aimed at a control.
 */
'use strict';

const GRID_COLS = 12;
const ROW_PX = 104;

/* Every widget declares what it is and how to draw it. Nothing about the board
   knows any particular widget, which is what keeps the registry open. */
const WIDGETS = {};

function defineWidget(type, spec) { WIDGETS[type] = { type, ...spec }; }

/* ---------------------------------------------------------------- layout */

const DEFAULT_LAYOUT = [
  { id: 'w1', type: 'health', w: 5, h: 2 },
  { id: 'w2', type: 'money', w: 4, h: 2 },
  { id: 'w3', type: 'safety', w: 3, h: 3 },
  { id: 'w4', type: 'volume', w: 7, h: 2 },
  { id: 'w5', type: 'reasons', w: 5, h: 2 },
  { id: 'w6', type: 'largest', w: 7, h: 3 },
  { id: 'w7', type: 'activity', w: 5, h: 3 },
];

const PRESETS = {
  'finance-ops': {
    label: 'Finance operations',
    layout: [
      { id: 'p1', type: 'money', w: 5, h: 2 },
      { id: 'p2', type: 'health', w: 4, h: 2 },
      { id: 'p3', type: 'safety', w: 3, h: 3 },
      { id: 'p4', type: 'largest', w: 7, h: 3 },
      { id: 'p5', type: 'reasons', w: 5, h: 3 },
    ],
  },
  'risk': {
    label: 'Risk and controls',
    layout: [
      { id: 'r1', type: 'safety', w: 4, h: 3 },
      { id: 'r2', type: 'exposure', w: 8, h: 2 },
      { id: 'r3', type: 'strata', w: 6, h: 3 },
      { id: 'r4', type: 'reasons', w: 6, h: 3 },
    ],
  },
  'engineering': {
    label: 'Engineering',
    layout: [
      { id: 'e1', type: 'solver', w: 6, h: 2 },
      { id: 'e2', type: 'safety', w: 6, h: 2 },
      { id: 'e3', type: 'hazards', w: 12, h: 3 },
      { id: 'e4', type: 'activity', w: 12, h: 3 },
    ],
  },
  'executive': {
    label: 'Executive',
    layout: [
      { id: 'x1', type: 'money', w: 6, h: 2 },
      { id: 'x2', type: 'exposure', w: 6, h: 2 },
      { id: 'x3', type: 'health', w: 6, h: 2 },
      { id: 'x4', type: 'safety', w: 6, h: 2 },
    ],
  },
};

const LS_KEY = 'attest-dashboard-layout';

function loadLayout() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return structuredClone(DEFAULT_LAYOUT);
    const l = JSON.parse(raw);
    // A layout referencing a widget type this build no longer defines would
    // render an empty box forever. Drop unknown types rather than persist rot.
    return Array.isArray(l) ? l.filter(w => WIDGETS[w.type]) : structuredClone(DEFAULT_LAYOUT);
  } catch { return structuredClone(DEFAULT_LAYOUT); }
}

function saveLayout(layout) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(layout)); } catch { /* quota */ }
}

/* ------------------------------------------------------------------ board */

class Board {
  constructor(host, ctx) {
    this.host = host;
    this.ctx = ctx;
    this.layout = loadLayout();
    this.editing = false;
    this.drag = null;
  }

  setContext(ctx) { this.ctx = ctx; }

  render() {
    this.host.innerHTML = `
      <div class="bd-bar">
        <h2 class="bd-t">Financial control board</h2>
        <span class="bd-sp"></span>
        ${this.editing ? `<select class="btn" id="bd-preset">
            <option value="">presets…</option>
            ${Object.entries(PRESETS).map(([k, p]) =>
              `<option value="${k}">${p.label}</option>`).join('')}
          </select>
          <button class="btn" id="bd-add">+ Add widget</button>
          <button class="btn" id="bd-reset">Reset</button>` : ''}
        <button class="btn ${this.editing ? 'on' : ''}" id="bd-edit"
          aria-pressed="${this.editing}">
          ${this.editing ? 'Done' : 'Customize'}</button>
      </div>
      <div class="bd${this.editing ? ' editing' : ''}" id="bd-grid"></div>`;

    const grid = this.host.querySelector('#bd-grid');
    grid.style.gridTemplateColumns = `repeat(${GRID_COLS}, minmax(0, 1fr))`;
    grid.innerHTML = this.layout.map(w => this.cell(w)).join('');
    this.layout.forEach(w => {
      const body = grid.querySelector(`[data-w="${w.id}"] .bd-body`);
      const spec = WIDGETS[w.type];
      if (body && spec) {
        try { body.innerHTML = spec.render(this.ctx, w); }
        catch (e) { body.innerHTML = `<div class="bd-empty">unavailable</div>`; }
      }
    });
    this.wire(grid);
  }

  cell(w) {
    const spec = WIDGETS[w.type] || {};
    const name = spec.title || w.type;
    /* The grip is a real <button> when editing, not a decorated span. That is
       what gives it focus, an accessible name and Enter/Space for free — and it
       is what makes the keyboard path below possible at all. §52. */
    const grip = this.editing
      ? `<button class="bd-g" data-grip aria-label="Move ${name}. Arrow keys to
           reorder, plus and minus to resize.">⠿</button>`
      : `<span class="bd-g" aria-hidden="true">⠿</span>`;
    return `<section class="bd-w" data-w="${w.id}" role="region"
        aria-label="${name}"
        style="grid-column: span ${w.w}; grid-row: span ${w.h}">
      <header class="bd-h">
        ${grip}
        <h3 class="bd-n">${name}</h3>
        <span class="bd-sp"></span>
        ${this.editing ? `
          <button class="bd-x" data-act="w-" aria-label="Make ${name} narrower">−</button>
          <button class="bd-x" data-act="w+" aria-label="Make ${name} wider">+</button>
          <button class="bd-x" data-act="h-" aria-label="Make ${name} shorter">▴</button>
          <button class="bd-x" data-act="h+" aria-label="Make ${name} taller">▾</button>
          <button class="bd-x" data-act="rm" aria-label="Remove ${name}">×</button>` : ''}
      </header>
      <div class="bd-body"></div>
    </section>`;
  }

  /* Keyboard equivalent of drag, §8 and §52. Pointer physics are not an
     accessible interface, and a board that can only be arranged with a mouse is
     a board some people cannot arrange. Arrows move, +/- resize, Delete removes
     — and focus follows the widget across the re-render so a sequence of moves
     is one continuous action rather than a hunt for the grip each time. */
  key(e, grid) {
    const grip = e.target.closest('[data-grip]');
    if (!grip) return;
    const id = grip.closest('[data-w]').dataset.w;
    const i = this.layout.findIndex(x => x.id === id);
    const w = this.layout[i];
    const swap = d => {
      const j = i + d;
      if (j < 0 || j >= this.layout.length) return;
      [this.layout[i], this.layout[j]] = [this.layout[j], this.layout[i]];
    };
    const k = e.key;
    if (k === 'ArrowLeft' || k === 'ArrowUp') swap(-1);
    else if (k === 'ArrowRight' || k === 'ArrowDown') swap(1);
    else if (k === '+' || k === '=') w.w = Math.min(GRID_COLS, w.w + 1);
    else if (k === '-' || k === '_') w.w = Math.max(2, w.w - 1);
    else if (k === 'Delete' || k === 'Backspace')
      this.layout = this.layout.filter(x => x.id !== id);
    else return;
    e.preventDefault();
    saveLayout(this.layout);
    this.render();
    this.host.querySelector(`[data-w="${id}"] [data-grip]`)?.focus();
    this.announce(`${WIDGETS[w.type]?.title || w.type} moved`);
  }

  /* A live region, because a visual reflow is not feedback for everyone. */
  announce(msg) {
    let el = document.getElementById('bd-live');
    if (!el) {
      el = document.createElement('div');
      el.id = 'bd-live';
      el.className = 'sr';
      el.setAttribute('aria-live', 'polite');
      document.body.appendChild(el);
    }
    el.textContent = msg;
  }

  wire(grid) {
    this.host.querySelector('#bd-edit').onclick = () => {
      this.editing = !this.editing; this.render();
    };
    const add = this.host.querySelector('#bd-add');
    if (add) add.onclick = () => this.openPicker();
    const reset = this.host.querySelector('#bd-reset');
    if (reset) reset.onclick = () => {
      this.layout = structuredClone(DEFAULT_LAYOUT); saveLayout(this.layout); this.render();
    };
    const pre = this.host.querySelector('#bd-preset');
    if (pre) pre.onchange = e => {
      const p = PRESETS[e.target.value];
      if (p) { this.layout = structuredClone(p.layout); saveLayout(this.layout); this.render(); }
    };

    grid.querySelectorAll('.bd-x').forEach(b => b.onclick = e => {
      e.stopPropagation();
      const id = b.closest('[data-w]').dataset.w;
      const w = this.layout.find(x => x.id === id);
      const act = b.dataset.act;
      if (act === 'rm') this.layout = this.layout.filter(x => x.id !== id);
      if (act === 'w+') w.w = Math.min(GRID_COLS, w.w + 1);
      if (act === 'w-') w.w = Math.max(2, w.w - 1);
      if (act === 'h+') w.h = Math.min(6, w.h + 1);
      if (act === 'h-') w.h = Math.max(1, w.h - 1);
      saveLayout(this.layout); this.render();
    });

    if (this.editing) {
      grid.querySelectorAll('[data-grip]').forEach(h =>
        h.addEventListener('pointerdown', e => this.startDrag(e, grid)));
      grid.addEventListener('keydown', e => this.key(e, grid));
    }
  }

  /* Reorder by pointer. The dragged card follows the cursor on a transform so
     nothing reflows under it, and the placeholder is the only thing that moves
     in the grid — which is what stops the jitter §8 warns about. */
  startDrag(e, grid) {
    // A keyboard-driven click on the grip arrives as a pointer event with no
    // real pointer behind it; starting a drag from one strands the card under a
    // cursor that never moves.
    if (e.pointerType && e.pointerType !== 'mouse' && e.pointerType !== 'touch'
        && e.pointerType !== 'pen') return;
    if (window.matchMedia('(max-width: 900px)').matches) return;
    e.preventDefault();
    const card = e.target.closest('[data-w]');
    const id = card.dataset.w;
    const rect = card.getBoundingClientRect();
    const off = { x: e.clientX - rect.left, y: e.clientY - rect.top };

    card.classList.add('dragging');
    card.style.width = `${rect.width}px`;
    card.style.height = `${rect.height}px`;
    const move = ev => {
      card.style.transform =
        `translate(${ev.clientX - rect.left - off.x}px, ${ev.clientY - rect.top - off.y}px)`;
      const over = document.elementFromPoint(ev.clientX, ev.clientY)?.closest('[data-w]');
      if (over && over !== card) {
        const from = this.layout.findIndex(x => x.id === id);
        const to = this.layout.findIndex(x => x.id === over.dataset.w);
        if (from >= 0 && to >= 0 && from !== to) {
          const [m] = this.layout.splice(from, 1);
          this.layout.splice(to, 0, m);
          const cards = [...grid.children];
          grid.insertBefore(card, to > from ? cards[to]?.nextSibling : cards[to]);
        }
      }
    };
    const up = () => {
      card.classList.remove('dragging');
      card.style.transform = card.style.width = card.style.height = '';
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      saveLayout(this.layout);
      this.render();
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  }

  openPicker() {
    const have = new Set(this.layout.map(w => w.type));
    const cats = {};
    Object.values(WIDGETS).forEach(s =>
      (cats[s.category || 'Other'] ||= []).push(s));
    const html = Object.entries(cats).map(([cat, list]) => `
      <div class="pk-cat">${cat}</div>
      ${list.map(s => `<button class="pk-i${have.has(s.type) ? ' used' : ''}"
          data-t="${s.type}">${s.title}
          <small>${s.blurb || ''}</small></button>`).join('')}`).join('');
    const back = document.createElement('div');
    back.className = 'pk-back';
    back.innerHTML = `<div class="pk"><div class="pk-h">Add a widget</div>${html}</div>`;
    document.body.appendChild(back);
    back.onclick = e => {
      if (e.target === back) return back.remove();
      const b = e.target.closest('.pk-i');
      if (!b) return;
      const spec = WIDGETS[b.dataset.t];
      this.layout.push({ id: 'w' + Math.random().toString(36).slice(2, 7),
                         type: spec.type, w: spec.w || 4, h: spec.h || 2 });
      saveLayout(this.layout); back.remove(); this.render();
    };
  }
}

window.ATTESTBoard = { Board, defineWidget, WIDGETS, PRESETS, GRID_COLS, ROW_PX };
