"""CLI: `python -m attest baseline`."""

from __future__ import annotations

import sys
from pathlib import Path

from attest.eval.harness import Timer, evaluate
from attest.generate.generator import build
from attest.pipeline import run

DATA = Path(__file__).resolve().parent.parent / "data"

#: Frozen on D1. The held-out seed is intended to be run exactly once, at the end.
SEED_TRAIN = 20260821
SEED_HOLDOUT = 900913


def main(argv: list[str]) -> int:
    n = int(argv[1]) if len(argv) > 1 else 1200
    holdout = "--holdout" in argv

    seed = SEED_HOLDOUT if holdout else SEED_TRAIN
    ds = build(n, seed=seed)
    ds.write(DATA / ("holdout" if holdout else "train"))

    with Timer() as t:
        preds, pools = run(ds.settlements, ds.orders)
    rep = evaluate(ds.settlements, ds.truth, preds, pools, t.elapsed)

    label = "HELD-OUT" if holdout else "TRAIN"
    print(rep.render(f"ATTEST  ·  D1 deterministic floor  ·  {label}  ·  seed {seed}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
