/* ATTEST — case file console.
 *
 * No reconciliation logic lives here. Every verdict, rupee, constraint and edge
 * on screen is computed by the engine and fetched from /api, including the
 * geometry of the flow diagram — laid out in Python so it is testable and so two
 * clients cannot draw the same proof differently.
 */
'use strict';

const S = { mode: 'board', events: null, obs: null, review: 15000, exposure: 10000000, pol: null, run: null, rows: [], view: [], i: 0, q: '', vf: '', cache: new Map() };
const el = id => document.getElementById(id);
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
  if (S.mode === 'board') { el('board').style.color = 'var(--acc)'; drawBoard(); }
  else open_();
}

function renderTop() {
  const s = S.run, m = s.money, c = s.counts, T = s.processed_paise || 1;
  el('m-proc').textContent = rs(s.processed_paise, true);
  el('s-proc').textContent = `${s.settlements.toLocaleString()} settlements · ${s.orders.toLocaleString()} orders`;
  el('m-post').textContent = rs(m.PROVEN, true);
  el('s-post').textContent = `${c.PROVEN} proven`;
  el('b-post').style.width = (m.PROVEN / T * 100).toFixed(2) + '%';
  const acct = (m.PROVEN + (s.settled_paise || 0)) / T;
  el('m-held').textContent = rs(s.settled_paise || 0, true);
  el('s-held').textContent = `agreed by every explanation · ${(acct * 100).toFixed(1)}% accounted for`;
  el('b-held').style.width = (acct * 100).toFixed(2) + '%';
  el('k-held').textContent = 'settled, not proven';
  el('m-wrong').textContent = s.wrong;
  el('s-wrong').textContent = `precision ${s.precision.toFixed(3)} · this seed`;
  el('b-wrong').style.width = Math.max(s.wrong / s.settlements * 100, 0.6).toFixed(2) + '%';
  el('b-wrong').style.background = s.wrong ? 'var(--warn)' : 'var(--ok)';
  el('barmeta').innerHTML = `${s.run_id} · seed ${s.seed} · <b>${s.seconds}s</b> · ` +
    `exact <b>${(s.exact * 100).toFixed(1)}%</b> · precision <b>${s.precision.toFixed(3)}</b> · ` +
    `blocking ceiling <b>${s.blocking_ceiling.toFixed(3)}</b>` +
    (s.provenance ? ` · <b>${s.provenance.rules_version}</b>` : '');
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
  if (S.mode !== 'work') return;
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
    ? `<div class="gate y"><span class="b ok">AUTO-POST APPROVED</span>
       <span class=w>${esc((j.reasons || []).slice(-1)[0] || '')}</span></div>`
    : `<div class="gate n">
       <span class="b warn">WHY ATTEST REFUSED</span>
       <ol class=whys>${(j.reasons || ['no judgement recorded'])
         .map(x => `<li>${esc(x)}</li>`).join('')}</ol>
       ${d.exception ? `<div class=nxt><b>Next step</b> ${esc(d.exception.next_step)}</div>` : ''}
       <div class=nxt style="border:0;padding-top:9px;margin-top:6px">
         <button class=btn id=inv>Investigate →</button></div>
       </div>`;

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
el('integ').onclick = () => {
  S.mode = S.mode === 'integ' ? 'work' : 'integ';
  ['board', 'integ', 'ask', 'policy'].forEach(k =>
    el(k).style.color = k === S.mode ? 'var(--acc)' : '');
  S.mode === 'integ' ? drawIntegrations() : open_();
};

async function drawIntegrations() {
  el('right').innerHTML = '<div class=empty><span class=spin></span>reading source state…</div>';
  const d = await api(`/api/integrations?run=${S.run ? S.run.run_id : ''}`);
  const a = d.active;
  const dot = ok => `<i class=dot2 style="background:${ok ? 'var(--ok)' : 'var(--dim3)'}"></i>`;
  const pill = (t, c) => `<span class=pillx style="color:${c}">${t}</span>`;

  el('right').innerHTML = `<div class=ing>
    <h2>Sources</h2>
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

el('board').onclick = () => {
  S.mode = S.mode === 'board' ? 'work' : 'board';
  ['board', 'integ', 'ask', 'policy'].forEach(k =>
    el(k).style.color = k === S.mode ? 'var(--acc)' : '');
  S.mode === 'board' ? drawBoard() : open_();
};

function boardContext() {
  return {
    summary: S.run, rows: S.rows, policy: S.pol, events: S.events,
    observatory: S.obs,
    open: sid => {
      const i = S.view.findIndex(r => r.id === sid);
      if (i < 0) return;
      S.mode = 'work'; el('board').style.color = ''; S.i = i; open_();
    },
  };
}

async function refreshEvents() {
  try { S.events = await api('/api/events'); } catch { /* feed is optional */ }
  try { if (!S.obs) S.obs = await api('/api/observatory'); } catch { /* optional */ }
}

function drawBoard() {
  el('right').innerHTML = '<div class=boardwrap id=boardhost></div>';
  const host = el('boardhost');
  if (!BOARD) BOARD = new ATTESTBoard.Board(host, boardContext());
  else { BOARD.host = host; BOARD.setContext(boardContext()); }
  BOARD.render();
  // The feed is fetched after the board paints, so an unavailable feed cannot
  // delay the widgets that do not need it.
  refreshEvents().then(() => { if (S.mode === 'board') BOARD.render(); });
  host.addEventListener('click', e => {
    const row = e.target.closest('.bd-row.link');
    if (row) boardContext().open(row.dataset.sid);
  });
}

el('ask').onclick = () => {
  S.mode = S.mode === 'ask' ? 'work' : 'ask';
  el('ask').style.color = S.mode === 'ask' ? 'var(--acc)' : '';
  el('policy').style.color = ''; el('board').style.color = ''; el('integ').style.color = '';
  S.mode === 'ask' ? drawAsk(null) : open_();
};

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
      if (i >= 0) { S.mode = 'work'; el('ask').style.color = ''; S.i = i; open_(); }
    });
}

el('policy').onclick = () => {
  S.mode = S.mode === 'policy' ? 'work' : 'policy';
  el('policy').style.color = S.mode === 'policy' ? 'var(--acc)' : '';
  el('ask').style.color = ''; el('board').style.color = ''; el('integ').style.color = '';
  S.mode === 'policy' ? loadPolicy() : open_();
};

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
