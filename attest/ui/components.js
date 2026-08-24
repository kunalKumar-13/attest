/* Semantic component layer.
 *
 * The autopsy counted 227 CSS classes across 16 screens, 11 different "header"
 * classes and 16 different implementations of one flex-baseline row. Every
 * screen invented its own vocabulary because there was nothing above the token
 * layer to inherit — tokens without components.
 *
 * These are not styling helpers. They are product-semantic primitives: a Metric
 * is "a number that means something with a label and a qualifier", an Amount is
 * "money, in paise, rendered the one correct way". A lens composes these and is
 * not permitted to reach past them for layout, because the moment one does, the
 * next one will, and we are back to 227 classes.
 *
 * Everything returns an HTML string except the stateful pieces (SubjectHeader,
 * LensStrip), which own a DOM node and PATCH it. That distinction is
 * load-bearing: the shell's transitions depend on the header and the strip not
 * being re-rendered when the axis they represent has not changed.
 */
'use strict';

const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* Indian digit grouping. One implementation, because a second one would
   eventually disagree with the first about a lakh. */
function rupees(paise, { whole = false, sign = false } = {}) {
  if (paise === null || paise === undefined) return '—';
  const neg = paise < 0;
  const v = Math.abs(paise);
  let r = String(Math.floor(v / 100));
  const p = String(v % 100).padStart(2, '0');
  if (r.length > 3) {
    let head = r.slice(0, -3);
    const tail = r.slice(-3);
    const parts = [];
    while (head.length > 2) { parts.unshift(head.slice(-2)); head = head.slice(0, -2); }
    if (head) parts.unshift(head);
    r = parts.join(',') + ',' + tail;
  }
  const body = whole ? r : `${r}.${p}`;
  return `${neg ? '−' : sign ? '+' : ''}₹${body}`;
}

const plural = (n, one, many) =>
  `${Number(n).toLocaleString()} ${n === 1 ? one : (many || one + 's')}`;

/* ------------------------------------------------------------------ atoms */

const Status = (s, opts = {}) => s
  ? `<span class="c-status s-${esc(s)}${opts.sm ? ' sm' : ''}">${esc(s)}</span>`
  : '';

const Metric = ({ label, value, note, tone }) => `<div class=c-metric>
  <span class=k>${esc(label)}</span>
  <span class=v${tone ? ` style="color:var(--st-${tone})"` : ''}>${value}</span>
  ${note ? `<span class=n>${esc(note)}</span>` : ''}</div>`;

const MetricRow = (metrics) =>
  `<div class=c-metrics>${metrics.map(Metric).join('')}</div>`;

/* Level 2 and 3 of progressive disclosure. Level 1 is whatever the lens shows
   by default; this is what the sceptic opens. Closed on arrival, every time —
   an operator on their ninth visit should not have to re-collapse the essay. */
const Disclosure = ({ summary, body, open = false }) => `<details class=c-disc${open ? ' open' : ''}${open ? ' open' : ''}>
  <summary>${esc(summary)}</summary>
  <div class=c-disc-b>${body}</div></details>`;

const Section = ({ title, aside, body, question }) => `<section class=c-section>
  ${title ? `<div class=c-section-h><h3>${esc(title)}</h3>
    ${question ? `<span class=q>${esc(question)}</span>` : ''}
    ${aside ? `<span class=a>${aside}</span>` : ''}</div>` : ''}
  ${body}</section>`;

/* One row shape. The autopsy found sixteen implementations of this. */
/* `subject` navigates; `context` inspects. Two affordances because they are two
   different acts — one changes what the workspace is about, the other opens
   something inside it. */
const Row = ({ id, amount, status, detail, aside, subject, context, tone }) => {
  const nav = subject || context;
  const attr = context ? `data-context="${esc(context.type)}:${esc(context.id)}"`
             : subject ? `data-subject="${esc(subject.type)}:${esc(subject.id)}"` : '';
  return `<${nav ? 'button' : 'div'} class="c-row${nav ? ' link' : ''}" ${attr}
     ${context ? 'aria-selected=false' : ''}>
    ${tone ? `<i class="c-dot s-${esc(tone)}"></i>` : ''}
    ${id !== undefined ? `<span class=c-row-id>${esc(id)}</span>` : ''}
    ${amount !== undefined ? `<span class=c-row-amt>${esc(rupees(amount))}</span>` : ''}
    ${status ? Status(status, { sm: true }) : ''}
    ${detail !== undefined ? `<span class=c-row-d>${detail}</span>` : ''}
    ${aside !== undefined ? `<span class=c-row-a>${aside}</span>` : ''}
  </${nav ? 'button' : 'div'}>`;
};

