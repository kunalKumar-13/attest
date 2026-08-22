/* A — FINANCIAL TERMINAL
 *
 * THE CASE IS THE OBJECT. THE INSTRUMENT IS THE ROOM.
 *
 * The autopsy measured 343px of vertical chrome — 38% of the viewport —
 * repeated identically on all seven lenses. Here the case turns 90°: it becomes
 * a rail that is written once and never re-rendered, and the instrument gets
 * the entire remaining rectangle at full height.
 *
 * The rail carries the seven answers a case owes: what it is, how much, where
 * it stopped, what is proven, what is uncertain, what would resolve it, what is
 * safe to do. Nothing else belongs there.
 */
'use strict';

(() => {
  const { esc, rupees, short, pct, actorMark, verdictMark, plural } = window.KIT;
  const D = window.EXP_DATA;
  const rows = (a, f) => (a || []).map(f).join('');

  /* ------------------------------------------------------- the case object */
  const CaseObject = (s, spine, stopped, S) => {
    const isPort = s.type === 'portfolio';
    const st = (spine && spine.stages || []).find(x => x.key === stopped);
    return `
    <div class="a-case">
      <div class="a-id">
        <span class="a-id-n">${esc(isPort ? s.label : s.id)}</span>
        ${s.status ? `<span class="a-verdict s-${esc(s.status)}">${esc(s.status)}</span>` : ''}
      </div>
      <div class="a-amt num">${rupees(s.amount_paise)}</div>
      <div class="a-amt-k">${esc(s.amount_label || '')}</div>

      ${spine ? `<div class="a-spine" role="img"
        aria-label="Money flow${stopped ? `, stopped at ${esc(stopped)}` : ''}">
        ${rows(spine.stages, x => {
          const top = Math.max(...spine.stages.map(y => y.continues_paise || 0), 1);
          const w = Math.max(pct(x.continues_paise || 0, top), x.continues_paise > 0 ? 1.5 : 0);
          const isStop = stopped === x.key;
          return `<button class="a-st ${isStop ? 'stop' : ''} s-${esc(x.state)}"
              data-stage="${esc(x.key)}"
              aria-label="${esc(x.label)}: ${esc(x.value)}${isStop ? ', stopped here' : ''}">
            <span class="a-st-k">${esc(x.label)}</span>
            <span class="a-st-bar"><i style="width:${w.toFixed(1)}%"></i></span>
            <span class="a-st-v num">${esc(x.value)}</span>
          </button>`;
        })}
      </div>` : ''}

      ${st ? `<div class="a-stop">
        <span class="a-k">stops at</span>
        <b>${esc(st.label)}</b>
        <span class="a-why">${esc(st.detail || '')}</span></div>` : ''}

      <div class="a-slot" id="a-now"></div>
      <div class="a-slot" id="a-next"></div>
    </div>`;
  };

  /* Instruments live at the rail's foot — not a horizontal band across the
   * top of the room, which the autopsy costed at 46px × 7 identical pixels. */
  const Instruments = (lenses, active) => `
    <div class="a-inst" aria-label="Instrument">${rows(lenses, l =>
      `<button data-lens="${esc(l.key)}" class="${l.key === active ? 'on' : ''}"
        title="${esc(l.question)}">${esc(l.label)}</button>`)}
    </div>`;

  /* The rail's two live slots. Written by whichever lens knows the answer,
   * so the rail states the case's current position without duplicating the
   * instrument's own content. */
  const setSlot = (id, html) => {
    const n = document.getElementById(id);
    if (n && n.innerHTML !== html) n.innerHTML = html;
  };
  const Now = (label, a, b) => `<span class="a-k">${esc(label)}</span>
    <div class="a-pair"><b class="num">${a}</b>${b ? `<i class="num">${b}</i>` : ''}</div>`;
  const Next = (what, value) => `<span class="a-k">next</span>
    <div class="a-next-w">${esc(what)}</div>
    ${value ? `<div class="a-next-v num">${value}<em>unlocked</em></div>` : ''}`;

  const H = (title, body, cls) =>
    `<section class="a-blk ${cls || ''}"><h2>${esc(title)}</h2>${body}</section>`;

  /* -------------------------------------------------------------- CONTROL */
  const control = {
    label: 'Control', question: 'What is happening?',
    layout: 'focus',
    async render(subject, S) {
      const { spine, actions, attention, settlement } = await D.control(subject, S);
      if (subject.type === 'portfolio') {
        const acts = (actions && actions.actions) || [];
        const grps = (attention && attention.groups) || [];
        setSlot('a-now', Now('held', rupees((grps[0] || {}).amount_paise || 0),
                             `${(grps[0] || {}).count || 0} cases`));
        setSlot('a-next', acts[0] ? Next(acts[0].what.split(';')[0],
                                         rupees(acts[0].leverage_paise)) : '');
        return H('Where the value is held',
          `<div class="a-flow">${rows(spine.stages, x => {
            const top = Math.max(...spine.stages.map(y => y.continues_paise || 0), 1);
            return `<div class="a-fl ${spine.stopped_at === x.key ? 'stop' : ''}">
              <div class="a-fl-k">${esc(x.label)}</div>
              <div class="a-fl-track"><i style="width:${pct(x.continues_paise||0,top).toFixed(1)}%"></i></div>
              <div class="a-fl-v num">${esc(x.value)}</div>
              <div class="a-fl-d">${esc(x.detail || '')}</div></div>`;
          })}</div>`)
        + H('What unlocks the most', `<div class="a-acts">${rows(acts, a =>
            `<button class="a-act k-${esc(a.kind)}" data-context="action:${esc(a.reason)}">
              <span class="a-act-k">${esc(a.kind).replace('_', ' ')}</span>
              <span class="a-act-w">${esc(a.what.split(';')[0])}</span>
              <span class="a-act-v num">${rupees(a.leverage_paise || a.value_paise)}</span>
              <span class="a-act-e">${plural(a.settlements, 'case')} · ${plural(a.steps, 'step')}</span>
            </button>`)}</div>`);
      }
      const d = settlement || {};
      const failed = (d.checks || []).filter(c => !c.ok);
      setSlot('a-now', Now(`${(d.proofs || []).length} explanations`, '', ''));
      setSlot('a-next', '');
      return H(failed.length
          ? `${plural(failed.length, 'check')} did not pass`
          : 'Every check passed',
        `<div class="a-checks">${rows(d.checks || [], c =>
          `<div class="a-chk ${c.ok ? 'ok' : 'no'}">
            <span class="a-chk-m">${c.ok ? '●' : '○'}</span>
            <span class="a-chk-n">${esc(c.name)}</span>
            <span class="a-chk-d">${esc(c.detail || '')}</span></div>`)}</div>`);
    },
    async context(ctx, subject, S) {
      const { actions, attention } = await D.control({ type: 'portfolio', id: 'portfolio' }, S);
      const o = ((actions && actions.actions) || []).find(x => x.reason === ctx.id);
      if (!o) return null;
      return { title: esc(o.reason.replace(/_/g, ' ')), body:
        `<p class="a-ctx-why">${esc(o.rationale || o.why || '')}</p>
         <div class="a-ex">${rows(o.examples || [], x =>
           `<button class="a-ex-r" data-subject="settlement:${esc(x.id || x)}">
             <span>${verdictMark(x.verdict)} ${esc(x.id || x)}</span>
             <span class="num">${x.amount_paise ? rupees(x.amount_paise) : ''}</span>
           </button>`)}</div>` };
    },
  };

  /* ------------------------------------------------------------- EVIDENCE */
  const evidence = {
    label: 'Evidence', question: 'Why should I believe this?', layout: 'focus',
    async render(subject, S) {
      const { evidence: e } = await D.evidence(subject, S);
      const sp = e.space || {};
      const uni = sp.universe || (e.counts && e.counts[0] && e.counts[0].n) || 0;
      const cand = sp.candidates || 0;
      const ex = e.explanations || [], sh = e.shared || {};
      setSlot('a-now', ex.length
        ? Now('agreed / disputed', rupees(sh.paise || 0), rupees(sh.disputed_paise || 0))
        : Now('candidates', String(cand), ''));
      setSlot('a-next', e.missing && e.missing[0]
        ? Next(e.missing[0].next || e.missing[0].what, '') : '');

      let left = uni;
      const band = `<div class="a-band" role="img"
        aria-label="${uni} orders reduced to ${cand} candidates">
        <div class="a-bd"><b class="num">${uni.toLocaleString('en-IN')}</b>
          <i style="width:100%"></i><em>in the book</em></div>
        ${rows(sp.reductions || e.reductions || [], r => {
          left = Math.max(0, left - (r.removed || 0));
          return `<div class="a-bd cut"><b class="num">−${(r.removed||0).toLocaleString('en-IN')}</b>
            <i class="${r.deterministic ? 'det' : 'conv'}" style="width:${pct(left,uni).toFixed(2)}%"></i>
            <em>${esc(r.name)} <span class="a-tag">${r.deterministic ? 'DETERMINISTIC' : 'CONVENTION'}</span></em>
          </div>`;
        })}
        <div class="a-bd keep"><b class="num">${cand}</b>
          <i style="width:${Math.max(1.2, pct(cand, uni)).toFixed(2)}%"></i>
          <em>reach the solver</em></div></div>`;

      return H(`${uni.toLocaleString('en-IN')} orders considered, ${cand} survive`, band)
        + (ex.length ? H(`${ex.length} explanations satisfy the amount exactly`,
          `<div class="a-exps">${rows(ex, x =>
            `<button class="a-exp" data-context="explanation:${esc(x.letter)}">
              <span class="a-exp-l">${esc(x.letter)}</span>
              <span class="a-exp-b">
                <i class="sh" style="width:${pct(x.shared, x.orders)}%"></i>
                <i class="uq" style="width:${pct((x.unique||[]).length, x.orders)}%"></i></span>
              <span class="a-exp-n num">${x.shared}<em>shared</em>
                <b>+${(x.unique||[]).length}</b><em>unique</em></span>
              <span class="a-exp-v num">${rupees(x.net_paise)}</span>
            </button>`)}</div>
          <div class="a-verdict-line">
            <span><b class="num">${rupees(sh.paise || 0)}</b> is settled whichever
              explanation is right</span>
            <span class="hot"><b class="num">${rupees(sh.disputed_paise || 0)}</b>
              turns on which one is, across ${plural(sh.differing || 0, 'order')}</span>
          </div>`) : '');
    },
    async context(ctx, subject, S) {
      const { evidence: e } = await D.evidence(subject, S);
      const x = (e.explanations || []).find(v => v.letter === ctx.id);
      if (!x) return null;
      return { title: `Explanation ${x.letter}`, body:
        `<div class="a-ctx-amt num">${rupees(x.net_paise)}</div>
         <p class="a-ctx-why">${x.orders} orders · ${x.shared} in every explanation ·
           ${(x.unique||[]).length} unique to this one · residual ${x.residual_paise}p
           within ±${x.tolerance_paise}p</p>
         <div class="a-ex">${rows(x.unique || [], o =>
           `<div class="a-ex-r"><span>${esc(o.id || o)}</span>
             <span class="num">${o.paise ? rupees(o.paise) : ''}</span></div>`)}</div>` };
    },
  };

  /* ---------------------------------------------------------- INVESTIGATE */
  const investigate = {
    label: 'Investigate', question: 'What should I check next?', layout: 'focus',
    async render(subject, S) {
      const { investigation: v } = await D.investigate(subject, S);
      if (v.groups) {
        setSlot('a-now', Now('open questions', String(v.groups.length), ''));
        setSlot('a-next', '');
        return H('Ordered by what an answer would unlock',
          `<div class="a-qs">${rows(v.groups, g =>
            `<div class="a-q"><span class="a-q-k">${esc(g.kind).replace('_',' ')}</span>
              <span class="a-q-t">${esc(g.question)}</span>
              <span class="a-q-v num">${rupees(g.value_paise)}</span>
              <span class="a-q-n">${plural(g.settlements, 'case')}</span></div>`)}</div>`);
      }
      const steps = v.steps || [];
      setSlot('a-now', Now('the loop', String(v.state || '').toUpperCase(),
                           v.verdict_changed ? 'verdict changed' : 'verdict unchanged'));
      setSlot('a-next', (v.resolvers || [])[0] ? Next(v.resolvers[0].what, '') : '');
      const beat = (s) => `<div class="a-beat ac-${esc(s.actor)}">
        <div class="a-beat-h"><span class="a-mark">${actorMark(s.actor)}</span>
          <span class="a-beat-a">${esc(s.actor)}</span>
          <span class="a-beat-v">${esc(s.action || '')}</span>
          ${s.result ? `<span class="a-beat-r">${esc(s.result)}</span>` : ''}</div>
        <div class="a-beat-d">${esc(s.detail || '')}</div></div>`;
      return H(esc(v.question || 'What should be investigated first?'),
        `<div class="a-exp-run">${rows(steps, beat)}</div>`)
        + (v.resolvers && v.resolvers.length ? H('What would resolve it',
          `<div class="a-checks">${rows(v.resolvers, r =>
            `<div class="a-chk ${r.status === 'missing' ? 'no' : 'ok'}">
              <span class="a-chk-m">${r.status === 'missing' ? '○' : '●'}</span>
              <span class="a-chk-n">${esc(r.what)}</span>
              <span class="a-chk-d">${esc(r.would || '')}</span></div>`)}</div>`) : '');
    },
  };

  /* --------------------------------------------------------------- POLICY */
  const policy = {
    label: 'Policy', question: 'What am I allowed to do?', layout: 'focus',
    async render(subject, S) {
      const { decision: d } = await D.policy(subject, S);
      const priced = d.expected_loss_paise != null && d.expected_loss_paise !== 0
                  || subject.type === 'portfolio';
      const total = (d.auto_post || 0) + (d.review || 0) + (d.block || 0);
      setSlot('a-now', Now('decision',
        subject.type === 'portfolio' ? `${d.auto_post} auto` : (d.decision || 'REVIEW'),
        subject.type === 'portfolio' ? `${d.review} review` : ''));
      setSlot('a-next', '');

      const bound = priced ? `<div class="a-bound">
          <div class="a-bnd-e"><b class="num">${rupees(d.expected_loss_paise)}</b>
            <em>expected loss</em></div>
          <div class="a-bnd-line">
            <i class="auto" style="width:${pct(d.auto_post, total).toFixed(1)}%"></i>
            <i class="rev" style="width:${pct(d.review, total).toFixed(1)}%"></i>
            <i class="blk" style="width:${pct(d.block, total).toFixed(1)}%"></i>
            <span class="a-bnd-m"></span></div>
          <div class="a-bnd-r"><b class="num">${rupees(d.review_paise)}</b>
            <em>cost of checking</em></div>
        </div>
        <div class="a-bnd-legend"><span class="auto">${d.auto_post} AUTO-POST</span>
          <span class="rev">${d.review} REVIEW</span>
          <span class="blk">${d.block} BLOCK</span></div>`
        : `<div class="a-unpriced">
            <b>UNPRICED</b>
            <p>No unique proof was established, so there is no error probability
               to price. A threshold drawn here would be a number invented to
               fill a space.</p>
            <div class="a-unpriced-r">THEREFORE <b>REVIEW</b></div>
          </div>`;

      return H(priced ? 'The boundary' : 'The boundary is not drawn', bound)
        + H('The order of the gates', `<div class="a-gates">
            <div class="a-gate"><b>PROOF</b><em>a unique, kernel-checked explanation</em></div>
            <div class="a-gate-ar">→</div>
            <div class="a-gate"><b>POLICY</b><em>expected loss below the cost of checking</em></div>
            <div class="a-gate-ar">→</div>
            <div class="a-gate"><b>ACTION</b><em>an entry is written</em></div>
          </div>
          <p class="a-ctx-why">Never MODEL → ACTION. The model may propose an
            anchor for the solver to test; it cannot verify one, price one, or
            post one.</p>`);
    },
  };

  window.PROTOTYPE = {
    id: 'A', name: 'Financial terminal',
    C: {
      esc, CaseObject, Instruments,
      ContextChrome: o => `<div class="a-ctx-h">
        <span class="a-ctx-k">${esc(o.kind || '')}</span>
        <span class="a-ctx-t">${esc(o.title || '')}</span>
        <button data-close-ctx class="a-ctx-x" aria-label="Close">×</button></div>`,
      EmptyState: (w, y) => `<div class="a-empty"><b>${esc(w)}</b><span>${esc(y||'')}</span></div>`,
      ErrorState: m => `<div class="a-err">${esc(m)}</div>`,
      LoadingState: () => `<div class="a-load" aria-busy="true"><i></i><i></i><i></i></div>`,
    },
    lenses: { control, evidence, investigate, policy },
  };
})();
