# Product autopsy — ATTEST 10

Phase 10.0. Measured against the running product at 1440×900 on 2026-08-23, by
walking all fourteen views and reading the rendered geometry. Nothing here is
recalled or reasoned; every number came back from the browser.

---

## The finding

**Roughly half of what an evaluator sees on any lens is the same 29 strings.**

Twenty-nine text strings are identical, and identically placed, on all seven
lenses. They are the subject header, the lens strip and the state spine.

| lens | share of the visible screen that is identical on all seven lenses |
|---|---|
| trust (settlement) | **96.7%** — 29 of 30 visible strings |
| journal | **78.4%** — 29 of 37 |
| policy | 58.0% |
| investigate | 53.7% |
| control | 49.2% |
| activity | 47.5% |
| evidence | **40.8%** — the best, and it is still two fifths |

Pairwise, `journal`/`trust` share **76.3%** of their visible text; `policy`/`trust`
**56.9%**; `investigate`/`trust` **52.7%**.

And the vertical cost:

```
                                        1440 × 900
   ┌──────────────────────────────────┐
   │ subject header            90px   │
   │ lens strip                46px   │  343px  =  38% of the viewport,
   │ state spine              162px   │           byte-identical on all
   ├──────────────────────────────────┤           seven lenses
   │                                  │
   │ the lens's own instrument        │  557px
   │                          557px   │
   └──────────────────────────────────┘
```

**This is what "seven lenses that happen to share a shell" means, measured.**

It is also the direct cost of something that was *correct*. Phase 9.3 promoted
the spine to every lens so the financial state is answerable at every moment,
and that was the right call — it is the product's strongest idea. But
continuity was implemented by **repeating the case at the top of every
instrument**, and repetition at 38% of the viewport is no longer continuity. It
is redundancy that the eye learns to skip.

The case should be an **object the instruments hang off**, not a band each
instrument redraws.

---

## Second finding — the case's answer is not in the visual hierarchy

The attention proxy ranks every above-fold leaf by visual weight
(size² × weight). On every lens the top two are the same:

```
   34px/500   ₹1,00,036.83        the amount
   20px/600   setl_000089         the identity
   ─────────── then a cliff ───────────
   13px …     everything else
```

On **`settlement/policy`**, the third, fourth and fifth heaviest things on
screen are: `ATTEST` (the application's own name, 11px/700), `Policy` (the lens
label), and `Verification`. The word **REVIEW** — which is the entire answer to
the question that lens asks — does not appear in the top six.

On **`settlement/evidence`**, the heaviest content element is `amount match` at
13px/700, sitting at `top=889` — below the fold.

Only `settlement/control` puts an answer in the hierarchy: `27 orders`,
`₹97,759.84`, `₹7,292.03` at 20px, at `top=409`.

**The case identity is loud and the case's conclusion is quiet.** The type
histogram says the same thing: 8–11 distinct size/weight pairs per view, of
which `11px/400` accounts for 30–105 nodes and `10px/400` for 5–49. Nearly
everything the product has to say is rendered as body text.

---

## Third finding — the work is below the fold

| view | scroll needed | actions below the fold |
|---|---|---|
| portfolio/trust | **3,090px · 6.8 screens** | **32** |
| portfolio/activity | 850px · 2.6 screens | 5 |
| portfolio/control | 475px · 1.9 screens | 6 |
| settlement/policy | 528px · 2.0 screens | 0 |
| settlement/evidence | 408px · 1.8 screens | 0 |

Trust is not a lens, it is a document — nearly seven screens deep, with 32
interactive things a reader cannot see.

And on **every** view the first interactive element is at `top=8`: the theme
toggle and the Run button. **The first thing an operator can touch on any screen
is application chrome, not case work.**

---

## What is working, and must survive

Measured, not assumed:

- **The spine reads pre-verbally.** SOURCE and MATCHING full, VERIFICATION a
  stub, POLICY and ACTION hairlines — the collapse is legible before any number.
- **The amount is unambiguously the subject** at 34px/500 against 13px body.
- **Evidence's compression band** is the least chrome-dominated view in the
  product (40.8%) and the only one whose instrument competes with the shell.
- **Interaction is 4–9ms** on every transition; nothing here is a performance
  problem.
- **The interaction contract holds** on all eight clauses.
- **`setl/control` proves the hierarchy can work** — it is the one view that
  puts a conclusion at 20px where the eye can find it.

---

## The diagnosis in one line

The shell won. It is correct, continuous, accessible and fast — and it occupies
38% of the viewport and half of what is visible, so the seven instruments render
in the margin left over.

**Phase 10 is not about making the instruments prettier. It is about giving them
the screen.**
