/* ATTEST — case file console.
 *
 * No reconciliation logic lives here. Every verdict, rupee, constraint and edge
 * on screen is computed by the engine and fetched from /api, including the
 * geometry of the flow diagram — laid out in Python so it is testable and so two
 * clients cannot draw the same proof differently.
 */
'use strict';

const S = { mode: 'control', sub: null, att: null, evdemo: null, events: null, obs: null, review: 15000, exposure: 10000000, pol: null, run: null, rows: [], view: [], i: 0, q: '', vf: '', cache: new Map() };
const el = id => document.getElementById(id);
const MAC = /Mac|iP(hone|ad)/.test(navigator.platform || navigator.userAgent);
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const SHORT = {
  MULTIPLE_VALID_ASSIGNMENTS: 'multi', NO_VALID_ASSIGNMENT: 'none',
  UNKNOWN_ADJUSTMENT: 'adj', REFUND_MISMATCH: 'refund', CHARGEBACK: 'cb',
  PARTIAL_SETTLEMENT: 'split', MISSING_TRANSACTION: 'missing',
  DUPLICATE_AMOUNT: 'dup', TIMING_MISMATCH: 'timing',
  INSUFFICIENT_EVIDENCE: 'insuff', SEARCH_SPACE_UNCERTAIN: 'local',
  DATA_QUALITY: 'data',
};
const VC = { PROVEN: 'var(--ok)', AMBIGUOUS: 'var(--warn)', CONTRADICTED: 'var(--dead)' };

/* Indian grouping — 4738219 paise shown as "4,738,219" reads as the wrong
   magnitude to the person whose money it is. */
function rs(paise, whole) {
  const neg = paise < 0, n = Math.abs(paise), p = n % 100;
  let r = String(Math.floor(n / 100));
  if (r.length > 3) {
    let h = r.slice(0, -3); const t = r.slice(-3), a = [];
    while (h.length > 2) { a.unshift(h.slice(-2)); h = h.slice(0, -2); }
    r = (h ? [h] : []).concat(a, [t]).join(',');
  }
  return (neg ? '−' : '') + '₹' + (whole ? r : r + '.' + String(p).padStart(2, '0'));
}
const api = p => fetch(p).then(r => r.json());
const cap = t => t ? t[0].toUpperCase() + t.slice(1) : t;
const plural = (n, one, many) =>
  `${n.toLocaleString()} ${n === 1 ? one : (many || one + 's')}`;
window.ATTEST_rs = rs;

/* One guard for every async path in the app. D15 and §30. */
const GUARD = new AsyncResourceGuard('attest');
let BOARD = null;

/* --------------------------------------------------------------------- run */

async function run() {
  el('run').innerHTML = '<span class=spin></span>Running';
  el('ledger').innerHTML = '<div class=empty><span class=spin></span>normalise · block<br>match · solve · verify</div>';
  S.cache.clear();
  S.run = await api(`/api/run?n=${el('size').value}`);
  S.rows = await api(`/api/rows?run=${S.run.run_id}`);
  el('run').textContent = 'Run';
  GUARD.invalidateAll();
  renderTop(); apply(); S.i = 0;
  // Stay where the user was. Re-running a portfolio is a data refresh, not a
  // navigation, and dropping them back to Attention loses their place — which
  // is most annoying on exactly the screens people re-run from.
  go(S.mode, S.screen);
}

function renderTop() {
  const s = S.run;
  el('barmeta').innerHTML = `${s.run_id} · seed ${s.seed} · <b>${s.seconds}s</b> · ` +
    `exact <b>${(s.exact * 100).toFixed(1)}%</b> · precision <b>${s.precision.toFixed(3)}</b> · ` +
    `blocking ceiling <b>${s.blocking_ceiling.toFixed(3)}</b>` +
    (s.provenance ? ` · <b>${s.provenance.rules_version}</b>` : '');
}

/* ------------------------------------------------------------- mode router
 * Four verbs, per §17. The navigation states what the product is for, and depth
 * lives inside a mode rather than beside it — which is what stops the sidebar
 * growing to eighteen items as features arrive.
 */
const MODES = {
  control: {
    views: [['attention', 'Attention', true], ['actions', 'Act', true],
            ['overview', 'Overview', true]],
    draw: { attention: () => drawControl(), actions: () => drawActions(),
            overview: () => drawBoard() },
  },
  investigate: {
    views: [['cases', 'Settlements', false], ['exceptions', 'Exceptions', true],
            ['changed', 'What changed', true], ['trail', 'AI trail', true],
            ['ask', 'Ask ATTEST', true]],
    draw: { cases: () => open_(), exceptions: () => drawExceptions(),
            changed: () => drawChanged(), trail: () => drawTrail(),
            ask: () => drawAsk(null) },
  },
  verify: {
    views: [['accuracy', 'Accuracy', true], ['observatory', 'Failures', true],
            ['trust', 'Trust centre', true]],
    draw: { accuracy: () => drawAccuracy(), observatory: () => drawObservatory(),
            trust: () => drawTrust() },
  },
  automate: {
    views: [['policy', 'Policy', true], ['journal', 'Journal', true],
            ['agents', 'Agents', true], ['sources', 'Sources', true],
            ['events', 'Live events', true]],
    draw: { policy: () => loadPolicy(), journal: () => drawJournal(),
            agents: () => drawAgents(), sources: () => drawIntegrations(),
            events: () => drawEvents() },
  },
};

function go(mode, view) {
  const M = MODES[mode];
  if (!M) return;
  const names = M.views.map(v => v[0]);
  S.mode = mode;
  S.screen = names.includes(view) ? view : names[0];
  S.sub = null;

  document.querySelectorAll('.mode').forEach(b => {
    const on = b.dataset.mode === mode;
    b.classList.toggle('on', on);
    b.setAttribute('aria-selected', String(on));
  });
  el('subnav').innerHTML = M.views.map(([k, label]) =>
    `<button class="sub${k === S.screen ? ' on' : ''}" data-view="${k}">${label}</button>`
  ).join('');
  el('panes').classList.toggle('solo', !!M.views.find(v => v[0] === S.screen)[2]);
  // The bar advertised j/k/filter/verdict on every screen; those only bind on
  // the settlements ledger. A shortcut hint that does nothing is worse than no
  // hint, because it teaches the wrong thing.
  const led = mode === 'investigate' && S.screen === 'cases';
  el('barkeys').innerHTML =
    `<span><kbd>${MAC ? '⌘' : 'ctrl'}</kbd><kbd>K</kbd> go anywhere</span>
     <span><kbd>↵</kbd> re-run</span>`
    + (led ? `<span><kbd>j</kbd><kbd>k</kbd> move</span><span><kbd>/</kbd> filter</span>
      <span><kbd>1</kbd><kbd>2</kbd><kbd>3</kbd> verdict</span><span><kbd>0</kbd> all</span>` : '');
  if (!S.run) { el('right').innerHTML = '<div class=empty>press Run</div>'; return; }
  M.draw[S.screen]();
}

document.querySelector('.modes').addEventListener('click', e => {
  const b = e.target.closest('.mode');
  if (b) go(b.dataset.mode);
});
el('subnav').addEventListener('click', e => {
  const b = e.target.closest('.sub');
  if (b) go(S.mode, b.dataset.view);
});

/* ------------------------------------------------------------------ control
 * Financial state, then what needs a person. In that order and nothing between
 * them — the audit's finding was that a board reports state and never says what
 * requires attention, which leaves the prioritising to the user's eye.
 */
