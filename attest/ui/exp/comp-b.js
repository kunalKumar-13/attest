/* COMPOSITION B — SPATIAL INVESTIGATION DESK
 *
 * Thesis: a case is a physical thing on a desk. It has a spine you can see
 * down the left edge, documents laid on a surface, and objects you pick up.
 * Picking one up does not take you elsewhere — it lifts out of the page you
 * were already reading, and putting it down leaves you where you were.
 *
 * The primary object is THE CASE. The spine is a structural column with real
 * thickness that narrows stage by stage, so the collapse is felt as a physical
 * taper rather than read as five bars. Motion is used more heavily here than in
 * A, and every use of it models an object moving, never a page changing.
 */
'use strict';

(() => {
  const { esc, rupees, short, pct, actorMark, verdictMark, plural } = window.KIT;
  const D = window.EXP_DATA;
  const rows = (a, f) => (a || []).map(f).join('');

  const SubjectHeader = s => `
    <div class="b-case">
      <div class="b-tab">${esc(s.type === 'portfolio' ? 'PORTFOLIO' : 'CASE')}</div>
      <div class="b-case-body">
        <div class="b-case-id">${esc(s.id === 'portfolio' ? s.label : s.id)}
          <em>${esc(s.sublabel || '')}</em></div>
        <div class="b-case-amt num">${rupees(s.amount_paise)}
          <em>${esc(s.amount_label || '')}</em></div>
      </div>
      <div class="b-case-meta">${rows(s.meta, m =>
        `<span><i>${esc(m.k)}</i> <b class="num">${esc(m.v)}</b></span>`)}</div>
    </div>`;

  const LensStrip = (lenses, active) => `
    <div class="b-keys" aria-label="Lens">${rows(lenses, l =>
      `<button data-lens="${esc(l.key)}" class="${l.key === active ? 'on' : ''}"
        title="${esc(l.question)}"><span class="n">${esc(l.label)}</span>
        <span class="q">${esc(l.question)}</span></button>`)}</div>`;

  /* The structural spine — a column that physically narrows where value stops. */
  const Spine = spine => {
    if (!spine || !spine.stages) return '';
    const top = Math.max(...spine.stages.map(s => s.continues_paise || 0), 1);
    return `<div class="b-spine" role="img"
      aria-label="Money flow: stopped at ${esc(spine.stopped_at || 'none')}">
      ${rows(spine.stages, s => {
        const w = Math.max(2, pct(s.continues_paise || 0, top));
        const stop = spine.stopped_at === s.key;
        return `<div class="b-seg ${stop ? 'stop' : ''}">
          <div class="b-seg-col"><i style="width:${w.toFixed(1)}%"></i></div>
          <div class="b-seg-t"><b>${esc(s.label)}</b>
            <span class="num">${s.continues_paise ? short(s.continues_paise) : '—'}</span>
            <em>${esc(s.detail || '')}</em></div>
        </div>`;
      })}</div>`;
  };

  const Doc = (title, body, cls) => `<article class="b-doc ${cls || ''}">
    <h2>${esc(title)}</h2>${body}</article>`;
  const Line = (a, b, c, ctx) => `<div class="b-line"${
    ctx ? ` data-context="${esc(ctx)}" tabindex="0"` : ''}>
    <span class="b-l-a">${a}</span><span class="b-l-b">${b || ''}</span>
    <span class="b-l-c num">${c || ''}</span></div>`;

  const withSpine = (spine, body) =>
    `<div class="b-desk">${Spine(spine)}<div class="b-surface">${body}</div></div>`;

  const control = {
    label: 'Control', question: 'What is happening?',
    layout: s => s.type === 'portfolio' ? 'master-detail' : 'focus',
    async master(subject, S) {
      const { spine, actions, attention } = await D.control(subject, S);
      const acts = (actions && actions.actions) || [];
      const grps = (attention && attention.groups) || [];
      return withSpine(spine,
        Doc('What unblocks the most', rows(acts, a =>
          `<div class="b-act k-${esc(a.kind)}" data-context="action:${esc(a.reason)}"
             tabindex="0"><div class="b-act-k">${esc(a.kind)}</div>
            <div class="b-act-w">${esc(a.what)}<em>${esc(a.why || '')}</em></div>
            <div class="b-act-v num">${rupees(a.leverage_paise || a.value_paise)}
              <em>${plural(a.steps, 'step')} · ${a.settlements} cases</em></div>
          </div>`))
        + Doc('Where it is stuck', rows(grps, g =>
          Line(`${esc(g.label)}<em>${esc(g.why || '')}</em>`,
               `${g.count} cases`, rupees(g.amount_paise), `group:${g.key}`))));
    },
    async render(subject, S) {
      const { spine, settlement } = await D.control(subject, S);
      return withSpine(spine, Doc('Checks',
        rows((settlement && settlement.checks) || [], c =>
          Line(`<b class="m">${c.ok ? '●' : '○'}</b> ${esc(c.name)}`,
               `<em>${esc(c.detail || '')}</em>`, ''))));
    },
    async context(ctx, S) {
      if (ctx.kind === 'settlement') {
        const d = await D.settlement(ctx.id, S);
        return { title: ctx.id, body: `<div class="b-obj-amt num">${rupees(d.amount)}</div>
          ${rows(d.checks, c => Line(`<b class="m">${c.ok ? '●' : '○'}</b> ${esc(c.name)}`,
            `<em>${esc(c.detail || '')}</em>`, ''))}` };
      }
      const { actions, attention } = await D.control(
        { type: 'portfolio', id: 'portfolio' }, S);
      const o = ((actions && actions.actions) || []).find(x => x.reason === ctx.id)
             || ((attention && attention.groups) || []).find(x => x.key === ctx.id);
      if (!o) return null;
      return { title: esc(o.reason || o.label), body:
        `<p class="b-why">${esc(o.rationale || o.why || '')}</p>
         ${rows(o.examples || o.items || [], x => Line(
           `${verdictMark(x.verdict)} ${esc(x.id || x)}`, '',
           x.amount_paise ? rupees(x.amount_paise) : '', `settlement:${x.id || x}`))}` };
    },
  };

  const journal = {
    label: 'Journal', question: 'Where did the money go?', layout: 'focus',
    async render(subject, S) {
      const { spine, journal: j, settlement } = await D.journal(subject, S);
      if (settlement) {
        const p = (settlement.proofs || [])[0];
        return withSpine(spine, !p
          ? Doc('No entry', `<p class="b-why">Nothing is posted. The verdict is
              ${esc(settlement.verdict)}.</p>`)
          : Doc('The entry this proof implies',
              Line('Bank', '', rupees(settlement.amount))
            + Line('Gateway fee', '', rupees(p.fee))
            + Line('Receivables', '<em>credit</em>', rupees(p.gross))
            + `<div class="b-resid">residual <b class="num">${p.residual}p</b>
                within <b class="num">±${p.tolerance}p</b></div>`)
          + Doc('Why it is not written', `<p class="b-why">${
              (settlement.proofs || []).length} explanations satisfy the amount
              exactly. An entry may only be written from one.</p>`));
      }
      const t = (j && j.totals) || {};
      return withSpine(spine, Doc('Today’s accounting',
          Line('Posted', '', rupees(t.posted_paise || 0))
        + Line('Withheld', '', rupees(t.withheld_paise || 0))
        + Line('Balance', '', (t.balance_paise || 0) === 0 ? 'balanced' : rupees(t.balance_paise)))
        + Doc('Refused', rows((j && j.refusals) || [], r =>
            Line(`⊘ ${esc(r.settlement_id)}`, `<em>${esc(r.reason)}</em>`,
                 rupees(r.amount_paise)))));
    },
  };

  const evidence = {
    label: 'Evidence', question: 'Why should I believe this?', layout: 'focus',
    async render(subject, S) {
      const { spine, evidence: e } = await D.evidence(subject, S);
      const sp = e.space || {};
      const uni = sp.universe || (e.counts && e.counts[0] && e.counts[0].n) || 0;
      const cand = sp.candidates || 0;
      /* A funnel with physical width: the book narrows to the pool. */
      const funnel = `<div class="b-funnel" role="img"
        aria-label="${uni} orders reduced to ${cand} candidates">
        <div class="b-fn"><i style="width:100%"></i>
          <b class="num">${uni.toLocaleString('en-IN')}</b><em>in the book</em></div>
        ${rows(sp.reductions || e.reductions || [], r => {
          const w = pct(uni - (r.removed || 0), uni);
          return `<div class="b-fn cut"><i style="width:${w.toFixed(2)}%"
            class="${r.deterministic ? 'det' : 'heu'}"></i>
            <b class="num">−${(r.removed || 0).toLocaleString('en-IN')}</b>
            <em>${esc(r.name)} · ${r.deterministic ? 'deterministic' : 'convention'}</em></div>`;
        })}
        <div class="b-fn keep"><i style="width:${Math.max(1.5, pct(cand, uni)).toFixed(2)}%"></i>
          <b class="num">${cand}</b><em>reach the solver</em></div></div>`;
      const ex = e.explanations || [], sh = e.shared || {};
      return withSpine(spine, Doc('What was considered', funnel)
        + (ex.length ? Doc(`${ex.length} explanations survive`,
            rows(ex, x => `<div class="b-exp" data-context="explanation:${esc(x.letter)}"
              tabindex="0"><span class="b-exp-l">${esc(x.letter)}</span>
              <span class="b-exp-bar"><i class="sh" style="width:${pct(x.shared, x.orders)}%"></i>
                <i class="uq" style="width:${pct((x.unique || []).length, x.orders)}%"></i></span>
              <span class="b-exp-n num">${x.shared} shared
                <b>+${(x.unique || []).length}</b></span>
              <span class="b-exp-v num">${rupees(x.net_paise)}</span></div>`)
            + `<div class="b-agree"><b class="num">${sh.n || 0}</b> orders agreed by all
                — <b class="num">${rupees(sh.paise || 0)}</b> is not in question.
                <span class="hot"><b class="num">${sh.differing || 0}</b> disputed,
                <b class="num">${rupees(sh.disputed_paise || 0)}</b>.</span></div>`) : ''));
    },
    async context(ctx, S) {
      const { evidence: e } = await D.evidence(S.subject, S);
      const x = (e.explanations || []).find(v => v.letter === ctx.id);
      if (!x) return null;
      return { title: `Explanation ${x.letter}`, body:
        `<div class="b-obj-amt num">${rupees(x.net_paise)}</div>
         <p class="b-why">${x.orders} orders · ${x.shared} shared with every other
           explanation · ${(x.unique || []).length} unique to this one.</p>
         ${rows(x.unique || [], o => Line(esc(o.id || o), '',
           o.paise ? rupees(o.paise) : '', `order:${o.id || o}`))}` };
    },
  };

  const investigate = {
    label: 'Investigate', question: 'What should I check next?', layout: 'focus',
    async render(subject, S) {
      const { spine, investigation: v } = await D.investigate(subject, S);
      if (v.groups) return withSpine(spine,
        Doc('Ordered by what an answer would unlock', rows(v.groups, g =>
          `<div class="b-act k-${esc(g.kind)}" data-context="group:${esc(g.reason)}"
             tabindex="0"><div class="b-act-k">${esc(g.kind)}</div>
            <div class="b-act-w">${esc(g.question)}<em>${esc(g.cause || '')}</em></div>
            <div class="b-act-v num">${rupees(g.value_paise)}
              <em>${g.settlements} cases</em></div></div>`))
        + (v.note ? Doc('Why this order', `<p class="b-why">${esc(v.note)}</p>`) : ''));
      const steps = v.steps || [], qs = v.questions || [];
      return withSpine(spine, Doc(v.question || 'What should be investigated first?',
        steps.length
          ? `<div class="b-trail">${rows(steps, s =>
              `<div class="b-tr ac-${esc(s.actor)}">
                 <span class="b-tr-m">${actorMark(s.actor)}</span>
                 <span class="b-tr-a">${esc(s.actor)}</span>
                 <span class="b-tr-v">${esc(s.action || '')}</span>
                 <span class="b-tr-d">${esc(s.detail || '')}${
                   s.result ? `<em>${esc(s.result)}</em>` : ''}</span></div>`)}</div>`
          : rows(qs, q => Line(esc(q.text || q.question || ''),
              `<em>${esc(q.hint || q.next || '')}</em>`,
              q.amount_paise ? rupees(q.amount_paise) : '')))
        + (v.state ? Doc(String(v.state).toUpperCase(),
            `<p class="b-why">${esc(v.note || '')}</p>`, 'b-verdict') : '')
        + (v.resolvers ? Doc('What would resolve it', rows(v.resolvers, r =>
            Line(`<b class="m">${r.status === 'missing' ? '○' : '●'}</b> ${esc(r.what)}`,
                 `<em>${esc(r.would || '')}</em>`, esc(r.status || '')))) : ''));
    },
  };

  const policy = {
    label: 'Policy', question: 'What am I allowed to do?', layout: 'focus',
    async render(subject, S) {
      const { spine, decision: d } = await D.policy(subject, S);
      const total = (d.auto_post || 0) + (d.review || 0) + (d.block || 0);
      const priced = d.expected_loss_paise != null;
      return withSpine(spine, Doc('The boundary', `
        <div class="b-gate">
          <div class="b-gate-side auto"><b class="num">${d.auto_post || 0}</b>
            <em>AUTOMATE</em></div>
          <div class="b-gate-bar"><i class="a" style="width:${pct(d.auto_post, total)}%"></i>
            <i class="r" style="width:${pct(d.review, total)}%"></i>
            <i class="b" style="width:${pct(d.block, total)}%"></i></div>
          <div class="b-gate-side rev"><b class="num">${d.review || 0}</b>
            <em>REVIEW</em></div>
        </div>
        ${Line('expected loss', '', priced ? rupees(d.expected_loss_paise)
          : '<span class="unp">UNPRICED</span>')}
        ${Line('cost of checking', '', rupees(d.review_paise))}
        ${Line('money protected', '', rupees(d.protected_paise))}
        ${Line('wrongly posted', '', String(d.wrong_posts || 0))}`)
        + (d.strata ? Doc('Priced by stratum', rows(d.strata, s =>
            Line(esc(s.key), `<em>${s.wrong} wrong of ${s.total}</em>`,
              s.priced == null ? '<span class="unp">UNPRICED</span>'
                : (s.priced * 100).toFixed(1) + '%'))) : ''));
    },
  };

  const activity = {
    label: 'Activity', question: 'What actually happened?', layout: 'focus',
    async render(subject, S) {
      const { spine, activity: a } = await D.activity(subject, S);
      if (a.deliveries) return withSpine(spine,
        Doc('How this run ended', rows(a.outcome, o =>
          Line(esc(o.k), '', esc(o.v))))
        + Doc('Events delivered', `<div class="b-chain">${rows(a.deliveries, d =>
            `<div class="b-ce dl-${esc(d.status)}"><span class="b-ce-m">${
               d.status === 'accepted' ? '●' : d.status === 'duplicate' ? '◑' : '⊘'}</span>
              <div class="b-ce-b"><span class="b-ce-a">${esc(d.provider)}
                <em>${esc(d.status)}</em></span>
                <div class="b-ce-w">${esc(d.kind)}</div>
                ${d.detail ? `<div class="b-ce-e">${esc(d.detail)}</div>` : ''}</div>
              <span class="b-ce-t num">${esc(d.received_at || '')}</span></div>`)}</div>`)
        + Doc('Unrevised', (a.unrevised || []).length
          ? rows(a.unrevised, u => Line(esc(u.id || u), '', ''))
          : `<div class="b-empty"><b>No unrevised settlements.</b>
             <span>${esc(a.unrevised_note || '')}</span></div>`));
      const ev = a.events || [], st = a.state || {};
      return withSpine(spine,
        (st.verdict ? Doc('Where it ended up',
          Line('verdict', '', esc(st.verdict)) + Line('decision', '', esc(st.decision || '—'))
          + Line('posted', '', st.posted ? 'yes' : 'not posted')) : '')
        + Doc(`${plural(ev.length, 'event')} this run`,
          `<div class="b-chain">${rows(ev, e =>
            `<div class="b-ce ac-${esc(e.actor)}" data-context="event:${esc(e.at)}"
               tabindex="0"><span class="b-ce-m">${actorMark(e.actor)}</span>
              <div class="b-ce-b"><span class="b-ce-a">${esc(e.actor)}
                <em>${esc(e.stage || '')}</em></span>
                <div class="b-ce-w">${esc(e.what || '')}${
                  e.value ? ` <b class="num">${esc(e.value)}</b>` : ''}</div>
                ${e.caused_by ? `<div class="b-ce-c">because ${esc(e.caused_by)}</div>` : ''}
                ${e.effect ? `<div class="b-ce-e">${esc(e.effect)}</div>` : ''}</div>
              <span class="b-ce-t num">${esc(e.at || '')}</span></div>`)}</div>`));
    },
  };

  const trust = {
    label: 'Trust', question: 'Can I believe the system itself?',
    subjects: ['portfolio'], layout: 'focus',
    async render(subject, S) {
      const { spine, claims: c } = await D.trust(subject, S);
      if (subject.type !== 'portfolio')
        return withSpine(spine, Doc('Trust is a property of the system',
          `<p class="b-why">Not of one settlement. Open it on the portfolio.</p>`));
      const cl = c.claims || [];
      const bad = cl.filter(x => x.status !== 'MEASURED');
      const ok = cl.filter(x => x.status === 'MEASURED');
      const card = x => `<div class="b-claim st-${esc(x.status)}"
        data-context="claim:${esc(x.id)}" tabindex="0">
        <span class="b-cl-s">${esc(x.status)}</span>
        <div class="b-cl-t">${esc(x.text)}</div>
        <div class="b-cl-a">${esc(x.artifact || '')}</div>
        <div class="b-cl-v num">${esc(x.value || '—')}</div></div>`;
      return withSpine(spine,
        Doc(`${bad.length} claims this system will not make`, rows(bad, card), 'b-bad')
        + Doc(`${ok.length} measured`, rows(ok, card)));
    },
  };

  window.COMPOSITION = {
    id: 'B', name: 'Spatial investigation desk',
    C: {
      esc, SubjectHeader, LensStrip,
      ContextChrome: (title, body) => `<div class="b-obj">
        <header><span class="b-obj-h">${esc(title)}</span></header>
        <div class="b-obj-b">${body}</div></div>`,
      EmptyState: (what, why) => `<div class="b-empty"><b>${esc(what)}</b>
        <span>${esc(why || '')}</span></div>`,
      ErrorState: msg => `<div class="b-err"><b>${esc(msg)}</b></div>`,
      LoadingState: () => `<div class="b-load" aria-busy="true">
        <i></i><i></i><i></i><i></i></div>`,
    },
    lenses: { control, journal, evidence, investigate, policy, activity, trust },
  };
})();