const DataTable = ({ cols, rows, foot }) => `<table class=c-table>
  <thead><tr>${cols.map(c =>
    `<th${c.num ? ' class=num' : ''}>${esc(c.label)}</th>`).join('')}</tr></thead>
  <tbody>${rows.map(r => `<tr>${r.map((cell, i) =>
    `<td${cols[i] && cols[i].num ? ' class=num' : ''}>${cell}</td>`).join('')}</tr>`).join('')}
  ${foot ? `<tr class=foot>${foot.map((cell, i) =>
    `<td${cols[i] && cols[i].num ? ' class=num' : ''}>${cell}</td>`).join('')}</tr>` : ''}
  </tbody></table>`;

const EmptyState = (msg, sub) => `<div class=c-empty>
  <div>${esc(msg)}</div>${sub ? `<span>${esc(sub)}</span>` : ''}</div>`;

const LoadingState = (msg) =>
  `<div class=c-empty><span class=c-spin></span>${esc(msg || '')}</div>`;

const ErrorState = (msg) => `<div class="c-empty err">${esc(msg)}</div>`;

/* ------------------------------------------------------------- state spine
 *
 * Not a progress bar. A statement about where value is standing and what is
 * holding it there — the same five stages for a portfolio and for one
 * settlement, because it is the same pipeline and only the population differs.
 */
function StateSpine(spine, opts = {}) {
  if (!spine || !spine.stages) return '';
  const per = spine.type === 'portfolio';

  // Proportional to what CONTINUES past each stage. The bar collapsing from
  // full width to a sliver is the entire story of the portfolio, and it should
  // be legible before any number is read. Five equal cards with ticks made the
  // reader do that comparison themselves, which is a stepper wearing a
  // financial diagram's clothes.
  const vals = spine.stages.map(s => s.continues_paise);
  const known = vals.every(v => typeof v === 'number');
  const top = known ? Math.max(...vals, 1) : 1;
  const MIN = 0.6;   // a surviving sliver must stay visible or it reads as zero

  return `<div class="c-flow${per ? ' portfolio' : ''}${opts.rail ? ' rail' : ''}"
    role="img" aria-label="Money flow${spine.stopped_at
      ? `, stopped at ${esc(spine.stopped_at)}` : ''}">
    ${spine.stages.map(s => {
      const w = known
        ? Math.max(s.continues_paise / top * 100, s.continues_paise > 0 ? MIN : 0)
        : (s.state === 'not_reached' ? 0 : 100);
      const held = per && s.held;
      return `<div class="c-flow-r ${esc(s.state)}">
        <span class=c-flow-n>${esc(s.label)}</span>
        <span class=c-flow-track>
          <i class=c-flow-bar style="width:${w.toFixed(2)}%"></i>
        </span>
        <span class=c-flow-v>${esc(s.value)}</span>
        <span class=c-flow-x>${held
          ? `<b>${esc(s.held_value || '')}</b> held · ${Number(s.held).toLocaleString()}`
          : s.state === 'stopped' ? `<b>stopped here</b>`
          : s.state === 'not_reached' ? 'not reached' : ''}</span>
      </div>
      ${(held || s.state === 'stopped') && opts.detail !== false
        ? `<div class=c-flow-d>${esc(s.detail)}</div>` : ''}`;
    }).join('')}
  </div>`;
}

/* --------------------------------------------------------- context chrome
 *
 * The shell owns this, not the lenses. §18: the context system stays generic,
 * so there is no DrawerSettlement and no DrawerExplanation — a lens supplies a
 * title, a kind and a body, and every drawer in the product is then the same
 * drawer. Each lens hand-writing its own header was three copies of a close
 * button waiting to drift.
 *
 * The breadcrumb is the point. §6 asks that the UI never suggest the context
 * REPLACED the subject, and the only reliable way to say that is to show the
 * chain it hangs off.
 */
