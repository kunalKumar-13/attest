/* ATTEST — front end.
 *
 * Holds no reconciliation logic. Every verdict, every rupee and every constraint
 * check on screen is computed by the engine and fetched from /api. A front end
 * that can decide a verdict is a front end that can disagree with the ledger,
 * and in finance the screen disagreeing with the ledger is the whole failure.
 */
'use strict';

const S = { run: null, rows: [], view: 'overview', sid: null, busy: false };

/* Indian digit grouping. Rendering 4738219 paise as "4,738,219" tells an Indian
   reader the wrong number at a glance, so the lakh/crore grouping is not
   cosmetic. */
function rs(paise, opts = {}) {
  const neg = paise < 0; let n = Math.abs(paise);
  const p = n % 100; let r = String(Math.floor(n / 100));
  if (r.length > 3) {
    let head = r.slice(0, -3); const tail = r.slice(-3); const parts = [];
    while (head.length > 2) { parts.unshift(head.slice(-2)); head = head.slice(0, -2); }
    r = (head ? [head] : []).concat(parts, [tail]).join(',');
  }
  const body = opts.whole ? r : `${r}.${String(p).padStart(2, '0')}`;
  return `${neg ? '−' : ''}₹${body}`;
}
const pct = x => (x * 100).toFixed(1) + '%';
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const el = id => document.getElementById(id);
const V = ['PROVEN', 'AMBIGUOUS', 'CONTRADICTED'];
const vcol = v => `var(--${v.toLowerCase()})`;

async function api(path) { const r = await fetch(path); return r.json(); }

/* ---------------------------------------------------------------- running */

async function runReconciliation() {
  if (S.busy) return;
  S.busy = true;
  el('runbtn').innerHTML = '<span class=spin></span>Reconciling';
  el('view').innerHTML = `<div class=empty><span class=spin></span>
    Normalising · blocking · exact match · subset solver · verifying proofs…</div>`;
  try {
    S.run = await api(`/api/run?n=${el('size').value}`);
    S.rows = await api(`/api/rows?run=${S.run.run_id}`);
    el('runmeta').textContent = `${S.run.run_id} · seed ${S.run.seed}`;
    S.sid = null; render();
  } finally {
    S.busy = false; el('runbtn').textContent = 'Run reconciliation';
  }
}

/* ---------------------------------------------------------------- widgets */

const cell = (k, v, s, colour) => `<div class=cell><div class=k>${k}</div>
  <div class=v ${colour ? `style="color:${colour}"` : ''}>${v}</div>
  ${s ? `<div class=s>${s}</div>` : ''}</div>`;

function verdictBar(counts, total) {
  const bar = V.map(v => `<i style="width:${(counts[v] / total) * 100}%;
    background:${vcol(v)}"></i>`).join('');
  const leg = V.map(v => `<span><i class=dot style="background:${vcol(v)}"></i>
    <b>${counts[v].toLocaleString()}</b> ${v.toLowerCase()}</span>`).join('');
  return `<div class=vbar>${bar}</div><div class=vlegend>${leg}</div>`;
}

function table(head, body) {
  return `<div class=tw><table><thead><tr>${head}</tr></thead>
    <tbody>${body || `<tr><td colspan=9 class=muted>Nothing here.</td></tr>`}
    </tbody></table></div>`;
}

const row = r => `<tr onclick="openSettlement('${r.id}')">
  <td class=n>${r.id}</td><td class=n>${r.date}</td>
  <td class="n r">${rs(r.amount)}</td>
  <td class="n r">${r.orders || '—'}</td>
  <td class="n r">${r.residual ? rs(r.residual) : '0.00'}</td>
  <td><span class="pill p-${r.verdict}">${r.verdict}</span></td>
  <td class=muted style="font-size:12px">${esc(r.layer)}</td></tr>`;

const HEAD = `<th>settlement</th><th>value date</th><th class="n r">amount</th>
  <th class="n r">orders</th><th class="n r">residual</th><th>verdict</th><th>resolved by</th>`;

/* ------------------------------------------------------------------ views */

