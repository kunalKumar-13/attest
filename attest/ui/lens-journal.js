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
  const { Section, DataTable, Disclosure, EmptyState, MetricRow, Row, Conclusion,
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
      // The refusal IS the answer here, so it leads. It used to be a section
      // heading at 10px, which made the lens look like it had nothing to say.
      return Conclusion({
        fact: 'No entry is written', tone: 'stop',
        figure: rupees(det.amount), figureLabel: 'not posted',
        because: why,
      }) + Section({
        title: 'Why nothing is posted',
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

    return Conclusion({
      fact: 'Balanced to the paisa', tone: 'go',
      figure: rupees(e.total_paise), figureLabel: 'posted',
      because: `${plural(e.orders, 'order')} across `
        + `${plural((e.lines || []).length, 'account')}, value date `
        + `${e.value_date}, UTR ${e.utr}. Debits equal credits or the entry `
        + `cannot be constructed at all.`,
    }) + Section({
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
          l.credit_paise
            ? `<button class=c-inline data-context="orders:${esc(subject.id)}"
                 >${esc(l.account)} ↗</button>`
            : esc(l.account),
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
          // CONTEXT, not subject: clicking a line in the day's accounting means
          // "show me that entry", not "make this settlement the whole
          // workspace". Promoting is a separate, deliberate act in the detail.
          context: { type: 'settlement', id: e.settlement_id },
        })).join('')
      : EmptyState(`Nothing clears the policy at ${rupees(d.review_paise)} a review.`,
                   'The boundary is the inequality, not a setting.');

    // The heading already states the reason; repeating it as the first clause
    // of the sentence beneath is the same fact twice. Show only the part the
    // heading does not carry.
    const tail = (reason, example) => {
      const i = example.indexOf('—');
      const rest = i > 0 ? example.slice(i + 1).trim() : example;
      return rest.toLowerCase().startsWith(reason.toLowerCase()) ? '' : rest;
    };
    const withheld = d.refusals.map(g => `<div class=c-group>
      <div class=c-group-h><b>${esc(g.reason)}</b>
        <span>${plural(g.count, 'settlement')}</span>
        <em>${esc(rupees(g.amount_paise, { whole: true }))}</em></div>
      ${tail(g.reason, g.example)
        ? `<div class=c-group-d>${esc(tail(g.reason, g.example))}</div>` : ''}
    </div>`).join('');

    // Journal's question is where the money went, and its answer is whether
    // the books balance and how much actually moved.
    return Conclusion({
      fact: d.balances ? 'The books balance' : 'The books do not balance',
      tone: d.balances ? 'go' : 'stop',
      figure: rupees(d.posted_paise), figureLabel: 'posted',
      because: `${plural(d.entry_count, 'entry', 'entries')} written, `
        + `${plural(d.refusal_count, 'settlement')} withheld at `
        + `${rupees(d.refused_paise)} — each with a stated reason. An entry is `
        + `written only from a unique, kernel-checked explanation.`,
    }) + Section({ title: "Today's accounting", body: head })
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

  /* The entry for one settlement, rendered into the detail pane. Identical
     content whether it is the right-hand column of the desk or a drawer over a
     settlement — the pane does not know which, and should not. */
  async function entryDetail(sid, S) {
    const api = window.shellApi;
    const [d, det] = await Promise.all([
      api(`/api/journal?run=${S.run}&review=${S.review}&exposure=${S.exposure}`),
      api(`/api/settlement?run=${S.run}&id=${encodeURIComponent(sid)}`),
    ]);
    const e = (d.entries || []).find(x => x.settlement_id === sid);
    const shell = { kind: 'Entry', title: sid,
                    promote: { type: 'settlement', id: sid } };

    if (!e) {
      const why = (det.judgement && det.judgement.reasons || []).slice(-1)[0]
        || 'no unique kernel-checked explanation';
      return { ...shell, status: det.verdict, body: Section({
        title: 'No entry is written',
        body: `<p class=c-lead>${esc(why)}</p>`,
      }) + (det.exception ? Section({
        title: 'What would change that',
        body: `<p class=c-lead>${esc(det.exception.next_step)}</p>`,
      }) : '') };
    }

    return { ...shell, status: det.verdict, body: Section({
      title: 'The money trail',
      aside: `<span class=c-muted>${plural(e.orders, 'order')}</span>`,
      body: MoneyTrail(e.lines, e.total_paise),
    }) + Section({
      title: 'The entry',
      aside: `<span class=c-muted>${esc(e.value_date)}</span>`,
      body: DataTable({
        cols: [{ label: 'Account' }, { label: 'Debit', num: true },
               { label: 'Credit', num: true }],
        rows: e.lines.map(l => [esc(l.account),
          l.debit_paise ? esc(rupees(l.debit_paise)) : '',
          l.credit_paise ? esc(rupees(l.credit_paise)) : '']),
        foot: ['Balance', esc(rupees(e.total_paise)), esc(rupees(e.total_paise))],
      }),
    }) };
  }

  /* Inside a settlement's own journal, the thing worth inspecting is which
     orders were discharged — the one fact the entry states and does not show. */
  async function ordersDetail(sid, S) {
    const api = window.shellApi;
    const det = await api(`/api/settlement?run=${S.run}&id=${encodeURIComponent(sid)}`);
    const p = det.proofs && det.proofs[0];
    const shell = { kind: 'Orders',
                    title: p ? plural(p.orders.length, 'order') : 'orders' };
    if (!p) return { ...shell,
      body: EmptyState('No explanation, so no orders were discharged.') };
    return { ...shell, body: DataTable({
      cols: [{ label: 'Order' }, { label: 'Method' },
             { label: 'Gross', num: true }, { label: 'Net', num: true }],
      rows: p.orders.map(o => [
        `<span class=c-mono>${esc(o.id.replace('ord_', ''))}</span>`,
        `<span class=c-muted>${esc(o.method)}</span>`,
        esc(rupees(o.gross)), esc(rupees(o.net))]),
      foot: ['Total', '', esc(rupees(p.gross)), esc(rupees(p.net))],
    }) };
  }

  window.defineLens('journal', {
    label: 'Journal',
    question: 'Where did the money go?',
    layout: subject => subject.type === 'portfolio' ? 'master-detail' : 'focus',
    emptyContext: 'Select an entry to see the money trail behind it.',
    holds: (ctx, subject) => subject.type === 'portfolio'
      ? ctx.type === 'settlement'
      : ctx.type === 'orders',
    master(subject, S) { return portfolio(S); },
    render(subject, S) {
      if (subject.type === 'settlement') return settlement(subject, S);
      return EmptyState('Journal has nothing to say about this subject.');
    },
    context(ctx, subject, S) {
      return ctx.type === 'orders'
        ? ordersDetail(subject.id, S)
        : entryDetail(ctx.id, S);
    },
  });
})();