function ContextChrome({ subject, lens, kind, title, status, promote }) {
  return `<div class=c-crumb data-crumb>
      <span class=c-crumb-s>${esc(subject.id === 'portfolio'
        ? 'Portfolio' : subject.id)}</span>
      <i>›</i><span class=c-crumb-l>${esc(lens)}</span>
      <i>›</i><span class=c-crumb-c>${esc(kind)}</span>
    </div>
    <div class=c-ctx-h>
      <b>${esc(title)}</b>
      ${status ? Status(status, { sm: true }) : ''}
      <span class=c-ctx-x>
        ${promote ? `<button class="c-ctx-b go"
          data-subject="${esc(promote.type)}:${esc(promote.id)}"
          title="Make this the subject — zoom in">Open ↗</button>` : ''}
        <button class=c-ctx-b data-close-ctx aria-label="Close" title="Close (Esc)">✕</button>
      </span>
    </div>`;
}

/* -------------------------------------------------- subject header (stateful)
 *
 * ONE header for portfolio, settlement, action and source. It PATCHES rather
 * than re-rendering, so that switching lens leaves it visually untouched —
 * which is the difference between an instrument and a page load.
 */
/* One composed identity, not four fields in a row.
 *
 * A case is its name, its state, its money and where that money currently
 * stands. The old header set those side by side at the same weight and the
 * amount — the financial subject of the whole screen — read as a field in a
 * record at 13.5px. Here the amount is the largest thing on the page and the
 * state and stage hang off the identity, because they are properties OF the
 * case rather than neighbours of it.
 *
 * It is patched, never re-rendered. During a lens change the workspace turns
 * over and this must not blink: the case is what did not change.
 */
class SubjectHeader {
  constructor(host) {
    this.host = host;
    this.host.className = 'c-subject';
    this.host.innerHTML = `
      <div class=c-case>
        <div class=c-case-amt><span class=v></span><span class=k></span></div>
        <div class=c-case-id>
          <span class=st></span>
          <span class=lbl></span>
          <span class=sub></span>
        </div>
        <div class=c-case-meta></div>
        <div class="c-slot c-state" id=c-state></div>
        <div class="c-slot c-now" id=c-now></div>
        <div class="c-slot c-next" id=c-next></div>
      </div>`;
    this.q = sel => this.host.querySelector(sel);
  }

  update(s) {
    if (!s || s.error) return;
    this.rec = s;
    const set = (sel, text) => {
      const n = this.q(sel);
      const t = text ?? '';
      if (n.textContent !== t) n.textContent = t;   // patch, never replace
      n.hidden = !t;
    };
    set('.lbl', s.type === 'portfolio' ? s.label : s.id);
    set('.sub', s.type === 'portfolio' ? s.sublabel : (s.amount_label || ''));
    const st = this.q('.st');
    st.className = s.status ? `st c-status s-${s.status}` : 'st c-status';
    st.textContent = s.status || '';
    st.hidden = !s.status;
    const amt = this.q('.c-case-amt');
    amt.hidden = s.amount_paise === null || s.amount_paise === undefined;
    set('.c-case-amt .v', rupees(s.amount_paise));
    set('.c-case-amt .k', s.type === 'portfolio' ? (s.amount_label || '') : '');
    const meta = (s.meta || [])
      .map(m => `<span><i>${esc(m.k)}</i>${esc(m.v)}</span>`).join('');
    const box = this.q('.c-case-meta');
    if (box.innerHTML !== meta) box.innerHTML = meta;
    this.host.dataset.type = s.type;
  }