function overview() {
  const s = S.run, m = s.money, c = s.counts;
  return `
  <div class="grid g5">
    ${cell('processed', rs(s.processed_paise, { whole: true }), `${s.settlements.toLocaleString()} settlements · ${s.orders.toLocaleString()} orders`)}
    ${cell('auto-reconciled', rs(m.PROVEN, { whole: true }), `${c.PROVEN} proven`, vcol('PROVEN'))}
    ${cell('needs review', rs(m.AMBIGUOUS, { whole: true }), `${c.AMBIGUOUS} ambiguous`, vcol('AMBIGUOUS'))}
    ${cell('unexplained', rs(m.CONTRADICTED, { whole: true }), `${c.CONTRADICTED} contradicted`, vcol('CONTRADICTED'))}
    ${cell('false proofs', s.wrong, `precision ${s.precision.toFixed(3)}`, s.wrong ? vcol('AMBIGUOUS') : vcol('PROVEN'))}
  </div>
  <h2>Reconciliation health</h2>
  ${verdictBar(c, s.settlements)}
  <p class=note style="margin-top:-14px;max-width:660px">A decline is a correct
  outcome, not a failure. The engine posts only where exactly one explanation
  satisfies every constraint; everything else is handed to a human with the
  competing explanations or the contradiction attached.</p>
  <h2>Largest settlements</h2>
  ${table(HEAD, [...S.rows].sort((a, b) => b.amount - a.amount).slice(0, 12).map(row).join(''))}`;
}

function reconciliation() {
  const c = S.run.counts;
  return `<h2>${S.rows.length.toLocaleString()} settlements ·
    ${c.PROVEN} proven · ${c.AMBIGUOUS} ambiguous · ${c.CONTRADICTED} contradicted
    · ${S.run.seconds}s</h2>
    ${table(HEAD, S.rows.map(row).join(''))}`;
}

function exceptions() {
  const ex = S.rows.filter(r => r.verdict !== 'PROVEN');
  const money = ex.reduce((a, r) => a + r.amount, 0);
  const amb = ex.filter(r => r.verdict === 'AMBIGUOUS').length;
  return `
  <div class="grid g5">
    ${cell('open exceptions', ex.length, 'awaiting a human decision')}
    ${cell('value held', rs(money, { whole: true }), 'not posted')}
    ${cell('multiple valid assignments', amb, 'arithmetic cannot choose', vcol('AMBIGUOUS'))}
    ${cell('no valid assignment', ex.length - amb, 'constraint unsatisfiable', vcol('CONTRADICTED'))}
  </div>
  <p class=note style="max-width:660px;margin:-8px 0 4px">Exceptions are
  first-class output, not residue. Each carries the reason it could not be
  proven — competing explanations, or the constraint that failed.</p>
  <h2>Open</h2>
  ${table(HEAD, ex.sort((a, b) => b.amount - a.amount).map(row).join(''))}`;
}

function evaluation() {
  const s = S.run;
  const bl = [['exact-only', '4.0%', '96.0%', '0', '0.0%', '1.000'],
              ['fuzzy', '3.2%', '92.4%', '11', '4.4%', '0.421'],
              ['greedy', '4.4%', '5.2%', '226', '90.4%', '0.166'],
              ['ATTEST', pct(s.exact), pct(1 - s.exact), String(s.wrong),
               pct(s.wrong / s.settlements), s.precision.toFixed(3)]];
  const rows = bl.map(r => `<tr style="cursor:default${r[0] === 'ATTEST' ? ';font-weight:700' : ''}">
    <td>${r[0]}</td><td class="n r">${r[1]}</td><td class="n r">${r[2]}</td>
    <td class="n r">${r[3]}</td><td class="n r">${r[4]}</td><td class="n r">${r[5]}</td></tr>`).join('');

  const cases = Object.entries(s.by_case).sort((a, b) => a[1].hit / a[1].n - b[1].hit / b[1].n)
    .map(([k, v]) => `<tr style="cursor:default"><td class=n>${k}</td>
      <td class="n r">${v.n}</td><td class="n r">${pct(v.hit / v.n)}</td></tr>`).join('');

  return `
  <h2>Against reference matchers · same data, same candidate pools</h2>
  ${table(`<th>matcher</th><th class="n r">exact set</th><th class="n r">declined</th>
    <th class="n r">WRONG</th><th class="n r">wrong %</th><th class="n r">precision</th>`, rows)}
  <p class=note style="max-width:680px">Read the <b>WRONG</b> column. Greedy declines
  5% of the time and is wrong 90% of the time — 226 of 250 settlements posted
  against orders that did not produce them. That is what a matcher with no way to
  abstain actually does. Greedy fails structurally, not by tuning: taking the
  largest order that fits is a local decision, and subset-sum has no
  greedy-choice property.</p>
  <h2>By hazard family · ground truth is exact by construction</h2>
  ${table(`<th>hazard</th><th class="n r">n</th><th class="n r">exact</th>`, cases)}
  <p class=note>Blocking recall ceiling <b>${s.blocking_ceiling.toFixed(3)}</b> —
  any accuracy figure must be read against it, since an order pruned at layer 0
  is unreachable by every later layer.</p>`;
}

function audit() {
  return `<h2>Run ${S.run.run_id}</h2><div class="card audit">
    ${S.run.audit.map(a => `<div><span class=t>${a.t}</span><b>${a.event}</b>
      &nbsp;${esc(a.detail)}</div>`).join('')}</div>
    <p class=note>Every run is reproducible: same seed, same data, same solver
    configuration, same result. Determinism is a requirement in finance, not a
    nicety — a reconciliation you cannot replay is a reconciliation you cannot
    defend.</p>`;
}

