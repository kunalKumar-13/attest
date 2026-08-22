/* The application shell. Subject × lens × context.
 *
 * Phase 1 gave the shell two axes and fixed the subject dying on navigation.
 * The Phase 1 gate found the next problem: the workspace was still a vertical
 * document. Movement through the product was scrolling, not focusing and
 * returning, because there was nowhere for a thing you are *temporarily
 * inspecting* to live. It had to become either a section further down the page
 * or a whole new subject, and neither is what inspecting something is.
 *
 * So there are three axes now, and they mean different things:
 *
 *     SUBJECT   what the workspace is about
 *     LENS      which question is being asked of it
 *     CONTEXT   what is being inspected inside that, right now
 *
 * Context is real application state, addressable and restorable, not a class
 * toggled on a div. That distinction is the whole of whether closing a drawer
 * returns you to where you were.
 *
 * The continuity contract, extended:
 *
 *   changing LENS      ->  subject unchanged; context kept if the new lens can
 *                          render it, dropped visibly if it cannot
 *   changing SUBJECT   ->  lens unchanged; context cleared, because inspecting
 *                          X inside subject A means nothing inside subject B
 *   changing CONTEXT   ->  neither subject nor lens moves, and the workspace
 *                          does NOT re-render — only the detail pane does
 *   never              ->  silently return to a default of anything
 */
'use strict';

const SHELL = {
  run: null,
  subject: { type: 'portfolio', id: 'portfolio' },
  lens: 'control',
  context: null,       // {type, id} — what is being inspected inside subject×lens
  record: null,
  lenses: [],
  review: 15000,
  exposure: 10000000,
  seq: 0,
  notice: null,
};

const LENS_ORDER = ['control', 'journal', 'evidence', 'investigate',
                    'policy', 'activity', 'trust'];

const LENSES = {};
function defineLens(key, impl) { LENSES[key] = impl; }

const api = p => fetch(p).then(r => r.json());
const el = id => document.getElementById(id);
const GUARD = new AsyncResourceGuard('shell');

/* A token identifies the full three-axis position a request was made from. A
   result is applicable only if all of it still holds — D15 at shell level. */
function token() {
  return { seq: ++SHELL.seq, type: SHELL.subject.type, id: SHELL.subject.id,
           lens: SHELL.lens, ctx: ctxKey(SHELL.context) };
}
function current(t, { ignoreContext = false } = {}) {
  return t.seq === SHELL.seq && t.type === SHELL.subject.type
      && t.id === SHELL.subject.id && t.lens === SHELL.lens
      && (ignoreContext || t.ctx === ctxKey(SHELL.context));
}
const ctxKey = c => (c ? `${c.type}:${c.id}` : '');
const prefersStill = () =>
  matchMedia('(prefers-reduced-motion: reduce)').matches;
const parseCtx = s => {
  if (!s) return null;
  const i = s.indexOf(':');
  return i < 0 ? null : { type: s.slice(0, i), id: s.slice(i + 1) };
};

/* --------------------------------------------------------------------- URL
 *   #/portfolio/journal
 *   #/settlement/setl_000089/journal
 *   #/settlement/setl_000089/journal?in=order:ord_000819
 *
 * Context rides in a query so the subject × lens grammar stays readable at a
 * glance, which §20 asks for. `in=` reads as what it is: what I am looking at
 * inside this.
 */
function toHash({ subject, lens, context }) {
  const base = subject.type === 'portfolio'
    ? `#/portfolio/${lens}`
    : `#/${subject.type}/${encodeURIComponent(subject.id)}/${lens}`;
  return context ? `${base}?in=${encodeURIComponent(ctxKey(context))}` : base;
}

