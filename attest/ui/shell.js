/* The application shell. Subject × lens, and nothing else.
 *
 * The autopsy found the subject dying in four of six navigations, caused by one
 * line — `S.sub = null` inside go(). That is not a bug to patch where it
 * happens. It is a symptom of the shell not owning subject state at all: every
 * screen was a fresh portfolio-wide question, so there was nothing for a
 * navigation to preserve.
 *
 * Here the shell owns both axes and they are independent. There is exactly one
 * way to change either:
 *
 *     navigate({ subject, lens })
 *
 * Omit a field and it is preserved. That is the whole continuity contract, and
 * it is enforced in one function rather than remembered at each call site.
 *
 * §7 of the directive, made executable:
 *
 *   changing LENS       ->  subject MUST NOT change
 *   changing SUBJECT    ->  lens MUST NOT change, if the new subject supports it
 *   lens unsupported    ->  fall back to the nearest valid lens VISIBLY
 *   never               ->  silently return to a default subject or lens
 */
'use strict';

const SHELL = {
  run: null,
  subject: { type: 'portfolio', id: 'portfolio' },
  lens: 'control',
  record: null,        // the canonical subject record from /api/subject
  spine: null,
  lenses: [],
  review: 15000,
  exposure: 10000000,
  seq: 0,              // monotonic request id; see the guard below
  notice: null,        // set when the contract had to fall back, shown to the user
};

const LENS_ORDER = ['control', 'journal', 'evidence', 'investigate',
                    'policy', 'activity', 'trust'];

/* The lens registry. A lens declares which subject types it can render and
   how; the shell never special-cases one. */
const LENSES = {};
function defineLens(key, impl) { LENSES[key] = impl; }

const api = p => fetch(p).then(r => r.json());
const el = id => document.getElementById(id);

/* ---------------------------------------------------------------- the guard
 *
 * D15 attached a real investigation trail to the wrong settlement. The existing
 * AsyncResourceGuard keyed on entity alone, which is not enough here: a result
 * is only applicable if the SUBJECT and the LENS that asked for it are both
 * still current. Either axis moving invalidates it.
 */
const GUARD = new AsyncResourceGuard('shell');

function token() {
  return { seq: ++SHELL.seq, type: SHELL.subject.type, id: SHELL.subject.id,
           lens: SHELL.lens };
}
function current(t) {
  return t.seq === SHELL.seq && t.type === SHELL.subject.type
      && t.id === SHELL.subject.id && t.lens === SHELL.lens;
}

/* ------------------------------------------------------------------- URL
 *
 * Hash-based, so subject and lens survive a reload with no server routes:
 *   #/portfolio/control
 *   #/settlement/setl_000089/journal
 */
function toHash({ subject, lens }) {
  return subject.type === 'portfolio'
    ? `#/portfolio/${lens}`
    : `#/${subject.type}/${encodeURIComponent(subject.id)}/${lens}`;
}