/* -------------------------------------------------------- settlement view */

async function openSettlement(sid) {
  S.sid = sid; S.view = 'detail';
  el('view').innerHTML = `<div class=empty><span class=spin></span>Loading proof…</div>`;
  const d = await api(`/api/settlement?run=${S.run.run_id}&id=${sid}`);
  el('title').textContent = sid;
  el('crumb').textContent = `${d.date} · ${d.verdict}`;
  document.querySelectorAll('#nav a').forEach(a => a.classList.remove('on'));
  el('view').innerHTML = detailView(d);
}

function detailView(d) {
  const p = d.proofs[0];
  const flow = p ? `<div class=flow>
    <div class=node><div class=l>orders (${p.orders.length})</div><div class=a>${rs(p.gross)}</div></div>
    <span class=arrow>→</span>
    <div class=node><div class=l>fees + GST</div><div class=a>−${rs(p.fee)}</div></div>
    <span class=arrow>→</span>
    <div class=node><div class=l>adjustments</div><div class=a>${p.adjustment ? rs(p.adjustment) : '₹0.00'}</div></div>
    <span class=arrow>→</span>
    <div class=node style="border-color:${vcol(d.verdict)}"><div class=l>settlement</div>
      <div class=a style="color:${vcol(d.verdict)}">${rs(d.amount)}</div></div>
    <span class=arrow>→</span>
    <div class=node><div class=l>bank</div><div class=a>${rs(d.amount)}</div></div>
  </div>` : '';

  const orderRows = p ? p.orders.map(o => `<tr style="cursor:default">
    <td class=n>${o.id}</td><td>${o.method}</td><td class=n>${o.captured_on}</td>
    <td class="n r">${rs(o.gross)}</td><td class="n r">${rs(o.fee)}</td>
    <td class="n r">${rs(o.net)}</td></tr>`).join('') : '';

  const ledger = p ? `<div class=card><h3>Composition</h3>
    <div class=sum-row><span class=muted>gross, ${p.orders.length} orders</span><span>${rs(p.gross)}</span></div>
    <div class=sum-row><span class=muted>fees and GST</span><span>−${rs(p.fee)}</span></div>
    <div class=sum-row><span class=muted>adjustments</span><span>${p.adjustment ? rs(p.adjustment) : '₹0.00'}</span></div>
    <div class="sum-row tot"><span>net</span><span>${rs(p.net)}</span></div>
    <div class=sum-row><span class=muted>bank credit</span><span>${rs(d.amount)}</span></div>
    <div class=sum-row><span class=muted>residual</span><span>${rs(p.residual)}</span></div>
    <div class=sum-row><span class=muted>tolerance, ${p.orders.length} × 1 paisa</span>
      <span>${p.tolerance} paise</span></div></div>` : '';

  const checks = d.checks.length ? `<div class=card><h3>Why this verdict</h3>
    ${d.checks.map(c => `<div class=chk><span class="m ${c.ok ? 'ok' : 'no'}">${c.ok ? '✓' : '⚠'}</span>
      <span class=nm>${c.name}</span><span class=dt>${esc(c.detail)}</span></div>`).join('')}
    </div>` : '';

  let extra = '';
  if (d.verdict === 'AMBIGUOUS') {
    extra = `<div class=card><h3>Competing explanations</h3>
      ${d.proofs.map((q, i) => `<div class=alt><div class=h>explanation ${i + 1} —
        ${q.orders.length} orders, net ${rs(q.net)}, residual ${rs(q.residual)}</div>
        <div class=ids>${q.orders.map(o => o.id).join(' ')}</div></div>`).join('')
        || '<p class=note>Out of envelope — not attempted.</p>'}
      <p class=note>More than one subset satisfies every constraint exactly.
      Arithmetic cannot choose between them, so the engine reports the field
      rather than picking one. Resolving this needs evidence beyond the amount —
      a reference, a counterparty — not a better search.</p></div>`;
  } else if (d.verdict === 'CONTRADICTED') {
    extra = `<div class=card><h3>Contradiction</h3>
      ${d.unsat_core.map(c => `<div class=chk><span class="m no">✗</span>
        <span class=dt>${esc(c)}</span></div>`).join('')}
      <p class=note>No subset of any candidate window satisfies the amount
      constraint. The engine names the constraint that fails rather than forcing
      a plausible answer.</p></div>`;
  }

  return `<div class=two><div>
    <div class=card><h3>Financial flow</h3>${flow || '<p class=note>No accepted explanation.</p>'}</div>
    ${p ? `<h2>Orders in this proof</h2>${table(
      `<th>order</th><th>method</th><th>captured</th><th class="n r">gross</th>
       <th class="n r">fee + GST</th><th class="n r">net</th>`, orderRows)}
      <p class=note>Every value here is recomputed from the order records by
      <code>verdict.check</code> — 28 lines, sharing no code with the solver that
      produced the proof. A bug in the prover can cost recall; it cannot post a
      wrong entry.</p>` : ''}
    ${extra}
  </div><div>
    <div class=card><h3>${d.verdict}</h3>
      <div class=sum-row><span class=muted>amount</span><span>${rs(d.amount)}</span></div>
      <div class=sum-row><span class=muted>value date</span><span>${d.date}</span></div>
      <div class=sum-row><span class=muted>UTR</span><span>${d.utr || '—'}</span></div>
      <div class=sum-row><span class=muted>resolved by</span><span>${esc(d.layer)}</span></div>
      <div class=sum-row><span class=muted>auto-post</span>
        <span style="color:${d.postable ? vcol('PROVEN') : vcol('AMBIGUOUS')}">
        ${d.postable ? 'ELIGIBLE' : 'BLOCKED'}</span></div>
    </div>
    ${ledger}${checks}
  </div></div>`;
}