function fromHash(h) {
  const [path, query] = (h || '').replace(/^#\/?/, '').split('?');
  const p = path.split('/').filter(Boolean);
  if (!p.length) return null;
  const context = parseCtx(new URLSearchParams(query || '').get('in'));
  if (p[0] === 'portfolio') {
    return { subject: { type: 'portfolio', id: 'portfolio' },
             lens: p[1] || 'control', context };
  }
  if (p.length >= 2) {
    return { subject: { type: p[0], id: decodeURIComponent(p[1]) },
             lens: p[2] || null, context };
  }
  return null;
}

/* ------------------------------------------------------------- navigation */

let HEADER = null, STRIP = null;
let ORIGIN = null;   // the rect the current context was opened from

async function navigate(next = {}, opts = {}) {
  const subject = next.subject || SHELL.subject;
  const changedSubject = subject.type !== SHELL.subject.type
                      || subject.id !== SHELL.subject.id;
  const wanted = next.lens || SHELL.lens;

  SHELL.subject = subject;
  SHELL.notice = null;

  const rec = await api(`/api/subject?run=${SHELL.run}`
    + `&type=${encodeURIComponent(subject.type)}&id=${encodeURIComponent(subject.id)}`);
  if (subject.type !== SHELL.subject.type || subject.id !== SHELL.subject.id) return;
  if (rec.error) { paintError(rec.error); return; }

  SHELL.record = rec;
  SHELL.lenses = rec.lenses || [];
  const keys = SHELL.lenses.map(l => l.key);

  let lens = wanted;
  if (!keys.includes(lens)) {
    lens = LENS_ORDER.filter(k => keys.includes(k))[0] || keys[0];
    SHELL.notice = `${labelOf(wanted)} does not apply to a ${subject.type}. `
                 + `Showing ${labelOf(lens)}.`;
  }
  const changedLens = lens !== SHELL.lens;
  SHELL.lens = lens;

  // Context survives a lens change only if the new lens can render it, and its
  // loss is announced. It never survives a subject change: inspecting an order
  // inside one settlement means nothing inside another.
  let context = 'context' in next ? next.context : SHELL.context;
  if (changedSubject && !('context' in next)) context = null;
  if (context && !canHoldContext(lens, subject, context)) {
    if (!changedSubject) {
      SHELL.notice = `${labelOf(lens)} cannot open a ${context.type}. `
                   + `Closed it.`;
    }
    context = null;
  }
  SHELL.context = context;

  const hash = toHash({ subject, lens, context });
  if (location.hash !== hash) {
    opts.replace ? history.replaceState(null, '', hash)
                 : history.pushState(null, '', hash);
  }

  HEADER.update(rec);
  STRIP.update(SHELL.lenses, lens);
  announce(`${rec.label}, ${labelOf(lens)}`
    + (context ? `, inspecting ${context.id}` : ''));
  await render({ changedSubject, changedLens });
}

/**
 * Open, close or move what is being inspected — WITHOUT re-rendering the
 * workspace. That is the difference between "I opened something" and "I
 * navigated somewhere else", and it is a different code path for exactly that
 * reason. Passing null closes.
 */
async function inspect(context, opts = {}) {
  if (ctxKey(context) === ctxKey(SHELL.context) && !opts.force) return;
  if (context && !canHoldContext(SHELL.lens, SHELL.subject, context)) return;

  // Closing collapses back toward whatever it opened from, so the gesture is
  // reversible rather than merely undone.
  const pane = el('w-ctx');
  if (!context && pane && SHELL.context && !prefersStill()) {
    pane.classList.add('x-out-ctx');
    await new Promise(r => setTimeout(r, 110));
    pane.classList.remove('x-out-ctx');
  }
  if (!context) ORIGIN = null;
  SHELL.context = context;

  const hash = toHash(SHELL);
  if (location.hash !== hash) {
    // Opening context is a history step so Back closes it, which is what a
    // person means by back after opening a drawer.
    opts.replace ? history.replaceState(null, '', hash)
                 : history.pushState(null, '', hash);
  }
  announce(context ? `inspecting ${context.id}` : 'closed');
  markSelection();
  await renderContext();
}

const labelOf = k => (LENSES[k] && LENSES[k].label) || k;

function canHoldContext(lensKey, subject, context) {
  const L = LENSES[lensKey];
  if (!L || !L.context) return false;
  return !L.holds || L.holds(context, subject);
}

/* --------------------------------------------------------------- rendering
 *
 * Three moves, three treatments, each preserving what did not change:
 *
 *   LENS      the header holds still; the workspace turns over
 *   SUBJECT   the strip holds still; the workspace slides
 *   CONTEXT   the workspace holds still; only the detail pane moves
 *
 * The third is the whole of Phase 2. If changing context re-rendered the
 * workspace it would be navigation wearing a drawer's clothes.
 */
/* The spine is structural, not a lens's decoration.
 *
 * It used to be rendered by whichever lens felt like calling StateSpine, which
 * meant it appeared on two views out of fourteen and vanished entirely on
 * Trust — where "where did the money stop" is exactly the question a reader is
 * holding while they read about the system's failures. Rendering it here makes
 * "on every lens, no exceptions" a property of the shell rather than a promise
 * seven files have to keep.
 *
 * Cached per subject so walking the lens strip does not re-request the same
 * flow seven times; the guard already discards anything stale.
 */
/* What the reader last scrolled the master to, BY THEIR OWN ACTION. Reset when
 * the master is rebuilt, because a new lens is a new document.
 *
 * `SETTLING` is what makes this correct rather than circular. Opening a context
 * reflows the master, the browser adjusts scrollTop, and that adjustment fires
 * a scroll event exactly like a real one — so a naive tracker records the
 * reflow as intent and then faithfully restores the wrong number. While the
 * shell is settling its own layout, scroll events are its own noise. */
let MASTER_SCROLL = 0;
let SETTLING = false;

const SPINE = new Map();
async function spineFor(subject) {
  const key = `${SHELL.run}/${subject.type}/${subject.id}/${SHELL.review}/${SHELL.exposure}`;
  if (!SPINE.has(key)) {
    SPINE.set(key, api(subject.type === 'portfolio'
      ? `/api/spine?run=${SHELL.run}&type=portfolio&review=${SHELL.review}&exposure=${SHELL.exposure}`
      : `/api/spine?run=${SHELL.run}&type=settlement&id=${encodeURIComponent(subject.id)}`)
      .catch(() => null));
  }
  return SPINE.get(key);
}

async function render({ changedSubject = false, changedLens = false } = {}) {
  const lens = LENSES[SHELL.lens];
  if (!lens) { paintError(`No lens ${SHELL.lens}`); return; }

  const mode = layoutFor(lens, SHELL.subject);
  const host = el('workspace');
  // No third treatment for "both changed": that happens only via the URL, and
  // it read as an unremarkable fade. A code path earning nothing is a code path
  // that will rot.
  const move = changedLens ? 'turn' : changedSubject ? 'slide' : null;
  if (move) host.classList.add(`x-out-${move}`);

  const t = token();
  let main, spine;
  try {
    [main, spine] = await Promise.all([
      mode === 'master-detail'
        ? lens.master(SHELL.subject, SHELL)
        : lens.render(SHELL.subject, SHELL),
      spineFor(SHELL.subject),
    ]);
  } catch (err) {
    main = window.C.ErrorState(String((err && err.message) || err));
  }
  if (!current(t, { ignoreContext: true })) return;

  host.className = `mode-${mode}`;
  host.classList.remove('x-out-turn', 'x-out-slide');
  host.innerHTML = `
    ${SHELL.notice ? `<div class=c-notice role=status>${window.C.esc(SHELL.notice)}</div>` : ''}
    <div class=w-spine id=w-spine>${window.C.StateSpine(spine, { rail: true })}</div>
    <div class=w-main id=w-main>${main}</div>
    <aside class=w-ctx id=w-ctx hidden aria-live=polite></aside>`;
  // The header carries the stage the spine stopped at, so identity and state
  // are one object rather than two things that happen to agree.
  if (HEADER && spine) HEADER.stage(spine.stopped_at, spine);
  if (move) {
    host.classList.add(`x-in-${move}`);
    host.addEventListener('animationend',
      () => host.classList.remove(`x-in-${move}`), { once: true });
  }
  MASTER_SCROLL = 0;
  const mainEl = el('w-main');
  if (mainEl) mainEl.addEventListener('scroll',
    () => { if (!SETTLING) MASTER_SCROLL = mainEl.scrollTop; }, { passive: true });
  if (lens.mount) lens.mount(mainEl, SHELL.subject, SHELL);
  markSelection();
  await renderContext();
}

/* Only this runs when context changes. The workspace above it is untouched. */
async function renderContext() {
  const pane = el('w-ctx');
  if (!pane) return;

  /* Opening a context narrows the master from the full width to its column.
   * The reflow moves the reader's place, and §7 says only the context appears
   * and disappears — the master is where they already were.
   *
   * The intended position is tracked CONTINUOUSLY rather than captured here.
   * renderContext can run more than once for a single open, and a second call
   * that re-reads scrollTop reads the value the first call's reflow already
   * moved — so the restore faithfully restores the wrong number. What the
   * reader chose is only knowable from their own scrolling. */
  const main = el('w-main');
  const want = MASTER_SCROLL;
  SETTLING = true;
  const restore = () => {
    if (main && main.scrollTop !== want) main.scrollTop = want;
  };
  const settled = () => { restore(); SETTLING = false; };
  const lens = LENSES[SHELL.lens];
  const mode = layoutFor(lens, SHELL.subject);

  // Two different facts, and conflating them made an EMPTY detail pane overlay
  // the master at phone widths and swallow every click:
  //   has-pane  the layout reserves a detail column
  //   has-ctx   something is actually being inspected
  const ws = el('workspace');
  ws.classList.toggle('has-pane', mode === 'master-detail');

  if (!SHELL.context) {
    // No placeholder. The absence of a context is the correct state, not a
    // state that needs explaining — and a pane holding one sentence was
    // taking a full grid row (1440x125) beneath the master, which is the
    // empty-pane finding of the 9.1 autopsy in a new orientation. Emptying it
    // rather than styling it around means `#w-ctx:empty` can remove it from
    // the layout entirely, whichever way the grid happens to be flowing.
    pane.hidden = true;
    pane.className = 'w-ctx';
    pane.innerHTML = '';
    ws.classList.remove('has-ctx');
    requestAnimationFrame(() => requestAnimationFrame(settled));
    return;
  }

  pane.hidden = false;
  pane.className = mode === 'master-detail' ? 'w-ctx' : 'w-ctx drawer';
  ws.classList.add('has-ctx');
  setOrigin(pane);
  pane.innerHTML = window.C.LoadingState('');

  const t = token();
  let html;
  try {
    html = await lens.context(SHELL.context, SHELL.subject, SHELL);
  } catch (err) {
    html = window.C.ErrorState(String((err && err.message) || err));
  }
  if (!current(t)) return;              // subject, lens or context moved

  const lensLabel = labelOf(SHELL.lens);
  pane.innerHTML = (typeof html === 'string' ? html : window.C.ContextChrome({
      subject: SHELL.subject, lens: lensLabel, kind: html.kind,
      title: html.title, status: html.status, promote: html.promote,
    }) + html.body);
  pane.classList.add('x-in-ctx');
  pane.addEventListener('animationend', () => {
    pane.classList.remove('x-in-ctx');
    settled();          // once the entrance has finished and layout is final
  }, { once: true });
  if (lens.mountContext) lens.mountContext(pane, SHELL.context, SHELL);
  requestAnimationFrame(() => requestAnimationFrame(restore));
  // Belt and braces: if the animation never runs (reduced motion, or a pane
  // that did not animate) animationend never fires and SETTLING would stick.
  setTimeout(settled, 400);
}

/* Anchor the drawer's growth to where the click happened. A pane that always
   expands from the same edge is a route transition with a different name. */
function setOrigin(pane) {
  const host = el('workspace').getBoundingClientRect();
  const r = ORIGIN;
  if (!r) { pane.style.removeProperty('--oy'); return; }
  const y = Math.min(Math.max(r.top + r.height / 2 - host.top, 0), host.height);
  pane.style.setProperty('--oy', `${y.toFixed(0)}px`);
}

function layoutFor(lens, subject) {
  const l = typeof lens.layout === 'function' ? lens.layout(subject) : lens.layout;
  return l || 'focus';
}

/* The selected row stays selected. §5: close the detail and it is still there. */
function markSelection() {
  const key = ctxKey(SHELL.context);
  document.querySelectorAll('[data-context]').forEach(n => {
    const on = n.dataset.context === key;
    n.classList.toggle('sel', on);
    if (n.hasAttribute('aria-selected')) n.setAttribute('aria-selected', String(on));
  });
}

function paintError(msg) { el('workspace').innerHTML = window.C.ErrorState(msg); }
function announce(text) { const n = el('live'); if (n) n.textContent = text; }

/* ------------------------------------------------------------------ events
 *
 * Two affordances, deliberately distinct:
 *   data-context  inspect this inside what I am already looking at
 *   data-subject  make this the thing the workspace is about
 */
document.addEventListener('click', e => {
  const close = e.target.closest('[data-close-ctx]');
  if (close) { inspect(null); return; }

  const c = e.target.closest('[data-context]');
  if (c) {
    e.preventDefault();
    // Remember where the click came from. §4: the drawer should look like it
    // opened out of the thing you clicked, not like a panel that lives at the
    // right edge and slides in whatever you touched.
    ORIGIN = c.getBoundingClientRect();
    inspect(parseCtx(c.dataset.context));
    return;
  }
  const b = e.target.closest('[data-subject]');
  if (b) {
    const [type, ...rest] = b.dataset.subject.split(':');
    navigate({ subject: { type, id: rest.join(':') } });
  }
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && SHELL.context) { e.preventDefault(); inspect(null); }
});

