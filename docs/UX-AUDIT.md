# UX audit and the P3 information architecture

Written before any P3 code, per §62. Everything in the inventory is what the
repository actually contains, not what it was supposed to.

## A · What exists

**Five conceptual surfaces**, all peers on a flat top bar: `board`, `work`
(ledger + case file), `ask`, `policy`, `integ`.

**Ten API endpoints**: run, rows, settlement, exceptions, investigate,
observatory, events, integrations, ask, policy.

**Fourteen widgets**: money, health, safety, exposure, volume, reasons, largest,
activity, strata, hazards, failures, events, rules, solver.

**Twenty-two design tokens** — and 11 distinct border radii, 19 distinct font
sizes, 10 hardcoded colours across 428 lines of CSS. The tokens exist; the
discipline does not.

## B · What is wrong with it

**1 · The navigation is a toggle list, not a hierarchy.** Board, Sources, Ask and
Policy are rendered as peers. They are not peers: one is a workspace, one is a
connection status page, one is a query surface, one is a control. A user cannot
infer the shape of the product from its navigation because the navigation has no
shape.

**2 · The ledger occupies 326px of every screen, including the ones it has
nothing to do with.** Reading source health does not require a settlement list
beside it.

**3 · There is no attention model.** The board reports state; it never says what
needs a person. A user with 198 unresolved settlements is handed a scrollable
list and left to prioritise by eye — which is exactly the labour the product
claims to remove.

**4 · The strongest screen is the hardest to reach.** The case file — proof,
evidence flow, search space, competing explanations — is the product, and it sits
behind a row click in a side rail.

**5 · Verdicts are labelled, not designed.** AMBIGUOUS renders as an amber pill
on an otherwise identical layout. The three states are the central idea and they
look like a status column.

**6 · No number explains itself.** §15 asks for a WHY path on every figure. Today
`₹0 wrongly auto-posted` is a number with no provenance in the interface, which
is a strange thing for a product about provenance.

**7 · Razorpay is a settings page.** The most product-defining integration is
presented as configuration.

## C · Three directions considered

**Direction 1 — Modes.** Four verbs: CONTROL, INVESTIGATE, VERIFY, AUTOMATE.
Each owns its own layout rather than sharing a fixed chrome.
*Strength*: the navigation states what the product is for. *Cost*: a rebuild of
the shell.

**Direction 2 — Persistent attention rail.** One canvas, a permanent left rail of
what needs a human, everything else opening in the main pane.
*Strength*: smallest change, strong attention model. *Cost*: still one flat
surface; depth has nowhere to live.

**Direction 3 — Case-centric.** The settlement is the whole application;
everything else is a lens over the current case.
*Strength*: purest expression of the thesis. *Cost*: portfolio-level questions —
policy, evaluation, source health — have no home.

## D · Chosen: Direction 1, with Direction 2's attention model inside CONTROL

Modes give depth somewhere to live and state the product's purpose in four words.
The attention queue becomes CONTROL's opening screen rather than a separate
surface, which is what the brief asks for: *seven things need your attention*,
before any chart.

    CONTROL      what is happening, and what needs me
    INVESTIGATE  why, and what would resolve it
    VERIFY       can this system be trusted
    AUTOMATE     what is allowed to happen without me

Everything currently on the top bar folds into one of the four. Sources moves
into AUTOMATE (a connection is a source of authority to act) and VERIFY carries
the evaluation and the failure observatory, which is where a sceptical engineer
goes first.

**Financial State** is the signature screen and it lives under CONTROL:
what we know, why, what would resolve it, what ATTEST will do.

## E · What was built, and what it cost

Fourteen screens across the four modes. Sub-navigation lives inside a mode, so
adding a surface does not add a top-level item — which was the failure the audit
predicted for the flat top bar.

    CONTROL      Attention · Overview
    INVESTIGATE  Settlements · Exceptions · What changed · Ask ATTEST
    VERIFY       Accuracy · Failures · Trust centre
    AUTOMATE     Policy · Agents · Sources · Live events

Three of these had modules but no surface before this pass: **Trust centre**
(`rules.py` provenance and `eval/gate.py`), **Agent permissions** (`agents.py`),
and **What changed** (`whatchanged.py`, written during the evidence work and
unused for six days).

### Screens that were changed to stop asserting and start demonstrating

**Live events** described signature verification and idempotency over an empty
log. It now sends four deliveries through the same code path the HTTP endpoint
uses and prints what came back: accepted, duplicate, replay mismatch, bad
signature. The log grows by four because four were really delivered.

**Agent permissions** listed capabilities. It now runs the pipeline against the
current run's findings, so the refusal of `post_accounting_entry` at the
capability stage is something the code did rather than something the page says.

**Accuracy** reads `benchmark/results.json` and `benchmark/baseline.json` — the
same two files the build reads — so the screen cannot report a pass that CI
would fail.

### Defects this pass found, all by screenshotting a screen and reading it

1. The board labelled proven value **auto-posted**. Proven means a unique
   kernel-checked explanation exists; the policy then prices it. The board
   claimed 52 settlements had posted while the policy screen, correctly, said 1.
2. Financial State said "27 of 31 orders explained". The four explanations do
   not share a denominator, so the sentence was arithmetic nonsense that read
   fluently. It now says 27 orders appear in all four explanations, ₹97,759.84
   is settled whichever is right, and ₹7,292.03 turns on which one is.
3. The candidate bars plotted each explanation's total — the same number four
   times. They now split shared orders from unique ones, which is the only thing
   that distinguishes the explanations: 27 shared, 4–5 unique.
4. Policy reasons were denominated in paise. A reader deciding whether to trust
   a posting had to convert before they could judge.
5. `class="gate n"` collided with `.n`, the global tabular-numeral class, so the
   whole refusal argument rendered in monospace.
6. Explanatory prose wore `.why`, the dotted-underline provenance affordance,
   promising a click that explains a number it does not have.
7. `run()` reset the screen on completion, so re-running from Trust centre
   dropped you back to Attention.
8. The status bar advertised `j`/`k`/`/`/verdict keys on every screen; they only
   bind on the ledger, and pressing `1` elsewhere silently filtered a list the
   user could not see.

### Measured after

    raw font sizes in CSS      99 across 19 values  ->  0
    raw border radii           35 across 13 values  ->  0
    WCAG AA text failures      46 distinct styles   ->  0
    horizontal overflow        36px at 430px        ->  0 from 430px to 1512px

The contrast result was the one that mattered. The old de-emphasis ramp bottomed
out at 2.38:1, and that is where nearly all the explanatory prose lived — so the
writing this product depends on to make its case was the writing hardest to
read.