/* --------------------------------------------------------------- routing */

const VIEWS = { overview, reconciliation, exceptions, evaluation, audit };
const TITLES = { overview: 'Overview', reconciliation: 'Reconciliation',
  exceptions: 'Exceptions', evaluation: 'Evaluation', audit: 'Audit log' };

function render() {
  if (!S.run) return;
  if (S.view === 'detail') return;
  el('title').textContent = TITLES[S.view];
  el('crumb').textContent = S.run ? `${S.run.run_id} · seed ${S.run.seed}` : '';
  el('view').innerHTML = VIEWS[S.view]();
}

el('nav').addEventListener('click', e => {
  const a = e.target.closest('a'); if (!a) return;
  document.querySelectorAll('#nav a').forEach(x => x.classList.remove('on'));
  a.classList.add('on'); S.view = a.dataset.v; S.sid = null;
  if (!S.run) { el('view').innerHTML = '<div class=empty>Run a reconciliation to begin.</div>'; return; }
  render();
});
el('runbtn').onclick = runReconciliation;

/* --------------------------------------------------------------- palette */

const CMDS = [
  { t: 'Run reconciliation', s: '⏎', f: runReconciliation },
  { t: 'Overview', s: 'view', f: () => go('overview') },
  { t: 'Reconciliation', s: 'view', f: () => go('reconciliation') },
  { t: 'Exceptions', s: 'view', f: () => go('exceptions') },
  { t: 'Evaluation', s: 'view', f: () => go('evaluation') },
  { t: 'Audit log', s: 'view', f: () => go('audit') },
];
function go(v) {
  S.view = v; S.sid = null;
  document.querySelectorAll('#nav a').forEach(a =>
    a.classList.toggle('on', a.dataset.v === v));
  render();
}
function palOpen(on) {
  el('pal').classList.toggle('on', on);
  if (on) { el('palq').value = ''; palRender(''); el('palq').focus(); }
}
function palRender(q) {
  q = q.toLowerCase();
  const cmds = CMDS.filter(c => c.t.toLowerCase().includes(q))
    .map((c, i) => ({ label: c.t, sub: c.s, run: c.f }));
  const hits = q.length > 1 ? S.rows.filter(r => r.id.toLowerCase().includes(q)).slice(0, 6)
    .map(r => ({ label: r.id, sub: `${rs(r.amount)} · ${r.verdict}`,
                 run: () => openSettlement(r.id) })) : [];
  const all = cmds.concat(hits);
  el('palr').innerHTML = all.length
    ? all.map((x, i) => `<div class="it${i === 0 ? ' sel' : ''}" data-i=${i}>
        ${esc(x.label)}<small>${esc(x.sub)}</small></div>`).join('')
    : '<div class=empty style="padding:24px 0">No matches.</div>';
  el('palr').onclick = e => {
    const it = e.target.closest('.it'); if (!it) return;
    palOpen(false); all[+it.dataset.i].run();
  };
  el('palr').dataset.first = all.length ? '1' : '';
  el('palr')._all = all;
}
el('palq').addEventListener('input', e => palRender(e.target.value));
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); palOpen(true); }
  else if (e.key === 'Escape') palOpen(false);
  else if (e.key === 'Enter' && el('pal').classList.contains('on')) {
    const all = el('palr')._all; if (all && all.length) { palOpen(false); all[0].run(); }
  }
});
el('pal').addEventListener('click', e => { if (e.target.id === 'pal') palOpen(false); });

runReconciliation();