window.addEventListener('popstate', () => {
  const s = fromHash(location.hash);
  if (!s) return;
  const sameSubject = s.subject.type === SHELL.subject.type
                   && s.subject.id === SHELL.subject.id;
  const sameLens = (s.lens || SHELL.lens) === SHELL.lens;
  // Back out of a drawer must not rebuild the workspace behind it.
  if (sameSubject && sameLens) inspect(s.context, { replace: true });
  else navigate(s, { replace: true });
});

window.addEventListener('resize', () => {
  if (STRIP) STRIP.update(SHELL.lenses, SHELL.lens);
});

/* ------------------------------------------------------------------ boot */

async function boot() {
  HEADER = new window.C.SubjectHeader(el('subject'));
  STRIP = new window.C.LensStrip(el('lenses'), lens => navigate({ lens }));
  el('workspace').innerHTML = window.C.LoadingState('reconciling…');
  const summary = await api(`/api/run?n=${el('size') ? el('size').value : 250}`);
  SHELL.run = summary.run_id;
  GUARD.invalidateAll();
  SPINE.clear();
  const start = fromHash(location.hash)
             || { subject: { type: 'portfolio', id: 'portfolio' }, lens: 'control' };
  await navigate(start, { replace: true });
}

window.SHELL = SHELL;
window.defineLens = defineLens;
window.navigate = navigate;
window.inspect = inspect;
window.shellApi = api;
window.LENSES = LENSES;
window.bootShell = boot;
