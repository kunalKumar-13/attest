/* COMPOSITION A — FINANCIAL TERMINAL
 *
 * Thesis: an operator watches this all day and reads it the way a trader reads
 * a book — by column, by alignment, by the shape of a number against its
 * neighbours. Density is the feature. Nothing scrolls that matters.
 *
 * The primary object is THE COLLAPSE. The spine is a full-width rail across the
 * top of every lens, with the money that survives each stage stated in a
 * monospaced column, so the eye lands on where the bar stops before it reads a
 * word. Every other lens hangs beneath that rail.
 *
 * Rules this composition holds itself to: no card unless it is an action or a
 * context object; hairlines only; every figure tabular; nothing centred.
 */
'use strict';

(() => {
  const { esc, rupees, short, pct, actorMark, verdictMark, plural } = window.KIT;
  const D = window.EXP_DATA;
  const rows = (a, f) => (a || []).map(f).join('');

  /* ---------------------------------------------------------- shell parts */
  const SubjectHeader = s => `
    <div class="a-hd">
      <div class="a-hd-id">
        <span class="a-id">${esc(s.id === 'portfolio' ? s.label : s.id)}</span>
        <span class="a-sub">${esc(s.sublabel || '')}</span>
      </div>
      <div class="a-hd-amt"><span class="num">${rupees(s.amount_paise)}</span>
        <span class="a-amt-l">${esc(s.amount_label || '')}</span></div>
      <div class="a-hd-meta">${rows(s.meta, m =>
        `<span class="a-mi"><i>${esc(m.k)}</i><b class="num">${esc(m.v)}</b></span>`)}</div>
    </div>`;

  const LensStrip = (lenses, active) => `
    <nav class="a-lens" aria-label="Lens">${rows(lenses, l =>
      `<button data-lens="${esc(l.key)}" class="${l.key === active ? 'on' : ''}"
        aria-current="${l.key === active ? 'true' : 'false'}"
        title="${esc(l.question)}"><span class="k">${esc(l.label)}</span></button>`)}
    </nav>`;

  /* THE COLLAPSE — the one thing this composition is built around. */
  const Spine = (spine) => {
    if (!spine || !spine.stages) return '';
    const top = Math.max(...spine.stages.map(s => s.continues_paise || 0), 1);
    return `<div class="a-spine" role="img"
      aria-label="Money flow: stopped at ${esc(spine.stopped_at || 'none')}">
      ${rows(spine.stages, (s, i) => {
        const w = pct(s.continues_paise || 0, top);
        const stop = spine.stopped_at === s.key;
        return `<div class="a-st ${stop ? 'stop' : ''} s-${esc(s.state)}">
          <div class="a-st-k">${esc(s.label)}</div>
          <div class="a-st-bar"><i style="width:${w.toFixed(2)}%"></i>${
            stop ? '<b class="a-cut" aria-hidden="true"></b>' : ''}</div>
          <div class="a-st-v num">${s.continues_paise ? short(s.continues_paise) : '—'}</div>
          <div class="a-st-d">${esc(s.detail || '')}</div>
        </div>`;
      })}
      ${spine.stopped_at ? `<div class="a-spine-note">stops at
        <b>${esc(spine.stopped_at)}</b></div>` : ''}
    </div>`;
  };

  const Panel = (title, body, cls) =>
    `<section class="a-pan ${cls || ''}"><h2>${esc(title)}</h2>${body}</section>`;

  /* ------------------------------------------------------------ CONTROL */
  const control = {
    label: 'Control', question: 'What is happening?',
    layout: s => s.type === 'portfolio' ? 'master-detail' : 'focus',
    async master(subject, S) {
      const { spine, actions, attention } = await D.control(subject, S);
      const acts = (actions && actions.actions) || [];
      const grps = (attention && attention.groups) || [];
      return Spine(spine)
        + Panel('What unblocks the most', `<table class="a-tbl a-acts">
          <thead><tr><th></th><th>action</th><th class="r">value unlocked</th>
            <th class="r">steps</th><th class="r">cases</th></tr></thead><tbody>${
          rows(acts, a => `<tr data-context="action:${esc(a.reason)}" tabindex="0">
            <td class="kind k-${esc(a.kind)}">${esc(a.kind)}</td>
            <td>${esc(a.what)}<div class="dim">${esc(a.why || '')}</div></td>
            <td class="r num big">${rupees(a.leverage_paise || a.value_paise)}</td>
            <td class="r num">${a.steps}</td>
            <td class="r num dim">${a.settlements}</td></tr>`)}</tbody></table>`)
        + Panel('Where it is stuck', `<table class="a-tbl"><tbody>${
          rows(grps, g => `<tr data-context="group:${esc(g.key)}" tabindex="0">
            <td>${esc(g.label)}<div class="dim">${esc(g.why || '')}</div></td>
            <td class="r num">${g.count}</td>
            <td class="r num big">${rupees(g.amount_paise)}</td></tr>`)}</tbody></table>`);
    },
    async render(subject, S) {
      const { spine, settlement } = await D.control(subject, S);
      const chk = (settlement && settlement.checks) || [];
      return Spine(spine) + Panel('Checks',
        `<table class="a-tbl"><tbody>${rows(chk, c =>
          `<tr><td class="mark">${c.ok ? '●' : '○'}</td><td>${esc(c.name)}</td>
           <td class="dim">${esc(c.detail || '')}</td></tr>`)}</tbody></table>`);
    },
    async context(ctx, S) {
      if (ctx.kind === 'action' || ctx.kind === 'group') {
        const { actions, attention } = await D.control(
          { type: 'portfolio', id: 'portfolio' }, S);
        const a = ((actions && actions.actions) || []).find(x => x.reason === ctx.id);
        const g = ((attention && attention.groups) || []).find(x => x.key === ctx.id);
        const o = a || g;
        if (!o) return null;
        return { title: esc(a ? a.reason : g.label), body: `
          <p class="a-ctx-why">${esc(o.rationale || o.why || '')}</p>
          <table class="a-tbl"><tbody>${rows(o.examples || o.items || [], x =>
            `<tr data-context="settlement:${esc(x.id || x)}" tabindex="0">
              <td class="mark">${verdictMark(x.verdict)}</td>
              <td>${esc(x.id || x)}</td>
              <td class="r num">${x.amount_paise ? rupees(x.amount_paise) : ''}</td>
            </tr>`)}</tbody></table>` };
      }
      if (ctx.kind !== 'settlement') return null;
      const d = await D.settlement(ctx.id, S);
      return { title: ctx.id, body: `
        <div class="a-ctx-amt num">${rupees(d.amount)}</div>
        <table class="a-tbl"><tbody>${rows(d.checks, c =>
          `<tr><td class="mark">${c.ok ? '●' : '○'}</td><td>${esc(c.name)}</td>
           <td class="dim">${esc(c.detail || '')}</td></tr>`)}</tbody></table>` };
    },
    emptyContext: 'Pick a row to inspect it.',
  };

  /* A settlement's accounting is its proof, balanced. The portfolio ledger is
   * the wrong object here: it answers "where did the money go" for 250 cases. */
  const settlementJournal = d => {
    const p = (d.proofs || [])[0];
    if (!p) return Panel('No entry is written',
      `<div class="a-empty"><b>Nothing is posted for this settlement.</b>
       <span>The verdict is ${esc(d.verdict)} — an entry needs a unique,
       kernel-checked explanation.</span></div>`);
    return Panel('What the entry would be', `
      <table class="a-tbl"><thead><tr><th>account</th><th class="r">debit</th>
        <th class="r">credit</th></tr></thead><tbody>
        <tr><td>Bank</td><td class="r num">${rupees(d.amount)}</td><td></td></tr>
        <tr><td>Gateway fee</td><td class="r num">${rupees(p.fee)}</td><td></td></tr>
        <tr><td>Receivables</td><td></td><td class="r num">${rupees(p.gross)}</td></tr>
      </tbody></table>
      <div class="a-agree">residual <b class="num">${p.residual}p</b>
        within <b class="num">±${p.tolerance}p</b>
        <span class="sep">·</span>
        <b class="num ${p.balances ? 'ok' : 'hot'}">${
          p.balances ? 'balances' : 'does not balance'}</b></div>`)
      + Panel('Why it is not written', `<div class="a-empty">
        <b>${esc(d.verdict)}</b><span>${(d.proofs || []).length} explanations
        satisfy the amount exactly. An entry may only be written from one.</span></div>`);
  };

  /* ------------------------------------------------------------ JOURNAL */
  const journal = {
    label: 'Journal', question: 'Where did the money go?', layout: 'focus',
    async render(subject, S) {
      const { spine, journal: j, settlement } = await D.journal(subject, S);
      if (settlement) return Spine(spine) + settlementJournal(settlement);
      const e = (j && j.totals) || {};
      return Spine(spine) + Panel('Accounting', `
        <div class="a-books">
          <div><i>posted</i><b class="num">${rupees(e.posted_paise || 0)}</b></div>
          <div><i>withheld</i><b class="num">${rupees(e.withheld_paise || 0)}</b></div>
          <div><i>balance</i><b class="num ${(e.balance_paise || 0) === 0 ? 'ok' : 'bad'}">${
            (e.balance_paise || 0) === 0 ? 'balanced' : rupees(e.balance_paise)}</b></div>
        </div>`)
        + Panel('Entries', `<table class="a-tbl"><thead><tr><th>account</th>
          <th class="r">debit</th><th class="r">credit</th></tr></thead><tbody>${
          rows((j && j.lines) || [], l =>
            `<tr><td>${esc(l.account)}</td>
             <td class="r num">${l.debit_paise ? rupees(l.debit_paise) : ''}</td>
             <td class="r num">${l.credit_paise ? rupees(l.credit_paise) : ''}</td></tr>`)
          }</tbody></table>`)
        + Panel('Refused', `<table class="a-tbl"><tbody>${
          rows((j && j.refusals) || [], r =>
            `<tr><td class="mark">⊘</td><td>${esc(r.settlement_id)}</td>
             <td class="dim">${esc(r.reason)}</td>
             <td class="r num">${rupees(r.amount_paise)}</td></tr>`)}</tbody></table>`);
    },
  };

  /* ----------------------------------------------------------- EVIDENCE */
  const evidence = {
    label: 'Evidence', question: 'Why should I believe this?', layout: 'focus',
    async render(subject, S) {
      const { spine, evidence: e } = await D.evidence(subject, S);
      const sp = e.space || {};
      const universe = sp.universe || (e.counts && e.counts[0] && e.counts[0].n) || 0;
      const cand = sp.candidates || 0;
      const band = `<div class="a-band" role="img"
        aria-label="${universe} orders reduced to ${cand} candidates">
        <div class="a-band-row"><span class="num">${universe.toLocaleString('en-IN')}</span>
          <i style="width:100%"></i><em>in the book</em></div>
        ${(() => {
          // CUMULATIVE. Each bar is what SURVIVES this cut, not what this cut
          // alone would leave — computed independently, a reduction removing 0
          // drew a full-width bar and read as if it had restored the pool.
          let left = universe;
          return rows(sp.reductions || e.reductions || [], r => {
            left = Math.max(0, left - (r.removed || 0));
            return `<div class="a-band-row red">
              <span class="num">−${(r.removed || 0).toLocaleString('en-IN')}</span>
              <i style="width:${pct(left, universe).toFixed(2)}%"
                 class="${r.deterministic ? 'det' : 'heu'}"></i>
              <em>${esc(r.name)} <b>${r.deterministic ? 'DETERMINISTIC' : 'CONVENTION'}</b></em>
            </div>`;
          });
        })()}
        <div class="a-band-row keep"><span class="num">${cand}</span>
          <i style="width:${pct(cand, universe).toFixed(2)}%"></i>
          <em>survive to the solver</em></div></div>`;

      const ex = e.explanations || [];
      const sh = e.shared || {};
      const exBlock = !ex.length ? '' : `
        <table class="a-tbl a-exp"><thead><tr><th></th><th class="r">orders</th>
          <th class="r">shared</th><th class="r">unique</th>
          <th class="r">net</th><th class="r">residual</th></tr></thead><tbody>${
        rows(ex, x => `<tr data-context="explanation:${esc(x.letter)}" tabindex="0">
          <td class="mark">${esc(x.letter)}</td>
          <td class="r num">${x.orders}</td><td class="r num dim">${x.shared}</td>
          <td class="r num hot">+${(x.unique || []).length}</td>
          <td class="r num">${rupees(x.net_paise)}</td>
          <td class="r num">${x.residual_paise}p ±${x.tolerance_paise}</td></tr>`)}</tbody></table>
        <div class="a-agree"><span class="num">${sh.n || 0}</span> agreed by all
          <b class="num">${rupees(sh.paise || 0)}</b>
          <span class="sep">·</span>
          <span class="num hot">${sh.differing || 0}</span> in dispute
          <b class="num hot">${rupees(sh.disputed_paise || 0)}</b></div>`;

      return Spine(spine) + Panel('The candidate universe', band)
        + (ex.length ? Panel(`${ex.length} explanations survive`, exBlock) : '')
        + Panel('Relationships', `<table class="a-tbl"><tbody>${
          rows((e.chain || []).slice(0, 8), c =>
            `<tr><td class="mark">${c.proven ? '●' : '◇'}</td>
             <td>${esc(c.kind)}</td><td class="dim">${esc(c.why || '')}</td>
             <td class="r num">${c.paise ? rupees(c.paise) : ''}</td></tr>`)}</tbody></table>`);
    },
  };

  evidence.context = async (ctx, S) => {
    const { evidence: e } = await D.evidence(S.subject, S);
    const x = (e.explanations || []).find(v => v.letter === ctx.id);
    if (!x) return null;
    return { title: `Explanation ${x.letter}`, body: `
      <div class="a-ctx-amt num">${rupees(x.net_paise)}</div>
      <p class="a-ctx-why">${x.orders} orders · ${x.shared} shared with every
        other explanation · ${(x.unique || []).length} unique to this one.</p>
      <table class="a-tbl"><tbody>${rows(x.unique || [], o =>
        `<tr data-context="order:${esc(o.id || o)}" tabindex="0">
          <td>${esc(o.id || o)}</td>
          <td class="r num">${o.paise ? rupees(o.paise) : ''}</td></tr>`)}</tbody></table>` };
  };

  /* -------------------------------------------------------- INVESTIGATE */
  const investigate = {
    label: 'Investigate', question: 'What should I check next?', layout: 'focus',
    async render(subject, S) {
      const { spine, investigation: v } = await D.investigate(subject, S);
      if (v.groups) return Spine(spine) + Panel(
        'Ordered by what an answer would unlock',
        `<table class="a-tbl"><thead><tr><th></th><th>question</th>
          <th class="r">unlocks</th><th class="r">cases</th></tr></thead><tbody>${
        rows(v.groups, g => `<tr data-context="group:${esc(g.reason)}" tabindex="0">
          <td class="kind k-${esc(g.kind)}">${esc(g.kind)}</td>
          <td>${esc(g.question)}<div class="dim">${esc(g.cause || '')}</div></td>
          <td class="r num big">${rupees(g.value_paise)}</td>
          <td class="r num dim">${g.settlements}</td></tr>`)}</tbody></table>`)
        + (v.note ? `<div class="a-out">${esc(v.note)}</div>` : '');
      const steps = v.steps || [];
      const qs = v.questions || [];
      return Spine(spine)
        + Panel(v.question || 'What should be investigated first?',
          steps.length ? `<table class="a-tbl a-trail"><tbody>${rows(steps, s =>
            `<tr class="ac-${esc(s.actor)}"><td class="mark">${actorMark(s.actor)}</td>
             <td class="ac">${esc(s.actor)}</td><td class="vb">${esc(s.action || '')}</td>
             <td>${esc(s.detail || '')}${s.result
               ? `<div class="dim">${esc(s.result)}</div>` : ''}</td></tr>`)}</tbody></table>`
          : `<table class="a-tbl"><tbody>${rows(qs, q =>
            `<tr><td>${esc(q.text || q.question || '')}</td>
             <td class="r num">${q.amount_paise ? rupees(q.amount_paise) : ''}</td>
             <td class="dim">${esc(q.hint || q.next || '')}</td></tr>`)}</tbody></table>`)
        + (v.state ? `<div class="a-out"><b>${esc(String(v.state).toUpperCase())}</b>
            ${esc(v.note || '')}</div>` : '')
        + (v.resolvers && v.resolvers.length ? Panel('What would resolve it',
          `<table class="a-tbl"><tbody>${rows(v.resolvers, r =>
            `<tr><td class="mark">${r.status === 'missing' ? '○' : '●'}</td>
             <td>${esc(r.what)}</td><td class="dim">${esc(r.would || '')}</td>
             <td class="r stt">${esc(r.status || '')}</td></tr>`)}</tbody></table>`) : '');
    },
  };

  /* ------------------------------------------------------------- POLICY */
  const policy = {
    label: 'Policy', question: 'What am I allowed to do?', layout: 'focus',
    async render(subject, S) {
      const { spine, decision: d } = await D.policy(subject, S);
      const total = (d.auto_post || 0) + (d.review || 0) + (d.block || 0);
      const bar = [['auto_post', d.auto_post, 'AUTO-POST'], ['review', d.review, 'REVIEW'],
                   ['block', d.block, 'BLOCK']];
      const priced = d.expected_loss_paise != null;
      return Spine(spine) + Panel('The boundary', `
        <div class="a-bound">
          ${rows(bar, b => `<div class="a-bd d-${b[0]}">
            <span class="l">${b[2]}</span>
            <i style="width:${pct(b[1] || 0, total).toFixed(2)}%"></i>
            <b class="num">${b[1] || 0}</b></div>`)}
        </div>
        <table class="a-tbl"><tbody>
          <tr><td>expected loss</td><td class="r num">${
            priced ? rupees(d.expected_loss_paise) : '<em class="unp">UNPRICED</em>'}</td></tr>
          <tr><td>cost of checking</td><td class="r num">${rupees(d.review_paise)}</td></tr>
          <tr><td>exposure ceiling</td><td class="r num">${rupees(d.exposure_paise)}</td></tr>
          <tr><td>money protected</td><td class="r num">${rupees(d.protected_paise)}</td></tr>
          <tr><td>wrongly posted</td><td class="r num ${d.wrong_posts ? 'bad' : 'ok'}">${
            d.wrong_posts || 0}</td></tr>
        </tbody></table>`)
        + (d.strata ? Panel('Priced by stratum', `<table class="a-tbl"><thead><tr>
            <th>stratum</th><th class="r">wrong</th><th class="r">of</th>
            <th class="r">priced</th></tr></thead><tbody>${rows(d.strata, s =>
            `<tr><td>${esc(s.key)}</td><td class="r num">${s.wrong}</td>
             <td class="r num dim">${s.total}</td>
             <td class="r num">${s.priced == null ? '<em class="unp">UNPRICED</em>'
               : (s.priced * 100).toFixed(1) + '%'}</td></tr>`)}</tbody></table>`) : '');
    },
  };

  /* ----------------------------------------------------------- ACTIVITY */
  const activity = {
    label: 'Activity', question: 'What actually happened?', layout: 'focus',
    async render(subject, S) {
      const { spine, activity: a } = await D.activity(subject, S);
      if (a.deliveries) {
        const dc = a.delivery_counts || {};
        return Spine(spine)
          + Panel('How this run ended', `<div class="a-books">${
            rows(a.outcome, o => `<div><i>${esc(o.k)}</i>
              <b class="num">${esc(o.v)}</b></div>`)}</div>`)
          + Panel('Events delivered', `<table class="a-tbl"><thead><tr><th></th>
              <th>event</th><th>status</th><th class="r">affected</th>
              <th class="r">received</th></tr></thead><tbody>${
            rows(a.deliveries, d => `<tr class="dl-${esc(d.status)}">
              <td class="mark">${d.status === 'accepted' ? '●'
                : d.status === 'duplicate' ? '◑' : '⊘'}</td>
              <td>${esc(d.kind)}<div class="dim">${esc(d.detail || '')}</div></td>
              <td class="stt">${esc(d.status)}</td>
              <td class="r num">${d.affected == null ? '' : d.affected}</td>
              <td class="r num dim">${esc(d.received_at || '')}</td></tr>`)}</tbody></table>`)
          + Panel('Unrevised', (a.unrevised || []).length
            ? `<table class="a-tbl"><tbody>${rows(a.unrevised, u =>
                `<tr><td>${esc(u.id || u)}</td></tr>`)}</tbody></table>`
            : `<div class="a-empty"><b>No unrevised settlements.</b>
               <span>${esc(a.unrevised_note || '')}</span></div>`);
      }
      const ev = a.events || [];
      const st = a.state || {};
      return Spine(spine)
        + (st.verdict ? Panel('Where it ended up', `<div class="a-books">
            <div><i>verdict</i><b>${esc(st.verdict)}</b></div>
            <div><i>decision</i><b>${esc(st.decision || '—')}</b></div>
            <div><i>posted</i><b class="${st.posted ? 'ok' : 'bad'}">${
              st.posted ? 'yes' : 'not posted'}</b></div></div>`) : '')
        + Panel(`${plural(ev.length, 'event')} this run`,
        `<table class="a-tbl a-evs"><tbody>${rows(ev, e =>
          `<tr class="ac-${esc(e.actor)}"><td class="mark">${actorMark(e.actor)}</td>
           <td class="ac">${esc(e.actor)}</td>
           <td class="vb">${esc(e.stage || '')}</td>
           <td>${esc(e.what || '')}${e.value ? ` <b class="num">${esc(e.value)}</b>` : ''}
             ${e.caused_by ? `<div class="dim">because ${esc(e.caused_by)}</div>` : ''}
             ${e.effect ? `<div class="dim">${esc(e.effect)}</div>` : ''}</td>
           <td class="r num dim">${esc(e.at || '')}</td></tr>`)}</tbody></table>`);
    },
  };

  /* -------------------------------------------------------------- TRUST */
  const trust = {
    label: 'Trust', question: 'Can I believe the system itself?',
    subjects: ['portfolio'], layout: 'focus',
    async render(subject, S) {
      if (subject.type !== 'portfolio')
        return `<div class="a-decline"><b>Trust is a property of the system.</b>
          Not of one settlement. Open it on the portfolio.</div>`;
      const { spine, claims: c } = await D.trust(subject, S);
      const cl = c.claims || [];
      const bad = cl.filter(x => x.status !== 'MEASURED');
      const ok = cl.filter(x => x.status === 'MEASURED');
      const tbl = list => `<table class="a-tbl a-claims"><tbody>${rows(list, x =>
        `<tr class="st-${esc(x.status)}"><td class="mark">${
           x.status === 'MEASURED' ? '●' : x.status === 'REJECTED' ? '⊘'
           : x.status === 'LIMITED' ? '◑' : '○'}</td>
         <td class="cid num">${esc(x.id)}</td>
         <td>${esc(x.text)}<div class="dim">${esc(x.artifact || '')}</div></td>
         <td class="r num">${esc(x.value || '—')}</td>
         <td class="stt">${esc(x.status)}</td></tr>`)}</tbody></table>`;
      return Spine(spine)
        + Panel(`${bad.length} claims this system will not make`, tbl(bad))
        + Panel(`${ok.length} measured`, tbl(ok));
    },
  };

  window.COMPOSITION = {
    id: 'A', name: 'Financial terminal',
    C: {
      esc, SubjectHeader, LensStrip,
      ContextChrome: (title, body) =>
        `<div class="a-ctx"><header>${esc(title)}</header><div>${body}</div></div>`,
      EmptyState: (what, why) =>
        `<div class="a-empty"><b>${esc(what)}</b><span>${esc(why || '')}</span></div>`,
      ErrorState: msg => `<div class="a-err"><b>${esc(msg)}</b></div>`,
      LoadingState: () => `<div class="a-load" aria-busy="true">
        <i></i><i></i><i></i></div>`,
    },
    lenses: { control, journal, evidence, investigate, policy, activity, trust },
  };
})();