async function drawControl() {
  if (S.sub) return drawState(S.sub);
  const s = S.run, m = s.money;
  const acct = (m.PROVEN + (s.settled_paise || 0)) / Math.max(s.processed_paise, 1);

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>Financial control</h1>
      <span class=sub>${s.settlements.toLocaleString()} settlements ·
        ${s.orders.toLocaleString()} orders · seed ${s.seed}</span></div>
    <div class=fs>
      <div class=metric><span class=k>processed</span>
        <span class=v>${rs(s.processed_paise, true)}</span>
        <span class=s>today</span></div>
      <div class=metric><span class=k>proven</span>
        <span class=v style="color:var(--st-proven)">${rs(m.PROVEN, true)}</span>
        <span class=s>${plural(s.counts.PROVEN, 'settlement')}</span></div>
      <div class=metric><span class=k>uncertain</span>
        <span class=v style="color:var(--st-ambiguous)">${rs(m.AMBIGUOUS, true)}</span>
        <span class=s>${plural(s.counts.AMBIGUOUS, 'settlement')}</span></div>
      <div class=metric><span class=k>contradicted</span>
        <span class=v style="color:var(--st-contradicted)">${rs(m.CONTRADICTED, true)}</span>
        <span class=s>${plural(s.counts.CONTRADICTED, 'settlement')}</span></div>
      <div class=metric><span class=k>protected</span>
        <span class=v>${rs(s.processed_paise - m.PROVEN, true)}</span>
        <span class=s>refused deliberately · ${(acct * 100).toFixed(0)}% accounted for</span></div>
    </div>
    <div id=att><div class=empty><span class=spin></span>building the queue…</div></div>
  </div>`;

  const a = await api(`/api/attention?run=${S.run.run_id}`);
  S.att = a;
  // Guard on the screen, not the mode: Overview lives in this same mode, so a
  // late attention fetch would otherwise paint over the board.
  if (S.screen !== 'attention' || S.sub) return;

  el('att').innerHTML = `
    <div class=att-hd><h2>${a.total_items} things need your attention</h2>
      <span class=amt>${rs(a.total_paise, true)} at stake</span></div>
    ${a.groups.map(g => `<section class=grp>
      <div class=grp-hd><b>${esc(g.label)}</b>
        <span class=n>${g.count}</span>
        <span class=tot>${rs(g.amount_paise, true)}</span></div>
      <p class=lede>${esc(g.why)}</p>
      ${g.items.map(it => `<button class=att data-sid="${it.id}">
        <i class="dot st-${it.verdict}"></i>
        <span class=id>${it.id.replace('setl_', '')}</span>
        <span class=amt>${rs(it.amount_paise)}</span>
        <span class=line>${esc(it.line)}</span>
        <span class=go>${esc(g.action)} →</span></button>`).join('')}
      ${g.count > g.items.length
        ? `<div class=more>+ ${g.count - g.items.length} more in this group</div>` : ''}
    </section>`).join('')}`;

  el('att').querySelectorAll('.att').forEach(b =>
    b.onclick = () => { S.sub = b.dataset.sid; drawState(b.dataset.sid); });
}

/* ------------------------------------------------------------ financial state
 * The signature screen. It answers four questions in order and refuses to open
 * with a status: what we know, why, what would resolve it, what ATTEST will do.
 * A settlement is one instance of financial state, and this is what looking at
 * one should feel like.
 */
async function drawState(sid) {
  el('right').innerHTML = '<div class=empty><span class=spin></span>loading financial state…</div>';
  const g = await GUARD.run(sid, () =>
    api(`/api/settlement?run=${S.run.run_id}&id=${sid}`), id => S.sub === id);
  if (!g.ok) return;
  const d = g.value;
  const ex = d.exception, st = ex && ex.settled, p = d.proofs[0];
  const j = d.judgement || {};

  // The intersection is what every surviving explanation agrees on, so it is
  // settled whichever one is right. Stating it as "27 of 31" would be arithmetic
  // nonsense — the explanations do not share a denominator.
  const known = st && st.order_ids.length ? `
      <div class=kn><b>${st.order_ids.length} orders</b> appear in
        ${d.proofs.length === 1 ? 'the explanation' : `all ${d.proofs.length} explanations`}</div>
      <div class=kn><b>${rs(st.net_paise)}</b> is settled whichever explanation is right</div>
      <div class=kn><b class=warn>${rs(st.disputed_paise)}</b> depends on which one is,
        across ${st.differing_orders} orders that differ between them</div>`
    : p ? `
      <div class=kn><b>${p.orders.length}</b> orders explain this credit exactly</div>
      <div class=kn><b>${rs(p.net_paise)}</b> accounted for</div>
      <div class=kn><b>${rs(p.residual_paise)}</b> residual against a bound of
        ±${p.tolerance} paise</div>`
    : `<div class=kn>No combination of the ${d.space ? d.space.candidates : 0}
        candidate orders reaches this credit</div>
       ${ex && ex.partial ? `<div class=kn><b>${rs(ex.partial.net_paise)}</b> explained,
        <b class=warn>${rs(ex.partial.unexplained_paise)}</b> unexplained</div>` : ''}`;

  // Every explanation is the same size and the same amount, so a bar of the
  // total says nothing. What separates them is where they disagree, so the bar
  // is split: shared orders, then the ones only this explanation uses.
  const shared = new Set(st ? st.order_ids : []);
  const widest = Math.max(...d.proofs.map(q => q.orders.length), 1);
  const cands = d.proofs.length > 1
    ? d.proofs.map((q, i) => {
        const uniq = q.orders.filter(o => !shared.has(o.id)).length;
        const both = q.orders.length - uniq;
        return `<div class=cand>
          <span class=cl>${String.fromCharCode(65 + i)}</span>
          <span class=cbar>
            <i class=cs style="width:${(both / widest * 100).toFixed(1)}%"></i>
            <i class=cu style="width:${(uniq / widest * 100).toFixed(1)}%"></i></span>
          <span class=cn>${both} shared${uniq ? ` + ${uniq}` : ''}</span>
          <span class=cv>${rs(q.net)}</span>
          <span class="cok ok">within ±${q.tolerance}p</span></div>`;
      }).join('')
    : '';

  el('right').innerHTML = `<div class=state>
    <button class=back id=back>← Attention</button>
    <div class=state-hd>
      <div class=mono style="color:var(--dim3);font-size:var(--t-label)">${esc(d.id)}</div>
      <div class=state-amt>${rs(d.amount)}</div>
      <div class="st st-${d.verdict}" style="margin-top:var(--s-3)">${d.verdict}</div>
      ${d.proofs.length > 1
        ? `<div class=state-sub>${d.proofs.length} valid explanations</div>` : ''}
    </div>

    <section class=blockq><h4>What we know</h4><div class=knw>${known}</div></section>

    ${cands ? `<section class=blockq><h4>Why</h4>
      <div class=cands>${cands}</div>
      <p class=qnote>Every one of these satisfies the amount constraint exactly.
        Arithmetic cannot distinguish them, so the engine does not.</p></section>` : ''}

    ${d.graph && d.graph.nodes.length ? `<section class=blockq>
      <h4>Composition${d.proofs.length > 1 ? ' · explanation A' : ''}</h4>
      ${flow(d.graph)}</section>` : ''}

    <section class=blockq><h4>What would resolve this</h4>
      <div class=res>${ex ? esc(ex.next_step) : 'Nothing outstanding.'}</div>
      ${d.space ? `<div class=qnote>${esc(d.space.claim)}</div>` : ''}</section>

    <section class=blockq><h4>What ATTEST will do</h4>
      <div class=will>
        ${(j.reasons || []).map(r => `<div class=w1><i></i>${esc(r)}</div>`).join('')}
        <div class=w1><i class="${j.decision === 'AUTO_POST' ? 'y' : ''}"></i>
          <b>${j.decision === 'AUTO_POST' ? 'Post automatically' : 'No automatic action'}</b></div>
        ${j.decision !== 'AUTO_POST'
          ? `<div class=w1><i></i>Preserve the exception</div>
             <div class=w1><i></i>Continue to accept evidence</div>` : ''}
      </div>
      <div class=acts>
        <button class="btn go" id=st-inv>Investigate</button>
        <button class=btn id=st-full>Full case file</button>
      </div></section>
  </div>`;

  el('back').onclick = () => { S.sub = null; drawControl(); };
  el('st-inv').onclick = () => runInvestigation(d.id);
  el('st-full').onclick = () => {
    const i = S.view.findIndex(r => r.id === d.id);
    if (i >= 0) { S.i = i; go('investigate'); }
  };
}


/* ------------------------------------------------------------------ ledger */

/* --------------------------------------------------------------- filtering
 * A small query language rather than a rack of dropdowns. The product is
 * already a command line in two other places, and a filter you can type is a
 * filter you can save, name and hand to someone else — which is the whole point
 * of the saved views below it.
 *
 *   >5000        amount at or above ₹5,000        <500   at or below
 *   unexplained  something is unaccounted for     clean  nothing is
 *   high         severity HIGH                    local  uniqueness not global
 *   proven       verdict, any of the four         multi  reason substring
 *   anything else matches the id, date, layer or reason as text
 */
const VERDICTS = ['PROVEN', 'AMBIGUOUS', 'CONTRADICTED', 'INSUFFICIENT'];

function matches(r, token) {
  const t = token.toLowerCase();
  let m;
  if ((m = t.match(/^>=?(\d+)$/))) return r.amount >= +m[1] * 100;
  if ((m = t.match(/^<=?(\d+)$/))) return r.amount <= +m[1] * 100;
  if (t === 'unexplained') return r.unexplained > 0;
  if (t === 'clean') return !r.unexplained;
  if (['high', 'medium', 'low'].includes(t)) return (r.severity || '').toLowerCase() === t;
  if (t === 'local') return (r.layer || '').includes('/r') && r.verdict === 'PROVEN';
  const v = VERDICTS.find(x => x.toLowerCase().startsWith(t) && t.length >= 3);
  if (v) return r.verdict === v;
  return (r.id + ' ' + r.date + ' ' + (r.layer || '') + ' ' + (r.reason || ''))
    .toLowerCase().includes(t);
}

function apply() {
  const tokens = S.q.trim().split(/\s+/).filter(Boolean);
  S.view = S.rows.filter(r =>
    (!S.vf || r.verdict === S.vf) && tokens.every(t => matches(r, t)));
  el('count').textContent = `${S.view.length}/${S.rows.length}`;
  if (S.i >= S.view.length) S.i = Math.max(S.view.length - 1, 0);
  paint();
  paintViews();
}

/* ------------------------------------------------------------- saved views
 * A filter is only worth typing once. These persist across sessions because a
 * reconciliation is a recurring job, and the query someone worked out at
 * month-end is the one they want again next month.
 */
const VIEWS_KEY = 'attest.views.v1';

function savedViews() {
  try { return JSON.parse(localStorage.getItem(VIEWS_KEY) || '[]'); }
  catch { return []; }
}

function writeViews(v) {
  try { localStorage.setItem(VIEWS_KEY, JSON.stringify(v.slice(0, 24))); }
  catch { /* private mode; the views are a convenience, not state */ }
}

//: Shipped starting points. Not stored, so they cannot be deleted and cannot
//: drift — they are examples of the language as much as they are filters.
const BUILTIN_VIEWS = [
  { name: 'Money at risk', q: 'unexplained', vf: '' },
  { name: 'Large ambiguity', q: '>50000 ambiguous', vf: '' },
  { name: 'Locally unique', q: 'local', vf: 'PROVEN' },
  { name: 'Contradicted', q: '', vf: 'CONTRADICTED' },
];

function paintViews() {
  const host = el('views');
  if (!host) return;
  const saved = savedViews();
  const active = v => v.q === S.q.trim() && (v.vf || '') === (S.vf || '');
  host.innerHTML =
    BUILTIN_VIEWS.concat(saved).map((v, i) => `<button class="vw${active(v) ? ' on' : ''}"
        data-i="${i}" title="${esc(v.q || 'no filter')}">${esc(v.name)}${
        i >= BUILTIN_VIEWS.length ? '<i data-del="' + (i - BUILTIN_VIEWS.length) + '">×</i>' : ''
      }</button>`).join('')
    + `<button class="vw add" id=vw-save title="Save the current filter">+ save</button>`;
}

function bindViews() {
  const host = el('views');
  if (!host) return;
  host.addEventListener('click', e => {
    const del = e.target.closest('i[data-del]');
    if (del) {
      e.stopPropagation();
      const v = savedViews(); v.splice(+del.dataset.del, 1); writeViews(v); paintViews();
      return;
    }
    if (e.target.closest('#vw-save')) {
      const q = S.q.trim();
      if (!q && !S.vf) return;
      const name = (prompt('Name this view', q || S.vf) || '').trim();
      if (!name) return;
      const v = savedViews();
      v.unshift({ name, q, vf: S.vf || '' });
      writeViews(v); paintViews();
      return;
    }
    const b = e.target.closest('.vw');
    if (!b || b.id === 'vw-save') return;
    const all = BUILTIN_VIEWS.concat(savedViews());
    const v = all[+b.dataset.i];
    if (!v) return;
    S.q = v.q; S.vf = v.vf || '';
    el('filter').value = v.q;
    document.querySelectorAll('#tabs b').forEach(x =>
      x.classList.toggle('on', (x.dataset.v || '') === (v.vf || '')));
    S.i = 0; apply(); open_();
  });
}

const gly = g => `<span class=gly>${g.map(v =>
  `<i class="${v === 1 ? 'y' : v === 0 ? 'n' : 'x'}"></i>`).join('')}</span>`;

function paint() {
  if (!S.view.length) return void (el('ledger').innerHTML = '<div class=empty>no rows</div>');
  el('ledger').innerHTML = S.view.map((r, i) => `<div class="row${i === S.i ? ' sel' : ''}" data-i=${i}>
    <span class=id>${r.id.replace('setl_', '')}</span>${gly(r.glyph)}
    <span class=amt>${rs(r.amount)}</span>
    <span class="vd v-${r.verdict}">${r.verdict.slice(0, 4)}</span>
    <span class=rc title="${esc(r.reason || '')}">${r.unexplained
      ? `<b class=warn>${rs(r.unexplained, true)}</b>`
      : (r.reason ? SHORT[r.reason] || '' : '')}</span></div>`).join('');
  el('ledger').querySelector('.row.sel')?.scrollIntoView({ block: 'nearest' });
}

/* -------------------------------------------------------------- flow chart
 * A Sankey. Width carries value, so composition is readable without reading a
 * number: one order dominating a settlement looks different from thirty even
 * ones, and both look different from a settlement whose fees are eating it.
 * Geometry comes from the API; this only paints it.
 */
function flow(g) {
  if (!g.nodes.length) return '';
  const W = 860, H = g.height, PAD = 66;
  const X = f => PAD + f * (W - PAD * 2);
  const byId = Object.fromEntries(g.nodes.map(n => [n.id, n]));
  const set = byId.settlement, bank = byId.bank;
  if (!set || !bank) return '';

  const lanes = g.nodes.filter(n => n.kind === 'order' || n.kind === 'remainder');
  const total = lanes.reduce((a, n) => a + n.paise, 0) || 1;

  // Ribbons stack on the settlement bar in the same order as the lanes, so the
  // eye can follow a single order across without tracing a line.
  const span = lanes.reduce((a, n) => a + n.h, 0) || 1;
  let acc = set.y;
  const ribbons = lanes.map(n => {
    // Scaled so the ribbons exactly fill the settlement bar: a ribbon that
    // changes width in flight would be drawing value that does not exist.
    const h = (n.h / span) * set.h;
    const x1 = X(0) + 8, x2 = X(set.x), mid = (x1 + x2) / 2;
    const y1 = n.y, y2 = acc; acc += h;
    const d = `M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2} ` +
              `L${x2},${y2 + h} C${mid},${y2 + h} ${mid},${y1 + n.h} ${x1},${y1 + n.h} Z`;
    const dim = n.kind === 'remainder';
    return `<path d="${d}" fill="url(#${dim ? 'ribd' : 'rib'})" opacity="${dim ? .28 : .62}">
      <title>${n.label} · ${rs(n.paise)}</title></path>`;
  }).join('');

  const laneRects = lanes.map(n => n.kind === 'remainder' ? `
    <rect x="${X(0)}" y="${n.y}" width="8" height="${Math.max(n.h, 2)}" rx="2"
      fill="none" stroke="var(--dim2)" stroke-width="1" stroke-dasharray="2 2"/>
    <text x="${X(0) - 8}" y="${n.y + n.h / 2}" text-anchor=end class=fl-lbl
      style="fill:var(--dim2)">${esc(n.label)}</text>
    <text x="${X(0) - 8}" y="${n.y + n.h / 2 + 11}" text-anchor=end class=fl-cap>COLLAPSED</text>` : `
    <rect x="${X(0)}" y="${n.y}" width="8" height="${Math.max(n.h, 2)}" rx="2" fill="var(--acc)"/>
    ${n.h > 8 ? `<text x="${X(0) - 8}" y="${n.y + n.h / 2 + 3}" text-anchor="end"
      class=fl-lbl>${esc(n.label)}</text>` : ''}`).join('');

  const fee = byId.fee;
  const feeArt = fee ? (() => {
    const x1 = X(set.x), x2 = X(fee.x), y1 = set.y + 12, y2 = fee.y + 12;
    return `<path d="M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}"
      stroke="var(--warn)" stroke-width="1.4" fill=none opacity=".62" stroke-dasharray="3 3"/>
      <text x="${x2 - 6}" y="${y2 + 3}" text-anchor=end class=fl-amt
        style="fill:var(--warn)">−${rs(-fee.paise)}</text>
      <text x="${x2 - 6}" y="${y2 + 15}" text-anchor=end class=fl-cap>FEES + GST</text>`;
  })() : '';

  const bars = `
    <rect x="${X(set.x)}" y="${set.y}" width="11" height="${set.h}" rx="3" fill="var(--ok)" opacity=".82"/>
    <text x="${X(set.x) + 18}" y="${set.y + 13}" class=fl-amt>${rs(set.paise)}</text>
    <text x="${X(set.x) + 18}" y="${set.y + 25}" class=fl-cap>NET OF ${esc(set.sub.toUpperCase())}</text>
    <path d="M${X(set.x) + 11},${set.y + set.h / 2 - 16} C${X(0.8)},${set.y + set.h / 2 - 16}
      ${X(0.8)},${set.y + set.h / 2 - 16} ${X(1) - 11},${set.y + set.h / 2 - 16}
      L${X(1) - 11},${set.y + set.h / 2 + 16} C${X(0.8)},${set.y + set.h / 2 + 16}
      ${X(0.8)},${set.y + set.h / 2 + 16} ${X(set.x) + 11},${set.y + set.h / 2 + 16} Z"
      fill="url(#rib2)" opacity=".55"/>
    <rect x="${X(1) - 11}" y="${set.y}" width="11" height="${set.h}" rx="3" fill="var(--acc)" opacity=".85"/>
    <text x="${X(1) - 18}" y="${set.y + 13}" text-anchor=end class=fl-amt>${rs(bank.paise)}</text>
    <text x="${X(1) - 18}" y="${set.y + 25}" text-anchor=end class=fl-cap>BANK CREDIT</text>`;

  return `<svg class=flow viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
    <defs>
      <linearGradient id=rib x1=0 x2=1><stop offset=0 stop-color="var(--acc)" stop-opacity=".55"/>
        <stop offset=1 stop-color="var(--ok)" stop-opacity=".5"/></linearGradient>
      <linearGradient id=rib2 x1=0 x2=1><stop offset=0 stop-color="var(--ok)" stop-opacity=".55"/>
        <stop offset=1 stop-color="var(--acc)" stop-opacity=".55"/></linearGradient>
      <linearGradient id=ribd x1=0 x2=1><stop offset=0 stop-color="var(--dim2)" stop-opacity=".5"/>
        <stop offset=1 stop-color="var(--dim2)" stop-opacity=".35"/></linearGradient>
    </defs>
    ${ribbons}${laneRects}${feeArt}${bars}
    <text x="${X(0)}" y="14" class=fl-cap>ORDERS</text></svg>`;
}

/* --------------------------------------------------------------- case file */

async function open_() {
  if (S.mode !== 'investigate') return;
  const r = S.view[S.i];
  if (!r) return void (el('right').innerHTML = '<div class=empty>no selection</div>');
  paint();
  let d = S.cache.get(r.id);
  if (!d) { d = await api(`/api/settlement?run=${S.run.run_id}&id=${r.id}`); S.cache.set(r.id, d); }
  if (S.view[S.i]?.id !== r.id) return;
  el('right').innerHTML = caseFile(d);
  const b = el('inv');
  if (b) b.onclick = () => runInvestigation(d.id);
}

/* --------------------------------------------------------- investigation
 * §32, and the place the disabled loop belongs. It is measured at precision
 * 0.521 and may not resolve anything, so this runs it and throws the verdict
 * away, keeping only the record of what was proposed and why it was refused.
 *
 * §16 is right that this is the stronger product. A model whose wrong answers
 * are visible and labelled is more useful than one whose right answers cannot
 * be told apart from its wrong ones.
 */
async function runInvestigation(sid) {
  const b = el('inv');
  if (b) b.innerHTML = '<span class=spin></span>investigating';
  const t = await api(`/api/investigate?run=${S.run.run_id}&id=${sid}`);
  // The selection can move while this is in flight — a filter, a j/k, a click.
  // Attaching a trail computed for one settlement to another's case file would
  // be a fabricated audit record, which is worse than showing nothing.
  if (S.view[S.i]?.id !== sid || S.mode !== 'work') return;
  const host = document.querySelector('.case');
  if (!host || !t.events || host.querySelector('.inv')) return;

  const rows = t.events.map(e => `<div class=ev-row>
    <span class="who ${e.actor}">${e.actor}</span>
    <span>${esc(e.detail)}${e.lens ? `<span class=lens>${esc(e.lens)}</span>` : ''}
      ${e.unexplained_paise ? `<div class=res>residual ${rs(e.unexplained_paise)} unexplained</div>` : ''}
    </span></div>`).join('');

  const el_ = document.createElement('div');
  el_.className = 'inv';
  el_.innerHTML = `<div class=hd><h4>Investigation trail</h4>
      <span class=st>AI RESOLUTION DISABLED</span></div>
    ${rows}
    <div class=foot>The verdict is unchanged: this ran, and its conclusion was
      discarded. ${esc(t.note)}</div>`;
  const gate = host.querySelector('.gate');
  gate.parentNode.insertBefore(el_, gate.nextSibling);
  el_.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  if (b) b.textContent = 'Investigate →';
}

function caseFile(d) {
  const p = d.proofs[0];
  const j = d.judgement || {};
  const gate = j.decision === 'AUTO_POST'
    ? `<div class="gate approved"><span class="b ok">AUTO-POST APPROVED</span>
       <span class=w>${esc((j.reasons || []).slice(-1)[0] || '')}</span></div>`
    : `<div class="gate refused">
       <span class="b warn">WHY ATTEST REFUSED</span>
       <ol class=whys>${(j.reasons || ['no judgement recorded'])
         .map(x => `<li>${esc(x)}</li>`).join('')}</ol>
       ${d.exception ? `<div class=nxt><b>Next step</b> ${esc(d.exception.next_step)}</div>` : ''}
       <div class=nxt style="border:0;padding-top:9px;margin-top:6px">
         <button class=btn id=inv>Investigate →</button></div>
       </div>`;

  const hero = p ? `<div class=hero>
    <h4>Evidence</h4>
    <div class=hint>Ribbon width is value: orders flow in on the left, fees and
      tax leave in the middle, and the bank credit lands on the right.</div>
    ${flow(d.graph)}</div>` : '';

  const ledger = p ? `<div class=blk><h4>Composition</h4><div class=lg>
    <div class=l><span class=a>gross · ${p.orders.length} orders</span><span class=b>${rs(p.gross)}</span></div>
    <div class=l><span class=a>fees + GST</span><span class="b neg">−${rs(p.fee)}</span></div>
    <div class=l><span class=a>adjustments</span><span class=b>${p.adjustment ? rs(p.adjustment) : '₹0.00'}</span></div>
    <div class="l t"><span class=a>net</span><span class=b>${rs(p.net)}</span></div>
    <div class=l><span class=a>bank credit</span><span class=b>${rs(d.amount)}</span></div>
    <div class=l><span class=a>residual</span><span class=b>${rs(p.residual)}</span></div>
    <div class=l><span class=a>bound · ${p.orders.length} × 1 paisa</span><span class=b>±${p.tolerance} paise</span></div>
    <div class=l><span class=a>bound consumed</span><span class=b>${p.tolerance ? ((Math.abs(p.residual) / p.tolerance) * 100).toFixed(0) : 0}%</span></div>
  </div></div>` : '';

  const ex = d.exception, st = ex && ex.settled;
  const settled = st && st.order_ids.length ? `<div class=blk>
    <h4>What is already settled</h4>
    <div class=lg>
      <div class=l><span class=a>${st.order_ids.length} orders in ${st.certain ? 'every' : 'every known'} explanation</span><span class=b>${rs(st.net_paise)}</span></div>
      <div class=l><span class=a>${st.differing_orders} orders in dispute</span><span class="b neg">${rs(st.disputed_paise)}</span></div>
    </div>
    <div class=note>${st.certain
      ? 'These orders belong to this settlement whichever explanation turns out to be right. That part is not in dispute.'
      : 'The enumerator reached its cap, so these are common to the explanations found rather than to all of them — likely settled, not certainly.'}
      ${esc(ex.next_step)}</div></div>` : '';

  const partial = ex && ex.partial ? `<div class=blk>
    <h4>Closest partial explanation</h4>
    <div class=lg>
      <div class=l><span class=a>${ex.partial.order_ids.length} orders explain</span><span class=b>${rs(ex.partial.net_paise)}</span></div>
      <div class=l><span class=a>unexplained</span><span class="b neg">${rs(ex.partial.unexplained_paise)}</span></div>
    </div>
    <div class=note>${esc(ex.next_step)}</div></div>` : '';

  const sp = d.space ? `<div class=blk><h4>Search space</h4>
    <div class=lg>
      <div class=l><span class=a>input universe</span><span class=b>${d.space.universe.toLocaleString()}</span></div>
      ${d.space.reductions.map(r => `<div class=l>
        <span class=a>− ${esc(r.name)} <i class="${r.deterministic ? 'ok' : 'warn'}">${r.deterministic ? 'deterministic' : 'heuristic'}</i></span>
        <span class=b>${r.removed.toLocaleString()}</span></div>`).join('')}
      <div class="l t"><span class=a>candidates</span><span class=b>${d.space.candidates.toLocaleString()}</span></div>
    </div>
    <div class=note><b class="${d.space.integrity === 'validated' ? 'ok' : 'warn'}">${d.space.integrity.toUpperCase()}</b> — ${esc(d.space.claim)}</div>
    ${d.coincidence ? `<div class=note style="padding-top:0">
      <b class="${d.coincidence.cheapness === 'sparse' ? 'ok' : 'warn'}">${d.coincidence.cheapness.toUpperCase()} neighbourhood</b>
      — ${esc(d.coincidence.note)}</div>` : ''}
    </div>` : '';

  const checks = d.checks.length ? `<div class=blk><h4>Constraints</h4>
    ${d.checks.map(c => `<div class=ck><div class=t>
      <span class="mk ${c.ok ? 'ok' : 'warn'}">${c.ok ? '✓' : '✗'}</span>
      <span>${c.name}</span></div><div class=d>${esc(c.detail)}</div></div>`).join('')}</div>` : '';

  const orders = p ? `<div class=blk><h4>Orders in this explanation</h4><div class=ords>
    <div class="o h"><span>order</span><span>method</span><span>gross</span><span>net</span></div>
    ${p.orders.map(o => `<div class=o><span>${o.id.replace('ord_', '')}</span>
      <span class=mth>${o.method}</span><span>${rs(o.gross)}</span><span>${rs(o.net)}</span></div>`).join('')}
  </div></div>` : '';

  const alts = d.proofs.length > 1 ? `<div class=blk><h4>Competing explanations · ${d.proofs.length}</h4>
    ${d.proofs.map((q, i) => `<div class=alt><span class=nn>#${i + 1}</span>
      <span class=kk>${q.orders.length} orders</span>
      <span class=n style="width:118px;text-align:right">${rs(q.net)}</span>
      <span class=ii>${q.orders.map(o => o.id.replace('ord_', '')).join(' ')}</span></div>`).join('')}
    <div class=note>Every one of these satisfies the amount constraint exactly.
    Choosing between them needs evidence beyond the amount — a reference, a
    counterparty — not a better search.</div></div>` : '';

  const core = (!p && d.unsat_core.length) ? `<div class=blk><h4>Contradiction</h4>
    ${d.unsat_core.map(c => `<div class=ck><div class=t><span class="mk warn">✗</span>
      <span>${esc(c)}</span></div></div>`).join('')}
    <div class=note>The engine names the constraint that fails rather than forcing
    a plausible answer.</div></div>` : '';

  return `<div class=case>
    <div class=chd><span class=sid>${d.id}</span>
      <span class="pill v-${d.verdict}">${d.verdict}</span>
      <span class="amt v-${d.verdict}">${rs(d.amount)}</span></div>
    <div class=csub>${d.date} · utr ${d.utr || '—'} · resolved by ${esc(d.layer)}
      · ${d.exhaustive ? 'search exhaustive' : 'search capped'}</div>
    ${gate}${hero}
    <div class=cols>${ledger}${checks}</div>
    ${settled}${partial}${sp}
    ${orders}${alts}${core}
    <div class=note style="padding:14px 0 0">Every value above is recomputed from
    the order records by <code>verdict.check</code> — 28 lines, sharing no code
    with the solver that produced the proof. A bug in the prover can cost recall;
    it cannot post a wrong entry.</div>
  </div>`;
}

/* ------------------------------------------------------------------ input */

function move(n) {
  if (!S.view.length) return;
  S.i = Math.max(0, Math.min(S.view.length - 1, S.i + n)); open_();
}
function setVF(v) {
  S.vf = v; S.i = 0;
  [...el('tabs').children].forEach(b => b.classList.toggle('on', b.dataset.v === v));
  apply(); open_();
}
el('run').onclick = run;
async function drawIntegrations() {
  el('right').innerHTML = '<div class=empty><span class=spin></span>reading source state…</div>';
  const run = S.run ? S.run.run_id : '';
  const [d, sy] = await Promise.all([
    api(`/api/integrations?run=${run}`),
    api(`/api/sync?run=${run}`),
  ]);
  if (S.screen !== 'sources') return;
  const a = d.active;
  const dot = ok => `<i class=dot2 style="background:${ok ? 'var(--ok)' : 'var(--dim3)'}"></i>`;
  const pill = (t, c) => `<span class=pillx style="color:${c}">${t}</span>`;

  // Sync health belongs here rather than on a tab of its own: "what am I
  // reading" and "is it still current" are two halves of one question, and
  // splitting them lets a reader answer the first and forget the second.
  const sync = `<section class=sync>
    <div class=sync-h>
      <span class="st st-${sy.owed.length ? 'AMBIGUOUS' : 'PROVEN'}">
        ${sy.owed.length ? 'RE-VERIFICATION OWED' : 'UP TO DATE'}</span>
      <span class=sync-run>${esc(sy.run_id || '—')} ·
        ${esc((sy.started_at || '').replace('T', ' ').replace('+00:00', ' UTC'))}</span>
      <span class=sync-ev>${plural(sy.events_since_run, 'delivery', 'deliveries')}
        since it decided</span>
    </div>
    <p class=lede>${esc(sy.freshness)}</p>
    ${sy.owed.length ? `
      <div class=fs style="border:0;padding:0;margin:var(--s-4) 0 var(--s-3)">
        <div class=metric><span class=k>owed</span>
          <span class=v style="color:var(--st-ambiguous)">${rs(sy.owed_paise, true)}</span>
          <span class=s>${plural(sy.owed.length, 'settlement')} decided before
            evidence that names them</span></div>
      </div>
      <div class=evs>${sy.owed.map(o => `<div class=ev>
        <span class="et mono">${esc(o.id)}</span>
        <span class="ek mono">${rs(o.amount_paise)}</span>
        <span class=ed>named by ${esc(o.because)}</span>
        <span class="est duplicate">unrevised</span></div>`).join('')}</div>` : ''}
    <p class=lede style="margin-top:var(--s-3)">${esc(sy.note)}</p>
  </section>`;

  el('right').innerHTML = `<div class=ing>
    <h2>Sources</h2>
    ${sync}
    <p class=lead>What ATTEST is reading, and what it is not. A source that is not
      connected says so; the one in use says what it actually is. Nothing here
      reports live unless it was pulled from a connected account.</p>

    <div class="src on">
      <div class=h>${dot(true)}<b>Active source</b>
        ${pill('SYNTHETIC', 'var(--warn)')}
        <span class=bd-sp style="flex:1"></span>
        ${pill('NOT LIVE', 'var(--dim2)')}</div>
      <div class=b>
        <div class=kv><span>records</span><b>${a.records.orders.toLocaleString()} orders ·
          ${a.records.settlements.toLocaleString()} settlements ·
          ${a.records.credits.toLocaleString()} bank credits</b></div>
        <div class=kv><span>coverage</span><b>${esc(a.coverage)}</b></div>
        <div class=kv><span>orders linked to a settlement</span>
          <b class=warn>${(a.linked_fraction * 100).toFixed(0)}%</b></div>
        ${a.provenance ? Object.entries(a.provenance).map(([k, v]) =>
          `<div class=kv><span>${k.replace('_version', '')} version</span><b>${esc(v)}</b></div>`).join('') : ''}
        <div class=kv><span>sync</span><b>${esc(d.sync.freshness)}</b></div>
        <div class=note>${esc(a.note)}</div>
      </div>
    </div>

    ${d.providers.map(p => `<div class=src>
      <div class=h>${dot(p.connected)}<b>${esc(p.label)}</b>
        ${p.connected ? pill('CONNECTED', 'var(--ok)') : pill('NOT CONNECTED', 'var(--dim2)')}
        <span style="flex:1"></span>
        ${p.linked_fraction ? `<span class=bd-ss>${(p.linked_fraction * 100).toFixed(0)}% of records
          arrive linked to a settlement</span>` : ''}</div>
      <div class=b>
        ${p.endpoints.length ? `<div class=kv><span>reads from</span><b style="flex:1">
          ${p.endpoints.map(e => `<span class=ep>${esc(e)}</span>`).join('')}</b></div>` : ''}
        <div class=kv><span>data accessed</span><b>${p.reads.map(esc).join(', ') || '—'}</b></div>
        <div class=kv><span>data written</span>
          <b class="${p.writes.length ? 'warn' : 'ok'}">${p.writes.length ? p.writes.join(', ') : 'none — read only'}</b></div>
        <div class=kv><span>requires</span><b>${p.requires.map(esc).join(', ')}</b></div>
        <div class=note>${esc(p.note)}${p.why ? `<br><br>${esc(p.why)}` : ''}</div>
      </div></div>`).join('')}
  </div>`;
}

function boardContext() {
  return {
    summary: S.run, rows: S.rows, policy: S.pol, events: S.events,
    observatory: S.obs,
    open: sid => {
      const i = S.view.findIndex(r => r.id === sid);
      if (i < 0) return;
      S.i = i; go('investigate', 'cases');
    },
  };
}

async function refreshEvents() {
  try { S.events = await api('/api/events'); } catch { /* feed is optional */ }
  try { if (!S.obs) S.obs = await api('/api/observatory'); } catch { /* optional */ }
  // The board reports how many proven settlements the policy actually posts,
  // which needs the policy. Fetched here rather than on the policy screen so
  // the board is never the only surface quoting an unpriced number.
  try {
    if (!S.pol && S.run) {
      S.pol = await api(`/api/policy?run=${S.run.run_id}&review=${S.review}&exposure=${S.exposure}`);
    }
  } catch { /* optional */ }
}

function drawBoard() {
  el('right').innerHTML = '<div class=boardwrap id=boardhost></div>';
  const host = el('boardhost');
  if (!BOARD) BOARD = new ATTESTBoard.Board(host, boardContext());
  else { BOARD.host = host; BOARD.setContext(boardContext()); }
  BOARD.render();
  // The feed is fetched after the board paints, so an unavailable feed cannot
  // delay the widgets that do not need it.
  refreshEvents().then(() => { if (S.screen === 'overview') BOARD.render(); });
  host.addEventListener('click', e => {
    const row = e.target.closest('.bd-row.link');
    if (row) boardContext().open(row.dataset.sid);
  });
}

/* ------------------------------------------------------------------ ask
 * §34: not a chatbot. No bubbles, no avatar, no sidebar. A command line over
 * the run's own records, where every claim carries the rows that make it
 * checkable — because a statement with nothing behind it is a thing a model can
 * produce whether or not it happened.
 */
const ASKS = [
  'why is setl_000089 unresolved',
  'which settlements are unsafe to auto-post',
  'what is settled but not proven',
  'show unexplained amounts above 100',
  'show high value ambiguous settlements',
  'show contradicted settlements',
];

async function runAsk(text) {
  if (!S.run || !text.trim()) return;
  drawAsk(null, text, true);
  const a = await api(`/api/ask?run=${S.run.run_id}&q=${encodeURIComponent(text)}`);
  drawAsk(a, text);
}

function drawAsk(a, text = '', busy = false) {
  const body = busy
    ? '<div class=empty><span class=spin></span>querying the records…</div>'
    : a ? `<div class=ans>
        <div class=hd><b>${esc(a.headline)}</b>
          <span class=kind>${a.understood ? esc(a.query.kind) : 'not understood'}</span></div>
        ${a.facts.map(f => `<div class=ft>${esc(f.text)}
          ${f.settlement_ids.length ? `<div class=ev>${f.settlement_ids.slice(0, 24)
            .map(id => `<b data-sid="${id}">${id.replace('setl_', '')}</b>`).join('')}
            ${f.settlement_ids.length > 24 ? `<b style="cursor:default">+${f.settlement_ids.length - 24}</b>` : ''}</div>` : ''}
          </div>`).join('')}
        <div class=q>executed as ${esc(JSON.stringify(a.query))}</div>
      </div>` : '';

  el('right').innerHTML = `<div class=ask>
    <h2>Ask ATTEST</h2>
    <p class=lead>Questions become a <b>structured query</b> that runs against this
      run's records. The translation could be a model; the execution never is — so
      a bad reading answers the wrong question, it cannot invent a number. Every
      claim carries the rows behind it.</p>
    <div class=qbar><span class=pr>&gt;</span>
      <input id=q value="${esc(text)}" placeholder="ask about this run…" autocomplete=off></div>
    <div class=chips>${ASKS.map(x => `<span class=chip>${esc(x)}</span>`).join('')}</div>
    ${body}</div>`;

  const inp = el('q');
  inp.focus();
  inp.setSelectionRange(inp.value.length, inp.value.length);
  inp.onkeydown = e => { if (e.key === 'Enter') runAsk(inp.value); e.stopPropagation(); };
  el('right').querySelectorAll('.chip').forEach(c =>
    c.onclick = () => runAsk(c.textContent));
  el('right').querySelectorAll('.ev b[data-sid]').forEach(b =>
    b.onclick = () => {
      const i = S.view.findIndex(r => r.id === b.dataset.sid);
      if (i >= 0) { S.i = i; go('investigate', 'cases'); }
    });
}

/* ------------------------------------------------------------- simulator
 * §36. The point is not the numbers at any one setting — it is that the
 * threshold was never chosen. Move what an analyst's hour is worth and the
 * boundary between automate and check moves on its own, because it is only ever
 * the solution to P(error) x cost(wrong) < cost(review). The frontier makes that
 * visible rather than asserting it.
 */
const STEPS = [2500, 5000, 10000, 15000, 25000, 50000, 100000, 250000, 500000];

async function loadPolicy() {
  if (!S.run) return;
  el('right').innerHTML = '<div class=empty><span class=spin></span>evaluating the portfolio at every costing…</div>';
  S.pol = await api(`/api/policy?run=${S.run.run_id}&review=${S.review}&exposure=${S.exposure}`);
  drawPolicy();
}

async function repriceOnly() {
  const p = await api(`/api/policy?run=${S.run.run_id}&review=${S.review}&exposure=${S.exposure}`);
  S.pol = { ...p, frontier: S.pol.frontier };
  drawPolicy();
}

function frontier(f, current) {
  const W = 900, H = 200, L = 54, R = 16, T = 14, B = 30;
  const xs = f.map(p => Math.log10(p.review_paise));
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const maxAuto = Math.max(...f.map(p => p.auto_post), 1);
  const X = v => L + ((Math.log10(v) - x0) / (x1 - x0 || 1)) * (W - L - R);
  const Y = v => T + (1 - v / maxAuto) * (H - T - B);

  const line = f.map((p, i) => `${i ? 'L' : 'M'}${X(p.review_paise).toFixed(1)},${Y(p.auto_post).toFixed(1)}`).join('');
  const area = line + `L${X(f[f.length - 1].review_paise).toFixed(1)},${H - B}L${X(f[0].review_paise).toFixed(1)},${H - B}Z`;
  const dots = f.map(p => `<circle cx="${X(p.review_paise).toFixed(1)}" cy="${Y(p.auto_post).toFixed(1)}"
     r="${Math.abs(p.review_paise - current) < 1 ? 4.5 : 2.5}"
     fill="${p.realised_loss_paise ? 'var(--warn)' : 'var(--ok)'}">
     <title>₹${(p.review_paise / 100).toLocaleString()} review → ${p.auto_post} auto-posted, ${rs(p.posted_paise, true)}, ${p.wrong_posts} wrong</title></circle>`).join('');
  const ticks = f.filter((_, i) => i % 2 === 0).map(p =>
    `<text x="${X(p.review_paise).toFixed(1)}" y="${H - 10}" text-anchor=middle class=fx>₹${(p.review_paise / 100).toLocaleString()}</text>`).join('');

  return `<svg class=front viewBox="0 0 ${W} ${H}" preserveAspectRatio=none>
    <defs><linearGradient id=fg x1=0 x2=0 y1=0 y2=1>
      <stop offset=0 stop-color="var(--ok)" stop-opacity=.24/>
      <stop offset=1 stop-color="var(--ok)" stop-opacity=0/></linearGradient></defs>
    <path d="${area}" fill="url(#fg)"/>
    <path d="${line}" fill=none stroke="var(--ok)" stroke-width=1.6 vector-effect=non-scaling-stroke/>
    ${dots}${ticks}
    <text x="6" y="${T + 8}" class=fx>${maxAuto}</text>
    <text x="6" y="${H - B}" class=fx>0</text>
    <text x="${L}" y="${T - 3}" class=fx>SETTLEMENTS AUTO-POSTED</text>
  </svg>`;
}

function drawPolicy() {
  const p = S.pol, n = p.settlements;
  const idx = STEPS.indexOf(S.review);
  const eidx = [1000000, 2500000, 5000000, 10000000, 25000000, 100000000].indexOf(S.exposure);
  const EXP = [1000000, 2500000, 5000000, 10000000, 25000000, 100000000];

  el('right').innerHTML = `<div class=pol>
    <h2>Auto-post policy</h2>
    <p class=lead>No threshold is configured here. A settlement posts itself when
      <b>P(error) × cost of a wrong posting &lt; cost of a human review</b>, so the
      boundary is whatever that inequality implies. Change what an analyst's hour is
      worth and it moves on its own.</p>

    <div class=sl>
      <div class=top><span class=nm>cost of a human review</span>
        <span class=val id=v-rev>${rs(S.review)}</span></div>
      <input type=range id=r-rev min=0 max=${STEPS.length - 1} step=1 value=${idx < 0 ? 3 : idx}>
      <div class=ends><span>₹25</span><span>₹5,000</span></div>
      <div class=why>An analyst's time to open a settlement, read the evidence and
        decide. Raise it and automating becomes cheaper than checking.</div>
    </div>

    <div class=sl>
      <div class=top><span class=nm>maximum exposure per settlement</span>
        <span class=val id=v-exp>${rs(S.exposure, true)}</span></div>
      <input type=range id=r-exp min=0 max=${EXP.length - 1} step=1 value=${eidx < 0 ? 3 : eidx}>
      <div class=ends><span>₹10,000</span><span>₹10,00,000</span></div>
      <div class=why>A hard ceiling above which a human looks regardless of the
        arithmetic — expected value is the wrong instrument for a tail a merchant
        cannot absorb.</div>
    </div>

    <div class=out>
      <div class=c><div class=k>auto-posted</div>
        <div class="v ok">${p.auto_post}</div>
        <div class=s>${(p.auto_post / n * 100).toFixed(1)}% of ${n} · ${rs(p.posted_paise, true)}</div></div>
      <div class=c><div class=k>human review</div>
        <div class="v warn">${p.review}</div>
        <div class=s>${(p.review / n * 100).toFixed(1)}% of the queue</div></div>
      <div class=c><div class=k>protected</div>
        <div class=v>${rs(p.protected_paise, true)}</div>
        <div class=s>refused, deliberately</div></div>
      <div class=c><div class=k>realised loss</div>
        <div class="v ${p.realised_loss_paise ? 'warn' : 'ok'}">${rs(p.realised_loss_paise, true)}</div>
        <div class=s>${p.wrong_posts} wrong post${p.wrong_posts === 1 ? '' : 's'} · vs ${rs(p.expected_loss_paise, true)} predicted</div></div>
    </div>

    <div class=blk><h4>Coverage against review cost</h4>
      <div style="padding:14px 17px">${frontier(p.frontier, S.review)}</div>
      <div class=note style="padding-top:0">Each point is the whole portfolio
        re-decided at that costing. Green means no wrong post at that setting;
        amber means the automation bought a real error. ${esc(p.calibration)}.</div>
    </div>

    <div class=blk><h4>Measured risk by stratum</h4>
      <div class=stt style="padding:4px 17px 12px">
        ${p.strata.map(s => `<div class=r><span>${esc(s.key)}</span>
          <span>${s.wrong}/${s.total} observed</span>
          <span class="${s.priced > 0.2 ? 'warn' : 'ok'}">priced ${s.priced.toFixed(4)}</span></div>`).join('')}
      </div>
      <div class=note style="padding-top:0">Priced at the 95% Wilson upper bound,
        not the observed rate. A stratum below the observation floor is not priced
        at all and posts nothing — being wrong about your own error rate is
        acceptable in exactly one direction.</div>
    </div>
  </div>`;

  el('r-rev').oninput = e => {
    S.review = STEPS[+e.target.value];
    el('v-rev').textContent = rs(S.review);
  };
  el('r-rev').onchange = repriceOnly;
  el('r-exp').oninput = e => {
    S.exposure = EXP[+e.target.value];
    el('v-exp').textContent = rs(S.exposure, true);
  };
  el('r-exp').onchange = repriceOnly;
}
// Theme is a viewer choice, remembered. Light is the default because a
// reconciliation console is read beside spreadsheets and mail more often than
// beside terminals.
const root = document.documentElement;
root.dataset.theme = localStorage.getItem('attest-theme') || 'light';
el('theme').onclick = () => {
  root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('attest-theme', root.dataset.theme);
  if (S.run) open_();
};
el('tabs').onclick = e => { const b = e.target.closest('b'); if (b) setVF(b.dataset.v); };
el('ledger').onclick = e => { const r = e.target.closest('.row'); if (r) { S.i = +r.dataset.i; open_(); } };
el('filter').addEventListener('input', e => { S.q = e.target.value; S.i = 0; apply(); open_(); });
el('filter').addEventListener('keydown', e => {
  if (e.key === 'Escape') { e.target.value = ''; S.q = ''; e.target.blur(); apply(); open_(); }
  e.stopPropagation();
});
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault(); openPalette(); return;
  }
  if (PAL.open) return;
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key;
  // The ledger keys move a selection that only exists on the settlements
  // screen. Firing them elsewhere silently re-filtered a list the user could
  // not see, which they then found already filtered when they returned.
  const onLedger = S.mode === 'investigate' && S.screen === 'cases';
  if (k === 'Enter') { run(); return; }
  if (!onLedger) return;
  if (k === 'j' || k === 'ArrowDown') { e.preventDefault(); move(1); }
  else if (k === 'k' || k === 'ArrowUp') { e.preventDefault(); move(-1); }
  else if (k === 'g') { S.i = 0; open_(); }
  else if (k === 'G') { S.i = S.view.length - 1; open_(); }
  else if (k === '/') { e.preventDefault(); el('filter').focus(); }
  else if (k === '1') setVF('PROVEN');
  else if (k === '2') setVF('AMBIGUOUS');
  else if (k === '3') setVF('CONTRADICTED');
  else if (k === '0') setVF('');
});

/* ------------------------------------------------------------ command palette
 * §57. Four modes and thirteen screens is a small enough product to navigate by
 * hand and a large enough one to be worth not having to. The palette is the
 * only place that enumerates every destination, which is deliberate: the top
 * bar states what the product is for, and this states what is in it.
 */
const PAL = { open: false, i: 0, hits: [] };

function commands() {
  const out = [];
  for (const [mode, M] of Object.entries(MODES)) {
    for (const [view, label] of M.views) {
      // No per-row hint: the group header is the mode, and repeating "why"
      // down four rows is noise where a distinguishing detail should be.
      out.push({
        group: `${mode[0].toUpperCase() + mode.slice(1)} · ${MODE_HINT[mode]}`,
        label, hint: '',
        run: () => go(mode, view),
      });
    }
  }
  out.push({ group: 'Action', label: 'Run reconciliation',
             hint: 'Enter', run: () => run() });
  out.push({ group: 'Action', label: 'Toggle theme', hint: '', run: () => el('theme').click() });
  for (const n of ['120', '250', '500', '1200']) {
    out.push({ group: 'Portfolio', label: `${n} settlements`, hint: 're-runs',
               run: () => { el('size').value = n; run(); } });
  }
  for (const v of BUILTIN_VIEWS.concat(savedViews())) {
    out.push({
      group: 'View', label: v.name, hint: v.q || v.vf.toLowerCase(),
      run: () => {
        S.q = v.q; S.vf = v.vf || '';
        go('investigate', 'cases');
        el('filter').value = v.q;
        document.querySelectorAll('#tabs b').forEach(x =>
          x.classList.toggle('on', (x.dataset.v || '') === (v.vf || '')));
        S.i = 0; apply(); open_();
      },
    });
  }
  if (S.att) {
    for (const g of S.att.groups) {
      for (const it of g.items.slice(0, 3)) {
        out.push({
          group: 'Needs attention', label: it.id,
          hint: `${rs(it.amount_paise)} · ${g.label.toLowerCase()}`,
          run: () => { go('control', 'attention'); S.sub = it.id; drawState(it.id); },
        });
      }
    }
  }
  return out;
}

const MODE_HINT = {
  control: 'what is happening', investigate: 'why',
  verify: 'can we prove it', automate: 'what is allowed',
};

function openPalette() {
  if (PAL.open) return;
  PAL.open = true; PAL.i = 0;
  const host = document.createElement('div');
  host.id = 'pal'; host.className = 'pal-wrap';
  host.innerHTML = `<div class=pal role=dialog aria-modal=true aria-label="Command palette">
    <input id=pal-q placeholder="Go to a screen, or run something…" autocomplete=off
      aria-label="Command" aria-controls=pal-list aria-expanded=true>
    <div id=pal-list role=listbox></div>
    <div class=pal-foot><kbd>↑</kbd><kbd>↓</kbd> move
      <kbd>↵</kbd> select <kbd>esc</kbd> close</div>
  </div>`;
  document.body.appendChild(host);

  const all = commands();
  const q = el('pal-q');

  const paint = () => {
    const t = q.value.trim().toLowerCase();
    PAL.hits = !t ? all : all.filter(c =>
      (c.group + ' ' + c.label + ' ' + c.hint).toLowerCase().includes(t));
    if (PAL.i >= PAL.hits.length) PAL.i = Math.max(PAL.hits.length - 1, 0);
    let last = '';
    el('pal-list').innerHTML = PAL.hits.length
      ? PAL.hits.map((c, i) => {
          const head = c.group !== last ? `<div class=pal-g>${esc(c.group)}</div>` : '';
          last = c.group;
          return head + `<div class="pal-i${i === PAL.i ? ' on' : ''}" data-i="${i}"
            role=option aria-selected="${i === PAL.i}">
            <span class=pal-l>${esc(c.label)}</span>
            <span class=pal-h>${esc(c.hint || '')}</span></div>`;
        }).join('')
      : '<div class=pal-none>Nothing matches.</div>';
    const on = el('pal-list').querySelector('.pal-i.on');
    if (on) on.scrollIntoView({ block: 'nearest' });
  };

  const choose = () => {
    const c = PAL.hits[PAL.i];
    closePalette();
    if (c) c.run();
  };

  q.addEventListener('input', () => { PAL.i = 0; paint(); });
  q.addEventListener('keydown', e => {
    e.stopPropagation();
    if (e.key === 'Escape') { closePalette(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); PAL.i = Math.min(PAL.i + 1, PAL.hits.length - 1); paint(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); PAL.i = Math.max(PAL.i - 1, 0); paint(); }
    else if (e.key === 'Enter') { e.preventDefault(); choose(); }
  });
  el('pal-list').addEventListener('click', ev => {
    const row = ev.target.closest('.pal-i');
    if (row) { PAL.i = +row.dataset.i; choose(); }
  });
  host.addEventListener('mousedown', ev => { if (ev.target === host) closePalette(); });

  paint();
  q.focus();
}

function closePalette() {
  const h = el('pal');
  if (h) h.remove();
  PAL.open = false;
}

bindViews();
run();

/* ------------------------------------------------------------------ verify
 * Three questions a reviewer actually asks, in the order they ask them: is it
 * accurate, where does it fail, and what decided. The audit found all three
 * scattered across widgets on a board where a reader had to already know what
 * to look for.
 */
async function drawAccuracy() {
  el('right').innerHTML = '<div class=empty><span class=spin></span>reading the benchmark…</div>';
  const t = await api(`/api/trust?run=${S.run ? S.run.run_id : ''}`);
  if (S.screen !== 'accuracy') return;
  const b = t.benchmark, g = t.gates;
  const pct = v => (v * 100).toFixed(1) + '%';

  const headline = [
    ['money wrongly auto-posted', rs(b.incorrectly_auto_posted_paise || 0, true),
     'across every evaluation seed', b.incorrectly_auto_posted_paise ? 'bad' : 'good'],
    ['proof precision', (b.proof_precision || 0).toFixed(3),
     `${b.proven || 0} proven, ${b.false_proofs || 0} of them wrong`, 'plain'],
    ['exact set recovery', pct(b.exact_set_recovery || 0),
     `${b.exact_sets || 0} settlements resolved to the exact order set`, 'plain'],
    ['value accounted for', pct(b.accounted_rate || 0),
     'proven, plus undisputed inside ambiguity', 'plain'],
  ];

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>Accuracy</h1>
      <span class=sub>${(b.evaluation_seeds || []).length || 5} held-out seeds ·
        pooled, not a best run</span></div>
    <div class=fs>
      ${headline.map(([k, v, s, tone]) => `<div class=metric>
        <span class=k>${k}</span>
        <span class=v style="color:${tone === 'good' ? 'var(--st-proven)'
          : tone === 'bad' ? 'var(--st-contradicted)' : 'var(--ink)'}">${v}</span>
        <span class=s>${s}</span></div>`).join('')}
    </div>

    <div class=att-hd><h2>Regression gates</h2>
      <span class=amt>${g.filter(x => x.state === 'pass').length}/${g.length} holding</span></div>
    <p class=lede>A gate compares this build to the recorded baseline. The
      first three are fatal — a breach fails the build. The last three are
      advisory on purpose: three documented decisions (D4, D8, D12) traded
      coverage for safety, and a gate that punished them would have argued for
      shipping them.</p>
    <div class=rgates>
      ${g.map(x => `<div class="rgate ${x.state}">
        <span class=gs>${x.state === 'pass' ? '✓' : x.state === 'fail' ? '✕'
          : x.state === 'warn' ? '!' : '—'}</span>
        <span class=gl>${esc(x.label)}
          ${x.fatal ? '<em>fatal</em>' : '<em class=adv>advisory</em>'}</span>
        <span class=gv>${x.value === null ? '—'
          : x.paise ? rs(x.value, true) : Number(x.value).toFixed(4)}</span>
        <span class=gb>base ${x.baseline === null ? '—'
          : x.paise ? rs(x.baseline, true) : Number(x.baseline).toFixed(4)}</span>
        <span class=gw>${esc(x.why)}</span></div>`).join('')}
    </div>

    ${b.note ? `<div class=bnote><b>Note</b>${esc(b.note)}</div>` : ''}
  </div>`;
}

