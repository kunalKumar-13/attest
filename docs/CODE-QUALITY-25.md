# Phase 25 — Code Quality: Before / After

Companion to `CODE-QUALITY-AUDIT-25.md`, which holds the measurements. This
records what changed, why each change is safe, and — at greater length — what
was deliberately left alone.

---

## Before / after

| | before | after |
|---|---|---|
| tracked source files | 155 | 155 |
| Python LOC | 17,135 | 17,105 |
| money formatters in Python | **4** | **1** |
| money formatters disagreeing with each other | **1** | 0 |
| duplicate benchmark-artifact readers | 2 | 2 *(kept — see below)* |
| `except Exception` | 8 | **5** |
| `except Exception` that could hide a caller's bug | 3 | **0** |
| bare `except:` | 0 | 0 |
| unused imports | 8 | **1** |
| unused locals | 9 | 7 |
| `TODO`/`FIXME`/`HACK` | 0 | 0 |
| import cycles | 0 | 0 |
| engine modules importing UI or API | 0 | 0 |
| formatting inside the proof kernel | 0 | 0 |
| money paths using `float` or `round` | 0 | 0 |
| README money rendered with dropped paise | **yes** | **no** |

---

## Critical invariants, and where the code enforces them

| | enforced at |
|---|---|
| **money** | `adapters/money.parse_amount(raw, Unit)` — exact or raises. `Decimal` appears nowhere else. Every downstream amount is `int` paise, named `*_paise`. |
| **rendering** | `attest/money.rupees` — the only definition in the package, now asserted by contract. No call site uses it inside a conditional. |
| **proof** | `Finding.postable` — a PROVEN verdict, re-derived by the 28-line kernel, over a space whose integrity is recorded. Absent space fails closed (CORE-001, named in the docstring). |
| **membership** | `set(proof.order_ids) <= space.members` in `verdict.py`, with `searchspace.why_not_postable` naming which of the six conditions failed (CORE-002). |
| **policy** | `policy.py` imports `Finding`/`Verdict` and no solver. It reads a verdict; it cannot produce one. |
| **ledger** | `ledger.py` reads `Decision`, `Judgement`, `Verdict` and the shared refusal function. It writes only what policy permitted. |
| **adapter** | `AMOUNT_UNIT = Unit.PAISE` declared at module level; `_identity()` per record type with `IdentityConflict` on disagreement; `Rejection` carries index, reason and identity. |
| **navigation** | zero assignments to `SHELL.subject/.lens/.context` outside `shell.js`; zero history writes outside it; `AsyncResourceGuard` plus a post-await subject re-check. |

---

## Changes made

### 1 · One money formatter

**Files** `attest/api.py`, `attest/eval/report.py`, `attest/eval/claims.py`

**Problem** Phase 12 consolidated money rendering into `attest/money.py` and
routed four modules through it. Three copies survived that sweep, and one of
them had drifted into a different formatter.

**Change** All three now import `attest.money.rupees`.

**Why safe** `api._rs` was proven byte-equivalent across **20,016 values**
including negatives, zero and 12-digit amounts; `report._rs` across **5,008**.
Deleting a function and importing an identical one cannot change output.

`claims._rs` was **not** equivalent — `f"₹{paise // 100:,}"` used Western
grouping and discarded the paise. This is the one deliberate behaviour change in
the phase, made under the rule permitting it when *current behaviour is
demonstrably defective*: a system whose argument is exact integer paise was
publishing truncated money to its own README.

```
BEFORE                              AFTER
settled (undisputed)  ₹6,766,131    settled (undisputed)   ₹67,66,131.23
disputed              ₹7,573,097    disputed               ₹75,73,097.75
processed            ₹10,204,411    processed             ₹1,02,04,411.89
auto-posted              ₹40,464    auto-posted               ₹40,464.20
wrongly auto-posted           ₹0    wrongly auto-posted            ₹0.00
```

No engine number changed — only how it is written. The generated block was
regenerated from the same artifacts by `claims.sync_readme()`, and the column
width widened from 12 to 16 so the fuller amounts stay aligned.

**Test coverage** `tests/test_operator_units.py` gains
`test_there_is_exactly_one_money_formatter` (AST scan of every tracked module —
asserts on the *file*, not a line number) and
`test_every_money_renderer_agrees_on_paise_and_grouping`.

