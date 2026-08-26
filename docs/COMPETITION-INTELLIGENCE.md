# Competition intelligence — Razorpay AI Buildathon

Researched from the official Buildathon page and corroborating sources on
2026-08-26. Claims are separated into what is **stated**, what is **strongly
inferable**, and what is **our hypothesis**. Nothing here is invented.

---

## A · Explicitly stated

**Track 04 — AI Finance Controller. The bar, verbatim:**

> **"Throughput plus measured accuracy plus an honest exception list. One
> cherry-picked match proves nothing."**

**Submission requirements:** a public repository, a **5-minute pitch video**, and
architecture documentation.

**Process:** *"No resume screening. No long application. No aptitude test. No
group discussion."* Builds showing strong signal go directly to a technical
panel interview.

**Terms:** students only, in-person Bangalore, September start, ₹75,000/month,
6 or 12 months. **Applications close 5 September 2026.**

**Other tracks' bars, which reveal what the organisers value across the board:**

| track | bar |
|---|---|
| 01 Growth & Agentic Commerce | *"Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."* |
| 02 Risk Manager | *"Honest metrics including false-positive cost."* |
| 03 Revenue Recovery | *"measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail."* |
| 05 Open | *"a real problem, a working product, meaningful use of AI, and evidence that it creates value."* |

**Named evaluation dimensions** reported consistently across sources:

- **AI Judgment** — *"whether AI tools, LLMs, or agents were applied
  appropriately instead of forcing unnecessary tech stacks"*
- **Failure Recovery** — *"how the applicant identified system failures at
  runtime and engineered graceful fallbacks"*
- Project Quality & Functionality, Code Quality & Architecture, Communication,
  Technical Depth — *"be ready to justify every major decision"*

---

## B · Strong inference

**They have been burned by demo theatre.** Four of five track bars independently
demand an audit trail, honest metrics, graceful failure, or a batch rather than
an anecdote. *"One cherry-picked match proves nothing"* is not generic advice —
it is a specific defence against a specific submission shape.

**Gratuitous AI is penalised, not rewarded.** "AI Judgment" is phrased as
*appropriately* **instead of** *forcing unnecessary tech stacks*. A multi-agent
system that did not need to be one scores worse than a small model used
precisely. This inverts the usual hackathon incentive.

**The video decides whether the repo is opened.** With no resume screen and a
5-minute cap, the video is the filter and the repo is the corroboration.

**"Failure Recovery" is about runtime, not test coverage.** *"Identified system
failures at runtime and engineered graceful fallbacks"* asks what broke while
running and what the system did about it.

---

## C · Our hypothesis

**ATTEST is unusually well-matched to the stated bar — and currently presented in
the one shape the bar warns against.** Every clause of Track 04 has a direct
answer in the system:

| the bar | what ATTEST has |
|---|---|
| throughput | 250 settlements, 2,368 orders per run; 500 across the benchmark panel |
| measured accuracy | 4.8% false-proof rate against `exact_only` 0% and `greedy` 95%; six gates; precision 0.9524 |
| honest exception list | the blocker register — **every one of the 250 settlements is accounted for** by a named exception with a capability label |
| *"one cherry-picked match proves nothing"* | **our demo is built entirely around one cherry-picked match** |

That last row is the strategic problem, and §II opens with it.

**The strongest available positioning is the intersection of "AI Judgment" and
Track 04.** Almost every submission will argue its AI is good. ATTEST can show
it *measured its own AI, found it worse than a coin flip, and removed it from
the authority path*. Against a dimension that explicitly rewards not forcing AI
where it does not belong, that is a stronger story than any accuracy claim — and
it is very hard for a competitor to copy in ten days, because it requires having
measured.

**Sources**

- [Razorpay AI Buildathon](https://razorpay.com/buildathon/)
- [Velonx — tracks, eligibility, selection process](https://velonx.in/blog/razorpay-ai-buildathon-2026-tracks-eligibility-stipend-selection-process)
- [Placement Officer — Buildathon overview](https://www.placement-officer.com/2026/08/razorpay-ai-buildathon-2026-build-ai.html)