async function drawObservatory() {
  el('right').innerHTML = '<div class=empty><span class=spin></span>loading failures…</div>';
  if (!S.obs) S.obs = await api('/api/observatory');
  if (S.screen !== 'observatory') return;
  const o = S.obs, es = o.entries || [];

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>Failure observatory</h1>
      <span class=sub>${o.count} recorded · ${o.refusals} of them cases where the
        fix was to ship less · ${o.words.toLocaleString()} words</span></div>
    <p class=lede>Every one of these was a real defect in a real build, and most
      were found by something other than a passing test. They are kept because a
      system that only records its successes cannot tell you where it is weak.
      The ones marked <b>refused</b> are the useful kind: a feature worked,
      measured worse than not having it, and was disabled rather than shipped
      because it demoed well.</p>
    <div class=fails>
      ${es.map(e => `<article class="fail${e.refusal ? ' ref' : ''}">
        <span class=fid>${esc(e.ref)}</span>
        <div class=fbody>
          <div class=fh><b>${esc(e.title)}</b>
            ${e.refusal ? '<span class=fsev>refused</span>' : ''}</div>
          <p class=fp>${esc(e.detail || e.headline)}</p>
          ${e.measurement ? `<p class="fp meas"><i></i>${esc(e.measurement)}</p>` : ''}
        </div>
      </article>`).join('')}
    </div>
    ${o.note ? `<div class=bnote><b>Note</b>${esc(o.note)}</div>` : ''}
  </div>`;
}

async function drawTrust() {
  el('right').innerHTML = '<div class=empty><span class=spin></span>reading provenance…</div>';
  const t = await api(`/api/trust?run=${S.run ? S.run.run_id : ''}`);
  if (S.screen !== 'trust') return;
  const p = t.provenance || {};

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>Trust centre</h1>
      <span class=sub>what decided, and under which rules</span></div>

    <section class=blockq><h4>Provenance of this run</h4>
      <p class=lede>A result without these is not reproducible whatever the seed
        says: the same data reconciled under a different fee schedule is a
        different answer to a different question. The solver version is a hash of
        the code that decides, so a change shows up whether or not anyone
        remembered to bump a number.</p>
      <div class=prov>
        ${Object.entries(p).map(([k, v]) => `<div class=prow>
          <span class=prk>${esc(k.replace('_version', ''))}</span>
          <span class="pv mono">${esc(v)}</span></div>`).join('')}
        <div class=prow><span class=prk>native kernel</span>
          <span class="pv mono">${t.solver.native ? 'attest_native (Rust)' : 'numpy fallback'}</span></div>
      </div></section>

    <section class=blockq><h4>Rules in force
        <span class="mono" style="color:var(--dim3);font-weight:400;font-size:var(--t-micro)">
          ${esc(t.rules.version)}</span></h4>
      <p class=lede>These are the rules, not a description of them — the version
        is a content hash of the rule set the engine ran. Change any rule and it
        changes, which is what makes a run's provenance meaningful rather than
        decorative.</p>
      <div class=rules>
        ${t.rules.described.map(x => `<div class=rl>
          <span class=rn>${esc(x.rule)}</span>
          <span class=rv>${esc(x.value)}</span>
          <span class=rw>${esc(x.why)}</span></div>`).join('')}
      </div></section>
  </div>`;
}

