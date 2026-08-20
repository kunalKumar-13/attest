/* ATTEST — case file console.
 *
 * No reconciliation logic lives here. Every verdict, rupee, constraint and edge
 * on screen is computed by the engine and fetched from /api, including the
 * geometry of the flow diagram — laid out in Python so it is testable and so two
 * clients cannot draw the same proof differently.
 */
'use strict';

const S = { run: null, rows: [], view: [], i: 0, q: '', vf: '', cache: new Map() };
const el = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
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

/* --------------------------------------------------------------------- run */

async function run() {
  el('run').innerHTML = '<span class=spin></span>Running';
  el('ledger').innerHTML = '<div class=empty><span class=spin></span>normalise · block<br>match · solve · verify</div>';
  S.cache.clear();
  S.run = await api(`/api/run?n=${el('size').value}`);
  S.rows = await api(`/api/rows?run=${S.run.run_id}`);
  el('run').textContent = 'Run';
  renderTop(); apply(); S.i = 0; open_();
}

function renderTop() {
  const s = S.run, m = s.money, c = s.counts, T = s.processed_paise || 1;
  el('m-proc').textContent = rs(s.processed_paise, true);
  el('s-proc').textContent = `${s.settlements.toLocaleString()} settlements · ${s.orders.toLocaleString()} orders`;
  el('m-post').textContent = rs(m.PROVEN, true);
  el('s-post').textContent = `${c.PROVEN} proven`;
  el('b-post').style.width = (m.PROVEN / T * 100).toFixed(2) + '%';
  el('m-held').textContent = rs(m.AMBIGUOUS + m.CONTRADICTED, true);
  el('s-held').textContent = `${c.AMBIGUOUS} ambiguous · ${c.CONTRADICTED} contradicted`;
  el('b-held').style.width = ((m.AMBIGUOUS + m.CONTRADICTED) / T * 100).toFixed(2) + '%';
  el('m-wrong').textContent = s.wrong;
  el('s-wrong').textContent = `precision ${s.precision.toFixed(3)} · this seed`;
  el('b-wrong').style.width = Math.max(s.wrong / s.settlements * 100, 0.6).toFixed(2) + '%';
  el('b-wrong').style.background = s.wrong ? 'var(--warn)' : 'var(--ok)';
  el('barmeta').innerHTML = `${s.run_id} · seed ${s.seed} · <b>${s.seconds}s</b> · ` +
    `exact <b>${(s.exact * 100).toFixed(1)}%</b> · precision <b>${s.precision.toFixed(3)}</b> · ` +
    `blocking ceiling <b>${s.blocking_ceiling.toFixed(3)}</b>`;
}

/* ------------------------------------------------------------------ ledger */

function apply() {
  const q = S.q.toLowerCase();
  S.view = S.rows.filter(r => (!S.vf || r.verdict === S.vf) &&
    (!q || r.id.includes(q) || r.date.includes(q)));
  el('count').textContent = `${S.view.length}/${S.rows.length}`;
  paint();
}

const gly = g => `<span class=gly>${g.map(v =>
  `<i class="${v === 1 ? 'y' : v === 0 ? 'n' : 'x'}"></i>`).join('')}</span>`;

function paint() {
  if (!S.view.length) return void (el('ledger').innerHTML = '<div class=empty>no rows</div>');
  el('ledger').innerHTML = S.view.map((r, i) => `<div class="row${i === S.i ? ' sel' : ''}" data-i=${i}>
    <span class=id>${r.id.replace('setl_', '')}</span>${gly(r.glyph)}
    <span class=amt>${rs(r.amount)}</span>
    <span class="vd v-${r.verdict}">${r.verdict.slice(0, 4)}</span></div>`).join('');
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
  const r = S.view[S.i];
  if (!r) return void (el('right').innerHTML = '<div class=empty>no selection</div>');
  paint();
  let d = S.cache.get(r.id);
  if (!d) { d = await api(`/api/settlement?run=${S.run.run_id}&id=${r.id}`); S.cache.set(r.id, d); }
  if (S.view[S.i]?.id !== r.id) return;
  el('right').innerHTML = caseFile(d);
}

function caseFile(d) {
  const p = d.proofs[0];
  const gate = d.postable
    ? `<div class="gate y"><span class="b ok">AUTO-POST ELIGIBLE</span>
       <span class=w>Exactly one explanation satisfies every constraint, and the
       kernel re-derived it from source records.</span></div>`
    : `<div class="gate n"><span class="b warn">POSTING BLOCKED</span>
       <span class=w>${d.verdict === 'AMBIGUOUS'
         ? `${d.proofs.length} explanations satisfy every constraint. Arithmetic cannot choose between them, so the engine does not.`
         : 'No subset of any candidate window satisfies the amount constraint.'}</span></div>`;

  const hero = p ? `<div class=hero>
    <h4>Evidence</h4>
    <div class=hint>Ribbon width is value. ${p.orders.length} orders flow into the
      settlement; fees leave it; the credit lands on the right.</div>
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
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key;
  if (k === 'j' || k === 'ArrowDown') { e.preventDefault(); move(1); }
  else if (k === 'k' || k === 'ArrowUp') { e.preventDefault(); move(-1); }
  else if (k === 'g') { S.i = 0; open_(); }
  else if (k === 'G') { S.i = S.view.length - 1; open_(); }
  else if (k === '/') { e.preventDefault(); el('filter').focus(); }
  else if (k === '1') setVF('PROVEN');
  else if (k === '2') setVF('AMBIGUOUS');
  else if (k === '3') setVF('CONTRADICTED');
  else if (k === '0') setVF('');
  else if (k === 'Enter') run();
});
run();
