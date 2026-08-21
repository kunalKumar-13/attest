/* The widget library — §6.
 *
 * Each entry is a pure render against the run context. No widget fetches, holds
 * state, or knows about any other widget, so the board can compose them in any
 * order at any size without coordination. A widget that needed to know its
 * neighbours would not survive being dragged.
 *
 * Every one of them must stay useful at every size it can be given (§9), which
 * mostly means: lead with the number, let the detail be what gets cut.
 */
'use strict';

(() => {
  const { defineWidget } = window.ATTESTBoard;
  const rs = (p, whole) => window.ATTEST_rs(p, whole);
  const esc = s => String(s).replace(/[&<>"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const V = ['PROVEN', 'AMBIGUOUS', 'CONTRADICTED', 'INSUFFICIENT'];
  const vc = v => `var(--${v === 'PROVEN' ? 'ok' : v === 'AMBIGUOUS' ? 'warn' : 'dead'})`;
  const none = t => `<div class=bd-empty>${t}</div>`;

  const stat = (k, v, s, c) => `<div class=bd-s>
    <div class=bd-k>${k}</div>
    <div class=bd-v ${c ? `style="color:${c}"` : ''}>${v}</div>
    ${s ? `<div class=bd-ss>${s}</div>` : ''}</div>`;

  defineWidget('money', {
    title: 'Money', category: 'Financial', w: 4, h: 2,
    blurb: 'processed, posted, settled, unexplained',
    render: ({ summary: s }) => {
      if (!s) return none('run a reconciliation');
      const acct = (s.money.PROVEN + (s.settled_paise || 0)) / Math.max(s.processed_paise, 1);
      return `<div class=bd-grid2>
        ${stat('processed', rs(s.processed_paise, true), `${s.settlements} settlements`)}
        ${stat('auto-posted', rs(s.money.PROVEN, true), `${s.counts.PROVEN} proven`, 'var(--ok)')}
        ${stat('settled, not proven', rs(s.settled_paise || 0, true),
               `${(acct * 100).toFixed(1)}% accounted for`, 'var(--warn)')}
        ${stat('unexplained', rs(s.unexplained_paise || 0, true), 'stated to the paisa', 'var(--dead)')}
      </div>`;
    },
  });

  defineWidget('health', {
    title: 'Reconciliation health', category: 'Financial', w: 5, h: 2,
    blurb: 'verdict breakdown',
    render: ({ summary: s }) => {
      if (!s) return none('run a reconciliation');
      const n = Math.max(s.settlements, 1);
      return `<div class=bd-bars>${V.filter(v => s.counts[v]).map(v => `
        <div class=bd-bar>
          <div class=bd-bl><span>${v.toLowerCase()}</span>
            <b class=n>${s.counts[v]}</b>
            <span class=bd-bp>${(s.counts[v] / n * 100).toFixed(1)}%</span></div>
          <div class=bd-bt><i style="width:${s.counts[v] / n * 100}%;background:${vc(v)}"></i></div>
        </div>`).join('')}
        <div class=bd-note>A decline is a correct outcome. The engine posts only
          where exactly one explanation survives every constraint.</div></div>`;
    },
  });

  defineWidget('safety', {
    title: 'Safety', category: 'Risk', w: 3, h: 2,
    blurb: 'precision, false proofs, exposure',
    render: ({ summary: s }) => {
      if (!s) return none('run a reconciliation');
      return `<div class=bd-grid1>
        ${stat('false proofs', s.wrong, 'this seed', s.wrong ? 'var(--warn)' : 'var(--ok)')}
        ${stat('proof precision', s.precision.toFixed(3), 'right when it claims sure')}
        ${stat('blocking ceiling', s.blocking_ceiling.toFixed(3), 'recall cannot exceed this')}
      </div>`;
    },
  });

  defineWidget('exposure', {
    title: 'Protected from automation', category: 'Risk', w: 6, h: 2,
    blurb: 'value the policy refused to post',
    render: ({ summary: s, policy: p }) => {
      if (!s) return none('run a reconciliation');
      const posted = p ? p.posted_paise : s.money.PROVEN;
      const prot = p ? p.protected_paise : s.processed_paise - s.money.PROVEN;
      const share = prot / Math.max(s.processed_paise, 1);
      return `<div>
        <div class=bd-big style="color:var(--warn)">${rs(prot, true)}</div>
        <div class=bd-ss>refused, deliberately — ${(share * 100).toFixed(1)}% of processed value</div>
        <div class=bd-bt style="margin-top:12px"><i style="width:${share * 100}%;background:var(--warn)"></i></div>
        <div class=bd-row style="margin-top:10px">
          <span>auto-posted</span><b class=n>${rs(posted, true)}</b></div>
        ${p ? `<div class=bd-row><span>realised loss</span>
          <b class="n ${p.realised_loss_paise ? 'warn' : 'ok'}">${rs(p.realised_loss_paise, true)}</b></div>` : ''}
      </div>`;
    },
  });

  defineWidget('volume', {
    title: 'Settlement volume', category: 'Operations', w: 7, h: 2,
    blurb: 'settlements per value date',
    render: ({ rows }) => {
      if (!rows || !rows.length) return none('run a reconciliation');
      const m = new Map();
      rows.forEach(r => m.set(r.date, (m.get(r.date) || 0) + 1));
      const pts = [...m.entries()].sort((a, b) => a[0] < b[0] ? -1 : 1);
      const vals = pts.map(p => p[1]);
      const max = Math.max(...vals, 1), W = 600, H = 96;
      const d = vals.map((v, i) =>
        `${i ? 'L' : 'M'}${(i / Math.max(vals.length - 1, 1) * W).toFixed(1)},${(H - v / max * (H - 6)).toFixed(1)}`).join('');
      return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio=none class=bd-spark>
          <defs><linearGradient id=bdg x1=0 x2=0 y1=0 y2=1>
            <stop offset=0 stop-color="var(--acc)" stop-opacity=".3"/>
            <stop offset=1 stop-color="var(--acc)" stop-opacity="0"/></linearGradient></defs>
          <path d="${d}L${W},${H}L0,${H}Z" fill="url(#bdg)"/>
          <path d="${d}" fill=none stroke="var(--acc)" stroke-width=1.5 vector-effect=non-scaling-stroke/>
        </svg>
        <div class=bd-axis><span>${pts[0]?.[0] || ''}</span>
          <span>${pts.length} value dates · peak ${max}</span>
          <span>${pts[pts.length - 1]?.[0] || ''}</span></div>`;
    },
  });

  defineWidget('reasons', {
    title: 'Why settlements are unresolved', category: 'Operations', w: 5, h: 2,
    blurb: 'exception reasons by value',
    render: ({ summary: s }) => {
      if (!s || !s.by_reason) return none('run a reconciliation');
      return `<div class=bd-tbl>${s.by_reason.slice(0, 6).map(r => `
        <div class=bd-row><span>${esc(r.reason.toLowerCase().replace(/_/g, ' '))}</span>
          <b class=n>${r.n}</b>
          <b class="n ${r.unexplained ? 'warn' : ''}" style="min-width:78px;text-align:right">
            ${r.unexplained ? rs(r.unexplained, true) : '—'}</b></div>`).join('')}</div>`;
    },
  });

  defineWidget('largest', {
    title: 'Largest unresolved', category: 'Operations', w: 7, h: 3,
    blurb: 'the queue, by money',
    render: ({ rows, open }) => {
      if (!rows || !rows.length) return none('run a reconciliation');
      const bad = rows.filter(r => r.verdict !== 'PROVEN')
        .sort((a, b) => b.amount - a.amount).slice(0, 12);
      if (!bad.length) return `<div class=bd-empty>Nothing unresolved.<br>
        <span style="color:var(--ok)">Every settlement has a provable explanation.</span></div>`;
      return `<div class=bd-tbl>${bad.map(r => `
        <div class="bd-row link" data-sid="${r.id}">
          <span class=n>${r.id.replace('setl_', '')}</span>
          <b class=n style="flex:1;text-align:right">${rs(r.amount)}</b>
          <span class="n" style="color:${vc(r.verdict)};min-width:44px;text-align:right;font-size:9px">
            ${r.verdict.slice(0, 4)}</span>
          <b class="n warn" style="min-width:64px;text-align:right">
            ${r.unexplained ? rs(r.unexplained, true) : ''}</b></div>`).join('')}</div>`;
    },
  });

  defineWidget('activity', {
    title: 'Verification activity', category: 'Operations', w: 5, h: 3,
    blurb: 'what the engine did, in order',
    render: ({ summary: s }) => {
      if (!s || !s.audit) return none('run a reconciliation');
      return `<div class=bd-feed>${s.audit.map(a => `
        <div class=bd-ev><span class=bd-t2>${a.t}</span>
          <div><b>${esc(a.event)}</b><div class=bd-ss>${esc(a.detail)}</div></div>
        </div>`).join('')}</div>`;
    },
  });

  defineWidget('strata', {
    title: 'Measured risk by stratum', category: 'Risk', w: 6, h: 3,
    blurb: 'observed error rates, Wilson-priced',
    render: ({ policy: p }) => {
      if (!p || !p.strata) return none('open the policy view once to load this');
      return `<div class=bd-tbl>${p.strata.map(s => `
        <div class=bd-row><span class=n style="font-size:10px">${esc(s.key)}</span>
          <b class=n>${s.wrong}/${s.total}</b>
          <b class="n ${s.priced > 0.2 ? 'warn' : 'ok'}" style="min-width:62px;text-align:right">
            ${s.priced.toFixed(4)}</b></div>`).join('')}
        <div class=bd-note>Priced at the 95% Wilson upper bound, never the observed
          rate. A stratum below the observation floor is not priced and posts nothing.</div></div>`;
    },
  });

  defineWidget('hazards', {
    title: 'Accuracy by hazard family', category: 'Technical', w: 12, h: 3,
    blurb: 'where the engine succeeds and fails',
    render: ({ summary: s }) => {
      if (!s || !s.by_case) return none('run a reconciliation');
      const e = Object.entries(s.by_case).sort((a, b) => a[1].hit / a[1].n - b[1].hit / b[1].n);
      return `<div class=bd-tbl>${e.map(([k, v]) => `
        <div class=bd-row><span>${esc(k.replace(/_/g, ' '))}</span>
          <div class=bd-bt style="flex:1;max-width:200px">
            <i style="width:${v.hit / v.n * 100}%;background:${v.hit ? 'var(--ok)' : 'var(--dead)'}"></i></div>
          <b class=n style="min-width:52px;text-align:right">${(v.hit / v.n * 100).toFixed(0)}%</b>
          <span class=n style="min-width:36px;text-align:right;color:var(--dim3)">${v.n}</span>
        </div>`).join('')}</div>`;
    },
  });

  defineWidget('rules', {
    title: 'Rules in force', category: 'Technical', w: 6, h: 3,
    blurb: 'what the engine believes about how money moves',
    render: ({ summary: s }) => {
      if (!s || !s.rules) return none('run a reconciliation');
      return `<div class=bd-tbl>${s.rules.map(r => `
          <div class=bd-row><span>${esc(r.rule)}</span>
            <b class=n style="flex:1;text-align:right">${esc(r.value)}</b></div>`).join('')}
        <div class=bd-note>Every rule is a belief, not a fact. When the engine's
          fee schedule disagrees with the gateway's, the truth becomes unreachable
          and settlements come back CONTRADICTED — measured: adding a ₹2 flat fee
          takes the share of true bundles that balance from 85% to 0%. That is the
          engine detecting a misconfigured rule, not a solver failing.</div>
        ${s.provenance ? `<div class=bd-note style="margin-top:8px">
          <b>${esc(s.provenance.rules_version)}</b> · ${esc(s.provenance.solver_version)}
          · ${esc(s.provenance.policy_version)}</div>` : ''}
      </div>`;
    },
  });

  defineWidget('solver', {
    title: 'Solver', category: 'Technical', w: 6, h: 2,
    blurb: 'throughput and reach',
    render: ({ summary: s }) => {
      if (!s) return none('run a reconciliation');
      return `<div class=bd-grid2>
        ${stat('wall clock', `${s.seconds}s`, `${s.settlements} settlements`)}
        ${stat('exact set match', `${(s.exact * 100).toFixed(1)}%`, 'complete truth recovered')}
        ${stat('orders', s.orders.toLocaleString(), 'candidate universe')}
        ${stat('rust kernel', 'active', 'two bitplanes, 52× at ₹80k', 'var(--ok)')}
      </div>`;
    },
  });
})();
