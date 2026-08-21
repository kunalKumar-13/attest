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
  let main;
  try {
    main = mode === 'master-detail'
      ? await lens.master(SHELL.subject, SHELL)
      : await lens.render(SHELL.subject, SHELL);
  } catch (err) {
    main = window.C.ErrorState(String((err && err.message) || err));
  }
  if (!current(t, { ignoreContext: true })) return;

  host.className = `mode-${mode}`;
  host.classList.remove('x-out-turn', 'x-out-slide');
  host.innerHTML = `
    ${SHELL.notice ? `<div class=c-notice role=status>${window.C.esc(SHELL.notice)}</div>` : ''}
    <div class=w-main id=w-main>${main}</div>
    <aside class=w-ctx id=w-ctx hidden aria-live=polite></aside>`;
  if (move) {
    host.classList.add(`x-in-${move}`);
    host.addEventListener('animationend',
      () => host.classList.remove(`x-in-${move}`), { once: true });
  }
  if (lens.mount) lens.mount(el('w-main'), SHELL.subject, SHELL);
  markSelection();
  await renderContext();
}

/* Only this runs when context changes. The workspace above it is untouched. */
async function renderContext() {
  const pane = el('w-ctx');
  if (!pane) return;
  const lens = LENSES[SHELL.lens];
  const mode = layoutFor(lens, SHELL.subject);

  if (!SHELL.context) {
    pane.hidden = mode !== 'master-detail';
    if (mode === 'master-detail') {
      pane.className = 'w-ctx';
      pane.innerHTML = window.C.EmptyState(
        lens.emptyContext || 'Select a row to inspect it.');
    } else {
      pane.innerHTML = '';
    }
    el('workspace').classList.toggle('has-ctx', mode === 'master-detail');
    return;
  }

  pane.hidden = false;
  pane.className = mode === 'master-detail' ? 'w-ctx' : 'w-ctx drawer';
  el('workspace').classList.add('has-ctx');
  pane.innerHTML = window.C.LoadingState('');

  const t = token();
  let html;
  try {
    html = await lens.context(SHELL.context, SHELL.subject, SHELL);
  } catch (err) {
    html = window.C.ErrorState(String((err && err.message) || err));
  }
  if (!current(t)) return;              // subject, lens or context moved
  pane.innerHTML = html;
  pane.classList.add('x-in-ctx');
  pane.addEventListener('animationend',
    () => pane.classList.remove('x-in-ctx'), { once: true });
  if (lens.mountContext) lens.mountContext(pane, SHELL.context, SHELL);
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