/* ----------------------------------------------------------------- automate */
async function drawAgents() {
  el('right').innerHTML = '<div class=empty><span class=spin></span>running the pipeline…</div>';
  const d = await api(`/api/agents?run=${S.run ? S.run.run_id : ''}`);
  if (S.screen !== 'agents') return;

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>Agent permissions</h1>
      <span class=sub>${d.roster.length} agents · ${d.blocked.length} capabilities
        held by none of them</span></div>

    <section class=blockq><h4>Granted to nothing</h4>
      <p class=lede>These are defined and refused rather than simply absent,
        because an absence is silent and a refusal is auditable. When an agent
        asks, the log says what it asked for and that it was denied — which is
        the record you want when someone asks what the automation tried to do.
        The engine posts entries, after a unique explanation has been
        kernel-checked and the policy has priced the risk. No agent is in that
        path.</p>
      <div class=blocked>${d.blocked.map(c =>
        `<span class=bl><i>✕</i>${esc(c)}</span>`).join('')}</div></section>

    <section class=blockq><h4>The pipeline, run against this portfolio</h4>
      <p class=lede>Agent → intent → evidence → verification → policy → action.
        Every stage can refuse. What follows is not a description of that path —
        it is that path, executed against the findings of the run you are
        looking at.</p>
      <div class=atts>
        ${d.attempts.map(a => `<article class="atmpt ${a.allowed ? 'ok' : 'no'}">
          <div class=ah><span class=an>${esc(a.agent)}</span>
            <span class=ai>wants to ${esc(a.intent)}</span>
            <span class="mono aj">${esc(a.subject)}</span>
            <span class="ares ${a.allowed ? 'y' : 'n'}">${a.allowed ? 'eligible' : 'refused'}</span></div>
          <div class=stg>${['capability', 'evidence', 'verification', 'policy', 'action']
            .map(name => {
              const st = a.steps.find(x => x.stage === name);
              const cls = !st ? 'never' : st.passed ? 'pass' : 'stop';
              return `<div class="sg ${cls}" title="${st ? esc(st.detail) : 'not reached'}">
                <i></i><span>${name}</span></div>`;
            }).join('')}</div>
          <div class=areason>${esc((a.steps[a.steps.length - 1] || {}).detail || '')}</div>
        </article>`).join('')}
      </div></section>

    <section class=blockq><h4>Roster</h4>
      <div class=rost>${d.roster.map(a => `<div class=ag>
        <div class=agn><b>${esc(a.name)}</b></div>
        <div class=agp>${esc(a.purpose)}</div>
        <div class=agc>${a.allowed.map(c => `<span class=cap>${esc(c)}</span>`).join('')}</div>
      </div>`).join('')}</div></section>
  </div>`;
}

async function drawEvents(keepDemo) {
  if (!keepDemo) S.evdemo = null;
  el('right').innerHTML = '<div class=empty><span class=spin></span>reading the event log…</div>';
  S.events = null;
  await refreshEvents();
  if (S.screen !== 'events') return;
  const xs = (S.events || { events: [] }).events || [];
  const d = S.evdemo;

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>Live events</h1>
      <span class=sub>${plural(xs.length, 'delivery', 'deliveries')} in the log</span></div>
    <p class=lede>Webhook deliveries, verified over the raw request bytes before
      anything is parsed, and de-duplicated on both the event id and a hash of the
      payload — an id that arrives twice with different contents is not the same
      event, and treating it as one is how a replay becomes a double posting.</p>

    <section class=blockq><h4>Demonstrate it</h4>
      <p class=lede>An empty log is honest and proves nothing. This sends four
        deliveries through the same verify, de-duplicate and scope path the HTTP
        endpoint uses — one valid, one exact replay, one reusing the id with a
        different amount, one altered after signing — and shows what the code
        returned for each.</p>
      <button class="btn go" id=ev-demo>${d ? 'Send four more' : 'Send four deliveries'}</button>
      ${d ? `<div class=evs style="margin-top:var(--s-4)">
        ${d.sent.map(c => `<div class=ev>
          <span class=et>sent</span>
          <span class=ed style="grid-column:span 2">${esc(c.case)}
            <em style="font-style:normal;color:var(--dim3)"> — ${esc(c.detail)}</em></span>
          <span class="est ${esc(c.status)}">${esc(c.status.replace(/_/g, ' '))}</span>
        </div>`).join('')}</div>
        <p class=lede style="margin-top:var(--s-3)">${esc(d.note)}</p>` : ''}
    </section>

    <section class=blockq><h4>Delivery log</h4>
      ${xs.length ? `<div class=evs>${xs.map(x => `<div class=ev>
        <span class=et>${esc((x.received_at || '').slice(11, 19))}</span>
        <span class="ek mono">${esc(x.kind || '')}</span>
        <span class=ed>${esc(x.detail || '')}${(x.affected || []).length
          ? ` — ${x.affected.map(esc).join(', ')}` : ''}</span>
        <span class="est ${esc(x.status || '')}">${esc((x.status || '').replace(/_/g, ' '))}</span>
      </div>`).join('')}</div>`
        : `<div class=empty>Nothing delivered yet.</div>`}
    </section>
  </div>`;

  el('ev-demo').onclick = async () => {
    const b = el('ev-demo');
    b.disabled = true; b.innerHTML = '<span class=spin></span>Sending';
    S.evdemo = await fetch(`/api/events/demo?run=${S.run.run_id}`,
                           { method: 'POST' }).then(r => r.json());
    // Re-render rather than patch: the log below is now four deliveries longer,
    // and updating only the heading left it reading "Nothing delivered yet".
    if (S.screen === 'events') drawEvents(true);
  };
}

