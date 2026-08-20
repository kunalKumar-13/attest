/* ATTEST — investigation console.
 *
 * Holds no reconciliation logic. Every verdict, rupee and constraint on screen
 * is computed by the engine and fetched from /api. A front end that can decide a
 * verdict is one that can disagree with the ledger.
 *
 * The interaction model is a debugger, not a dashboard: the ledger and the proof
 * are on screen together, moving between settlements never navigates, and the
 * keyboard is the primary input because an investigator working a queue of two
 * hundred exceptions should never reach for a mouse.
 */
'use strict';

const S = { run: null, rows: [], view: [], i: 0, filter: '', vf: null, cache: new Map() };
const el = id => document.getElementById(id);
const V = ['PROVEN', 'AMBIGUOUS', 'CONTRADICTED'];
const vc = { PROVEN: 'var(--ok)', AMBIGUOUS: 'var(--warn)', CONTRADICTED: 'var(--dead)' };
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* Indian grouping. 4738219 paise rendered "4,738,219" tells an Indian reader the
   wrong number at a glance, so lakh/crore grouping is correctness, not polish. */
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

/* ------------------------------------------------------------------- run */

async function run() {
  el('run').innerHTML = '<span class=spin></span>running';
  el('ledger').innerHTML = '<div class=empty><span class=spin></span>normalise · block · match · solve · verify</div>';
  S.cache.clear();
  S.run = await api(`/api/run?n=${el('size').value}`);
  S.rows = await api(`/api/rows?run=${S.run.run_id}`);
  el('run').textContent = 'run ⏎';
  strip(); apply(); S.i = 0; select();
}

function strip() {
  const s = S.run, m = s.money;
  el('m-proc').textContent = rs(s.processed_paise, true);
  el('m-post').textContent = rs(m.PROVEN, true);
  el('m-held').textContent = rs(m.AMBIGUOUS, true);
  el('m-unex').textContent = rs(m.CONTRADICTED, true);
  el('m-wrong').textContent = s.wrong;
  el('m-wrong').className = 'v ' + (s.wrong ? 'warn' : 'ok');
  el('barmeta').innerHTML = `${s.run_id} · seed ${s.seed} · ` +
    `<b>${s.seconds}s</b> · exact <b>${(s.exact * 100).toFixed(1)}%</b> · ` +
    `precision <b>${s.precision.toFixed(3)}</b> · ceiling <b>${s.blocking_ceiling.toFixed(3)}</b>`;
}

/* ---------------------------------------------------------------- ledger */

function apply() {
  const q = S.filter.toLowerCase();
  S.view = S.rows.filter(r =>
    (!S.vf || r.verdict === S.vf) &&
    (!q || r.id.includes(q) || r.date.includes(q) || r.verdict.toLowerCase().startsWith(q)));
  el('count').textContent = `${S.view.length}/${S.rows.length}`;
  paint();
}

function glyph(g) {
  return `<span class=gly>${g.map(v =>
    `<i class="${v === 1 ? 'y' : v === 0 ? 'n' : 'x'}"></i>`).join('')}</span>`;
}

/* Residual drawn against its own tolerance band, centred on zero. Width is the
   fraction of the bound consumed; side is the sign. */
function resbar(ratio, verdict) {
  if (ratio === null || ratio === undefined) return '<span class=res><i class=tr></i></span>';
  const f = Math.max(-1, Math.min(1, ratio));
  const w = Math.abs(f) * 50;
  const left = f < 0 ? 50 - w : 50;
  return `<span class=res><i class=tr></i><i class=md></i>
    <i class=fl style="left:${left}%;width:${Math.max(w, 1.2)}%;background:${vc[verdict]}"></i></span>`;
}

function paint() {
  if (!S.view.length) { el('ledger').innerHTML = '<div class=empty>no rows</div>'; return; }
  el('ledger').innerHTML = S.view.map((r, i) => `<div class="row${i === S.i ? ' sel' : ''}" data-i=${i}>
    <span class=id>${r.id.replace('setl_', '')}</span>
    ${glyph(r.glyph)}
    <span class=amt>${rs(r.amount)}</span>
    <span class=cnt>${r.orders || '·'}</span>
    <span class="vd v-${r.verdict}">${r.verdict.slice(0, 4)}</span>
  </div>`).join('');
  const sel = el('ledger').querySelector('.row.sel');
  if (sel) sel.scrollIntoView({ block: 'nearest' });
}

/* ----------------------------------------------------------------- proof */

async function select() {
  const r = S.view[S.i];
  if (!r) { el('proof').innerHTML = '<div class=empty>no selection</div>'; return; }
  paint();
  let d = S.cache.get(r.id);
  if (!d) {
    d = await api(`/api/settlement?run=${S.run.run_id}&id=${r.id}`);
    S.cache.set(r.id, d);
  }
  if (S.view[S.i] && S.view[S.i].id !== r.id) return;  // moved on while fetching
  renderProof(d); renderChecks(d);
}