  /* The financial state of the case, and what follows from it.
   *
   * Written from SUBJECT-level data only. A rail assembled from whichever lens
   * is open would be a summary of the instrument, and the product model is that
   * the case does not change when the room does — which is also asserted by
   * `test_changing_lens_leaves_the_subject_and_the_header_untouched`.
   */
  caseState(spine, kase) {
    const put = (id, html) => {
      const n = this.q('#' + id);
      if (!n) return;
      if (n.innerHTML !== html) n.innerHTML = html;
      n.hidden = !html;
    };

    put('c-state', spine ? StateSpine(spine, { rail: true }) : '');

    const k = kase || {};
    const rows = [];
    if (k.agreed_paise != null) {
      rows.push(`<div class=c-fact><span class=c-fk>agreed</span>
        <b class=c-fv>${esc(rupees(k.agreed_paise))}</b>
        <em>${esc(plural(k.shared_n || 0, 'order'))} in every explanation</em></div>`);
    }
    if (k.disputed_paise != null) {
      rows.push(`<div class="c-fact hot"><span class=c-fk>disputed</span>
        <b class=c-fv>${esc(rupees(k.disputed_paise))}</b>
        <em>turns on ${esc(plural(k.differing || 0, 'order'))}</em></div>`);
    }
    put('c-now', rows.join(''));

    const n = k.next;
    put('c-next', n ? `<div class=c-nx>
      <span class=c-fk>next</span>
      <div class=c-nx-w>${esc(n.what)}</div>
      ${n.value_paise != null ? `<div class=c-nx-v><b>${esc(rupees(n.value_paise))}</b>
        <em>unlocked${n.cases ? ` · ${esc(plural(n.cases, 'case'))}` : ''}${
          n.steps ? ` · ${esc(plural(n.steps, 'step'))}` : ''}</em></div>` : ''}
    </div>` : '');
  }
}

/* ---------------------------------------------------- lens strip (stateful)
 *
 * Also patches. Switching SUBJECT must leave this visually untouched, because
 * the question the user is asking has not changed — only the thing they are
 * asking it about.
 */
class LensStrip {
  constructor(host, onPick) {
    this.host = host;
    this.host.className = 'c-lenses';
    this.host.setAttribute('role', 'tablist');
    this.keys = null;
    host.addEventListener('click', e => {
      const b = e.target.closest('[data-lens]');
      if (b) onPick(b.dataset.lens);
    });
    host.addEventListener('keydown', e => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      const bs = [...host.querySelectorAll('[data-lens]')];
      const i = bs.findIndex(b => b.getAttribute('aria-selected') === 'true');
      const n = bs[i + (e.key === 'ArrowRight' ? 1 : -1)];
      if (n) { e.preventDefault(); n.focus(); onPick(n.dataset.lens); }
    });
  }

  update(lenses, active) {
    const keys = lenses.map(l => l.key).join(',');
    if (keys !== this.keys) {
      this.keys = keys;
      this.host.innerHTML = lenses.map(l =>
        `<button data-lens="${esc(l.key)}" role=tab title="${esc(l.question)}"
           aria-selected=false><span class=c-lens-n>${esc(l.label)}</span>
           <span class=c-lens-q>${esc(l.question)}</span></button>`).join('');
    }
    // The sliding ink indicator went with the horizontal tab band it belonged
    // to. Absolutely positioned inside what is now a two-column grid in the
    // rail, it stretched to 136x888 and painted over the case. The active
    // instrument is carried by weight and ground instead — and the ROOM is
    // what should be telling you which instrument you are holding.
    this.host.querySelectorAll('[data-lens]').forEach(b => {
      const on = b.dataset.lens === active;
      b.setAttribute('aria-selected', String(on));
      b.classList.toggle('on', on);
    });
  }
}

/* THE ROOM'S ANSWER.
 *
 * Every lens asks one question, and the autopsy found that on six of seven the
 * answer was not among the three strongest things on screen — on Policy the
 * word REVIEW lost to the application's own name. This is the instrument's
 * conclusion, and it is the first and largest thing in the room.
 *
 * `fact` is the verdict in the lens's own vocabulary. `figure` is the money it
 * turns on, when there is one. `because` is one sentence of why — prose is
 * allowed to say WHY, never WHAT.
 */
function Conclusion({ fact, figure, figureLabel, because, tone }) {
  return `<div class="c-concl${tone ? ` t-${esc(tone)}` : ''}">
    <div class=c-concl-f>${esc(fact)}</div>
    ${figure ? `<div class=c-concl-n><b>${esc(figure)}</b>${
      figureLabel ? `<em>${esc(figureLabel)}</em>` : ''}</div>` : ''}
    ${because ? `<p class=c-concl-w>${esc(because)}</p>` : ''}
  </div>`;
}

/* Exported because a lens uses it. Amount and Panel were declared in Phase 1
   and called by nothing, so they are gone — a component with no caller is a
   guess about the future, and it will be the wrong guess. */
window.C = {
  esc, rupees, plural, Conclusion,
  Status, Metric, MetricRow, Disclosure, Section, Row, ContextChrome,
  DataTable, EmptyState, LoadingState, ErrorState, StateSpine,
  SubjectHeader, LensStrip,
};