async function drawExceptions() {
  el('right').innerHTML = '<div class=empty><span class=spin></span>grouping exceptions…</div>';
  const d = await api(`/api/exceptions?run=${S.run.run_id}`);
  if (S.screen !== 'exceptions') return;
  const gs = d.groups || d.reasons || [];

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>Exceptions</h1>
      <span class=sub>${gs.reduce((a, g) => a + (g.count || 0), 0)} across
        ${gs.length} reasons</span></div>
    <p class=lede>Grouped by why the engine stopped, not by what it was looking
      at. Two settlements that failed for the same reason are one problem;
      working them one at a time is how a queue stops being finishable.</p>
    <div class=exg>${gs.map(g => `<article class=exc>
      <div class=eh><b>${esc(g.label || g.reason || '')}</b>
        <span class=en>${g.count || 0}</span>
        <span class=ev2>${rs(g.amount_paise || 0, true)}</span></div>
      <p class=ew>${esc(g.why || g.description || '')}</p>
      ${g.next_step ? `<p class=ex-next><b>Next</b> ${esc(g.next_step)}</p>` : ''}
      ${(g.examples || []).length ? `<div class=exs>${g.examples.map(x =>
        `<button class=exl data-sid="${esc(x.id || x)}">${esc(x.id || x)}</button>`).join('')}</div>` : ''}
    </article>`).join('')}</div>
  </div>`;

  el('right').querySelectorAll('.exl').forEach(b => b.onclick = () => {
    const i = S.view.findIndex(r => r.id === b.dataset.sid);
    if (i >= 0) { S.i = i; go('investigate', 'cases'); }
  });
}

/* -------------------------------------------------------------- what changed
 * §19, §30. Reconciliation is a standing claim about a moving set of records,
 * so the morning question is not "what is the state" but "what changed, and
 * why". Both runs here are real: the earlier one is this portfolio with a
 * fraction of its orders withheld, as records that had not arrived yet.
 */
async function drawChanged() {
  el('right').innerHTML = `<div class=empty><span class=spin></span>
    reconciling the earlier book, then comparing…</div>`;
  const d = await api(`/api/whatchanged?run=${S.run.run_id}`);
  if (S.screen !== 'changed') return;

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>What changed</h1>
      <span class=sub>${d.changed} settlements moved · ${d.unchanged} held</span></div>
    <p class=lede>Two real runs, not a replay. The earlier one is this same
      portfolio with ${plural(d.withheld, 'order')} withheld — ${d.withheld_pct}% of
      the book, standing in for records that had not arrived yet — put through
      the whole engine. Every move below is then attributed by asking whether an
      order that appeared is actually load-bearing for the verdict that moved. An
      order that arrived but appears in none of the new explanations did not
      cause anything, and saying it did because it turned up at the same time is
      exactly the confident-sounding wrongness this engine exists to refuse.</p>

    <div class=fs>
      <div class=metric><span class=k>changed</span>
        <span class=v>${d.changed}</span>
        <span class=s>${rs(d.amount_paise, true)} of settlement value</span></div>
      <div class=metric><span class=k>held</span>
        <span class=v>${d.unchanged}</span>
        <span class=s>same verdict, same orders</span></div>
      <div class=metric><span class=k>unattributed</span>
        <span class=v style="color:${d.unattributed ? 'var(--st-contradicted)' : 'var(--st-proven)'}">
          ${d.unattributed}</span>
        <span class=s>${d.unattributed ? 'the inputs do not explain these'
          : 'every move traced to an input difference'}</span></div>
      <div class=metric><span class=k>orders</span>
        <span class=v>${d.orders_before.toLocaleString()} → ${d.orders_after.toLocaleString()}</span>
        <span class=s>the only difference between the runs</span></div>
    </div>

    ${d.groups.map(g => `<section class=grp>
      <div class=grp-hd><b>${esc(g.direction[0].toUpperCase() + g.direction.slice(1))}</b>
        <span class=n>${g.count}</span>
        <span class=tot>${rs(g.amount_paise, true)}</span></div>
      <p class=lede>${esc(d.meanings[g.direction] || '')}</p>
      ${g.items.map(it => `<button class=att data-sid="${it.id}">
        <span class=id>${it.id.replace('setl_', '')}</span>
        <span class=amt>${rs(it.amount_paise)}</span>
        <span class=move><i class="st st-${it.before}">${it.before.slice(0, 4)}</i>
          →<i class="st st-${it.after}">${it.after.slice(0, 4)}</i></span>
        <span class=line>${it.causes.length
          ? esc(it.causes[0].detail)
          : '<em>unattributed — no input difference accounts for this</em>'}</span>
        <span class=go>Open →</span></button>`).join('')}
      ${g.count > g.items.length
        ? `<div class=more>+ ${g.count - g.items.length} more</div>` : ''}
    </section>`).join('')}
  </div>`;

  el('right').querySelectorAll('.att').forEach(b => b.onclick = () => {
    const i = S.view.findIndex(x => x.id === b.dataset.sid);
    if (i >= 0) { S.i = i; go('investigate', 'cases'); }
  });
}

