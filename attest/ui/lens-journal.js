/* JOURNAL — "Where did the money go?"
 *
 * The same lens over two subjects, which is the whole point of the shell:
 * portfolio × journal is the day's accounting, settlement × journal is one
 * entry. Neither is a special case of the other and neither is a separate
 * screen.
 *
 * The money trail is the signature. A double-entry table is correct and
 * unreadable at a glance; the trail says the same thing in the shape money
 * actually moves — gross in, deductions out, credit landing — and the table is
 * underneath it for anyone who wants the entry as an accountant would file it.
 */
'use strict';

(() => {
  const { Section, DataTable, Disclosure, EmptyState, MetricRow, Row,
          rupees, plural, esc } = window.C;

  /* ORDERS → FEES → GST → SETTLEMENT → BANK, as proportional segments. */
  function MoneyTrail(lines, total) {
    const dr = lines.filter(l => l.debit_paise);
    const cr = lines.filter(l => l.credit_paise)[0];
    const max = Math.max(total, 1);
    const seg = (label, paise, tone, neg) => `<div class=c-trail-seg>
      <span class=l>${esc(label)}</span>
      <span class=b><i class="s-${tone}" style="width:${paise / max * 100}%"></i></span>
      <span class=v>${neg ? '−' : ''}${esc(rupees(paise))}</span></div>`;

    return `<div class=c-trail>
      ${cr ? seg('Orders', cr.credit_paise, 'PROVEN') : ''}
      ${dr.slice(1).map(l =>
        seg(l.account.replace(' (recoverable)', ''), l.debit_paise, 'AMBIGUOUS', true)
      ).join('')}
      <div class=c-trail-rule></div>
      ${dr[0] ? seg('Bank credit', dr[0].debit_paise, 'PROVEN') : ''}
      <div class=c-trail-bal>Balanced to the paisa ✓</div>
    </div>`;
  }

  async function settlement(subject, S) {
    const api = window.shellApi;
    const d = await api(`/api/journal?run=${S.run}`
      + `&review=${S.review}&exposure=${S.exposure}`);
    const e = (d.entries || []).find(x => x.settlement_id === subject.id);

    if (!e) {
      // Not an error. The refusal is the answer, and it has a reason.
      const det = await api(`/api/settlement?run=${S.run}&id=${encodeURIComponent(subject.id)}`);
      const j = det.judgement || {};
      const why = (j.reasons || []).slice(-1)[0]
        || 'no unique kernel-checked explanation';
      return Section({
        title: 'No entry is written',
        body: `<p class=c-lead>${esc(why)}</p>`
          + Disclosure({
              summary: 'Why nothing partial is posted',
              body: `<p>Candidate order sets discharge receivables against
                <em>different customers</em>. There is no partially correct
                journal entry — posting the wrong one moves money in the books
                against someone who does not owe it.</p>`,
            }),
      }) + Section({
        title: 'What would change that',
        body: `<p class=c-lead>${esc(det.exception ? det.exception.next_step
          : 'A unique explanation, then a policy that clears it.')}</p>`,
      });
    }

    return Section({
      title: 'The money trail',
      aside: `<span class=c-muted>${plural(e.orders, 'order')}</span>`,
      body: MoneyTrail(e.lines, e.total_paise),
    }) + Section({
      title: 'The entry',
      aside: `<span class=c-muted>${esc(e.value_date)} · UTR ${esc(e.utr)}</span>`,
      body: DataTable({
        cols: [{ label: 'Account' }, { label: 'Debit', num: true },
               { label: 'Credit', num: true }, { label: 'Memo' }],
        rows: e.lines.map(l => [
          esc(l.account),
          l.debit_paise ? esc(rupees(l.debit_paise)) : '',
          l.credit_paise ? esc(rupees(l.credit_paise)) : '',
          `<span class=c-muted>${esc(l.memo)}</span>`,
        ]),
        foot: ['Balance', esc(rupees(e.total_paise)), esc(rupees(e.total_paise)),
               `<span class=c-muted>residual ${e.residual_paise}p within ±${e.tolerance_paise}p</span>`],
      }) + Disclosure({
        summary: 'Why this balances by construction',
        body: `<p><code>net = gross − fee − tax</code> is the identity the whole
          engine rests on, so the balance check is the fee model restated. An
          entry that does not balance means the rule set disagrees with the
          records, not that someone mistyped — so it raises at construction
          rather than being held for review.</p>
          <p class=c-muted>${esc(e.provenance)}</p>`,
      }),
    });
  }

  async function portfolio(S) {
    const api = window.shellApi;
    const d = await api(`/api/journal?run=${S.run}`
      + `&review=${S.review}&exposure=${S.exposure}`);

    const head = MetricRow([
      { label: 'posted', value: rupees(d.posted_paise, { whole: true }),
        tone: 'proven', note: plural(d.entry_count, 'entry', 'entries') },
      { label: 'withheld', value: rupees(d.refused_paise, { whole: true }),
        note: `${plural(d.refusal_count, 'settlement')}, each with a reason` },
      { label: 'balance', value: d.balances ? '✓' : '✕',
        tone: d.balances ? 'proven' : 'contradicted',
        note: d.balances ? 'debits equal credits' : 'THE JOURNAL DOES NOT BALANCE' },
    ]);

    const entries = d.entries.length
      ? d.entries.map(e => Row({
          id: e.settlement_id.replace('setl_', ''),
          amount: e.total_paise,
          detail: `<span class=c-muted>${plural(e.orders, 'order')} · ${esc(e.value_date)}</span>`,
          aside: 'balanced ✓',
          subject: { type: 'settlement', id: e.settlement_id },
        })).join('')
      : EmptyState(`Nothing clears the policy at ${rupees(d.review_paise)} a review.`,
                   'The boundary is the inequality, not a setting.');

    const withheld = d.refusals.map(g => `<div class=c-group>
      <div class=c-group-h><b>${esc(g.reason)}</b>
        <span>${g.count}</span>
        <em>${esc(rupees(g.amount_paise, { whole: true }))}</em></div>
      <div class=c-muted style="padding:0 var(--s-4) 10px">${esc(g.example)}</div>
    </div>`).join('');

    return Section({ title: "Today's accounting", body: head })
      + Section({
          title: 'Entries',
          aside: `<span class=c-muted>${esc(rupees(d.posted_paise, { whole: true }))}</span>`,
          body: entries,
        })
      + Section({
          title: 'Withheld',
          aside: `<span class=c-muted>${esc(rupees(d.refused_paise, { whole: true }))}</span>`,
          body: withheld + Disclosure({
            summary: 'Why these are grouped by reason rather than listed',
            body: `<p>Two settlements withheld for the same reason are one
              problem. Keying on the sentence put fifty settlements into fifty
              buckets of one, which is a list wearing a summary's clothes.</p>`,
          }),
        });
  }

  window.defineLens('journal', {
    label: 'Journal',
    question: 'Where did the money go?',
    render(subject, S) {
      if (subject.type === 'portfolio') return portfolio(S);
      if (subject.type === 'settlement') return settlement(subject, S);
      return EmptyState('Journal has nothing to say about this subject.');
    },
  });
})();