function renderProof(d) {
  const p = d.proofs[0];
  el('proofmeta').textContent = d.layer;

  const head = `<div class=hdr><span class=sid>${d.id}</span>
    <span class="vd v-${d.verdict}">${d.verdict}</span>
    <span class=amt>${rs(d.amount)}</span></div>
    <div class=sub>${d.date} · utr ${d.utr || '—'} · ${d.exhaustive ? 'search exhaustive' : 'search capped'}</div>`;

  if (!p) {
    return void (el('proof').innerHTML = head + `
      <h4>no accepted explanation</h4>
      ${d.unsat_core.map(c => `<div class=alt><div class=ai>${esc(c)}</div></div>`).join('')
        || '<div class=empty>out of envelope</div>'}
      <p class=sub style="margin-top:14px;line-height:1.6">No subset of any
      candidate window satisfies the amount constraint. The engine names the
      constraint that fails rather than forcing a plausible answer.</p>`);
  }

  const eq = `<div class=eq>
    <div class=l><span class=lb>gross · ${p.orders.length} orders</span><span class=vl>${rs(p.gross)}</span></div>
    <div class=l><span class=lb>fees + GST</span><span class="vl neg">−${rs(p.fee)}</span></div>
    <div class=l><span class=lb>adjustments</span><span class=vl>${p.adjustment ? rs(p.adjustment) : '₹0.00'}</span></div>
    <div class="l t"><span class=lb>net</span><span class=vl>${rs(p.net)}</span></div>
    <div class="l q"><span class=lb>bank credit</span><span class=vl>${rs(d.amount)}</span></div>
    <div class=l><span class=lb>residual</span><span class=vl>${rs(p.residual)}</span></div>
    <div class=l><span class=lb>bound · ${p.orders.length} × 1 paisa</span><span class=vl>±${p.tolerance} paise</span></div>
  </div>`;

  const orders = `<h4>orders in this explanation</h4><div class=ord>
    <div class="o h"><span>order</span><span>method</span><span>gross</span><span>net</span></div>
    ${p.orders.map(o => `<div class=o><span>${o.id.replace('ord_', '')}</span>
      <span class=mth>${o.method}</span><span>${rs(o.gross)}</span><span>${rs(o.net)}</span></div>`).join('')}
  </div>`;

  const alts = d.proofs.length > 1 ? `<h4>competing explanations · ${d.proofs.length}</h4>
    ${d.proofs.map((q, i) => `<div class=alt>
      <div class=ah>#${i + 1} · ${q.orders.length} orders · net ${rs(q.net)} · residual ${rs(q.residual)}</div>
      <div class=ai>${q.orders.map(o => o.id.replace('ord_', '')).join(' ')}</div></div>`).join('')}
    <p class=sub style="line-height:1.6">More than one subset satisfies every
    constraint exactly. Arithmetic cannot choose between them, so the engine
    reports the field rather than picking one. Resolving this needs evidence
    beyond the amount — a reference, a counterparty — not a better search.</p>` : '';

  el('proof').innerHTML = head + eq + orders + alts;
}

function renderChecks(d) {
  const p = d.proofs[0];
  const post = d.postable
    ? `<div class=post><span class="b ok">AUTO-POST ELIGIBLE</span>
       <div class=sub style="margin-top:4px">unique, kernel-checked</div></div>`
    : `<div class=post><span class="b warn">POSTING BLOCKED</span>
       <div class=sub style="margin-top:4px">${d.verdict === 'AMBIGUOUS'
         ? 'explanation is not unique' : 'no explanation satisfies the constraints'}</div></div>`;

  const stat = p ? `<div class=stat>
    <div class=l><span>orders</span><span>${p.orders.length}</span></div>
    <div class=l><span>residual</span><span>${p.residual} paise</span></div>
    <div class=l><span>bound</span><span>±${p.tolerance} paise</span></div>
    <div class=l><span>consumed</span><span>${p.tolerance ? ((Math.abs(p.residual) / p.tolerance) * 100).toFixed(0) : 0}% of bound</span></div>
    <div class=l><span>candidates</span><span>${d.proofs.length}</span></div>
    <div class=l><span>layer</span><span>${esc(d.layer)}</span></div>
  </div>` : '';

  const checks = d.checks.map(c => `<div class=ck>
    <div class=t><span class="mk ${c.ok ? 'ok' : 'warn'}">${c.ok ? '✓' : '✗'}</span>
      <span class=nm>${c.name}</span></div>
    <div class=d>${esc(c.detail)}</div></div>`).join('');

  el('checks').innerHTML = post + stat + (checks || '<div class=empty>—</div>');
}

/* -------------------------------------------------------------- keyboard */

function move(n) {
  if (!S.view.length) return;
  S.i = Math.max(0, Math.min(S.view.length - 1, S.i + n));
  select();
}
function setVF(v) { S.vf = v; S.i = 0; apply(); select(); }

el('run').onclick = run;
el('ledger').onclick = e => {
  const r = e.target.closest('.row'); if (!r) return;
  S.i = +r.dataset.i; select();
};
el('filter').addEventListener('input', e => { S.filter = e.target.value; S.i = 0; apply(); select(); });
el('filter').addEventListener('keydown', e => {
  if (e.key === 'Escape') { e.target.value = ''; S.filter = ''; e.target.blur(); apply(); select(); }
  e.stopPropagation();
});

document.addEventListener('keydown', e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key;
  if (k === 'j' || k === 'ArrowDown') { e.preventDefault(); move(1); }
  else if (k === 'k' || k === 'ArrowUp') { e.preventDefault(); move(-1); }
  else if (k === 'g') { S.i = 0; select(); }
  else if (k === 'G') { S.i = S.view.length - 1; select(); }
  else if (k === '/') { e.preventDefault(); el('filter').focus(); }
  else if (k === '1') setVF('PROVEN');
  else if (k === '2') setVF('AMBIGUOUS');
  else if (k === '3') setVF('CONTRADICTED');
  else if (k === '0') setVF(null);
  else if (k === 'Enter') run();
});

run();