### 2 · Named exception handlers at three boundaries

**Files** `attest/api.py` ×2, `attest/eval/claims.py`

**Problem** `except Exception` around a file read plus a JSON parse plus a dict
index. The fallback semantics were right — an absent artifact means NOT
MEASURED, never a passing claim — but the handler also caught programming errors
in its own expression and returned the fail-closed value, which would present a
bug as a missing measurement.

**Change** `except (OSError, ValueError)` for the artifact readers,
`except (OSError, ValueError, KeyError)` for the anchoring statistic, each with
a comment stating the fallback's meaning.

**Why safe** Strictly narrower. Every exception previously caught *and expected*
is still caught; only unexpected ones now surface. One additionally sets
`share = None` explicitly where it previously relied on the initialiser.

**Test coverage** Trust's claim register is covered by existing browser
contracts asserting that an unmeasured claim renders as NOT VERIFIED.

### 3 · Unused imports and locals

**Files** `attest/eval/adversarial.py`, `attest/eval/blocking_study.py`,
`attest/hypothesis.py`, `attest/api.py`, three test modules

**Change** Removed 7 unused imports and 2 unused locals, each reported by
pyflakes and re-verified after.

**Why safe** Removing a name nothing reads cannot change behaviour; the full
suite re-ran green.

---

## Changes NOT made

This section matters more than the one above.

### `attest/pipeline.py` — proposed, reverted, reported

`_attach_cores` catches `except Exception` around an optional ortools import.
The fallback is documented and correct — *"a missing core costs an explanation,
never a verdict"* — but it is as broad as the ones tightened above.

I narrowed it to `(ImportError, RuntimeError, ValueError)` and then **reverted
it**, for two reasons. `pipeline.py` is in the pre-commit protected set, and
§25M says protected core is not auto-edited. And the narrowing is not obviously
safe: `pack()` runs CP-SAT through an optional dependency, and an ortools error
outside that tuple would now abort a run that previously degraded to a missing
explanation. That trade needs a measurement I do not have.

**Proposal for a human:** narrow to `(ImportError, Exception)` is meaningless;
the useful form is to catch `ImportError` separately from solver failure, which
requires knowing what `pack` can raise. Worth doing with ortools installed and
the blocking study run; not worth guessing at.

### `attest/api.py` at 2,315 lines

Six of the nine functions over 100 lines live here, and §25N asks for a thin API
layer. It is **not** thin — but it is also not doing business logic: the long
functions are *view assemblers* that read domain objects and shape JSON. The
business logic they call lives in `policy`, `ledger`, `exceptions`, `hypothesis`
and `searchspace`, none of which `api.py` reimplements.

Splitting it into per-view modules is a large mechanical refactor of the layer
every browser contract reads through, in a phase whose first rule is no
behavioural change. The cost is real and the benefit is organisational. **Left
alone, and recorded as the largest outstanding structural item.**

### `RazorpayAdapter.normalise` at 161 lines

§25L asks for a boring adapter. The eleven properties are all explicit and in
the right order; they are interleaved across three record types in one pass
rather than separated into three functions. Splitting would read better and
would touch the single most safety-critical parsing path in the repository.
Covered by 336 lines of adapter tests and the 34-attack adversarial suite —
which is an argument for it being *possible*, not for it being *necessary* now.

### `attest/ui/exp/` and `attest/ui/proto/`

Static analysis calls ten files unused. `docs/COMPOSITION-REVIEW.md` records
that `comp-b` and `comp-c` were removed and `comp-a` kept as the surviving
composition. Deleting them would make the surviving documentation false. This is
precisely the case §25O's conservatism exists for.

### Two benchmark-artifact readers

`api._load` and `claims._load` do the same thing. Consolidating means one of
them imports the other, which either drags `eval` into the API layer or the API
into `eval`. Two five-line readers is a smaller cost than a new dependency edge
between layers that currently do not know about each other.

### Renaming

`amount_paise`, `expected_loss_paise`, `review_paise`, `disputed_paise`,
`net_paise` — the unit is already in the name wherever ambiguity is possible.
§25F says not to rename for aesthetics when the convention is unambiguous. It is.

