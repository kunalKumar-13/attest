# Three directions for ATTEST

Written after `UX-AUTOPSY.md` and before any code, per the directive. Each is a
different answer to the same five measured defects:

    1. six lenses masquerading as six screens
    2. the subject dies on navigation (4 of 6 transitions)
    3. explanation is always-on (43% of on-screen text)
    4. no component layer between tokens and screens (227 classes, 11 headers)
    5. every screen the same shape (title → paragraph → list)

These are genuinely different products, not three skins. Each section ends with
what it would cost and what it would be bad at, because a direction whose
weaknesses I cannot name is one I have not thought about.

---

# Direction A — THE LEDGER ROOM

*One canvas. Everything else is summoned over it.*

**Navigation.** None. There are no tabs, modes or sub-navigation. There is one
permanent canvas and a command bar. Every other surface in the product opens as
a sheet over the canvas, and the canvas stays visible behind it. Closing the
sheet returns you exactly where you were because you never left.

**First screen.** The money, permanently:

    ₹53,02,701 processed today
    ₹4,99,574 proven · ₹47,96,811 uncertain · ₹6,316 contradicted

    3 actions can resolve ₹53,02,701
      ▸ Supply an order-level reference    SYSTEMIC   ₹47,96,811   1 step
      ▸ Widen the window and re-run        FREE       ₹4,99,574    1 step
      ▸ Find a fee correction              PER ITEM   ₹6,316       1 step

    198 things need a person, by money
      000089  ₹1,00,036.83  27 orders settled; ₹7,292.03 across 12 in dispute

**Settlement.** A sheet slides over the canvas at 60% width. The portfolio
totals stay visible at the edge, so you never lose the sense of scale you were
working at.

**Investigation.** Sheets stack, at most two deep, with a breadcrumb. A third
push replaces the second rather than burying it.

**Evidence / AI / proof.** Sections within the settlement sheet, collapsed by
default, each one line until opened.

**Actions.** The action queue is *on the canvas*, not behind navigation. It is
the second thing you see, always.

**Razorpay.** A strip on the canvas: source, last sync, verdicts unrevised.
Clicking opens the sources sheet.

**Why it is better.** Kills the navigation act entirely — defect 2 is solved by
construction, because there is nowhere to navigate to. Defect 1 improves
because the lenses become filters on one canvas list.

**What it is bad at.** Deep work in a 60% sheet is cramped, and Policy, Trust
centre and the Failure observatory are not sheet-shaped — they are dense
full-width surfaces that would fight the container. Defects 3 and 4 are
untouched. It is also the least distinctive of the three: a canvas with slide-
overs is a known pattern, and a Razorpay engineer has seen it.

**Cost.** Smallest. Perhaps a third of the UI rewritten.

---

# Direction B — THE SPINE

*The verification pipeline is the interface.*

**Navigation.** The five stages are permanent, across the top, always:

    STATE ──── EVIDENCE ──── VERIFICATION ──── POLICY ──── ACTION

That is not a metaphor for the architecture; it *is* the architecture, made
into the only navigation there is. You do not go to a page. You move a subject
along the spine, and the spine shows where it stopped.

**First screen.** The portfolio distributed across the spine — how much money
is standing at each stage and what is blocking it:

    STATE          EVIDENCE        VERIFICATION    POLICY          ACTION
    ₹53,02,701     ₹53,02,701      ₹4,99,574       ₹353            ₹353
    250 settled    250 scoped      52 proven       1 clears        1 posts
                                   197 ambiguous   51 too risky
                                   1 contradicted

Where the money stops is the whole story, and it is legible in one glance:
₹47.96L stops at VERIFICATION, and it stops for one reason.

**Settlement.** The same spine, one subject. Each stage is a step you can open,
and the stage that refused is pre-opened. A proven settlement shows five green
stages; an ambiguous one shows the arrow stopping at VERIFICATION with the
three surviving explanations underneath.

**Investigation.** Investigation is the EVIDENCE stage of a subject that
stopped. The AI trail is a panel inside it, marked as proposing rather than
deciding — the spine makes it structurally obvious that the model sits before
the verifier.

**Evidence / proof.** The graph belongs to EVIDENCE, the kernel result and the
search-space integrity claim to VERIFICATION. The journal is ACTION. Nothing
needs a page.

**AI.** Structurally subordinate. It cannot appear to the right of VERIFICATION
because that is not where it sits in the system. The layout is the argument.

**Actions.** ACTION is a stage, and the Act queue is that stage viewed across
the whole portfolio.

**Razorpay.** Upstream of STATE — a source rail feeding the spine, with sync
health as "records arrived after this subject passed STATE".

**Why it is better.** It is the only direction where the interface *is* the
thesis. "AI proposes, ATTEST proves, Policy decides" stops being a tagline on a
README and becomes the shape of the screen. It fixes defect 5 completely: every
stage has a different natural shape, so no two views look alike. It fixes
defect 2 because the subject is what moves.

**What it is bad at.** Portfolio-level work that is not about a subject —
the policy cost sweep, the Trust centre, the Failure observatory, the
benchmark — has no natural home on a per-subject spine. Forcing them on would
be a lie about the model. It probably needs a second, smaller room for "about
the system rather than about the money", which weakens the "one structure"
claim. It is also a strong commitment: if the five stages are ever wrong, the
whole UI is wrong.

