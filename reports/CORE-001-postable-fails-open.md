# CORE-001 — `Finding.postable` fails open when no search space is recorded

**Status:** reported, not patched. `attest/verdict.py` is protected by
`.githooks/pre-commit`; the guard says report with a reproduction rather than
edit, so this is the report.

**Found by:** hardening phase 8.13, writing the AI-boundary check as an attack
rather than as an assertion.

---

## The defect

```python
# attest/verdict.py, Finding.postable
if self.verdict is not Verdict.PROVEN:
    return False
from attest.searchspace import Integrity, SearchSpace
if isinstance(self.space, SearchSpace):
    return self.space.integrity is not Integrity.COMPROMISED
return True          # <-- a finding with NO search space is postable
```

A `Finding` carrying no search-space record at all returns `postable = True`.
The property exists to encode D8 — *uniqueness inside a space that excluded the
truth is not uniqueness* — and it currently trusts a proof whose candidate
universe is unrecorded. It fails **open** where §8.11 of the hardening brief
requires that "a proof without search-space provenance is incomplete".

## Reproduction

```python
from attest.verdict import Finding, Proof, Verdict

naked = Finding("s1", Verdict.PROVEN,
                (Proof("s1", ("o1",), 1, 0, 0, 0, 1, 0, 1),))
assert naked.space is None
assert naked.postable is True        # currently passes; should not
```

Reached through the ledger, the forged proof is refused — but by
`Unbalanced` in `ledger.post`, i.e. by arithmetic rather than by the integrity
gate:

```python
from attest.ledger import post
out = post(naked, settlement, permissive_judgement, orders)
# raises Unbalanced, rather than returning a Refusal citing the search space
```

Defence in depth caught it. The gate that was supposed to did not.

## Blast radius

**None observed in the engine.** `attest/pipeline.py` attaches a `SearchSpace`
to every finding it produces, so no run reaches this branch:

```
250-settlement run: 52 postable before, 52 after a local fix
all six regression gates: +0.0000 on every metric
```

The exposure is to any `Finding` assembled outside the pipeline — a test
fixture, an adapter, a future caller, or an attacker who omits the field
precisely because it is the field being judged.

## Suggested fix

Invert the default so the absent case is disqualifying:

```python
if not isinstance(self.space, SearchSpace):
    return False
return self.space.integrity is not Integrity.COMPROMISED
```

## Suggested tests to land with it

```python
def test_a_proof_without_search_space_provenance_cannot_post():
    naked = Finding("s1", Verdict.PROVEN,
                    (Proof("s1", ("o1",), 1, 0, 0, 0, 1, 0, 1),))
    assert not naked.postable

def test_the_engine_still_attaches_a_search_space_to_every_proof():
    r = api.execute(250, 20260821)
    for f in r.findings:
        if f.verdict is Verdict.PROVEN:
            assert isinstance(f.space, SearchSpace) and f.space.reductions
```

The second matters as much as the first: failing closed is only safe if the
engine actually records what it is being asked for. It does, verified on the
250-settlement panel.
