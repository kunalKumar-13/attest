/* COMPOSITION C — MINIMAL EVIDENCE WORKSPACE
 *
 * Thesis: restraint is a trust signal. An instrument that does not decorate its
 * findings is easier to believe than one that does.
 *
 * Every lens is a proof sheet with the same three-beat structure —
 *
 *     CLAIM        what this lens asserts
 *       ↓
 *     EVIDENCE     what supports or undermines it
 *       ↓
 *     VERDICT      what follows, including what does not
 *
 * — but the EVIDENCE beat is a different instrument in each lens, which is what
 * keeps them distinguishable without chrome. State is carried by geometry:
 * indent, rule weight, and whether a mark is hollow or filled. There are no
 * cards. There is almost no colour.
 */
'use strict';

(() => {
  const { esc, rupees, short, pct, actorMark, verdictMark, plural } = window.KIT;
  const D = window.EXP_DATA;
  const rows = (a, f) => (a || []).map(f).join('');

  const SubjectHeader = s => `
    <div class="c-sub">
      <div class="c-sub-l">
        <h1>${esc(s.id === 'portfolio' ? s.label : s.id)}</h1>
        <p>${esc(s.sublabel || '')}</p>
      </div>
      <div class="c-sub-amt num">${rupees(s.amount_paise)}</div>
      <div class="c-sub-m">${rows(s.meta, m =>
        `<span>${esc(m.k)} <b class="num">${esc(m.v)}</b></span>`)}</div>
    </div>`;

  const LensStrip = (lenses, active) => `
    <div class="c-idx">${rows(lenses, (l, i) =>
      `<button data-lens="${esc(l.key)}" class="${l.key === active ? 'on' : ''}">
        <span class="i num">${String(i + 1).padStart(2, '0')}</span>
        <span class="n">${esc(l.label)}</span></button>`)}</div>`;

  /* The ruler: a single measured line, ticked where each stage ends. */
  const Spine = spine => {
    if (!spine || !spine.stages) return '';
    const top = Math.max(...spine.stages.map(s => s.continues_paise || 0), 1);
    return `<div class="c-ruler" role="img"
      aria-label="Money flow: stopped at ${esc(spine.stopped_at || 'none')}">
      ${rows(spine.stages, s => {
        const w = pct(s.continues_paise || 0, top);
        const stop = spine.stopped_at === s.key;
        return `<div class="c-tick ${stop ? 'stop' : ''}">
          <div class="c-tick-l">${esc(s.label)}</div>
          <div class="c-tick-r"><i style="width:${w.toFixed(2)}%"></i></div>
          <div class="c-tick-v num">${s.continues_paise ? short(s.continues_paise) : '—'}</div>
        </div>`;
      })}</div>`;
  };

  /* The three-beat sheet. `claim` is a sentence; `verdict` may be a refusal. */
  const Sheet = ({ claim, evidence, verdict, instrument }) => `
    <div class="c-sheet ${instrument ? 'in-' + instrument : ''}">
      <div class="c-claim">${claim}</div>
      <div class="c-ev">${evidence}</div>
      ${verdict ? `<div class="c-verdict">${verdict}</div>` : ''}
    </div>`;

  const Item = (a, b, c, ctx) => `<div class="c-item"${
    ctx ? ` data-context="${esc(ctx)}" tabindex="0"` : ''}>
    <span>${a}</span><span class="c-i-b">${b || ''}</span>
    <span class="c-i-c num">${c || ''}</span></div>`;

  const wrap = (spine, sheet) => Spine(spine) + sheet;

  const control = {
    label: 'Control', question: 'What is happening?',
    layout: s => s.type === 'portfolio' ? 'master-detail' : 'focus',
    async master(subject, S) {
      const { spine, actions, attention } = await D.control(subject, S);
      const acts = (actions && actions.actions) || [];
      const stopped = (spine && spine.stopped_at) || '—';
      return wrap(spine, Sheet({
        instrument: 'flow',
        claim: `Value stops at <b>${esc(stopped)}</b>.`,
        evidence: rows((attention && attention.groups) || [], g =>
          Item(`${esc(g.label)}<em>${esc(g.why || '')}</em>`,
               `${g.count} cases`, rupees(g.amount_paise), `group:${g.key}`)),
        verdict: `<div class="c-v-h">What moves the most value</div>` + rows(acts, a =>
          Item(`${esc(a.what)}<em>${esc(a.rationale || a.why || '')}</em>`,
               `${plural(a.steps, 'step')}`, rupees(a.leverage_paise || a.value_paise),
               `action:${a.reason}`)),
      }));
    },
    async render(subject, S) {
      const { spine, settlement } = await D.control(subject, S);
      const d = settlement || {};
      const failed = (d.checks || []).filter(c => !c.ok);
      return wrap(spine, Sheet({
        instrument: 'flow',
        claim: `This settlement is <b>${esc(d.verdict || '')}</b>.`,
        evidence: rows(d.checks || [], c =>
          Item(`<b class="m ${c.ok ? 'y' : 'n'}">${c.ok ? '●' : '○'}</b> ${esc(c.name)}`,
               `<em>${esc(c.detail || '')}</em>`, '')),
        verdict: failed.length
          ? `<b>${plural(failed.length, 'check')} did not pass.</b>
             ${esc(failed[0].detail || '')}`
          : `<b>Every check passed.</b>`,
      }));
    },
    async context(ctx, S) {
      if (ctx.kind === 'settlement') {
        const d = await D.settlement(ctx.id, S);
        return { title: ctx.id, body: `<div class="c-o-amt num">${rupees(d.amount)}</div>
          ${rows(d.checks, c => Item(
            `<b class="m ${c.ok ? 'y' : 'n'}">${c.ok ? '●' : '○'}</b> ${esc(c.name)}`,
            `<em>${esc(c.detail || '')}</em>`, ''))}` };
      }
      const { actions, attention } = await D.control(
        { type: 'portfolio', id: 'portfolio' }, S);
      const o = ((actions && actions.actions) || []).find(x => x.reason === ctx.id)
             || ((attention && attention.groups) || []).find(x => x.key === ctx.id);
      if (!o) return null;
      return { title: esc(o.reason || o.label), body: `<p>${esc(o.rationale || o.why || '')}</p>
        ${rows(o.examples || o.items || [], x => Item(
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
        return wrap(spine, Sheet({
          instrument: 'ledger',
          claim: p ? `An entry for <b class="num">${rupees(settlement.amount)}</b>
                      would balance.` : `No entry can be written.`,
          evidence: !p ? '' :
              Item('Bank', 'debit', rupees(settlement.amount))
            + Item('Gateway fee', 'debit', rupees(p.fee))
            + Item('Receivables', 'credit', rupees(p.gross))
            + `<div class="c-rule"></div>`
            + Item('Residual', `<em>within ±${p.tolerance} paise</em>`, `${p.residual}p`),
          verdict: `<b>It is not written.</b> ${(settlement.proofs || []).length}
            explanations satisfy the amount exactly, and an entry may only be
            written from one.`,
        }));
      }
      const t = (j && j.totals) || {};
      return wrap(spine, Sheet({
        instrument: 'ledger',
        claim: `The books balance.`,
        evidence: Item('Posted', '', rupees(t.posted_paise || 0))
          + Item('Withheld', '', rupees(t.withheld_paise || 0))
          + `<div class="c-rule"></div>`
          + Item('Balance', '', (t.balance_paise || 0) === 0
              ? 'balanced' : rupees(t.balance_paise)),
        verdict: `<div class="c-v-h">Refused</div>` + rows((j && j.refusals) || [], r =>
          Item(`${esc(r.settlement_id)}`, `<em>${esc(r.reason)}</em>`,
               rupees(r.amount_paise))),
      }));
    },
  };

  const evidence = {
    label: 'Evidence', question: 'Why should I believe this?', layout: 'focus',
    async render(subject, S) {
      const { spine, evidence: e } = await D.evidence(subject, S);
      const sp = e.space || {};
      const uni = sp.universe || (e.counts && e.counts[0] && e.counts[0].n) || 0;
      const cand = sp.candidates || 0;
      const ex = e.explanations || [], sh = e.shared || {};
      /* The compression is a stepped rule: each cut is a shorter line. */
      const compress = `<div class="c-comp" role="img"
        aria-label="${uni} orders reduced to ${cand} candidates">
        <div class="c-cm"><b class="num">${uni.toLocaleString('en-IN')}</b>
          <i style="width:100%"></i><em>in the book</em></div>
        ${rows(sp.reductions || e.reductions || [], r => {
          const w = pct(uni - (r.removed || 0), uni);
          return `<div class="c-cm ${r.deterministic ? '' : 'assume'}">
            <b class="num">−${(r.removed || 0).toLocaleString('en-IN')}</b>
            <i style="width:${w.toFixed(2)}%"></i>
            <em>${esc(r.name)}${r.deterministic ? '' : ' — an assumption'}</em></div>`;
        })}
        <div class="c-cm keep"><b class="num">${cand}</b>
          <i style="width:${Math.max(1, pct(cand, uni)).toFixed(2)}%"></i>
          <em>reach the solver</em></div></div>`;
      return wrap(spine, Sheet({
        instrument: 'proof',
        claim: subject.type === 'portfolio'
          ? `${uni.toLocaleString('en-IN')} orders were in the book. Most were
             removed before any solving happened.`
          : sp.claim ? esc(sp.claim)
          : `${cand} of ${uni.toLocaleString('en-IN')} orders could explain this credit.`,
        evidence: compress + (!ex.length ? '' : `<div class="c-exps">${rows(ex, x =>
          `<div class="c-exp" data-context="explanation:${esc(x.letter)}" tabindex="0">
            <span class="c-exp-l">${esc(x.letter)}</span>
            <div class="c-exp-b">
              <div class="c-exp-n"><span class="num">${x.shared}</span> shared</div>
              <div class="c-exp-u"><span class="num">+${(x.unique || []).length}</span> unique</div>
              <div class="c-exp-r"></div>
              <div class="c-exp-v num">${rupees(x.net_paise)}</div>
            </div></div>`)}</div>`),
        verdict: !ex.length ? '' : `<b>Not unique.</b>
          <b class="num">${sh.n || 0}</b> orders are in every explanation —
          <b class="num">${rupees(sh.paise || 0)}</b> is not in question.
          The dispute is <b class="num">${sh.differing || 0}</b> orders,
          <b class="num">${rupees(sh.disputed_paise || 0)}</b>.`,
      }));
    },
    async context(ctx, S) {
      const { evidence: e } = await D.evidence(S.subject, S);
      const x = (e.explanations || []).find(v => v.letter === ctx.id);
      if (!x) return null;
      return { title: `Explanation ${x.letter}`, body:
        `<div class="c-o-amt num">${rupees(x.net_paise)}</div>
         <p>${x.orders} orders · ${x.shared} shared · ${(x.unique || []).length} unique.</p>
         ${rows(x.unique || [], o => Item(esc(o.id || o), '',
           o.paise ? rupees(o.paise) : '', `order:${o.id || o}`))}` };
    },
  };

  const investigate = {
    label: 'Investigate', question: 'What should I check next?', layout: 'focus',
    async render(subject, S) {
      const { spine, investigation: v } = await D.investigate(subject, S);
      if (v.groups) return wrap(spine, Sheet({
        instrument: 'trail',
        claim: `Three questions account for
          <b class="num">${rupees(v.total_paise)}</b>.`,
        evidence: rows(v.groups, g => Item(
          `${esc(g.question)}<em>${esc(g.cause || '')}</em>`,
          `${g.settlements} cases`, rupees(g.value_paise), `group:${g.reason}`)),
        verdict: v.note ? esc(v.note) : '',
      }));
      const steps = v.steps || [], qs = v.questions || [];
      return wrap(spine, Sheet({
        instrument: 'trail',
        claim: esc(v.question || 'What should be investigated first?'),
        evidence: steps.length
          ? `<div class="c-trail">${rows(steps, s =>
              `<div class="c-tr ac-${esc(s.actor)}">
                <span class="c-tr-m">${actorMark(s.actor)}</span>
                <span class="c-tr-a">${esc(s.actor)} <em>${esc(s.action || '')}</em></span>
                <span class="c-tr-d">${esc(s.detail || '')}${
                  s.result ? `<em>${esc(s.result)}</em>` : ''}</span></div>`)}</div>`
          : rows(qs, q => Item(esc(q.text || q.question || ''),
              `<em>${esc(q.hint || q.next || '')}</em>`,
              q.amount_paise ? rupees(q.amount_paise) : '')),
        verdict: v.state
          ? `<b>${esc(String(v.state).toUpperCase())}.</b> ${esc(v.note || '')}`
            + (v.resolvers ? `<div class="c-v-h">What would resolve it</div>`
              + rows(v.resolvers, r => Item(
                `<b class="m ${r.status === 'missing' ? 'n' : 'y'}">${
                  r.status === 'missing' ? '○' : '●'}</b> ${esc(r.what)}`,
                `<em>${esc(r.would || '')}</em>`, esc(r.status || ''))) : '')
          : '',
      }));
    },
  };

  const policy = {
    label: 'Policy', question: 'What am I allowed to do?', layout: 'focus',
    async render(subject, S) {
      const { spine, decision: d } = await D.policy(subject, S);
      const total = (d.auto_post || 0) + (d.review || 0) + (d.block || 0);
      const priced = d.expected_loss_paise != null;
      /* The threshold is drawn only where a probability exists. */
      const line = priced ? `<div class="c-thresh" role="img"
        aria-label="Automate below the threshold, review above">
        <div class="c-th-bar">
          <i class="a" style="width:${pct(d.auto_post, total)}%"></i>
          <i class="r" style="width:${pct(d.review, total)}%"></i>
          <i class="b" style="width:${pct(d.block, total)}%"></i></div>
        <div class="c-th-ends"><span>AUTOMATE <b class="num">${d.auto_post || 0}</b></span>
          <span>REVIEW <b class="num">${d.review || 0}</b></span></div></div>`
        : `<div class="c-unpriced"><b>UNPRICED</b> — no proof was established, so
            there is no error probability to price. A threshold drawn here would
            be a number invented to fill a space.</div>`;
      return wrap(spine, Sheet({
        instrument: 'boundary',
        claim: `Automate when <span class="c-ineq">P(error) × cost(error)
          &lt; cost(review)</span>.`,
        evidence: line
          + Item('expected loss', '', priced ? rupees(d.expected_loss_paise)
              : '<span class="unp">UNPRICED</span>')
          + Item('cost of checking', '', rupees(d.review_paise))
          + Item('money protected', '', rupees(d.protected_paise))
          + Item('wrongly posted', '', String(d.wrong_posts || 0)),
        verdict: d.strata ? `<div class="c-v-h">Priced by stratum</div>`
          + rows(d.strata, s => Item(esc(s.key),
              `<em>${s.wrong} wrong of ${s.total}</em>`,
              s.priced == null ? '<span class="unp">UNPRICED</span>'
                : (s.priced * 100).toFixed(1) + '%')) : '',
      }));
    },
  };

  const activity = {
    label: 'Activity', question: 'What actually happened?', layout: 'focus',
    async render(subject, S) {
      const { spine, activity: a } = await D.activity(subject, S);
      if (a.deliveries) return wrap(spine, Sheet({
        instrument: 'time',
        claim: `${a.deliveries.length} events arrived. ${
          (a.unrevised || []).length} settlements are unrevised.`,
        evidence: `<div class="c-time">${rows(a.deliveries, d =>
          `<div class="c-te dl-${esc(d.status)}">
            <span class="c-te-t num">${esc(d.received_at || '')}</span>
            <span class="c-te-m">${d.status === 'accepted' ? '●'
              : d.status === 'duplicate' ? '◑' : '⊘'}</span>
            <div class="c-te-b"><span class="c-te-a">${esc(d.status)}</span>
              ${esc(d.kind)}${d.detail ? `<em>${esc(d.detail)}</em>` : ''}</div>
          </div>`)}</div>`,
        verdict: (a.unrevised || []).length ? '' :
          `<b>Nothing is unrevised.</b> ${esc(a.unrevised_note || '')}`,
      }));
      const ev = a.events || [], st = a.state || {};
      return wrap(spine, Sheet({
        instrument: 'time',
        claim: st.verdict
          ? `It ended <b>${esc(st.verdict)}</b>, decided <b>${esc(st.decision || '—')}</b>,
             and was <b>${st.posted ? 'posted' : 'not posted'}</b>.`
          : `${plural(ev.length, 'event')} this run.`,
        evidence: `<div class="c-time">${rows(ev, e =>
          `<div class="c-te ac-${esc(e.actor)}">
            <span class="c-te-t num">${esc(e.at || '')}</span>
            <span class="c-te-m">${actorMark(e.actor)}</span>
            <div class="c-te-b"><span class="c-te-a">${esc(e.actor)}</span>
              ${esc(e.what || '')}${e.value ? ` <b class="num">${esc(e.value)}</b>` : ''}
              ${e.caused_by ? `<em>because ${esc(e.caused_by)}</em>` : ''}
              ${e.effect ? `<em>${esc(e.effect)}</em>` : ''}</div></div>`)}</div>`,
        verdict: '',
      }));
    },
  };

  const trust = {
    label: 'Trust', question: 'Can I believe the system itself?',
    subjects: ['portfolio'], layout: 'focus',
    async render(subject, S) {
      const { spine, claims: c } = await D.trust(subject, S);
      if (subject.type !== 'portfolio')
        return wrap(spine, Sheet({
          claim: `Trust is a property of the system, not of one settlement.`,
          evidence: `<p class="c-note">Open it on the portfolio.</p>`,
        }));
      const cl = c.claims || [];
      const bad = cl.filter(x => x.status !== 'MEASURED');
      const ok = cl.filter(x => x.status === 'MEASURED');
      const one = x => `<div class="c-cl st-${esc(x.status)}"
        data-context="claim:${esc(x.id)}" tabindex="0">
        <span class="c-cl-s">${esc(x.status)}</span>
        <span class="c-cl-t">${esc(x.text)}<em>${esc(x.artifact || '')}</em></span>
        <span class="c-cl-v num">${esc(x.value || '—')}</span></div>`;
      return wrap(spine, Sheet({
        instrument: 'claims',
        claim: `${bad.length} of ${cl.length} claims are not measured.`,
        evidence: rows(bad, one),
        verdict: `<div class="c-v-h">${ok.length} measured</div>` + rows(ok, one),
      }));
    },
  };

  window.COMPOSITION = {
    id: 'C', name: 'Minimal evidence workspace',
    C: {
      esc, SubjectHeader, LensStrip,
      ContextChrome: (title, body) => `<div class="c-obj">
        <header>${esc(title)}</header><div>${body}</div></div>`,
      EmptyState: (what, why) => `<div class="c-empty"><b>${esc(what)}</b>
        <span>${esc(why || '')}</span></div>`,
      ErrorState: msg => `<div class="c-err">${esc(msg)}</div>`,
      LoadingState: () => `<div class="c-load" aria-busy="true"><i></i><i></i></div>`,
    },
    lenses: { control, journal, evidence, investigate, policy, activity, trust },
  };
})();