**Cost.** Large. Most of the UI, and a new layout primitive.

---

# Direction C — THE CASE DESK

*One subject, many lenses. The subject never dies.*

**Navigation.** Two axes, and neither is a page.

- **Subject** — what you are looking at. A settlement, a group of them, an
  action, a rule set, a source, or *the portfolio itself*. Held in a rail on
  the left and changeable from ⌘K.
- **Lens** — how you are looking at it: `state · evidence · proof · policy ·
  journal · trail · history`. A strip, not a menu.

The portfolio is not a special screen. It is the root subject, and every lens
works on it. `portfolio × state` is the control centre. `portfolio × journal`
is the whole day's accounting. `setl_000089 × journal` is one entry.

**First screen.** `portfolio × state`: money at the top, the leverage-ranked
action queue, the attention queue. The same content Direction A puts on its
canvas, but reachable as one cell of a grid rather than as a special case.

**Settlement.** Click any row anywhere and the subject changes. The lens does
not. If you were looking at `journal` and you click a settlement, you get that
settlement's journal entry — because you already said what you wanted to know,
and the product should not make you say it again.

This is the direct fix for defect 2, and it is stronger than persistence: the
subject is the *root of application state* rather than a thing that survives.

**Investigation.** `subject × evidence` and `subject × trail`. The AI trail is
a lens like any other and is marked as proposing.

**Evidence / proof.** `proof` is a first-class lens, so a proven settlement's
certificate is one keystroke from its journal entry, its policy decision and
its evidence graph — with no navigation between them.

**AI.** A lens, never a mode. It cannot be mistaken for the engine because it
sits in the same strip as `policy` and `proof` and is labelled as proposal.

**Actions.** `portfolio × actions`. Selecting an action makes *the action* the
subject; its lenses are the settlements it unlocks, the evidence it needs, the
value it releases.

**Razorpay.** A source is a subject. `razorpay × state` is connection health,
`razorpay × history` is the delivery log, `razorpay × evidence` is what it
contributed to the current book.

**Why it is better.** It is the only direction that names the real defect. Six
screens were one `GROUP BY`; here the grouping *is* the lens, made explicit and
composable, so the six collapse into one surface with a strip. It is the only
one where portfolio-level and subject-level work use the same machinery, so the
Trust centre and the Failure observatory are not exceptions. And it forces the
component layer that defect 4 says is missing: a lens must render any subject,
so the parts have to be shared.

Explanation attaches to the *lens*, not the page — shown on first use of a lens
and collapsed thereafter — which is the fix for defect 3.

**What it is bad at.** Two axes are more to learn than one, and a subject × lens
grid can feel like an IDE rather than a financial instrument if the density is
wrong. Not every lens is meaningful for every subject, and greyed-out cells are
a bad look; the product has to hide rather than disable. It is the most work.

**Cost.** Largest. The shell, the component layer, and every screen re-expressed
as a lens.

---

# The choice: C, with B's spine as the `state` lens

**C is the architecture.** It is the only one of the three that names the
measured defects rather than routing around them:

| Defect | A | B | C |
|---|---|---|---|
| 1 · six lenses as six screens | partly | partly | **named and fixed** |
| 2 · subject dies on navigation | avoided | fixed | **fixed at the root** |
| 3 · explanation always-on | untouched | partly | **fixed per lens** |
| 4 · no component layer | untouched | forced | **forced** |
| 5 · every screen the same shape | partly | **fixed** | fixed |

**B is the picture.** Direction B's one great idea is that the pipeline should
be visible, and it does not need to own the whole product to deliver that. So
the `state` lens — the default, the first thing anyone sees at both portfolio
and settlement level — renders as the spine:

    STATE ──── EVIDENCE ──── VERIFICATION ──── POLICY ──── ACTION

At `portfolio × state` it shows where the money stops. At `setl_000089 × state`
it shows where that settlement stopped and why. The other lenses are then the
stages opened up, which is a coherent story rather than a compromise: the spine
is the map and the lenses are the territory.

This keeps B's argument — the layout says *AI proposes, ATTEST proves, Policy
decides* — while giving the portfolio-level surfaces B had nowhere to put a
natural home as lenses on the root subject.

**A is rejected**, but its discipline is adopted: no navigation act should cost
you your place. Under C that is guaranteed by construction rather than by
sheets, because changing lens does not change subject and changing subject does
not change lens.

## What this means concretely

- 16 screens become **1 shell × 7 lenses**, with the subject rail.
- `Attention`, `Act`, `Exceptions`, `Overview`, `Journal`, `Settlements` stop
  being screens. They are `portfolio × state`, `portfolio × actions`,
  `portfolio × journal`, and a lens-aware queue.
- `Financial State` — the best thing in the current UI — becomes
  `settlement × state`, which is what it always was.
- ⌘K becomes the primary interaction: it sets subject, lens, or both.
- A component layer is built first, because a lens that must render any subject
  cannot invent its own header.
- Every API route survives. This is a shell and IA change, not an engine one.

Nothing here is implemented yet. That is the next step, and it starts with the
component layer rather than with a screen.