function fromHash(h) {
  const p = (h || '').replace(/^#\/?/, '').split('/').filter(Boolean);
  if (!p.length) return null;
  if (p[0] === 'portfolio') {
    return { subject: { type: 'portfolio', id: 'portfolio' },
             lens: p[1] || 'control' };
  }
  if (p.length >= 2) {
    return { subject: { type: p[0], id: decodeURIComponent(p[1]) },
             lens: p[2] || null };
  }
  return null;
}

/* ------------------------------------------------------------- navigation */

let HEADER = null, STRIP = null;

/**
 * The only way to move. Both fields optional; what you omit is preserved.
 *
 * `reason` is for the fallback notice — when a subject cannot support the
 * current lens the user is told, because §7 forbids doing it silently.
 */
async function navigate(next = {}, opts = {}) {
  const subject = next.subject || SHELL.subject;
  const changedSubject = subject.type !== SHELL.subject.type
                      || subject.id !== SHELL.subject.id;
  const wanted = next.lens || SHELL.lens;

  SHELL.subject = subject;
  SHELL.notice = null;

  const t = token();
  const rec = await api(`/api/subject?run=${SHELL.run}`
    + `&type=${encodeURIComponent(subject.type)}&id=${encodeURIComponent(subject.id)}`);
  if (!current({ ...t, lens: SHELL.lens })) return;   // subject moved again
  if (rec.error) { paintError(rec.error); return; }

  SHELL.record = rec;
  SHELL.lenses = rec.lenses || [];
  const keys = SHELL.lenses.map(l => l.key);

  // The contract's one branch: keep the lens if the new subject supports it,
  // otherwise fall back to the nearest valid one and SAY SO.
  let lens = wanted;
  if (!keys.includes(lens)) {
    const near = LENS_ORDER.filter(k => keys.includes(k));
    lens = near[0] || keys[0];
    SHELL.notice = `${labelOf(wanted)} does not apply to a ${subject.type}. `
                 + `Showing ${labelOf(lens)}.`;
  }
  const changedLens = lens !== SHELL.lens;
  SHELL.lens = lens;

  const hash = toHash({ subject, lens });
  if (location.hash !== hash) {
    opts.replace ? history.replaceState(null, '', hash)
                 : history.pushState(null, '', hash);
  }

  HEADER.update(rec);
  STRIP.update(SHELL.lenses, lens);
  announce(`${rec.label}, ${labelOf(lens)}`);
  await render({ changedSubject, changedLens });
}

const labelOf = k => (window.C && LENSES[k] && LENSES[k].label) || k;

/* ------------------------------------------------------------- rendering
 *
 * The transition is the product. Two moves, two treatments, each preserving
 * the axis that did not change:
 *
 *   LENS changed    the header does not move at all; the workspace turns over
 *   SUBJECT changed the strip does not move at all; the workspace slides
 *
 * If both changed it is a jump and reads as one. If neither changed it is a
 * refresh and must not animate, or the product flickers at itself.
 */
async function render({ changedSubject = false, changedLens = false } = {}) {
  const host = el('workspace');
  const lens = LENSES[SHELL.lens];
  if (!lens) { paintError(`No lens ${SHELL.lens}`); return; }

  const move = changedSubject && changedLens ? 'jump'
             : changedLens ? 'turn'
             : changedSubject ? 'slide' : null;

  if (move) host.classList.add(`x-out-${move}`);
  const t = token();

  let html;
  try {
    html = await lens.render(SHELL.subject, SHELL);
  } catch (err) {
    html = window.C.ErrorState(String(err && err.message || err));
  }
  if (!current(t)) return;             // subject or lens moved during the await

  host.classList.remove('x-out-turn', 'x-out-slide', 'x-out-jump');
  host.innerHTML = (SHELL.notice
    ? `<div class=c-notice role=status>${window.C.esc(SHELL.notice)}</div>` : '')
    + html;
  host.scrollTop = changedSubject || changedLens ? 0 : host.scrollTop;
  if (move) {
    host.classList.add(`x-in-${move}`);
    host.addEventListener('animationend', () =>
      host.classList.remove(`x-in-${move}`), { once: true });
  }
  if (lens.mount) lens.mount(host, SHELL.subject, SHELL);
}

function paintError(msg) {
  el('workspace').innerHTML = window.C.ErrorState(msg);
}

function announce(text) {
  const n = el('live');
  if (n) n.textContent = text;
}

/* Any element carrying data-subject changes the subject and KEEPS THE LENS.
   One delegated listener, so a lens can emit a link without wiring anything —
   and cannot accidentally implement its own navigation. */
document.addEventListener('click', e => {
  const b = e.target.closest('[data-subject]');
  if (!b) return;
  const [type, ...rest] = b.dataset.subject.split(':');
  navigate({ subject: { type, id: rest.join(':') } });
});

window.addEventListener('popstate', () => {
  const s = fromHash(location.hash);
  if (s) navigate(s, { replace: true });
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
window.shellApi = api;
window.shellToken = token;
window.shellCurrent = current;
window.LENSES = LENSES;
window.bootShell = boot;
