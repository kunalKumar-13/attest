# Recording the canonical run

## Setup

```bash
git clone https://github.com/kunalKumar-13/attest && cd attest
python3.13 -m venv .venv && ./.venv/bin/pip install -e .
./run-demo
```

`run-demo` prints the journey with every figure read live from the run, so it
doubles as a pre-flight check: if a number on that printout disagrees with the
script, the script is wrong.

The run is deterministic. Seed `20260821`, 250 settlements, 2,368 orders. The
same seed produces the same 52 / 197 / 1 every time, on any machine.

## What must be true before you hit record

**The adversarial artifact.** `benchmark/adversarial.json` is tracked, so a
clone already has it and Trust reads 34 / 34 / 0 without you running anything.
*(An earlier draft of this file claimed a fresh checkout would not have it.
That was wrong — verified on a clean clone.)* Re-running
`./.venv/bin/python -m attest.eval.adversarial` regenerates it and should end
on `34 attacks · 34 defended/control-ok · 0 breached`.

**The kernel — this is the one that matters.** The recording uses the native
kernel. Without it the portable solver runs a ₹30,000 envelope instead of
₹2,00,000, and the portfolio figures change:

| | native kernel | portable |
|---|---|---|
| split | 52 / 197 / 1 | 51 / 161 / 1 · **37 insufficient** |
| held at verification | ₹48,03,127.81 across 198 | ₹49,16,887.51 across 199 |
| top blocker | ₹47,96,811.78 · 197 | ₹25,58,683.75 · 37 |

Everything from 1:35 onward is **identical on both**: `setl_000225` at
₹27,208.12, AMBIGUOUS, 2,368 → 164 → 4, the model/solver/engine boundary,
27 of 63 at 42.9%, the 500-settlement benchmark panel, 6/6 gates, 34/34,
21/21, the 28-line kernel. The case was chosen for exactly this reason.

Build it before recording:

```bash
cd native && maturin develop --release && cd ..
```

Then confirm `./run-demo` prints `ATTEST · GENERATED · NATIVE KERNEL` before
any portfolio figure. If it prints `PORTABLE`, stop — the numbers on screen
will not be the numbers in the script.

**The window.** 1440×900. Hide bookmarks. Full-screen the browser. Nothing else
visible: no editor, no terminal, no notifications. Turn off anything that can
produce a banner for five minutes.

## Recording

Follow `DEMO-SHOTLIST-35.md` row by row. It gives the cursor action and the
figure that must be legible for each line.

Record the screen and the audio in one take if you can. If you cannot, record
the screen clean and lay the voice over it afterwards — but keep the scroll
pacing from the shot list, because the timings are built around figures being
on screen when they are spoken.

**Scroll slowly.** The reveal animations run at 250ms and the fields draw over
about 900ms. Scrolling fast means the population field is still assembling when
you start talking about it.

**Do not click anything the shot list does not name.** Every click reads as
intent; a click with no reason reads as fumbling.

## The two pauses

At **2:00**, after "four survive", stop for one beat before "no unique
explanation means no financial action."

At **2:43**, after the counterfactual, stop on `NO FINANCIAL ACTION` for a
beat before moving on. This is the moment the whole submission turns on. Let it
sit.

## If a take goes wrong

The likely failure is time. The script is 801 spoken words — about five minutes
at a measured pace, and it is easy to run long by explaining the reduction cuts
or touring the instruments.

If you are over at 3:20, cut the optional `/app` insert and tighten §06 the
machinery to columns one and two only. Do not cut the AI section or the
refusal; they are the submission.

## After

- Watch it once with the sound off. If the story is unclear without narration,
  the shot list is wrong, not the script.
- Watch it once without watching. If the numbers are unclear from the audio
  alone, you are speaking figures that are not on screen.
- Check no frame shows anything that is not ATTEST.
