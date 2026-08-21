/* POLICY — "Given what ATTEST knows, what is it allowed to do?"
 *
 * Not a settings page and not a rule list. The subject of this lens is a
 * DECISION, and the visual is the boundary that produced it:
 *
 *     expected loss  <  cost of a review     ->  automate
 *     expected loss  >= cost of a review     ->  check
 *
 * Two things this lens must never do. It must never present itself as changing
 * a verdict — a settlement can be AMBIGUOUS and REVIEW, and those are two facts
 * rather than one. And it must never express a decision as a confidence: "92%
 * confident" is not an argument anyone can audit, whereas "₹135.48 expected
 * loss against ₹150.00 to check" is one a controller can disagree with.
 *
 * The simulator changes the COSTING, and a costing is hashed into the policy
 * version — so a what-if is a different policy version rather than a
 * recomputation of the recorded one. That is what makes §25 honest instead of
 * a promise: the historical decision keeps its version because the version is
 * derived from the inputs that made it.
 */
'use strict';

(() => {
  const { Section, Row, MetricRow, Disclosure, EmptyState,
          rupees, plural, esc } = window.C;

  const STEPS = [2500, 5000, 10000, 15000, 25000, 50000, 100000, 250000, 500000];

  /* §7, §32. One axis, two comparable numbers, and a line between them. A
     reader should see which side a settlement is on before reading a word. */
  function Boundary(b) {
    if (!b.priced) {
      return `<div class="p-bound unpriced">
        <div class=p-bound-s>${esc(b.statement)}</div></div>`;
    }
    const loss = b.expected_loss_paise, rev = b.review_paise;
    const span = Math.max(loss, rev) * 2;
    const pos = v => Math.min(v / span * 100, 96);
    const cheaper = loss < rev;
    return `<div class="p-bound ${cheaper ? 'auto' : 'review'}">
      <div class=p-bound-t>
        <i class=p-bound-line style="left:${pos(rev)}%"></i>
        <i class=p-bound-mark style="left:${pos(loss)}%"></i>
        <span class=p-bound-zl>automating is cheaper</span>
        <span class=p-bound-zr>checking is cheaper</span>
      </div>
      <div class=p-bound-k>
        <span class=lo><b>${esc(rupees(loss))}</b> expected loss</span>
        <span class=rv><b>${esc(rupees(rev))}</b> to check</span>
      </div>
      <div class=p-bound-s>${esc(b.statement)}</div>
    </div>`;
  }

  /* §17. The chain, as gates in order. Nothing reaches policy without passing
     proof, and the layout says so by putting them in that order and grouping
     them under the stage that owns them. */
  function Gates(gates) {
    const stages = [...new Set(gates.map(g => g.stage))];
    return `<div class=p-gates>${stages.map(st => `
      <div class=p-stage>
        <div class=p-stage-h>${esc(st)}</div>
        ${gates.filter(g => g.stage === st).map(g => `<div class="p-gate ${g.ok ? 'ok' : 'no'}">
          <i aria-hidden=true>${g.ok ? '✓' : '✕'}</i>
          <span class=p-gate-n>${esc(g.name)}</span>
          <span class=p-gate-s>${g.ok ? 'passed' : 'not satisfied'}</span>
          <span class=p-gate-w>${esc(g.why)}</span>
        </div>`).join('')}
      </div>`).join('<i class=p-stage-arrow aria-hidden=true></i>')}</div>`;
  }

  async function settlement(subject, S) {
    const d = await window.shellApi(`/api/decision?run=${S.run}`
      + `&type=settlement&id=${encodeURIComponent(subject.id)}`
      + `&review=${S.review}&exposure=${S.exposure}`);
    if (d.error) return EmptyState(d.error);

    return `<div class="p-head ${esc(d.decision)}">
        ${d.simulated ? '<div class=p-sim>Simulated costing — no action will be executed</div>' : ''}
        <span class=p-head-k>what policy permits</span>
        <div class=p-head-d>
          <i aria-hidden=true></i>${esc(d.decision.replace(/_/g, '-'))}</div>
        <div class=p-head-s>the verdict is
          <b class="c-status s-${esc(d.verdict)} sm">${esc(d.verdict)}</b>
          — policy reads it and does not change it</div>
      </div>`
      + Section({ title: 'The boundary', body: Boundary(d.boundary) })
      + Section({
          title: 'What had to hold',
          aside: `<span class=c-muted>${d.gates.filter(g => g.ok).length}/${d.gates.length} passed</span>`,
          body: Gates(d.gates),
        })
      + Section({
          title: 'What went in',
          body: `<dl class=p-in>${d.inputs.map(x => `<div>
            <dt>${esc(x.k)}</dt>
            <dd><b>${esc(x.v)}</b>${x.note ? `<span>${esc(x.note)}</span>` : ''}</dd>
          </div>`).join('')}</dl>`
            + Disclosure({
                summary: 'Every step the engine took',
                body: `<ol class=c-reasons>${d.reasons
                  .map(x => `<li>${esc(x)}</li>`).join('')}</ol>`,
              }),
        })
      + Section({
          title: 'Which policy decided this',
          body: `<dl class=e-prov>
            <div><dt>policy</dt><dd class=c-mono>${esc(d.policy_version)}</dd></div>
            ${d.simulated ? `<div><dt>recorded as</dt>
              <dd class=c-mono>${esc(d.recorded_version)}</dd></div>` : ''}
            ${Object.entries(d.provenance || {}).map(([k, v]) =>
              `<div><dt>${esc(k.replace('_version', ''))}</dt>
                <dd class=c-mono>${esc(v)}</dd></div>`).join('')}
          </dl>` + Disclosure({
            summary: 'Why a what-if is a different policy, not a recomputation',
            body: `<p>The policy version is a content hash of the costing. Change
              what a review is worth and the version changes with it, so a
              historical decision keeps its own version rather than being
              silently re-decided under today's numbers.</p>`,
          }),
        });
  }

  /* ------------------------------------------------------------- portfolio */
  async function portfolioMaster(S) {
    const d = await window.shellApi(`/api/decision?run=${S.run}&type=portfolio`
      + `&review=${S.review}&exposure=${S.exposure}`);
    const total = d.settlements || 1;
    const idx = STEPS.indexOf(S.review);

    return `<div class="p-head ${d.simulated ? 'sim' : ''}">
        ${d.simulated ? '<div class=p-sim>Simulated costing — no action will be executed</div>' : ''}
        <span class=p-head-k>what ATTEST may automate</span>
        <div class=p-head-d><i aria-hidden=true></i>${esc(rupees(d.posted_paise, { whole: true }))}</div>
        <div class=p-head-s>of ${esc(rupees(d.posted_paise + d.protected_paise, { whole: true }))} processed</div>
      </div>`
      + Section({
          title: 'What each decision holds',
          body: d.groups.map(g => `<button class="p-grp d-${esc(g.decision)}"
              data-context="decision:${esc(g.decision)}">
              <span class=p-grp-d>${esc(g.decision.replace(/_/g, '-'))}</span>
              <span class=p-grp-b><i style="width:${g.count / total * 100}%"></i></span>
              <span class=p-grp-n>${plural(g.count, 'settlement')}</span>
              <span class=p-grp-v>${esc(rupees(g.paise, { whole: true }))}</span>
            </button>`).join(''),
        })
      + Section({
          title: 'What if a review were worth more',
          aside: '<span class=p-sim-tag>simulation</span>',
          body: `<div class=p-sim-c>
            <label for=p-rev>an analyst opening one settlement and deciding</label>
            <input id=p-rev type=range min=0 max="${STEPS.length - 1}"
              value="${idx < 0 ? 3 : idx}" aria-label="Cost of a review">
            <output id=p-rev-v>${esc(rupees(S.review))}</output>
          </div>
          <div class=p-front>${(d.frontier || []).map(p => {
            const on = p.review_paise === S.review;
            return `<div class="p-front-r${on ? ' on' : ''}">
              <span class=p-front-c>${esc(rupees(p.review_paise))}</span>
              <span class=p-front-b><i style="width:${p.auto_post / total * 100}%"></i></span>
              <span class=p-front-n>${p.auto_post}</span>
              <span class=p-front-v>${esc(rupees(p.posted_paise, { whole: true }))}</span>
              <span class=p-front-w>${p.wrong_posts
                ? `<b>${p.wrong_posts} wrong</b>` : '0 wrong'}</span>
            </div>`;
          }).join('')}</div>`
            + Disclosure({
                summary: 'What this frontier is measuring',
                body: `<p>Every row is the same portfolio decided under a
                  different cost of review. The threshold is never configured:
                  it is wherever expected loss crosses that cost. Nothing is
                  executed by moving it — the recorded decisions keep the policy
                  version they were made under.</p>`,
              }),
        });
  }

  async function decisionContext(which, S) {
    const d = await window.shellApi(`/api/decision?run=${S.run}&type=portfolio`
      + `&review=${S.review}&exposure=${S.exposure}`);
    const g = (d.groups || []).find(x => x.decision === which);
    if (!g) return { kind: 'Decision', title: which, body: EmptyState('Unknown') };
    return {
      kind: 'Decision', title: which.replace(/_/g, '-'),
      body: Section({
          body: MetricRow([
            { label: 'settlements', value: String(g.count) },
            { label: 'value', value: rupees(g.paise, { whole: true }),
              tone: which === 'AUTO_POST' ? 'proven' : 'ambiguous' },
          ]),
        })
        + Section({ title: 'Why they land here',
            body: `<p class=c-lead style="font-size:var(--t-label)">${esc(g.why)}</p>` })
        + Section({
            title: 'What happens next',
            body: `<p class=c-lead style="font-size:var(--t-label)">${
              which === 'AUTO_POST'
                ? 'Policy permits a posting. It does not perform one — the entry '
                  + 'is written by the engine and appears in Journal.'
                : 'No automatic action. The settlement waits for a person, and '
                  + 'Investigate carries the question that would resolve it.'}</p>`,
          }),
    };
  }

  window.defineLens('policy', {
    label: 'Policy',
    question: 'What are we allowed to do?',
    layout: subject => subject.type === 'portfolio' ? 'master-detail' : 'focus',
    emptyContext: 'Select a decision to see what it holds.',
    holds: (ctx, subject) => subject.type === 'portfolio' && ctx.type === 'decision',
    master(subject, S) { return portfolioMaster(S); },
    render(subject, S) {
      if (subject.type === 'settlement') return settlement(subject, S);
      return EmptyState('Policy has nothing to say about this subject.');
    },
    mount(host, subject, S) {
      const r = host.querySelector('#p-rev');
      if (!r) return;
      const out = host.querySelector('#p-rev-v');
      r.addEventListener('input', () => {
        out.textContent = window.C.rupees(STEPS[+r.value]);
      });
      r.addEventListener('change', () => {
        S.review = STEPS[+r.value];
        window.navigate({}, { replace: true });
      });
    },
    context(ctx, subject, S) { return decisionContext(ctx.id, S); },
  });
})();
