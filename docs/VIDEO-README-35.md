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

**The engine.** `./.venv/bin/python -m attest.eval.adversarial` should end on
`34 attacks · 34 defended/control-ok · 0 breached`. It also rewrites
`benchmark/adversarial.json`, which the Trust instrument reads — so if you have
never run it on this checkout, the product will correctly say the pass has not
been run, and that will be on camera.

**The kernel.** If the optional Rust kernel is not built, the solver envelope
drops from ₹2,00,000 to ₹30,000 and the strip will read `Portable` instead of
`Native kernel`. The canonical case `setl_000225` is reachable either way —
that was the point of choosing it — but the strip's wording changes, so decide
which one you are recording and stay consistent.

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