/* ---------------------------------------------------------------- journal
 * §21. A verdict is not the deliverable. Everything upstream exists to earn the
 * right to write an accounting entry, and this is where that right is exercised
 * or declined — with the balance check shown, because the check is the fee
 * model restated and an entry that does not balance means the rules disagree
 * with the records.
 */
async function drawJournal() {
  el('right').innerHTML = '<div class=empty><span class=spin></span>composing entries…</div>';
  const d = await api(`/api/journal?run=${S.run.run_id}`
    + `&review=${S.review}&exposure=${S.exposure}`);
  if (S.screen !== 'journal') return;
  const amt = v => v ? rs(v) : '';

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>Journal</h1>
      <span class=sub>${plural(d.entry_count, 'entry', 'entries')} ·
        ${plural(d.refusal_count, 'refusal')} · priced at
        ${rs(d.review_paise)} a review</span>
      <button class=btn id=j-pol style="margin-left:auto">Change the costing →</button></div>
    <p class=lede>The accounting ATTEST would write. Each entry is fixed by the
      fee model and nothing else — bank, gateway fee and recoverable GST against
      receivables discharged — so the balance check is <b>net = gross − fee −
      tax</b> restated. An entry that does not balance is a rule set disagreeing
      with the records, not a bookkeeping slip, and it is refused at construction
      rather than held for review.</p>

    <div class=fs>
      <div class=metric><span class=k>posted</span>
        <span class=v style="color:var(--st-proven)">${rs(d.posted_paise, true)}</span>
        <span class=s>${plural(d.entry_count, 'entry', 'entries')} at this policy</span></div>
      <div class=metric><span class=k>withheld</span>
        <span class=v>${rs(d.refused_paise, true)}</span>
        <span class=s>${plural(d.refusal_count, 'settlement')}, each with a reason</span></div>
      <div class=metric><span class=k>balance</span>
        <span class=v style="color:${d.balances ? 'var(--st-proven)' : 'var(--st-contradicted)'}">
          ${d.balances ? '✓' : '✕'}</span>
        <span class=s>${d.balances ? 'debits equal credits, to the paisa'
          : 'THE JOURNAL DOES NOT BALANCE'}</span></div>
    </div>

    <div class=att-hd><h2>Entries</h2>
      <span class=amt>${rs(d.posted_paise, true)}</span></div>
    ${d.entries.length ? d.entries.map(e => `<article class=je>
      <div class=je-h><span class="mono jid">${esc(e.settlement_id)}</span>
        <span class=jd>${esc(e.value_date)}</span>
        <span class="mono ju">UTR ${esc(e.utr)}</span>
        <span class=jn>${plural(e.orders, 'order')}</span>
        <span class=jt>${rs(e.total_paise)}</span></div>
      <table class=jl><thead><tr><th>Account</th><th>Debit</th><th>Credit</th>
        <th>Memo</th></tr></thead><tbody>
        ${e.lines.map(L => `<tr>
          <td>${esc(L.account)}</td>
          <td class=jnum>${amt(L.debit_paise)}</td>
          <td class=jnum>${amt(L.credit_paise)}</td>
          <td class=jmemo>${esc(L.memo)}</td></tr>`).join('')}
        <tr class=jsum><td>Balance</td>
          <td class=jnum>${rs(e.total_paise)}</td>
          <td class=jnum>${rs(e.total_paise)}</td>
          <td class=jmemo>residual ${e.residual_paise}p within
            ±${e.tolerance_paise}p</td></tr>
      </tbody></table>
      <div class="mono jprov">${esc(e.provenance)}</div>
    </article>`).join('')
      : `<div class=empty>Nothing clears the policy at ${rs(d.review_paise)} a
         review. Raise what a review is worth and entries appear — the boundary
         is the inequality, not a setting.</div>`}

    <div class=att-hd style="margin-top:var(--s-6)"><h2>Withheld</h2>
      <span class=amt>${rs(d.refused_paise, true)}</span></div>
    <p class=lede>Grouped by why, not by which. Two settlements withheld for the
      same reason are one problem.</p>
    ${d.refusals.map(g => `<div class=jref>
      <div class=jref-h><b>${esc(g.reason)}</b>
        <span class=n>${g.count}</span>
        <span class=tot>${rs(g.amount_paise, true)}</span></div>
      <div class=jref-e>${esc(g.example)}</div></div>`).join('')}
  </div>`;

  el('j-pol').onclick = () => go('automate', 'policy');
}

/* ------------------------------------------------------------ action centre
 * §31. Attention answers "what is stuck". This answers "what should I do
 * first", and those order differently: 197 ambiguous settlements is one action,
 * not 197, because every one of them is ambiguous for the same missing field.
 * Ranking by settlement value buries a one-line change worth eighty times more
 * than a week of individual work.
 */
async function drawActions() {
  el('right').innerHTML = '<div class=empty><span class=spin></span>ranking the work…</div>';
  const d = await api(`/api/actions?run=${S.run.run_id}`);
  if (S.screen !== 'actions') return;

  const KIND = {
    systemic: ['Systemic', 'var(--st-proven)'],
    rerun: ['Free re-run', 'var(--st-investigate)'],
    per_item: ['Per item', 'var(--st-ambiguous)'],
  };

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>What to do</h1>
      <span class=sub>${plural(d.actions.length, 'action')} ·
        ${plural(d.total_steps, 'piece')} of work ·
        ${rs(d.total_value_paise, true)} at stake</span></div>
    <p class=lede>Ranked by what each piece of work unlocks, not by how many
      settlements are waiting. Those order differently, and the difference
      matters: a queue that mixes "ask the gateway for one more column" with
      "find this ₹6,316 adjustment" and sorts both by amount puts a week of
      individual work above a one-line change worth eighty times more.</p>

    <div class=fs>
      <div class=metric><span class=k>one change unlocks</span>
        <span class=v style="color:var(--st-proven)">${rs(d.systemic_value_paise, true)}</span>
        <span class=s>systemic — at the source, once</span></div>
      <div class=metric><span class=k>free to try</span>
        <span class=v style="color:var(--st-investigate)">${rs(d.rerun_value_paise, true)}</span>
        <span class=s>no new data; the engine already holds it</span></div>
      <div class=metric><span class=k>hand-worked</span>
        <span class=v>${rs(d.per_item_value_paise, true)}</span>
        <span class=s>${plural(d.per_item_steps, 'record')} to find, one at a time</span></div>
    </div>

    ${d.actions.map((a, i) => {
      const [label, colour] = KIND[a.kind] || ['', 'var(--dim3)'];
      return `<article class="act ${a.kind}">
        <div class=act-h>
          <span class=act-n>${i + 1}</span>
          <b>${esc(cap(a.what.split(';')[0]))}</b>
          <span class=act-k style="color:${colour}">${label}</span>
        </div>
        <div class=act-m>
          <div><span class=k>unlocks</span><b>${rs(a.value_paise, true)}</b></div>
          <div><span class=k>across</span><b>${plural(a.settlements, 'settlement')}</b></div>
          <div><span class=k>work</span><b>${plural(a.steps, 'step')}</b></div>
          <div><span class=k>per step</span><b>${rs(a.leverage_paise, true)}</b></div>
        </div>
        <p class=act-r>${esc(a.rationale)}</p>
        <p class=act-w><span class=k>because</span> ${esc(a.why)}</p>
        <div class=exs>${a.examples.map(x =>
          `<button class=exl data-sid="${esc(x)}">${esc(x.replace('setl_', ''))}</button>`).join('')}
        </div>
      </article>`;
    }).join('')}
  </div>`;

  el('right').querySelectorAll('.exl').forEach(b => b.onclick = () => {
    const i = S.view.findIndex(x => x.id === b.dataset.sid);
    if (i >= 0) { S.i = i; go('investigate', 'cases'); }
  });
}