---

## The question

> *If I joined this repository tomorrow as a Razorpay engineer, would I trust
> myself to modify it without accidentally changing financial truth?*

**Yes, for money and proof.** Money has one entry point that refuses rather than
coerces, one representation, and now one renderer that a test enforces. A proof
cannot be posted without a recorded search space, and cannot cite an order
outside it — both structural, both with the incident that motivated them named
in the code. The proof kernel contains no formatting at all, so no display
change can reach a verdict.

**One reservation, and it is honest:** `api.py` is 2,315 lines. Nothing
financial is decided there, but a newcomer looking for where a number comes from
has a long file to read before they find out it came from somewhere else. That
is the remaining reason, and it is organisational rather than a risk to
correctness.

---

## What the clean room found

§25Q is mandatory for a reason. A fresh extraction — `git ls-files | tar`, a new
`python3.13` venv, `pip install -e .` — found three things the working tree
could not.

### 1 · The interpreter guard works

```
$ python3 -m venv .venv && .venv/bin/python -c "import attest"
RuntimeError: ATTEST needs Python 3.11 or newer; this is 3.9

  macOS ships 3.9 as `python3`. Use an explicit version:
      python3.13 -m venv .venv && ./.venv/bin/pip install -e .
```

Not a defect — the guard catching macOS's default interpreter and naming both
the fix and the failure record (D1) is exactly what it was built for.

### 2 · My own new contract passed for the wrong reason

`test_there_is_exactly_one_money_formatter` shelled out to `git ls-files` to
enumerate modules. A clean extraction is **not a git working tree**: the command
returns nothing, the loop body never executes, `defs` stays empty — and the
assertion compares an empty list against the expected one and fails. In a
subtly different arrangement it would have *passed* on an empty list, which is
the accidental-pass shape §25J warns about, written by me, one phase after
writing that warning down.

Rewritten to walk `(ROOT / "attest").rglob("*.py")` with an
`assert sources` guard, and verified in both trees.

### 3 · `ci/verify.sh` asserted a contract count that went stale

```
CONTRACTS=90        # actual: 133
```

The stage exists to close a real trap — browser contracts skip themselves when
nothing is listening on `:8420`, and a skip reports as a pass, so `0 passed`
would otherwise be green. The literal was correct when written and has been
wrong for every contract added since, which means the stage would fail a
perfectly green suite. A guard that cries wolf teaches people to stop believing
it.

**Change** the count is derived from the source:

```sh
CONTRACTS=$(grep -c "^def test_" tests/test_shell_contract.py)
```

Strictly stronger than the literal: it still catches "ran nothing", and it now
also catches a contract that silently stopped being collected. It cannot go
stale.

`docs/REPRODUCE.md` carried the same stale numbers in three places (`90`
contracts, `251 passed`, a four-row environment table). Remeasured against the
clean room — **297 passed** with the full stack, **138 passed / 134 skipped**
without Playwright's server or `ortools`.

Historical phase records (`FAILURE-REGRESSION-MAP.md`, `INTERACTION.md`,
`PROTOTYPE-REVIEW-10.md`, `VISUAL-LANGUAGE.md`) also name older counts and were
**left alone**: a dated measurement is not a contradiction, and rewriting the
record of what was true then would be the worse error.

### Gate numbers differ in the clean room, and that is documented

```
                              working tree        clean room
money wrongly auto-posted     0 → 0    +0         0 → 0    +0
false proof rate         0.0080 → 0.0080 +0.0000  0.0080 → 0.0080 +0.0000
proof precision          0.9524 → 0.9524 +0.0000  0.9524 → 0.9506 -0.0018
safe resolution rate     0.0220 → 0.0220 +0.0000  0.0220 → 0.0160 -0.0060
```

The clean room has no `ortools` and no built Rust kernel, so it runs the numpy
path. `REPRODUCE.md` states this on line 15 — *"the engine runs without it, and
the numbers differ"*. The two **safety** gates are identical to four decimal
places in both environments; only coverage moved, which the gate itself reports
as an allowed trade.

**This is environmental variance, not drift from the cleanup.** The evidence
that the cleanup changed nothing is the working tree: all six gates at
**+0.0000** both before and after, in one environment.
