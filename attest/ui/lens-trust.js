/* TRUST — "Can I believe ATTEST itself?"
 *
 * Two compositions were built and compared per §44.
 *
 *   A · REGISTER  one scannable row per claim, carrying its status, its value
 *                 and the artifact it reads; the limitation opens as context
 *   B · TRACE     each claim expanded inline into claim, status, result,
 *                 source, measured-on and limitation
 *
 * A was kept. B expanded eight claims into forty rows and 3,213px, so the
 * register could not be scanned — and it duplicated inline what the context
 * drawer does everywhere else in the product. Its one advantage, the limitation
 * being visible without a click, is not worth losing the ability to read the
 * register at all. B is deleted.
 *
 * The order is the argument and it is not negotiable (§2, §34): failures first,
 * then what was built and rejected, then what is not known, and only then the
 * claims. A trust surface that opens with green ticks is a pitch deck.
 *
 * Nothing here is transcribed (§6). Every figure names the artifact it came
 * from, because a number typed into an interface is a number nothing checks —
 * which is exactly how a precision figure sat unchallenged for six days.
 */
'use strict';

(() => {
  const { Section, MetricRow, Disclosure, EmptyState, Conclusion,
          plural, esc } = window.C;

  const STATE = {
    MEASURED: 'ok', SUPPORTED: 'ok', LIMITED: 'lim',
    'NOT MEASURED': 'none', REJECTED: 'no', UNKNOWN: 'none',
    PASS: 'ok', WARN: 'lim', FAIL: 'no',
  };

  /* §2, §34. The uncomfortable numbers, first and undiminished. */
  function BadNews(d) {
    const rejected = d.failures.entries.filter(e => e.refusal);
    return `<div class=t-bad>
      <div class=t-bad-r>
        <span class=t-bad-n>${d.failures.count}</span>
        <span class=t-bad-l>recorded failures</span>
        <span class=t-bad-d>each with what was expected, what happened, and
          what changed</span></div>
      <div class=t-bad-r>
        <span class=t-bad-n>${rejected.length}</span>
        <span class=t-bad-l>features built, measured, then disabled</span>
        <span class=t-bad-d>${esc(rejected.map(e => e.ref).join(' · ')) || '—'}</span></div>
      <div class=t-bad-r>
        <span class=t-bad-n>${d.unknowns.length}</span>
        <span class=t-bad-l>things not known</span>
        <span class=t-bad-d>stated below rather than omitted</span></div>
    </div>`;
  }

  function Unknowns(d) {
    return `<div class=t-unk>${d.unknowns.map(u => `<div class=t-unk-r>
      <span class=t-unk-w>${esc(u.what)}</span>
      <span class=t-unk-y>${esc(u.why)}</span>
    </div>`).join('')}</div>`;
  }

  /* --------------------------------------------- composition A · REGISTER */
  function registerA(d) {
    const groups = [...new Set(d.claims.map(c => c.group))];
    return groups.map(g => `<div class=t-grp>
      <div class=t-grp-h>${esc(g)}</div>
      ${d.claims.filter(c => c.group === g).map(c => `
        <button class="t-claim s-${STATE[c.status] || 'none'}"
            data-context="claim:${esc(c.id)}">
          <span class=t-claim-h>
            <span class=t-claim-id>${esc(c.id)}</span>
            <span class=t-claim-t>${esc(c.claim)}</span>
            <span class=t-claim-s>${esc(c.status)}</span></span>
          ${c.value ? `<span class=t-claim-v>${esc(c.value)}</span>` : ''}
          <span class=t-claim-src>${esc(c.source || 'no source')}</span>
        </button>`).join('')}
    </div>`).join('');
  }

  async function portfolio(S) {
    const d = await window.shellApi(`/api/claims?run=${S.run}`);
    const failing = d.gates.filter(g => g.state !== 'PASS').length;

    // Trust leads with what the system will not claim. The strongest thing on
    // this screen must be a limitation, not a green tick — a trophy wall is
    // the failure mode this lens exists to avoid.
    const unmeasured = (d.claims || []).filter(c => c.status !== 'MEASURED').length;
    const unknowns = (d.unknowns || []).length;
    return Conclusion({
      fact: 'Live Razorpay validation',
      tone: 'stop',
      figure: 'NOT VERIFIED',
      figureLabel: `${unknowns} things not known`,
      because: `${unmeasured} of ${(d.claims || []).length} claims are not `
        + `MEASURED, ${(d.failures || {}).count || 0} failures are recorded with `
        + `what broke and what changed, and ${failing} of ${d.gates.length} `
        + `gates are failing. No live account has ever been contacted; the `
        + `numbers here describe generated data.`,
    }) + `<div class=t-head>
        <span class=t-head-k>where ATTEST has failed</span>
        <h2>The uncomfortable numbers first</h2>
      </div>`
      + Section({ body: BadNews(d) })
      + Section({
          title: 'What is not known',
          body: Unknowns(d) + Disclosure({
            summary: 'Why this section exists at all',
            body: `<p>A surface that only shows what was measured is not a trust
              surface. Each of these is a real gap in this repository — an
              absent capability rather than an unmeasured one — and saying
              "not recorded" is different from saying "unknown".</p>`,
          }),
        })
      + Section({
          title: 'What ATTEST claims, and what supports it',
          aside: `<span class=c-muted>${esc(d.scope)}</span>`,
          body: registerA(d)
            + Disclosure({
                summary: 'Where these figures come from',
                body: `<ul class=t-art>${d.artifacts.map(a =>
                  `<li><b class=c-mono>${esc(a.name)}</b> ${a.present
                    ? esc(a.records) : '<em>missing</em>'}</li>`).join('')}</ul>
                  <p>Nothing on this screen is typed in. Every figure names the
                  artifact it reads, so a number cannot drift from its
                  evidence.</p>`,
              }),
        })
      + Section({
          title: 'The gates the build enforces',
          aside: `<span class=c-muted>${failing
            ? `${failing} not passing` : 'all passing'}</span>`,
          body: `<div class=t-gates>${d.gates.map(g => `
            <div class="t-gate s-${STATE[g.state] || 'none'}">
              <span class=t-gate-s>${esc(g.state)}</span>
              <span class=t-gate-n>${esc(g.label)}
                ${g.fatal ? '<em>fatal</em>' : '<em class=adv>advisory</em>'}</span>
              <span class=t-gate-v>${g.value === null || g.value === undefined
                ? 'not measured' : esc(String(g.value))}</span>
              <span class=t-gate-w>${esc(g.why)}</span>
            </div>`).join('')}</div>`,
        })
      + Section({
          title: 'What the model may and may not do',
          body: `<div class=t-perm>
            <div class=t-perm-c><span class=t-perm-h>granted to nothing</span>
              ${(d.ai_permissions.blocked || []).map(c =>
                `<span class="t-perm-i no">✕ ${esc(c)}</span>`).join('')}</div>
            <div class=t-perm-c><span class=t-perm-h>agents in the roster</span>
              ${(d.ai_permissions.roster || []).map(a =>
                `<span class=t-perm-i>${esc(a.name)}</span>`).join('')}</div>
          </div>`,
        })
      + ((d.fixed || []).length ? Section({
          title: 'Found in the protected core, and fixed',
          body: `<div class=t-fixed>${d.fixed.map(f => `<div class=t-fix>
            <div class=t-fix-h><span class=t-fix-id>${esc(f.id)}</span>
              <b>${esc(f.what)}</b>
              <span class=t-fix-s>${esc(f.status)}</span></div>
            <dl class=t-trace-d2>
              <div><dt>why it mattered</dt><dd>${esc(f.why_it_mattered)}</dd></div>
              <div><dt>fix</dt><dd>${esc(f.fix)}</dd></div>
              <div><dt>measured</dt><dd>${esc(f.measured)}</dd></div>
              <div><dt>report</dt><dd class=c-mono>${esc(f.report)}</dd></div>
              <div><dt>regression tests</dt><dd>${f.tests}</dd></div>
            </dl></div>`).join('')}</div>`,
        }) : '')
      + Section({
          title: 'Every failure, in order',
          aside: `<span class=c-muted>${plural(d.failures.count, 'entry', 'entries')}</span>`,
          body: `<div class=t-fails>${d.failures.entries.map(e => `
            <button class="t-fail${e.refusal ? ' ref' : ''}"
                data-context="failure:${esc(e.ref)}">
              <span class=t-fail-r>${esc(e.ref)}</span>
              <span class=t-fail-t>${esc(e.title)}</span>
              ${e.refusal ? '<span class=t-fail-b>disabled after measuring</span>' : ''}
            </button>`).join('')}</div>`,
        });
  }

  async function claimContext(id, S) {
    const d = await window.shellApi(`/api/claims?run=${S.run}`);
    const c = (d.claims || []).find(x => x.id === id);
    if (!c) return { kind: 'Claim', title: id, body: EmptyState('Unknown claim') };
    return { kind: 'Claim', title: c.id, status: null, body:
      Section({ body: `<p class=c-lead>${esc(c.claim)}</p>` })
      + Section({ body: `<dl class=e-prov>
          <div><dt>status</dt><dd>${esc(c.status)}</dd></div>
          ${c.value ? `<div><dt>result</dt><dd class=c-mono>${esc(c.value)}</dd></div>` : ''}
          <div><dt>source</dt><dd class=c-mono>${esc(c.source || '—')}</dd></div>
          ${c.measured_on ? `<div><dt>measured on</dt><dd>${esc(c.measured_on)}</dd></div>` : ''}
        </dl>` })
      + (c.limitation ? Section({ title: 'Limitation',
          body: `<p class=c-lead style="font-size:var(--t-label)">${esc(c.limitation)}</p>` }) : '')
      + (c.detail ? Section({ title: 'Method',
          body: `<p class=c-lead style="font-size:var(--t-label)">${esc(c.detail)}</p>` }) : '') };
  }

  async function failureContext(ref, S) {
    const d = await window.shellApi(`/api/claims?run=${S.run}`);
    const e = (d.failures.entries || []).find(x => x.ref === ref);
    if (!e) return { kind: 'Failure', title: ref, body: EmptyState('Unknown') };
    return { kind: 'Failure', title: e.ref,
      status: e.refusal ? 'REJECTED' : null, body:
      Section({ body: `<p class=c-lead>${esc(e.title)}</p>` })
      + Section({ title: 'What happened',
          body: `<p class=c-lead style="font-size:var(--t-label)">${esc(e.detail || e.headline)}</p>` })
      + (e.measurement ? Section({ title: 'Measured',
          body: `<pre class=meas>${esc(e.measurement)}</pre>` }) : '')
      + (e.refusal ? Section({ title: 'Decision',
          body: `<p class=c-lead style="font-size:var(--t-label)">Built,
            measured, and then disabled. The improvement was not worth what it
            cost in safety, and the code stays so the measurement can be
            repeated.</p>` }) : '') };
  }

  window.defineLens('trust', {
    label: 'Trust',
    question: 'Can I believe the system itself?',
    layout: () => 'focus',
    holds: (ctx, subject) => subject.type === 'portfolio'
      && (ctx.type === 'claim' || ctx.type === 'failure'),
    render(subject, S) {
      if (subject.type === 'portfolio') return portfolio(S);
      return Conclusion({
        fact: 'Trust is a property of the system',
        tone: 'hold',
        because: 'Not of one settlement. Whether this case is right depends on '
          + 'whether the engine, the rules and the search space can be '
          + 'believed at all — open Trust on the portfolio.',
      });
    },
    context(ctx, subject, S) {
      return ctx.type === 'claim'
        ? claimContext(ctx.id, S) : failureContext(ctx.id, S);
    },
  });
})();