/* ------------------------------------------------------------ AI trail
 * §15, §16, D8. The hypothesis loop was built, measured twice and shipped
 * disabled. This screen runs it anyway and throws the verdict away, because a
 * model whose wrong answers are visible and labelled is worth more than one
 * whose right answers cannot be told apart from its wrong ones.
 */
const ACTOR = {
  model: ['Model', 'var(--st-investigate)'],
  solver: ['Solver', 'var(--st-ambiguous)'],
  engine: ['Engine', 'var(--dim2)'],
};

async function drawTrail(sid) {
  el('right').innerHTML = `<div class=empty><span class=spin></span>
    proposing, then trying to refute…</div>`;
  const d = await api(`/api/trail?run=${S.run.run_id}`
    + (sid ? `&id=${encodeURIComponent(sid)}` : ''));
  if (S.screen !== 'trail') return;
  const t = d.trail;

  el('right').innerHTML = `<div class=ctl>
    <div class=ctl-hd><h1>AI trail</h1>
      <span class=sub>resolution disabled · the loop still runs</span>
      <span class="st st-CONTRADICTED" style="margin-left:auto">NOT IN THE PATH</span></div>

    <p class=lede>${esc(d.what_it_still_does)}</p>

    <section class=blockq><h4>Why it is disabled</h4>
      <p class=lede>${esc(d.why_disabled)}</p>
      <pre class=meas>${esc(d.measurement.table)}</pre>
      ${d.measured && d.measured.precision !== undefined ? `
        <div class=tconc style="margin-bottom:var(--s-4)">
          <div class=tc><span class=k>re-measured precision</span>
            <b style="color:var(--st-contradicted)">${d.measured.precision.toFixed(3)}</b></div>
          <div class=tc><span class=k>resolved / wrong</span>
            <b>${d.measured.resolved} / ${d.measured.wrong}</b></div>
          <div class=tc><span class=k>three rounds vs one</span>
            <b>${d.measured.precision === d.measured.one_round.precision
              ? 'identical — exploring changed nothing' : 'differ'}</b></div>
          <div class=tc><span class=k>single-date pools</span>
            <b>${(d.measured.single_date_share * 100).toFixed(0)}%</b></div>
        </div>` : ''}
      <p class=lede>${esc(d.why_it_fails)}</p>
      ${d.measured && d.measured.note ? `<p class=lede>${esc(d.measured.note)}</p>` : ''}
      <div class="mono jprov">${esc(d.measurement.ref)} · ${esc(d.measurement.title)}</div>
    </section>

    <section class=blockq><h4>Run it</h4>
      <p class=lede>Pick an ambiguous settlement and watch the loop work. The
        largest is chosen by default, because that is the case most favourable
        to the feature.</p>
      <div class=exs>${d.candidates.map(c =>
        `<button class="exl${c.id === d.settlement_id ? ' on' : ''}"
           data-sid="${esc(c.id)}">${esc(c.id.replace('setl_', ''))}
           · ${rs(c.amount_paise, true)}</button>`).join('')}</div>
    </section>

    ${t ? `<section class=blockq>
      <h4>${esc(t.settlement_id)} · ${plural(t.events.length, 'step')}</h4>
      <div class=trail>${t.events.map(e => {
        const [name, colour] = ACTOR[e.actor] || [e.actor, 'var(--dim3)'];
        return `<div class="tev ${esc(e.act)}">
          <span class=tactor style="color:${colour}">${esc(name)}</span>
          <span class=tact>${esc(e.act)}</span>
          <span class=tdet>${esc(e.detail)}</span>
        </div>`;
      }).join('')}</div>

      <div class=tconc>
        <div class=tc><span class=k>engine's verdict</span>
          <b class="st st-${esc(t.verdict)}">${esc(t.verdict)}</b></div>
        <div class=tc><span class=k>loop would have said</span>
          <b class="st st-${esc(t.would_have_concluded)}">${esc(t.would_have_concluded)}</b></div>
        <div class=tc><span class=k>what changed</span>
          <b>nothing — the verdict was discarded</b></div>
      </div>
      <p class=lede>${esc(t.note)}</p>
    </section>` : '<div class=empty>No ambiguous settlement to investigate.</div>'}
  </div>`;

  el('right').querySelectorAll('.exl').forEach(b =>
    b.onclick = () => drawTrail(b.dataset.sid));
}
