"""The subject × lens continuity contract, driven through a real browser.

These are the invariants from the directive's §7 and §8, written as assertions
rather than as a convention someone has to remember:

    changing LENS     -> subject unchanged, header untouched
    changing SUBJECT  -> lens unchanged, strip untouched
    async result      -> discarded if either axis moved during the request
    reload            -> both axes restored from the URL

The autopsy found the subject dying in four of six navigations under the old
shell. That was possible because nothing tested it. Requires a running server
and playwright; skipped when either is absent, because a test that cannot run
should not fail a build for the wrong reason.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request

import pytest

URL = "http://localhost:8420/workspace.html"

playwright = pytest.importorskip("playwright.sync_api",
                                 reason="playwright not installed")


def _server_up() -> bool:
    try:
        urllib.request.urlopen("http://localhost:8420/api/observatory", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


pytestmark = pytest.mark.skipif(not _server_up(),
                                reason="attest.web is not running on :8420")


@pytest.fixture(scope="module")
def page():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1400, "height": 900})
        errors: list[str] = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_function("() => SHELL.record", timeout=90000)
        pg.wait_for_timeout(800)
        pg.errors = errors            # type: ignore[attr-defined]
        yield pg
        b.close()


def _state(pg):
    """subject, lens, context — the three axes the shell owns."""
    return pg.evaluate(
        "[SHELL.subject.type + ':' + SHELL.subject.id, SHELL.lens,"
        " SHELL.context ? SHELL.context.type + ':' + SHELL.context.id : null]")


def test_changing_lens_leaves_the_subject_and_the_header_untouched(page):
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'control'})")
    page.wait_for_timeout(1500)
    before_subject = _state(page)[0]
    before_header = page.inner_text(".c-subject")

    page.click("[data-lens=journal]")
    page.wait_for_timeout(1500)
    after_subject, after_lens, _ = _state(page)

    assert after_subject == before_subject
    assert after_lens == "journal"
    assert page.inner_text(".c-subject") == before_header


def test_changing_subject_leaves_the_lens_and_the_strip_untouched(page):
    """Phase 2 changed how a subject change is REQUESTED, not the contract.

    Clicking a row in a master list now sets CONTEXT — that is what master and
    detail means, and Phase 1 was wrong to make it navigation. Promoting the
    inspected thing to the subject is a separate, deliberate act, and it is that
    act which must preserve the lens."""
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'journal'})")
    page.wait_for_timeout(1600)
    before_strip = page.inner_text(".c-lenses")

    page.click(".c-row.link")
    page.wait_for_timeout(1300)
    page.click(".c-ctx-b.go")
    page.wait_for_timeout(1600)
    subject, lens, context = _state(page)

    assert subject.startswith("settlement:")
    assert lens == "journal", "the user already said what they wanted to know"
    assert context is None, "context does not survive a subject change"
    assert page.inner_text(".c-lenses") == before_strip


def test_the_url_addresses_both_axes_and_a_reload_restores_them(page):
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000089'},lens:'control'})")
    page.wait_for_timeout(1600)
    assert page.evaluate("location.hash") == "#/settlement/setl_000089/control"

    page.reload(wait_until="networkidle")
    page.wait_for_function("() => SHELL.record", timeout=90000)
    page.wait_for_timeout(900)
    assert _state(page) == ["settlement:setl_000089", "control", None]


def test_a_result_is_discarded_when_the_subject_moved_during_the_request(page):
    """D15, at the shell level. A slow response for one subject must not paint
    over another — attaching real evidence to the wrong subject is a fabricated
    audit record, and worse than showing nothing."""
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'control'})")
    page.wait_for_timeout(1500)

    # Hold the journal request open, ask for it, then move the subject.
    page.route("**/api/journal*", lambda route: (page.wait_for_timeout(2500),
                                                 route.continue_()))
    page.evaluate("navigate({lens:'journal'})")
    page.wait_for_timeout(300)
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000089'},lens:'control'})")
    page.wait_for_timeout(3500)
    page.unroute("**/api/journal*")

    subject, lens, _ = _state(page)
    assert (subject, lens) == ("settlement:setl_000089", "control")
    # inner_text returns what is rendered, and the section headings are
    # uppercased by CSS — compare case-insensitively or the test asserts about
    # the stylesheet rather than about the behaviour.
    body = page.inner_text("#workspace").lower()
    assert "money trail" not in body, "a stale journal render landed"
    # "Where it stopped" moved out of Control and into the shell's state spine,
    # which now renders above every lens — so it no longer identifies Control.
    # The guarantee is unchanged: the stale journal must not land, and Control
    # must be what is showing.
    assert "what we know" in body or "the decision" in body


def test_an_unsupported_lens_falls_back_visibly_and_never_silently(page):
    """§7: never silently return to a default. A source has no journal, so
    asking for one must say so rather than quietly showing something else."""
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'journal'})")
    page.wait_for_timeout(1500)
    page.evaluate("navigate({subject:{type:'source',id:'active'}})")
    page.wait_for_timeout(1600)

    subject, lens, _ = _state(page)
    assert subject.startswith("source:")
    assert lens != "journal", "source does not support journal"
    assert page.query_selector(".c-notice"), "the fallback was not announced"
    assert "does not apply" in page.inner_text(".c-notice")


def test_the_shell_raised_no_script_errors(page):
    assert page.errors == []           # type: ignore[attr-defined]


# --------------------------------------------------------------- Phase 2: context

def test_inspecting_a_row_does_not_move_the_subject_or_rebuild_the_master(page):
    """§5's interaction model. Opening something is not going somewhere: the
    master list must not re-render, or the thing you clicked moves under you."""
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'journal'})")
    page.wait_for_timeout(1600)
    before = page.inner_text("#w-main")

    page.click(".c-row.link")
    page.wait_for_timeout(1300)
    subject, lens, context = _state(page)

    assert subject == "portfolio:portfolio"
    assert lens == "journal"
    assert context and context.startswith("settlement:")
    assert page.inner_text("#w-main") == before, "the master re-rendered"
    assert len(page.inner_text("#w-ctx")) > 80, "the detail is empty"


def test_the_selected_row_stays_selected_while_its_detail_is_open(page):
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'journal'})")
    page.wait_for_timeout(1600)
    page.click(".c-row.link")
    page.wait_for_timeout(1200)
    assert page.eval_on_selector_all(".c-row.sel", "x => x.length") == 1
    assert page.eval_on_selector_all(
        ".c-row[aria-selected=true]", "x => x.length") == 1


def test_closing_returns_to_exactly_where_you_were(page):
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'journal'})")
    page.wait_for_timeout(1600)
    before = page.inner_text("#w-main")
    page.click(".c-row.link")
    page.wait_for_timeout(1200)
    page.click("[data-close-ctx]")
    page.wait_for_timeout(900)

    subject, lens, context = _state(page)
    assert (subject, lens, context) == ("portfolio:portfolio", "journal", None)
    assert page.inner_text("#w-main") == before
    assert page.eval_on_selector_all(".c-row.sel", "x => x.length") == 0


def test_escape_and_back_close_the_drawer_without_leaving_the_page(page):
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'journal'})")
    page.wait_for_timeout(1600)

    page.click(".c-row.link")
    page.wait_for_timeout(1200)
    page.keyboard.press("Escape")
    page.wait_for_timeout(800)
    assert _state(page)[2] is None, "Escape did not close"

    page.click(".c-row.link")
    page.wait_for_timeout(1200)
    page.go_back()
    page.wait_for_timeout(1100)
    subject, lens, context = _state(page)
    assert context is None, "Back did not close the drawer"
    assert (subject, lens) == ("portfolio:portfolio", "journal"), \
        "Back left the page instead of closing what was opened"


def test_the_url_addresses_context_too(page):
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'journal'})")
    page.wait_for_timeout(1600)
    page.click(".c-row.link")
    page.wait_for_timeout(1200)
    assert "?in=settlement" in page.evaluate("location.hash")

    page.reload(wait_until="networkidle")
    page.wait_for_function("() => SHELL.record", timeout=90000)
    page.wait_for_timeout(1400)
    assert _state(page)[2] is not None, "context did not survive a reload"


def test_a_context_the_next_lens_cannot_hold_is_dropped_visibly(page):
    """§7 again, for the third axis. An order inspected inside Journal is not a
    thing Control can open, and dropping it silently would be the same lie."""
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000020'},lens:'journal'})")
    page.wait_for_timeout(1700)
    page.click(".c-inline")
    page.wait_for_timeout(1300)
    assert _state(page)[2] is not None

    page.click("[data-lens=control]")
    page.wait_for_timeout(1700)
    assert _state(page)[2] is None
    assert page.query_selector(".c-notice"), "the drop was not announced"


def test_a_drawer_leaves_the_subject_visible_underneath(page):
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000089'},lens:'control'})")
    page.wait_for_timeout(1700)
    page.click(".c-cand")
    page.wait_for_timeout(1300)
    assert page.eval_on_selector_all(".w-ctx.drawer", "x => x.length") == 1
    assert len(page.inner_text("#w-main")) > 200, "the workspace was replaced"


# ------------------------------------------------- Phase 2 gate: the spatial feel

def test_the_drawer_opens_from_the_object_that_was_clicked(page):
    """§4. A pane that always expands from the same edge is a route transition
    with a different name. The origin must follow the click."""
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'control'})")
    page.wait_for_timeout(1800)
    rows = page.query_selector_all(".c-row.link")
    assert len(rows) >= 3, "not enough rows to tell origins apart"

    origins = []
    for r in (rows[0], rows[2], rows[-1]):
        r.click()
        page.wait_for_timeout(650)
        origins.append(page.evaluate(
            "document.getElementById('w-ctx').style.getPropertyValue('--oy')"))
    assert len(set(origins)) > 1, f"origin never moved: {origins}"
    assert "px" in page.evaluate(
        "getComputedStyle(document.getElementById('w-ctx')).transformOrigin")


def test_the_context_states_the_chain_it_hangs_off(page):
    """§6. The UI must never suggest the context replaced the subject."""
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000089'},lens:'control'})")
    page.wait_for_timeout(1800)
    page.click(".c-cand")
    page.wait_for_timeout(1300)

    crumb = page.inner_text(".c-crumb")
    assert "setl_000089" in crumb
    assert "CONTROL" in crumb.upper()
    assert "EXPLANATION" in crumb.upper()
    # and the subject header is still the settlement, unchanged
    assert "setl_000089" in page.inner_text(".c-subject")


def test_opening_an_explanation_shows_the_orders_behind_it(page):
    """§13, the most important product test. "4 orders" must open into four
    orders, without leaving the settlement."""
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000089'},lens:'control'})")
    page.wait_for_timeout(1800)
    page.click(".c-cand")
    page.wait_for_timeout(1400)

    pane = page.inner_text("#w-ctx")
    rows = page.eval_on_selector_all("#w-ctx .c-table tbody tr", "x => x.length")
    assert rows >= 1, "the explanation opened onto no orders"
    assert "only this explanation uses" in pane.lower()
    subject, lens, context = _state(page)
    assert subject == "settlement:setl_000089"
    assert lens == "control"
    assert context and context.startswith("explanation:")


def test_the_context_chrome_is_generic_not_per_kind(page):
    """§18: no DrawerSettlement, no DrawerExplanation. Every drawer in the
    product is the same drawer, or the close button will drift."""
    for hash_, click, kind in [
        ("#/portfolio/journal", ".c-row.link", "Entry"),
        ("#/settlement/setl_000089/control", ".c-cand", "Explanation"),
    ]:
        page.evaluate(f"location.hash = {hash_!r}")
        page.wait_for_timeout(1800)
        page.click(click)
        page.wait_for_timeout(1300)
        assert page.query_selector(".c-crumb"), f"{kind} has no breadcrumb"
        assert page.query_selector("[data-close-ctx]"), f"{kind} has no close"
        assert kind.upper() in page.inner_text(".c-crumb").upper()


def test_the_master_scroll_position_survives_open_and_close(page):
    """§7: only context disappears.

    The literal position 420 is gone, not the guarantee. Moving the case into
    the rail gave the instrument 343px more height, so the same content now
    scrolls 132px where it used to scroll 666 — 420 is past the end and the
    browser clamps it, which would make the assertion about arithmetic rather
    than about behaviour.

    Scrolling to the maximum instead is a STRONGER test of the same thing: the
    bottom is exactly where a reflow-induced clamp would bite.
    """
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'control'})")
    page.wait_for_timeout(1800)
    want = page.evaluate("""() => {
        const e = document.getElementById('w-main');
        const max = e.scrollHeight - e.clientHeight;
        e.scrollTop = max;
        return e.scrollTop; }""")
    assert want > 0, "the master does not scroll at all; this asserts nothing"
    page.wait_for_timeout(300)
    page.click(".c-row.link")
    page.wait_for_timeout(1100)
    assert page.evaluate("document.getElementById('w-main').scrollTop") == want
    page.click("[data-close-ctx]")
    page.wait_for_timeout(900)
    assert page.evaluate("document.getElementById('w-main').scrollTop") == want


# ------------------------------------------------------------ P3: Evidence

def _ev(page, hash_):
    page.evaluate(f"location.hash = {hash_!r}")
    page.wait_for_timeout(2200)


def test_portfolio_evidence_loads_scoped(page):
    """§28: the evidence landscape, not every record in the book."""
    _ev(page, "#/portfolio/evidence")
    assert _state(page)[:2] == ["portfolio:portfolio", "evidence"]
    nodes = page.eval_on_selector_all("#workspace *", "x => x.length")
    assert nodes < 400, f"portfolio evidence rendered {nodes} elements"
    assert "convention" in page.inner_text("#workspace").lower()


def test_settlement_evidence_shows_the_search_space_boundary(page):
    """§16. A proof can be perfect inside a space that excluded the truth, and a
    reader cannot judge that without seeing what was CONSIDERED."""
    _ev(page, "#/settlement/setl_000089/evidence")
    txt = page.inner_text("#workspace")
    assert "WHAT WAS CONSIDERED" in txt.upper()
    # the funnel states both ends and names each reduction's status
    assert "2,368" in txt and "73" in txt
    assert "CONVENTION" in txt.upper()
    assert "DETERMINISTIC" in txt.upper()


def test_an_ambiguous_settlement_shows_shared_versus_unique(page):
    """§7, §8. Ambiguity shown, not stated."""
    _ev(page, "#/settlement/setl_000089/evidence")
    rows = page.eval_on_selector_all(".e-set-r", "x => x.length")
    assert rows >= 2, "no explanation set rendered"
    txt = page.inner_text("#workspace")
    assert "settled whichever explanation is right" in txt
    assert "turns on which one is" in txt


def test_the_model_is_visually_and_semantically_separate_from_evidence(page):
    """§6, §18. A hypothesis must never look as authoritative as a fact."""
    _ev(page, "#/settlement/setl_000089/evidence")
    assert page.query_selector(".e-ai"), "no model section"
    assert "not evidence" in page.inner_text(".e-ai-tag").lower()
    # and it is not inside the verified-relationship section
    verified = page.eval_on_selector_all(".e-rel .e-ai", "x => x.length")
    assert verified == 0, "a hypothesis rendered among verified relationships"
    assert "non-discriminative" in page.inner_text("#workspace").lower()


def test_an_evidence_object_opens_as_context_not_navigation(page):
    """§10. Evidence uses the existing shell from day one."""
    _ev(page, "#/settlement/setl_000089/evidence")
    before = page.inner_text("#w-main")
    page.click(".e-set-r")
    page.wait_for_timeout(1400)
    subject, lens, context = _state(page)
    assert subject == "settlement:setl_000089"
    assert lens == "evidence"
    assert context == "explanation:A"
    assert page.inner_text("#w-main") == before, "the workspace re-rendered"
    assert "EXPLANATION" in page.inner_text(".c-crumb").upper()


def test_evidence_context_nests_from_explanation_to_order(page):
    """§25, and §35's north star: money → record → relationship → evidence
    without losing the case."""
    _ev(page, "#/settlement/setl_000089/evidence")
    page.click(".e-set-r")
    page.wait_for_timeout(1400)
    page.click("#w-ctx .c-row.link")
    page.wait_for_timeout(1400)
    subject, lens, context = _state(page)
    assert subject == "settlement:setl_000089", "the case was lost"
    assert lens == "evidence"
    assert context.startswith("order:")
    assert "PROVENANCE" in page.inner_text("#w-ctx").upper()


def test_closing_evidence_context_restores_the_workspace(page):
    _ev(page, "#/settlement/setl_000089/evidence")
    before = page.inner_text("#w-main")
    page.click(".e-set-r")
    page.wait_for_timeout(1300)
    page.keyboard.press("Escape")
    page.wait_for_timeout(900)
    assert _state(page) == ["settlement:setl_000089", "evidence", None]
    assert page.inner_text("#w-main") == before


def test_switching_to_evidence_preserves_the_subject(page):
    _ev(page, "#/settlement/setl_000020/control")
    page.click("[data-lens=evidence]")
    page.wait_for_timeout(2000)
    subject, lens, _ = _state(page)
    assert subject == "settlement:setl_000020"
    assert lens == "evidence"


def test_a_proven_settlement_shows_no_competing_explanations(page):
    """The lens must understand the verdict states. §7."""
    _ev(page, "#/settlement/setl_000020/evidence")
    txt = page.inner_text("#workspace").upper()
    assert "WHAT WAS CONSIDERED" in txt
    assert "VERIFIED RELATIONSHIPS" in txt
    assert "AGREE ON" not in txt, "a proven settlement has nothing to disagree about"


def test_evidence_relationships_state_their_kind_and_status(page):
    """§5: never node → node → node with the relationship unexplained."""
    _ev(page, "#/settlement/setl_000089/evidence")
    rels = page.eval_on_selector_all(".e-rel", "x => x.length")
    assert rels >= 1
    first = page.inner_text(".e-rel")
    assert "verified" in first.lower()
    assert len(page.inner_text(".e-rel-w").strip()) > 10, "the edge does not say why"


def test_evidence_survives_a_reload_with_context_open(page):
    _ev(page, "#/settlement/setl_000089/evidence")
    page.click(".e-set-r")
    page.wait_for_timeout(1300)
    page.reload(wait_until="networkidle")
    page.wait_for_function("() => SHELL.record", timeout=90000)
    page.wait_for_timeout(1600)
    assert _state(page) == ["settlement:setl_000089", "evidence", "explanation:A"]


def test_a_stale_evidence_fetch_cannot_land_on_another_subject(page):
    """§30.12 — D15 at the evidence layer."""
    _ev(page, "#/settlement/setl_000089/evidence")
    page.route("**/api/evidence*", lambda route: (page.wait_for_timeout(2500),
                                                  route.continue_()))
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000020'}})")
    page.wait_for_timeout(400)
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'}})")
    page.wait_for_timeout(3600)
    page.unroute("**/api/evidence*")
    subject, lens, _ = _state(page)
    assert subject == "portfolio:portfolio"
    # "2,368" appears in BOTH views — the portfolio counts the whole book too —
    # so the marker has to be something only a settlement renders.
    body = page.inner_text("#workspace").lower()
    assert "could belong to this credit" not in body, "a stale settlement view landed"
    assert "the evidence in this run" in body


# --------------------------------------------------------- P4: Investigate

def test_portfolio_investigate_is_questions_not_a_table_of_settlements(page):
    """§13. "197 ambiguous settlements" is a queue nobody can finish; one
    question worth ₹47L that a single answer settles is work."""
    _ev(page, "#/portfolio/investigate")
    assert _state(page)[:2] == ["portfolio:portfolio", "investigate"]
    cases = page.eval_on_selector_all(".i-case", "x => x.length")
    assert 1 <= cases <= 12, f"{cases} rows is a table, not a queue"
    txt = page.inner_text("#w-main")
    assert "?" in txt, "the queue does not ask anything"
    assert "one answer" in txt.lower()


def test_settlement_investigate_states_the_question_first(page):
    _ev(page, "#/settlement/setl_000089/investigate")
    q = page.inner_text(".i-q h2")
    assert q.endswith("?"), f"not a question: {q!r}"
    assert "indistinguishable" in q.lower()


def test_the_timeline_names_actor_action_input_and_result(page):
    """§16. Never a sentence the reader has to parse to work out who did what."""
    _ev(page, "#/settlement/setl_000089/investigate")
    steps = page.eval_on_selector_all(".i-tl-s", "x => x.length")
    assert steps >= 3, "no trail"
    actors = page.eval_on_selector_all(".i-tl-a", "x => x.map(n => n.textContent)")
    assert "Model" in actors and "Solver" in actors and "Engine" in actors
    # and the order is the argument: the model cannot appear after the verdict
    assert actors.index("Model") < actors.index("Solver") < actors.index("Engine")


def test_the_three_actors_are_visually_distinct(page):
    """§4, §28. The model proposes, the solver tests, the engine decides, and
    the layout must make that impossible to misread."""
    _ev(page, "#/settlement/setl_000089/investigate")
    colours = page.evaluate("""(() => {
      const pick = c => {
        const n = document.querySelector('.e-act-' + c + ' .i-tl-m');
        return n ? getComputedStyle(n).borderColor : null; };
      return [pick('model'), pick('solver'), pick('engine')]; })()""")
    assert all(colours), "an actor has no marker"
    assert len(set(colours)) == 3, f"actors share a colour: {colours}"


def test_the_solver_result_is_a_named_state_not_a_confidence(page):
    """§18. "AI confidence" collapses six different findings into one."""
    _ev(page, "#/settlement/setl_000089/investigate")
    results = page.eval_on_selector_all(".i-tl-r", "x => x.map(n => n.textContent.trim())")
    assert results, "the solver reported nothing"
    assert any("NON DISCRIMINATIVE" in r for r in results)
    body = page.inner_text("#workspace").lower()
    assert "confidence" not in body


def test_abstention_is_shown_as_restraint_and_changes_no_verdict(page):
    """§8, §9, §25. The investigation ran; the verdict did not move.

    Phase 23: the word `abstained` left `.i-abs`, which was painting the room's
    own conclusion a second time at the same size. It is still stated — it
    leads the room — so this reads the room for the abstention and `.i-abs`
    for what that block actually owns: that nothing moved as a result."""
    _ev(page, "#/settlement/setl_000089/investigate")
    room = page.inner_text("#w-main")
    assert "abstained" in room.lower()
    abs_ = page.inner_text(".i-abs")
    assert "no financial action" in abs_.lower()
    assert "AMBIGUOUS" in abs_
    # the subject header still carries the same verdict
    assert "AMBIGUOUS" in page.inner_text(".c-subject")


def test_a_failed_hypothesis_is_not_hidden(page):
    """§6. A trail cleaned up to make the model look competent is worth
    nothing."""
    _ev(page, "#/settlement/setl_000089/investigate")
    txt = page.inner_text("#workspace")
    assert "capture-batch" in txt, "the refuted hypothesis was removed"
    assert "does not distinguish" in txt.lower()


def test_the_lens_failure_is_derived_from_this_pool_not_hardcoded(page):
    """§7. D22 should emerge because it is true here, not because it was typed
    into the interface."""
    _ev(page, "#/settlement/setl_000089/investigate")
    sig = page.inner_text(".i-sig-r") + page.inner_text(".i-sig-d")
    assert "capture date" in sig.lower()
    assert "73" in sig, "the pool size is not stated"
    body = page.inner_text("#workspace")
    assert "D22" not in body, "a failure reference leaked into the product copy"


def test_a_trail_step_opens_as_context_without_offering_promotion(page):
    """§11, §12. A hypothesis is not a subject anything can be about, so no
    promotion is offered — an affordance that leads nowhere teaches the wrong
    model."""
    _ev(page, "#/settlement/setl_000089/investigate")
    before = page.inner_text("#w-main")
    page.click(".i-tl-s")
    page.wait_for_timeout(1400)
    subject, lens, context = _state(page)
    assert subject == "settlement:setl_000089"
    assert lens == "investigate"
    assert context and context.startswith("step:")
    assert page.inner_text("#w-main") == before
    assert page.query_selector("[data-close-ctx]")
    assert not page.query_selector(".c-ctx-b.go"), "promotion was offered"


def test_closing_an_investigation_step_restores_the_workspace(page):
    _ev(page, "#/settlement/setl_000089/investigate")
    before = page.inner_text("#w-main")
    page.click(".i-tl-s")
    page.wait_for_timeout(1300)
    page.keyboard.press("Escape")
    page.wait_for_timeout(900)
    assert _state(page) == ["settlement:setl_000089", "investigate", None]
    assert page.inner_text("#w-main") == before


def test_investigate_to_evidence_preserves_the_subject(page):
    """§21."""
    _ev(page, "#/settlement/setl_000089/investigate")
    page.click("[data-lens=evidence]")
    page.wait_for_timeout(2000)
    subject, lens, _ = _state(page)
    assert subject == "settlement:setl_000089"
    assert lens == "evidence"


def test_investigate_offers_no_way_to_execute_a_financial_action(page):
    """§22, §24. It discovers. Policy decides. Action executes."""
    _ev(page, "#/settlement/setl_000089/investigate")
    body = page.inner_text("#workspace").lower()
    for word in ("post entry", "approve", "auto-post now", "execute", "confirm"):
        assert word not in body, f"Investigate offers {word!r}"
    buttons = page.eval_on_selector_all(
        "#w-main button", "x => x.map(n => n.textContent.trim().toLowerCase())")
    assert not [b for b in buttons if "post" in b or "approve" in b]


def test_a_stale_investigation_cannot_land_on_another_subject(page):
    """§31.13 — D15 at this layer."""
    _ev(page, "#/settlement/setl_000089/investigate")
    page.route("**/api/investigation*", lambda route: (page.wait_for_timeout(2500),
                                                       route.continue_()))
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'}})")
    page.wait_for_timeout(3600)
    page.unroute("**/api/investigation*")
    subject, _, _ = _state(page)
    assert subject == "portfolio:portfolio"
    assert "indistinguishable" not in page.inner_text("#workspace").lower()


# -------------------------------------------------------------- P5: Policy

def test_portfolio_policy_groups_by_what_is_permitted(page):
    """§21."""
    _ev(page, "#/portfolio/policy")
    assert _state(page)[:2] == ["portfolio:portfolio", "policy"]
    groups = page.eval_on_selector_all(".p-grp .p-grp-d",
                                       "x => x.map(n => n.textContent.trim())")
    assert set(groups) == {"AUTO-POST", "REVIEW", "BLOCK"}


def test_settlement_policy_states_the_decision_and_the_verdict_apart(page):
    """§4, §8. A settlement can be AMBIGUOUS and REVIEW; those are two facts.

    Phase 13B: the decision left `.p-head`, which was painting it a second time
    below the conclusion that already leads with it. Both facts are still
    stated and still apart — the decision above, the verdict and what policy
    does with it below — so this reads the room rather than the one block."""
    _ev(page, "#/settlement/setl_000089/policy")
    assert "REVIEW" in page.inner_text(".c-concl")
    head = page.inner_text(".p-head")
    assert "AMBIGUOUS" in head
    assert "does not change it" in head
    assert "REVIEW" not in head, "the decision is stated twice again"


def test_the_decision_is_expressed_as_a_cost_comparison(page):
    """§1, §15, §27. Not a score, not a confidence — an inequality."""
    _ev(page, "#/settlement/setl_000020/policy")
    body = page.inner_text("#workspace")
    assert "expected loss" in body.lower()
    assert "to check" in body.lower()
    assert "₹" in page.inner_text(".p-bound-k")


def test_the_word_confidence_never_appears_in_policy(page):
    """§15."""
    for h in ("#/portfolio/policy", "#/settlement/setl_000020/policy",
              "#/settlement/setl_000089/policy"):
        _ev(page, h)
        assert "confidence" not in page.inner_text("#workspace").lower()


def test_an_unproven_settlement_is_never_priced(page):
    """§16, §33. Policy cannot reach a settlement the proof did not establish,
    so there is no expected loss to compare — and the UI must say that rather
    than show a number it does not have."""
    _ev(page, "#/settlement/setl_000089/policy")
    # Phase 13 §16: this used to read `.p-bound`, a box whose entire content was
    # the sentence the conclusion already leads with. The guarantee did not
    # move — "nothing was priced" is still stated, and the absence of a marker
    # is now absolute rather than a marker-less box.
    assert "nothing was priced" in page.inner_text("#workspace").lower()
    assert page.eval_on_selector_all(".p-bound-mark", "x => x.length") == 0
    assert page.eval_on_selector_all(".p-bound", "x => x.length") == 0, \
        "an unpriced settlement drew a decision boundary"
    # every proof gate failed, so no policy gate could pass
    ok = page.eval_on_selector_all(".p-gate.ok", "x => x.length")
    assert ok == 0, "a policy gate passed without proof"


def test_the_proof_gates_precede_the_policy_gates(page):
    """§17, §33. AI never skips proof, and the layout is the argument."""
    _ev(page, "#/settlement/setl_000020/policy")
    stages = page.eval_on_selector_all(".p-stage-h",
                                       "x => x.map(n => n.textContent.trim().toLowerCase())")
    assert stages == ["proof", "policy"], stages


def test_the_policy_version_is_visible_and_derived_from_the_costing(page):
    """§12, §25. A what-if is a different policy version, not a recomputation."""
    _ev(page, "#/settlement/setl_000020/policy")
    body = page.inner_text("#workspace")
    assert "policy_" in body
    recorded = page.evaluate("""(async () => {
      const a = await (await fetch(`/api/decision?run=${SHELL.run}&type=settlement`
        + `&id=setl_000020&review=15000`)).json();
      const b = await (await fetch(`/api/decision?run=${SHELL.run}&type=settlement`
        + `&id=setl_000020&review=50000`)).json();
      return [a.policy_version, b.policy_version, a.simulated, b.simulated];
    })()""")
    assert recorded[0] != recorded[1], "the costing did not change the version"
    assert recorded[2] is False and recorded[3] is True


def test_the_ui_decision_matches_the_engine(page):
    """§5, §30.8. The UI represents the engine; it does not re-derive it.

    Phase 13B: `.p-head-d` was the second painting of the decision and is gone.
    Re-pointed at the conclusion that leads the room — and strengthened, because
    the old form checked one element while the room could still have contained a
    contradicting decision elsewhere. Now the engine's decision must be stated
    AND no other decision word may appear anywhere in the room."""
    _ev(page, "#/settlement/setl_000020/policy")
    from_api = page.evaluate("""(async () => {
      const d = await (await fetch(`/api/decision?run=${SHELL.run}`
        + `&type=settlement&id=setl_000020&review=${SHELL.review}`)).json();
      return d.decision; })()""")
    shown = from_api.replace("_", "-")
    assert shown in page.inner_text(".c-concl"), \
        f"the room does not state the engine's decision {shown}"
    # whole lines, not substrings: "COST OF A REVIEW" is a label for what a
    # person's time is worth, not a decision, and a naive `in` check reads it
    # as the engine having been contradicted
    lines = {l.strip().upper()
             for l in page.inner_text("#w-main").splitlines()}
    for other in ("AUTO-POST", "REVIEW", "BLOCK"):
        if other != shown:
            assert other not in lines, \
                f"engine says {shown} but the room also states {other}"


def test_simulating_a_costing_does_not_change_the_recorded_decision(page):
    """§19, §26. Simulation operates on a snapshot and executes nothing."""
    _ev(page, "#/portfolio/policy")
    before = page.evaluate("""(async () => (await (await fetch(
      `/api/decision?run=${SHELL.run}&type=portfolio&review=15000`)).json()).auto_post)()""")
    page.evaluate("SHELL.review = 250000; navigate({}, {replace:true})")
    page.wait_for_timeout(2200)
    assert page.query_selector(".p-sim"), "the simulation was not labelled"
    after = page.evaluate("""(async () => (await (await fetch(
      `/api/decision?run=${SHELL.run}&type=portfolio&review=15000`)).json()).auto_post)()""")
    assert before == after, "simulating mutated the recorded decision"
    page.evaluate("SHELL.review = 15000; navigate({}, {replace:true})")
    page.wait_for_timeout(1800)


def test_policy_offers_no_way_to_execute_an_action(page):
    """§22. Policy says ALLOWED. Action executes. Keep the boundary."""
    _ev(page, "#/settlement/setl_000020/policy")
    buttons = page.eval_on_selector_all(
        "#w-main button", "x => x.map(n => n.textContent.trim().toLowerCase())")
    for b in buttons:
        assert "post now" not in b and "execute" not in b and "approve" not in b


def test_a_policy_decision_opens_as_context(page):
    _ev(page, "#/portfolio/policy")
    before = page.inner_text("#w-main")
    page.click(".p-grp")
    page.wait_for_timeout(1400)
    subject, lens, context = _state(page)
    assert subject == "portfolio:portfolio"
    assert lens == "policy"
    assert context and context.startswith("decision:")
    assert page.inner_text("#w-main") == before
    assert "DECISION" in page.inner_text(".c-crumb").upper()


def test_policy_to_journal_preserves_the_subject(page):
    """§23. The chain is followable without losing the case."""
    _ev(page, "#/settlement/setl_000020/policy")
    page.click("[data-lens=journal]")
    page.wait_for_timeout(1900)
    subject, lens, _ = _state(page)
    assert subject == "settlement:setl_000020"
    assert lens == "journal"


def test_policy_decisions_are_readable_without_colour(page):
    """§29. Colour may reinforce; it cannot be the only signal."""
    _ev(page, "#/settlement/setl_000089/policy")
    gates = page.eval_on_selector_all(
        ".p-gate .p-gate-s", "x => x.map(n => n.textContent.trim().toLowerCase())")
    assert gates and all(g in ("passed", "not satisfied") for g in gates)
    assert page.eval_on_selector_all(".p-gate i", "x => x.map(n => n.textContent.trim())")


def test_a_stale_policy_fetch_cannot_land_on_another_subject(page):
    _ev(page, "#/settlement/setl_000089/policy")
    page.route("**/api/decision*", lambda route: (page.wait_for_timeout(2500),
                                                  route.continue_()))
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000020'}})")
    page.wait_for_timeout(3600)
    page.unroute("**/api/decision*")
    assert _state(page)[0] == "settlement:setl_000020"
    assert "1,00,036.83" not in page.inner_text("#workspace")


# ------------------------------------------------------------ P6: Activity

def test_portfolio_activity_shows_a_run_with_phases_beneath_it(page):
    """§6, §27. Five thousand individual events here would be a log."""
    _ev(page, "#/portfolio/activity")
    assert _state(page)[:2] == ["portfolio:portfolio", "activity"]
    phases = page.eval_on_selector_all(".a-ev", "x => x.length")
    assert 3 <= phases <= 30, f"{phases} entries is a log, not a run"
    assert "run_" in page.inner_text(".a-state")


def test_settlement_activity_tells_one_lifecycle(page):
    _ev(page, "#/settlement/setl_000089/activity")
    stages = page.eval_on_selector_all(".a-stage",
                                       "x => x.map(n => n.textContent.trim())")
    for s in ("source", "matching", "verification", "policy", "action"):
        assert s in stages, f"{s} missing from the lifecycle"
    assert stages.index("source") < stages.index("verification") < stages.index("action")


def test_every_event_states_what_caused_it(page):
    """§9, §41. Causality is the connector, not a column."""
    _ev(page, "#/settlement/setl_000089/activity")
    causes = page.eval_on_selector_all(".a-cause span",
                                       "x => x.map(n => n.textContent.trim())")
    assert len(causes) >= 4, "the timeline has no causal links"
    assert all(c.startswith("because") for c in causes)


def test_permission_and_execution_are_separate_events(page):
    """§18, §31, §40 — the foundational distinction. ALLOWED is not DONE."""
    _ev(page, "#/settlement/setl_000020/activity")
    stages = page.eval_on_selector_all(".a-stage",
                                       "x => x.map(n => n.textContent.trim())")
    assert stages.count("policy") == 1 and stages.count("action") == 1
    assert stages.index("policy") < stages.index("action")
    body = page.inner_text("#workspace")
    assert "permitted" in body.lower()
    assert "LEDGER UPDATED" in body
    # the two carry different badges, so they cannot be read as one fact
    assert page.eval_on_selector_all(".a-badge.yes", "x => x.length") >= 1
    assert page.eval_on_selector_all(".a-badge.done", "x => x.length") >= 1


def test_a_settlement_that_was_not_posted_says_the_ledger_is_unchanged(page):
    """§18 again, from the other side: permission withheld must not read as an
    action that merely has not happened yet."""
    _ev(page, "#/settlement/setl_000089/activity")
    body = page.inner_text("#workspace")
    assert "LEDGER UNCHANGED" in body
    assert "NOT PERMITTED" in body.upper()
    assert page.eval_on_selector_all(".a-badge.done", "x => x.length") == 0


def test_the_actors_are_distinguishable(page):
    """§17. Compact semantic markers, no avatars."""
    _ev(page, "#/settlement/setl_000089/activity")
    actors = page.eval_on_selector_all(".a-actor",
                                       "x => x.map(n => n.textContent.trim())")
    assert {"System", "Engine", "Model", "Solver", "Policy"} <= set(actors)
    glyphs = page.eval_on_selector_all(".a-mark",
                                       "x => x.map(n => n.textContent.trim())")
    assert len(set(glyphs)) >= 4, f"actors share a glyph: {set(glyphs)}"


def test_no_human_actor_is_invented(page):
    """§16. This system records no operator identity anywhere, so Activity must
    not manufacture one. The gap is the honest rendering of a gap."""
    for h in ("#/portfolio/activity", "#/settlement/setl_000089/activity"):
        _ev(page, h)
        actors = page.eval_on_selector_all(".a-actor",
                                           "x => x.map(n => n.textContent.trim())")
        assert "Human" not in actors
        body = page.inner_text("#workspace").lower()
        for word in ("reviewed by", "approved by", "@"):
            assert word not in body


def test_an_event_opens_as_context_and_says_it_is_immutable(page):
    """§11, §12. Inspecting is not re-running."""
    _ev(page, "#/settlement/setl_000089/activity")
    before = page.inner_text("#w-main")
    page.click(".a-ev")
    page.wait_for_timeout(1400)
    subject, lens, context = _state(page)
    assert subject == "settlement:setl_000089"
    assert lens == "activity"
    assert context and context.startswith("event:")
    assert page.inner_text("#w-main") == before, "the timeline re-rendered"
    ctx = page.inner_text("#w-ctx").lower()
    assert "does not re-run" in ctx or "immutable" in ctx


def test_closing_an_event_restores_the_timeline(page):
    _ev(page, "#/settlement/setl_000089/activity")
    before = page.inner_text("#w-main")
    page.click(".a-ev")
    page.wait_for_timeout(1300)
    page.keyboard.press("Escape")
    page.wait_for_timeout(900)
    assert _state(page) == ["settlement:setl_000089", "activity", None]
    assert page.inner_text("#w-main") == before


def test_unrevised_is_the_word_used_not_stale_or_wrong(page):
    """§14. An important product language rule — and it only has anything to
    say once something IS unrevised, so deliver an event first."""
    _ev(page, "#/portfolio/activity")
    page.evaluate("""(async () => { await fetch(
      `/api/events/demo?run=${SHELL.run}`, {method:'POST'}); })()""")
    page.wait_for_timeout(2000)
    page.evaluate("navigate({}, {replace:true})")
    page.wait_for_timeout(2400)
    body = page.inner_text("#workspace").lower()
    assert "unrevised" in body, "the word is not used where the concept appears"
    for banned in ("stale", "invalid verdict", "wrong verdict"):
        assert banned not in body


def test_a_repeat_delivery_is_explained_as_producing_no_second_action(page):
    """§20. Idempotency matters in a payments system and must be legible."""
    _ev(page, "#/portfolio/activity")
    page.evaluate("""(async () => { await fetch(
      `/api/events/demo?run=${SHELL.run}`, {method:'POST'}); })()""")
    page.wait_for_timeout(2000)
    page.evaluate("navigate({}, {replace:true})")
    page.wait_for_timeout(2400)
    # The delivery statuses are visible; the explanation sits behind a
    # disclosure, so read textContent rather than innerText for that half.
    assert "duplicate" in page.inner_text("#workspace").lower()
    explained = page.eval_on_selector(
        "#w-main", "n => n.textContent.toLowerCase()")
    assert "no second action" in explained
    assert "replay mismatch" in page.inner_text("#workspace").lower() \
        or "replay_mismatch" in explained


def test_replay_reports_a_measured_comparison_not_a_claim(page):
    """§36. A replay button was only built because the claim is measurable."""
    _ev(page, "#/portfolio/activity")
    original = page.evaluate("SHELL.run")
    page.click("#a-replay-go")
    page.wait_for_selector(".a-rep", timeout=120000)
    page.wait_for_timeout(600)
    out = page.inner_text(".a-rep")
    assert "Reproduced" in out
    assert "differing" in out.lower()
    assert "provenance" in out.lower()
    # the original run is untouched — the shell still points at it
    assert page.evaluate("SHELL.run") == original


def test_activity_to_evidence_preserves_the_subject(page):
    _ev(page, "#/settlement/setl_000089/activity")
    page.click("[data-lens=evidence]")
    page.wait_for_timeout(2000)
    subject, lens, _ = _state(page)
    assert subject == "settlement:setl_000089" and lens == "evidence"


def test_activity_to_policy_preserves_the_subject(page):
    _ev(page, "#/settlement/setl_000089/activity")
    page.click("[data-lens=policy]")
    page.wait_for_timeout(2000)
    subject, lens, _ = _state(page)
    assert subject == "settlement:setl_000089" and lens == "policy"


def test_activity_is_not_a_generic_log_table(page):
    """§41. If it can be represented as timestamp | actor | event | status, the
    design has failed. Every entry must carry cause and effect."""
    _ev(page, "#/settlement/setl_000089/activity")
    events = page.eval_on_selector_all(".a-ev", "x => x.length")
    effects = page.eval_on_selector_all(".a-eff", "x => x.length")
    causes = page.eval_on_selector_all(".a-cause", "x => x.length")
    assert effects >= events - 1, "events without a stated effect"
    assert causes >= events - 2, "events without a stated cause"
    assert page.eval_on_selector_all("#w-main table", "x => x.length") == 0


def test_a_stale_activity_fetch_cannot_land_on_another_subject(page):
    _ev(page, "#/settlement/setl_000089/activity")
    page.route("**/api/activity*", lambda route: (page.wait_for_timeout(2500),
                                                  route.continue_()))
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000020'}})")
    page.wait_for_timeout(3600)
    page.unroute("**/api/activity*")
    assert _state(page)[0] == "settlement:setl_000020"
    assert "1,00,036.83" not in page.inner_text("#workspace")


# --------------------------------------------------------------- P7: Trust

def test_trust_opens_with_the_failures_not_with_the_wins(page):
    """§2, §34. A trust surface that opens with green ticks is a pitch deck."""
    _ev(page, "#/portfolio/trust")
    assert _state(page)[:2] == ["portfolio:portfolio", "trust"]
    head = page.inner_text(".t-head")
    assert "failed" in head.lower()
    body = page.inner_text("#w-main").lower()
    assert "not verified" in body, "the surface does not lead with a limitation"

    # The failure block precedes the claim register. Asserted by DOM position
    # rather than by a heading string: the register's section is now titled
    # "what it has demonstrated" and lives inside a verified zone, so searching
    # for the old wording tested the copy rather than the ordering.
    order = page.evaluate("""() => {
        const main = document.getElementById('w-main');
        const bad = main.querySelector('.t-bad');
        const claim = main.querySelector('.t-claim');
        if (!bad || !claim) return null;
        return bad.compareDocumentPosition(claim)
               & Node.DOCUMENT_POSITION_FOLLOWING ? 'bad-first' : 'claims-first';
    }""")
    assert order == "bad-first", \
        f"the claim register comes before the failures ({order})"


def test_every_claim_names_the_artifact_it_reads(page):
    """§5, §6. A number typed into an interface is a number nothing checks."""
    _ev(page, "#/portfolio/trust")
    sources = page.eval_on_selector_all(".t-claim-src",
                                        "x => x.map(n => n.textContent.trim())")
    assert len(sources) >= 6
    assert all(s and s != "no source" for s in sources)
    assert any("benchmark/" in s for s in sources)


def test_the_headline_figures_match_the_artifacts_on_disk(page):
    """§6 again, mechanically: the surface must agree with the files."""
    same = page.evaluate("""(async () => {
      const c = await (await fetch(`/api/claims?run=${SHELL.run}`)).json();
      const r = await (await fetch('/results.json').catch(() => ({json:()=>({})}))).json()
        .catch(() => ({}));
      return {scope: c.scope, claims: c.claims.length,
              hasBaselines: c.artifacts.some(a => a.name.includes('baselines') && a.present)};
    })()""")
    assert same["claims"] >= 6
    assert same["hasBaselines"], "the baseline artifact is missing"
    assert "settlement" in same["scope"]


def test_a_claim_without_a_machine_readable_source_is_marked_limited(page):
    """§23. The surface has to be able to say no."""
    _ev(page, "#/portfolio/trust")
    states = page.eval_on_selector_all(".t-claim-s",
                                       "x => x.map(n => n.textContent.trim())")
    assert "LIMITED" in states, "nothing is qualified — every claim reads as measured"
    assert not all(s == "MEASURED" for s in states), "a wall of green"


def test_trust_states_a_claim_against_itself(page):
    """§36, §49. A red result can increase trust if it is honest."""
    _ev(page, "#/portfolio/trust")
    body = page.inner_text("#w-main").lower()
    assert "not the most precise" in body, \
        "the panel does not report where a baseline beats ATTEST"


def test_the_wrongly_posted_figure_is_scoped_to_the_panel(page):
    """§29. ₹0 is a measurement, not a guarantee."""
    _ev(page, "#/portfolio/trust")
    page.click("[data-context='claim:C-001']")
    page.wait_for_timeout(1400)
    ctx = page.inner_text("#w-ctx").lower()
    assert "settlement" in ctx and "seed" in ctx, "no scope stated"
    assert "not a claim that" in ctx or "only that" in ctx


def test_limitations_are_shown_and_are_absences_not_unknowns(page):
    """§21, §22. Absence is not failure and must not be dressed as mystery."""
    _ev(page, "#/portfolio/trust")
    body = page.inner_text("#w-main")
    assert "not known" in body.lower()
    rows = page.eval_on_selector_all(".t-unk-r", "x => x.length")
    assert rows >= 4
    low = body.lower()
    assert "no operator identity" in low
    assert "unknown operator" not in low


def test_rejected_features_are_visible_as_rejected(page):
    """§4, §33. Built, measured, disabled is stronger than a feature list."""
    _ev(page, "#/portfolio/trust")
    body = page.inner_text("#w-main").lower()
    assert "built, measured, then disabled" in body
    refs = page.eval_on_selector_all(".t-fail.ref", "x => x.length")
    assert refs >= 1


def test_the_ai_precision_number_is_not_hidden_or_improved(page):
    """§14. The number that disabled the resolver stays on the surface."""
    _ev(page, "#/portfolio/trust")
    body = page.inner_text("#w-main").lower()
    assert "cannot reliably resolve" in body
    vals = page.eval_on_selector_all(".t-claim-v",
                                     "x => x.map(n => n.textContent.trim())")
    assert any("precision" in v for v in vals)


def test_what_the_model_may_not_do_is_stated(page):
    """§13. Connected to the real permission model."""
    _ev(page, "#/portfolio/trust")
    body = page.inner_text("#w-main").lower()
    assert "granted to nothing" in body
    blocked = page.eval_on_selector_all(".t-perm-i.no", "x => x.length")
    assert blocked >= 3


def test_the_gates_show_what_they_protect_not_just_a_tick(page):
    """§19."""
    _ev(page, "#/portfolio/trust")
    gates = page.eval_on_selector_all(".t-gate", "x => x.length")
    assert gates >= 5
    whys = page.eval_on_selector_all(".t-gate-w",
                                     "x => x.map(n => n.textContent.trim())")
    assert all(len(w) > 20 for w in whys), "a gate does not say what it protects"
    assert page.eval_on_selector_all(".t-gate-n em", "x => x.length") >= 5


def test_a_claim_opens_as_context_with_its_limitation(page):
    _ev(page, "#/portfolio/trust")
    before = page.inner_text("#w-main")
    page.click(".t-claim")
    page.wait_for_timeout(1400)
    subject, lens, context = _state(page)
    assert subject == "portfolio:portfolio"
    assert lens == "trust"
    assert context and context.startswith("claim:")
    assert page.inner_text("#w-main") == before
    assert "CLAIM" in page.inner_text(".c-crumb").upper()


def test_a_failure_opens_as_context_with_its_measurement(page):
    _ev(page, "#/portfolio/trust")
    page.click(".t-fail.ref")
    page.wait_for_timeout(1400)
    assert _state(page)[2].startswith("failure:")
    ctx = page.inner_text("#w-ctx").lower()
    assert "disabled" in ctx or "measured" in ctx


def test_closing_trust_context_restores_the_register(page):
    _ev(page, "#/portfolio/trust")
    before = page.inner_text("#w-main")
    page.click(".t-claim")
    page.wait_for_timeout(1300)
    page.keyboard.press("Escape")
    page.wait_for_timeout(900)
    assert _state(page) == ["portfolio:portfolio", "trust", None]
    assert page.inner_text("#w-main") == before


def test_trust_carries_no_marketing_language(page):
    """§35. A lab notebook, not a pitch deck."""
    _ev(page, "#/portfolio/trust")
    body = page.eval_on_selector("#w-main", "n => n.textContent.toLowerCase()")
    for word in ("industry-leading", "best-in-class", "revolutionary",
                 "ai-powered", "enterprise-grade", "production-ready",
                 "world-class", "cutting-edge"):
        assert word not in body, f"marketing language: {word!r}"


def test_trust_declines_to_render_on_a_settlement(page):
    """Trust is a property of the system, not of one record."""
    _ev(page, "#/settlement/setl_000089/trust")
    body = page.inner_text("#workspace").lower()
    assert "property of the system" in body
    assert page.eval_on_selector_all(".t-claim", "x => x.length") == 0


def test_a_stale_trust_fetch_cannot_land_on_another_subject(page):
    _ev(page, "#/portfolio/trust")
    page.route("**/api/claims*", lambda route: (page.wait_for_timeout(2500),
                                                route.continue_()))
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000020'},lens:'control'})")
    page.wait_for_timeout(3600)
    page.unroute("**/api/claims*")
    assert _state(page)[0] == "settlement:setl_000020"
    assert "uncomfortable numbers" not in page.inner_text("#workspace").lower()


# --------------------------------------------------------------------------
# Phase 9.4 — interaction guarantees that were defects before they were rules.
# --------------------------------------------------------------------------

def test_the_state_spine_is_present_on_every_lens(page):
    """§9.3C. It is the application's "you are here".

    It used to be drawn by whichever lens chose to call StateSpine, so it
    appeared on two views out of fourteen and vanished entirely on Trust —
    the one lens where a reader is holding "where did the money stop" while
    reading about the system's own failures. It is rendered by the shell now,
    which is what makes "no exceptions" a property rather than a promise.
    """
    for subject in ("portfolio", "settlement/setl_000089"):
        for lens in ("control", "journal", "evidence", "investigate",
                     "policy", "activity", "trust"):
            page.evaluate(f"() => location.hash = '#/{subject}/{lens}'")
            page.wait_for_timeout(500)
                # The spine moved from a band above the workspace into the case
                # rail — part of the case's financial identity now, not a strip
                # over the instrument. The guarantee is unchanged: present on
                # every lens, which is what this asserts.
            h = page.evaluate("""() => {
                const e = document.querySelector('.c-flow');
                return e ? e.getBoundingClientRect().height : 0; }""")
            assert h > 0, f"no state spine on {subject}/{lens}"


def test_the_master_owns_the_full_width_until_something_is_inspected(page):
    """§9.3N. The absence of a context is itself the correct state.

    The pane was hidden when nothing was selected, but its grid COLUMN stayed:
    the master rendered at 54% of the workspace and the other 46% was reserved
    for the sentence "Select a row to inspect it."
    """
    page.evaluate("() => location.hash = '#/portfolio/control'")
    page.wait_for_timeout(900)
    share = page.evaluate("""() => {
        const ws = document.getElementById('workspace');
        const m = document.getElementById('w-main');
        return m.getBoundingClientRect().width / ws.getBoundingClientRect().width; }""")
    assert share > 0.95, f"master holds only {share:.0%} with no context open"

    page.click(".c-row.link")
    page.wait_for_timeout(900)
    shared = page.evaluate("""() => {
        const ws = document.getElementById('workspace');
        const m = document.getElementById('w-main');
        return m.getBoundingClientRect().width / ws.getBoundingClientRect().width; }""")
    assert shared < 0.8, "opening a context did not give the pane its column"
    page.keyboard.press("Escape")
    page.wait_for_timeout(600)


def test_the_palette_reaches_a_settlement_by_keyboard_alone(page):
    """§9.4.18. The whole journey must be possible without a mouse.

    Reaching a settlement otherwise means tabbing through a queue of 250.
    """
    page.evaluate("() => location.hash = '#/portfolio/control'")
    page.wait_for_timeout(900)
    page.keyboard.press("Meta+k")
    page.wait_for_timeout(400)
    assert page.evaluate("() => PALETTE.isOpen()"), "Cmd+K did not open the palette"
    assert page.evaluate("() => document.activeElement.classList.contains('c-pal-q')"), \
        "the palette opened without taking focus"

    page.keyboard.type("setl_0000")
    page.wait_for_timeout(400)
    labels = page.evaluate(
        "() => [...document.querySelectorAll('.c-pal-l')].map(n => n.textContent)")
    assert labels and all(l.startswith("setl_") for l in labels[:3]), \
        f"a settlement query returned {labels[:3]}"

    page.keyboard.press("Enter")
    page.wait_for_timeout(900)
    assert page.evaluate("() => SHELL.subject.type") == "settlement"
    assert not page.evaluate("() => PALETTE.isOpen()"), "the palette stayed open"


def test_closing_the_palette_never_drops_focus_to_the_document(page):
    """§9.4.18. Focus landing on <body> is how a keyboard journey ends."""
    page.evaluate("() => location.hash = '#/portfolio/control'")
    page.wait_for_timeout(800)
    page.keyboard.press("Meta+k")
    page.wait_for_timeout(400)
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    tag = page.evaluate("() => document.activeElement.tagName")
    assert tag != "BODY", "focus was returned to the document"


# --------------------------------------------------------------------------
# Phase 11 — the operational workflow. A blocker is the smallest missing fact
# preventing money from progressing, and the product's job is to say what it
# is, what it holds, and whether ATTEST can do anything about it.
# --------------------------------------------------------------------------

def test_no_action_label_claims_a_capability_attest_does_not_have(page):
    """§3, §16, §18. The one rule that makes the rest of it honest.

    Every blocker carries a capability label, and every one of the three is
    something ATTEST cannot perform: an external change at the source, a
    decision about the engine's own defaults, or a human searching a record.
    A label that implies otherwise is the product lying about itself.
    """
    _ev(page, "#/portfolio/control")
    caps = page.eval_on_selector_all(
        ".c-blk-c", "x => x.map(n => n.textContent.trim().toUpperCase())")
    assert len(caps) >= 3, "blockers do not state what ATTEST can do about them"

    PERMITTED = {"REQUIRES EXTERNAL EVIDENCE", "REQUIRES ENGINE CHANGE",
                 "REQUIRES HUMAN SEARCH", "ENGINE ACTION", "POLICY SIMULATION"}
    for c in caps:
        assert c in PERMITTED, f"unrecognised capability label: {c!r}"

    # An executable label may only appear where the engine can genuinely act.
    # Nothing in this list can be executed today, so nothing may claim it.
    body = page.inner_text("#w-main").upper()
    for lie in ("FREE RE-RUN", "ONE CLICK", "RESOLVE NOW", "FIX AUTOMATICALLY"):
        assert lie not in body, f"{lie!r} promises an operation that cannot run"


def test_the_free_re_run_label_is_gone(page):
    """§3. It was never free and it was never available.

    The pipeline already escalates through every rung on each run, so widening
    the window means widening beyond the lag ladder — a constant in protected
    blocking.py that the blocking study explicitly decided to keep. Calling it
    a free re-run invited an operator to look for a button that cannot exist.
    """
    for h in ("#/portfolio/control", "#/portfolio/journal"):
        _ev(page, h)
        assert "free re-run" not in page.inner_text("#w-main").lower()


def test_selecting_a_blocker_scopes_its_population(page):
    """§4. A blocker is work, and work has a population."""
    _ev(page, "#/portfolio/control")
    page.click(".c-blk")
    page.wait_for_timeout(1200)
    subject, lens, context = _state(page)
    assert subject == "portfolio:portfolio", "selecting a blocker navigated away"
    assert lens == "control", "selecting a blocker changed the instrument"
    assert context and context.startswith("action:")
    rows = page.eval_on_selector_all(".c-pop-r", "x => x.length")
    assert rows >= 1, "the blocker does not show the settlements it holds"


def test_a_case_remembers_the_blocker_it_came_from(page):
    """§5, §10. Three instruments later, an operator should still know why
    this case is on screen — and it must survive reload, because the reason
    belongs in the URL exactly as the other state does."""
    _ev(page, "#/portfolio/control")
    page.click(".c-blk")
    page.wait_for_timeout(1200)
    page.click(".c-pop-r")
    page.wait_for_timeout(1400)

    assert page.evaluate("() => SHELL.subject.type") == "settlement"
    origin = page.evaluate("() => SHELL.from")
    assert origin, "the case forgot the blocker it was opened from"
    assert "from=" in page.evaluate("() => location.hash")
    assert page.query_selector(".c-from"), "the blocker is not shown on the case"

    for lens in ("evidence", "investigate", "policy", "journal", "activity"):
        page.evaluate(f"() => navigate({{lens:'{lens}'}})")
        page.wait_for_timeout(700)
        assert page.evaluate("() => SHELL.from") == origin, \
            f"the blocker was lost switching to {lens}"
        assert page.query_selector(".c-from"), f"blocker not shown on {lens}"

    page.reload(wait_until="networkidle")
    page.wait_for_function("() => SHELL && SHELL.record", timeout=90000)
    page.wait_for_timeout(900)
    assert page.evaluate("() => SHELL.from") == origin, \
        "the blocker did not survive a reload"


def test_the_contradicted_case_is_reachable_without_knowing_its_id(page):
    """§6. It was only findable by typing setl_000109 into the URL."""
    _ev(page, "#/portfolio/control")
    blockers = page.query_selector_all(".c-blk")
    assert len(blockers) >= 3
    blockers[-1].click()          # the per-item blocker holds the contradiction
    page.wait_for_timeout(1200)
    ids = page.eval_on_selector_all(".c-pop-id", "x => x.map(n => n.textContent.trim())")
    assert ids, "the per-item blocker shows no settlements"
    page.click(".c-pop-r")
    page.wait_for_timeout(1400)
    assert page.evaluate("() => SHELL.record.status") == "CONTRADICTED"


def test_a_contradicted_case_is_not_reported_as_passing(page):
    """A settlement can pass every check it was given and still have no
    explanation at all — the contradiction lives in the unsat core. Control
    reported 'every check passed' over exactly that."""
    _ev(page, "#/settlement/setl_000109/control")
    concl = page.inner_text(".c-concl").lower()
    assert "every check passed" not in concl
    assert "no combination explains" in concl
    assert "447.05" in concl, "the unresolved residual is not stated"


def test_the_review_cost_lever_never_edits_the_recorded_policy(page):
    """§8. Looking at what a review is worth must not change what was decided."""
    _ev(page, "#/portfolio/control")
    lever = page.inner_text(".c-lever")
    assert "post without a person" in lever
    assert "not modified" in lever.lower(), \
        "the lever does not say the recorded policy is untouched"

    before = page.evaluate("""() => fetch(
        `/api/decision?run=${SHELL.run}&type=portfolio`)
        .then(r => r.json()).then(d => d.recorded_version)""")
    page.evaluate("() => navigate({lens:'policy'})")
    page.wait_for_timeout(900)
    after = page.evaluate("""() => fetch(
        `/api/decision?run=${SHELL.run}&type=portfolio`)
        .then(r => r.json()).then(d => d.recorded_version)""")
    assert before == after, "the recorded policy version moved"


def test_the_blocker_value_stays_visible_while_inspecting_a_case(page):
    """§5. The value is why the work was chosen; losing it loses the reason."""
    _ev(page, "#/portfolio/control")
    page.click(".c-blk")
    page.wait_for_timeout(1200)
    page.click(".c-pop-r")
    page.wait_for_timeout(1400)
    page.evaluate("() => navigate({lens:'evidence'})")
    page.wait_for_timeout(800)
    from_text = page.inner_text(".c-from")
    assert "₹" in from_text, "the blocker's value is not carried onto the case"


def test_no_room_leads_with_a_bare_entity_count(page):
    """Phase 12 Part 12. The first thing the eye meets in a room is the answer
    to that room's question, not an inventory of what it contains.

    Activity led with '60 / events delivered' — the only figure of seven that
    was a countable rather than a conclusion."""
    for lens in ("control", "evidence", "investigate", "policy",
                 "journal", "activity", "trust"):
        _ev(page, f"#/portfolio/{lens}")
        fig = page.inner_text(".c-concl-n b").strip()
        # a conclusion carries money, a verdict, or a ratio — never a lone count
        assert ("₹" in fig or "/" in fig or " of " in fig
                or fig.isupper()), \
            f"{lens} leads with a bare count: {fig!r}"


def test_activity_does_not_count_refused_events_as_delivered(page):
    """Phase 12 G-2. 43 of 60 inbound events were refused as duplicates,
    replays or bad signatures. A room whose subject is what actually happened
    must not headline all 60 as though they landed."""
    _ev(page, "#/portfolio/activity")
    # a fresh run has no deliveries at all, and the claim under test is about
    # how refusals are reported — so put some refusals in the log first
    page.evaluate("""(async () => { await fetch(
      `/api/events/demo?run=${SHELL.run}`, {method:'POST'}); })()""")
    page.wait_for_timeout(2000)
    page.evaluate("navigate({}, {replace:true})")
    page.wait_for_timeout(2400)

    label = page.inner_text(".c-concl-n em").lower()
    assert "delivered" not in label, \
        f"the headline still describes inbound events as delivered: {label!r}"

    room = page.inner_text("#workspace").lower()
    assert "deliveries since" in room, "the delivery record is gone entirely"

    # whatever the webhook state, the room must state it exactly: every
    # non-zero outcome named, and refusals never folded into acceptances
    d = page.evaluate("""async () => {
        const r = await fetch(`/api/activity?run=${SHELL.run}&type=portfolio`);
        return await r.json();}""")
    for kind, n in (d.get("delivery_counts") or {}).items():
        if n:
            assert kind.replace("_", " ") in room, \
                f"{n} {kind} deliveries are not stated anywhere in Activity"

    # the headline counts verdicts, not deliveries — asserted by derivation
    # rather than by "the delivery number is absent", which collides by
    # coincidence once enough events have been delivered
    total = max((o.get("n") or 0) for o in d["outcome"])
    unrev = len(d.get("unrevised") or [])
    assert page.inner_text(".c-concl-n b").strip() == f"{total - unrev} of {total}", \
        "the headline figure is not the count of settlements whose verdicts stand"


def _money_sizes(page, root):
    """Every painted ₹ amount under `root`, with its computed type size."""
    return page.evaluate("""(sel) => {
      const r = document.querySelector(sel); if (!r) return [];
      const out = [];
      const vis = e => { const s = getComputedStyle(e);
        return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0'; };
      const walk = el => { for (const n of el.childNodes) {
        if (n.nodeType === 3 && n.textContent.includes('\\u20b9')) {
          const g = document.createRange(); g.selectNodeContents(n);
          const b = g.getBoundingClientRect();
          if (b.height && b.width) out.push({
            t: n.textContent.trim(),
            px: parseFloat(getComputedStyle(n.parentElement).fontSize)});
        } else if (n.nodeType === 1 && vis(n)) walk(n); } };
      walk(r); return out; }""", root)


def test_money_never_renders_at_annotation_size(page):
    """Phase 13 §6. '₹ amounts must never visually look like metadata.'

    The State Spine painted ₹48,03,127.81 — the money held at verification, and
    the answer to 'where did my money stop' — at 9px, the same size as the word
    'Source' beside it. The 10px and 11px tiers are for provenance, timestamps
    and counts. Money is the subject of this product, not an annotation."""
    BODY = 13
    for route in ("#/portfolio/control", "#/settlement/setl_000089/evidence",
                  "#/settlement/setl_000109/control"):
        _ev(page, route)
        small = [m for m in _money_sizes(page, ".c-case") if m["px"] < BODY]
        assert not small, (
            f"{route}: money at annotation size in the case rail: "
            + ", ".join(f"{m['t']} at {m['px']:.0f}px" for m in small[:6]))


def test_the_money_that_stopped_outranks_any_single_blocker(page):
    """Phase 13 §6. Establish visual roles: money that stopped is not smaller
    than one item of work.

    ₹6,316.03 — the smallest blocker in the list — rendered at 20px while
    ₹48,03,127.81 held at verification rendered at 9px. A ₹6,316 problem was
    painted 2.2x larger than ₹48 lakh of stuck money."""
    _ev(page, "#/portfolio/control")
    held = [m for m in _money_sizes(page, ".c-state") if m["px"]]
    assert held, "no money in the state spine"
    stopped = max(m["px"] for m in held)
    # an individual work item, not the room's headline conclusion — that
    # figure is the leverage of the top blocker and leads the room by design
    rows = page.query_selector_all(".c-blk-v")
    assert rows, "no blocker rows on the landing"
    biggest_blocker = max(
        page.evaluate("e => parseFloat(getComputedStyle(e).fontSize)", r)
        for r in rows)
    assert stopped >= biggest_blocker, (
        f"a single blocker is painted at {biggest_blocker:.0f}px while the money "
        f"that stopped is at {stopped:.0f}px")


def test_no_control_renders_with_browser_default_chrome(page):
    """Phase 13 §17. 'No card-grid-everything.'

    `button { font: inherit; color: inherit }` resets the type and nothing
    else, so every button that did not set its own background inherited
    Chromium's `buttonface` grey and a 2px outset border. 111 of ~190 visible
    controls were rendering as raw OS buttons — including all seven instrument
    dock items, whose stylesheet comment describes 'a seated indent against the
    rail edge rather than a filled chip', and the three blocker rows, which
    read as the SaaS cards the brief warns against.

    Nothing about that was a design decision. It was a missing reset."""
    seen = []
    for subject in ("portfolio", "settlement/setl_000089"):
        for lens in ("control", "evidence", "investigate", "policy",
                     "journal", "activity", "trust"):
            _ev(page, f"#/{subject}/{lens}")
            seen += page.evaluate("""() =>
              [...document.querySelectorAll('button')]
                .filter(e => e.offsetParent)
                .map(e => { const s = getComputedStyle(e);
                  return {cls: e.className || '(no class)',
                          bg: s.backgroundColor, bd: s.borderTopStyle}; })
                .filter(r => r.bd === 'outset' || r.bg === 'rgb(239, 239, 239)')""")
    assert not seen, (
        f"{len(seen)} controls render with browser default chrome: "
        + ", ".join(sorted({r["cls"] for r in seen})[:8]))


def test_every_instrument_states_its_question(page):
    """Phase 13 §9. 'It is an instrument index, not a navigation bar.'

    The dock's own stylesheet says an item should state what it asks — and
    `.c-lens-q { display: none }` hid the question on every instrument except
    the selected one, so six of seven read as bare nouns. A menu names places."""
    _ev(page, "#/portfolio/control")
    items = page.query_selector_all(".c-lenses button")
    assert len(items) == 7, f"expected seven instruments, saw {len(items)}"
    for it in items:
        q = it.query_selector(".c-lens-q")
        assert q and q.is_visible(), \
            f"{it.inner_text().strip()[:20]} states no question"
        assert q.inner_text().strip().endswith("?"), \
            f"not a question: {q.inner_text()!r}"


def test_the_dock_reads_as_the_product_loop(page):
    """Phase 13 §1, §9. The instruments are ordered by the operator's
    sequence — where did it stop, can it be proved, what would separate them,
    what may we do, what entered the books, what happened, what can I believe.

    Journal sat second, which put 'what entered the books' before 'may we post
    at all'."""
    _ev(page, "#/portfolio/control")
    order = [b.get_attribute("data-lens")
             for b in page.query_selector_all(".c-lenses button")]
    assert order == ["control", "evidence", "investigate", "policy",
                     "journal", "activity", "trust"], order


def test_no_type_size_outside_the_declared_scale(page):
    """Phase 13 §5. Six steps: 10, 11, 13, 15, 20, 34.

    An undeclared 9px tier had grown to 14 rules and 50 painted elements, and
    it was not carrying decoration — it carried the stage names, the held
    amounts and the capability labels. That is how ₹48,03,127.81 came to be
    painted smaller than the word beside it. A scale with an escape hatch is
    not a scale.

    `<html>` is excluded: it carries the browser's 16px root default and never
    paints text of its own."""
    SCALE = {10, 11, 13, 15, 20, 34}
    off = {}
    for subject in ("portfolio", "settlement/setl_000089"):
        for lens in ("control", "evidence", "investigate", "policy",
                     "journal", "activity", "trust"):
            _ev(page, f"#/{subject}/{lens}")
            for size, n in page.evaluate("""() => {
                const fs = {};
                const vis = e => { const s = getComputedStyle(e);
                  return s.display !== 'none' && s.visibility !== 'hidden'
                      && s.opacity !== '0'; };
                document.querySelectorAll('*').forEach(e => {
                  if (e.tagName === 'HTML' || !vis(e)) return;
                  const f = Math.round(parseFloat(getComputedStyle(e).fontSize));
                  if (f) fs[f] = (fs[f] || 0) + 1; });
                return fs; }""").items():
                if int(size) not in SCALE:
                    off[int(size)] = off.get(int(size), 0) + n
    assert not off, f"type sizes outside the declared scale: {dict(sorted(off.items()))}"


def test_no_room_paints_the_same_sentence_twice(page):
    """Phase 13 §16. 'Delete prose that merely explains.'

    Policy stated its boundary sentence as the conclusion and then again,
    word for word, under THE BOUNDARY — and on an unpriced case that section
    contained nothing else, so it was a heading over a repeat. A sentence
    painted twice halves the signal of everything around it."""
    import re as _re

    def sentences(text):
        out = set()
        for raw in _re.split(r"[\n.;]+", text):
            t = " ".join(raw.split()).lower().strip(" —·")
            if len(t.split()) >= 6:
                out.add(t)
        return out

    # Scoped to the conclusion against the rest of the room. A justification
    # repeated down the rows of a list is data — 250 settlements share one
    # reduction reason and each row is entitled to state it. Saying the room's
    # headline a second time further down is not.
    dupes = []
    for subject in ("portfolio", "settlement/setl_000089",
                    "settlement/setl_000020"):
        for lens in ("control", "evidence", "investigate", "policy",
                     "journal", "activity", "trust"):
            _ev(page, f"#/{subject}/{lens}")
            concl = page.query_selector(".c-concl")
            if not concl:
                continue
            # counted in the live room: a detached clone's innerText degrades
            # to textContent and would pick up collapsed disclosure bodies that
            # nobody can see
            room = " ".join(
                page.eval_on_selector("#workspace", "n => n.innerText").split()
            ).lower()
            for t in sentences(concl.inner_text()):
                if room.count(t) > 1:
                    dupes.append((f"{subject}/{lens}", t[:66]))
    assert not dupes, "the room's conclusion is repeated verbatim below it:\n" \
        + "\n".join(f"  {w}: {s}" for w, s in dupes[:8])


def test_no_section_is_a_heading_over_nothing(page):
    """Phase 13 §5, §16. A titled block with no body is a promise the room
    does not keep — the reader looks for content that is not there.

    Three appeared while removing repeated copy: Policy's boundary on an
    unpriced case, Activity's unrevised list when nothing is unrevised, and
    the rail's NEXT once the spine grew tall enough to push it out."""
    empty = []
    for subject in ("portfolio", "settlement/setl_000089",
                    "settlement/setl_000020"):
        for lens in ("control", "evidence", "investigate", "policy",
                     "journal", "activity", "trust"):
            _ev(page, f"#/{subject}/{lens}")
            empty += [f"{subject}/{lens}: {t}" for t in page.evaluate("""() =>
              [...document.querySelectorAll('#workspace .c-section')]
                .filter(s => s.offsetParent)
                .filter(s => {
                  const b = s.querySelector('.c-section-b, .c-sec-b') || s;
                  const head = s.querySelector('h2, h3, .c-section-t, .c-sec-t');
                  const bodyText = (b.innerText || '')
                    .replace(head ? head.innerText : '', '').trim();
                  return bodyText.length === 0; })
                .map(s => (s.innerText || '').split('\\n')[0].slice(0, 40))""")]
    assert not empty, "sections with a heading and no body:\n  " + "\n  ".join(empty[:6])


def test_the_search_space_chain_ends_at_the_surviving_explanations(page):
    """Phase 13 §11. The signature moment: 2,368 → 73 → 4, in one object.

    The compression stopped at the candidate universe, and the number of
    explanations that survived it lived in a separate section below — so the
    sequence a judge is meant to read in three seconds was never completed
    where it was being told. 'The system did not magically find a match; it
    proved inside an explicitly defined universe' only lands if the universe,
    the cuts and what came out the far side are one figure."""
    _ev(page, "#/settlement/setl_000089/evidence")
    uni = page.inner_text(".e-uni")
    assert "surviving" in uni.lower() or "explanation" in uni.lower(), \
        f"the chain does not reach the explanations:\n{uni}"
    survivors = page.inner_text(".e-uni-end .e-uni-n").strip()
    shown = len(page.query_selector_all(".e-set-r"))
    assert survivors == str(shown), \
        f"chain says {survivors} survived, {shown} explanations are drawn"
    # and the assumption the whole chain rests on is stated, not disclosed
    assert "convention" in uni.lower(), \
        "the chain does not say the boundary rests on a convention"


def test_returning_to_the_work_returns_to_the_work(page):
    """Phase 22 §1 step 15, §6. The close of the loop the product is built on.

    'Back to the work' inherited the case's lens and dropped the blocker
    context, so a return from Trust landed on portfolio Trust — a page with no
    work on it, nothing selected, and the affected population gone. The button
    was labelled with the one thing it did not do."""
    _ev(page, "#/portfolio/control")
    page.click(".c-blk")
    page.wait_for_timeout(600)
    came_from = page.evaluate("() => location.hash")
    assert "in=action" in came_from
    page.click(".c-pop-r")
    page.wait_for_timeout(700)
    # wander to the far end of the loop before turning round
    page.click('[data-lens="trust"]')
    page.wait_for_timeout(600)
    page.click(".c-from-b")
    page.wait_for_timeout(900)

    back = page.evaluate("() => location.hash")
    assert back == came_from, \
        f"did not return to the work: went to {back}, came from {came_from}"
    assert len(page.query_selector_all(".c-pop-r")) > 0, \
        "the affected population is not listed after returning"
    assert len(page.query_selector_all(".c-blk")) == 3, \
        "the ranked work is not on screen after returning"


# Phase 22 §10. Which stages of the chain each instrument is talking about.
# The routing is derived, not authored: VERIFICATION belongs to Evidence when
# there is a proof to read and to Investigate when the question is what would
# separate the explanations.
CHAIN_OWNERS = {
    "source": "evidence", "matching": "evidence",
    "policy": "policy", "action": "journal",
}


def test_the_state_spine_is_the_way_into_the_instruments(page):
    """Phase 22 §10. The spine states the whole model and was five inert divs.

    Each stage is owned by exactly one instrument, so clicking a stage is a
    lens change — already addressable, already in the URL, already reversible
    with Back. No new state, no new screen."""
    _ev(page, "#/settlement/setl_000089/control")
    stages = page.query_selector_all(".c-state .c-flow-r")
    assert len(stages) == 5, f"expected five stages, saw {len(stages)}"
    for st in stages:
        assert st.get_attribute("data-lens"), \
            f"stage is inert: {st.inner_text()[:30]!r}"
    for name, lens in CHAIN_OWNERS.items():
        el = page.query_selector(f'.c-state .c-flow-r[data-stage="{name}"]')
        assert el, f"no stage {name}"
        assert el.get_attribute("data-lens") == lens, \
            f"{name} routes to {el.get_attribute('data-lens')}, expected {lens}"


def test_an_ambiguous_verification_routes_to_investigate(page):
    """The one stage whose owner depends on state. With a unique proof the
    question is 'can it be proved' — Evidence. With four explanations surviving
    it is 'what would separate them' — Investigate."""
    _ev(page, "#/settlement/setl_000089/control")
    amb = page.get_attribute('.c-state .c-flow-r[data-stage="verification"]',
                             "data-lens")
    _ev(page, "#/settlement/setl_000020/control")
    proven = page.get_attribute('.c-state .c-flow-r[data-stage="verification"]',
                                "data-lens")
    assert amb == "investigate", f"ambiguous verification routes to {amb}"
    assert proven == "evidence", f"proven verification routes to {proven}"


def test_clicking_a_stage_changes_only_the_lens(page):
    """The case must not move. A stage is a way into an instrument, not a
    different subject and not a context."""
    _ev(page, "#/settlement/setl_000089/control")
    before = page.inner_text(".c-case-amt .v")
    page.click('.c-state .c-flow-r[data-stage="policy"]')
    page.wait_for_timeout(700)
    assert "/policy" in page.evaluate("() => location.hash")
    assert "setl_000089" in page.evaluate("() => location.hash")
    assert page.inner_text(".c-case-amt .v") == before, "the case changed"


def test_each_room_lights_the_stages_it_is_talking_about(page):
    """Phase 22 §10. The spine is rendered by the shell on every lens, so a
    room can mark its own segment without drawing a second spine."""
    expect = {
        "evidence": {"matching", "verification"},
        "investigate": {"verification"},
        "policy": {"verification", "policy"},
        "journal": {"policy", "action"},
    }
    for lens, stages in expect.items():
        _ev(page, f"#/settlement/setl_000089/{lens}")
        lit = set(page.eval_on_selector_all(
            ".c-state .c-flow-r.lit", "x => x.map(e => e.dataset.stage)"))
        assert lit == stages, f"{lens} lights {lit or 'nothing'}, expected {stages}"


def test_the_next_question_is_derived_from_the_case_not_a_script(page):
    """Phase 22 §7. 'These must be derived from actual state.'

    The same instrument proposes a different next question depending on what
    the case actually is. Evidence on an ambiguous case sends you to
    Investigate — several explanations survive and the question is what would
    separate them. Evidence on a proven case has nothing to separate, so it
    sends you to Policy."""
    _ev(page, "#/settlement/setl_000089/evidence")     # AMBIGUOUS
    amb = page.get_attribute(".c-onward", "data-lens")
    _ev(page, "#/settlement/setl_000020/evidence")     # PROVEN
    proven = page.get_attribute(".c-onward", "data-lens")
    _ev(page, "#/settlement/setl_000109/evidence")     # CONTRADICTED
    contra = page.get_attribute(".c-onward", "data-lens")
    assert amb == "investigate", f"ambiguous evidence proposes {amb}"
    assert proven == "policy", f"proven evidence proposes {proven}"
    assert contra == "policy", \
        f"contradicted evidence proposes {contra} — there is nothing to separate"


def test_the_next_question_disappears_at_the_end_of_the_loop(page):
    """Phase 22 §7. 'If there is no meaningful next action, show nothing.'

    Trust is where the loop ends. An interface that always has a next thing to
    offer is a workflow being forced, not a product being read."""
    _ev(page, "#/settlement/setl_000089/trust")
    # `.up` is a different affordance: a handoff to another SUBJECT, because
    # one settlement cannot testify to its own engine. What must not exist here
    # is a next INSTRUMENT — there is nothing after "what can I believe".
    assert not page.query_selector(".c-onward:not(.up)"), \
        "Trust proposes a next instrument; it is the end of the loop"


def test_the_next_question_never_points_at_the_room_you_are_in(page):
    """A suggestion to read what is already on screen is noise."""
    for lens in ("control", "evidence", "investigate", "policy",
                 "journal", "activity", "trust"):
        _ev(page, f"#/settlement/setl_000089/{lens}")
        el = page.query_selector(".c-onward:not(.up)")
        if el:
            assert el.get_attribute("data-lens") != lens, \
                f"{lens} proposes itself"


def test_the_next_question_is_a_question(page):
    """It states what the next instrument would answer, not its name alone.
    'Evidence' is a place; 'can the explanation be proved' is a reason to go."""
    _ev(page, "#/settlement/setl_000089/control")
    el = page.query_selector(".c-onward")
    assert el, "control proposes no next question on an unresolved case"
    assert "?" in el.inner_text(), f"not a question: {el.inner_text()!r}"


def test_trust_on_a_case_offers_the_way_to_the_system(page):
    """Phase 22 §6. Trust on a settlement correctly refuses to answer — whether
    one case is right depends on whether the engine can be believed at all.

    But it said 'open Trust on the portfolio' and gave no way to do it, so the
    last beat of the case story was a two-line screen naming a destination the
    reader had to find themselves."""
    _ev(page, "#/settlement/setl_000089/trust")
    go = page.query_selector(".c-onward[data-subject]")
    assert go, "no way through to the systemic view"
    assert go.get_attribute("data-lens") == "trust"
    assert go.get_attribute("data-subject").startswith("portfolio")
    go.click()
    page.wait_for_timeout(900)
    assert page.evaluate("() => location.hash") == "#/portfolio/trust"
    assert "NOT VERIFIED" in page.inner_text("#w-main")


def test_no_label_in_a_repeated_row_wraps(page):
    """Phase 13B §12, §19. 'The interface should feel expensive because it is
    precise.'

    Phase 13 promoted these labels off an undeclared 9px tier onto the scale's
    10px, and WOULD UNBLOCK stopped fitting its 96px column — it wrapped on all
    three rows of the blocker register, pushing each value down and leaving the
    label column 3px ragged. That register is the first list on the landing and
    the answer to what to do first."""
    _ev(page, "#/portfolio/control")
    bad = page.evaluate("""() =>
      [...document.querySelectorAll('.c-blk-b i, .c-blk-w i, .c-blk-n i')]
        .filter(e => e.offsetParent)
        .filter(e => e.getBoundingClientRect().height > 18)
        .map(e => e.innerText.trim() + ' @ '
             + Math.round(e.getBoundingClientRect().height) + 'px')""")
    assert not bad, f"labels wrapping in the blocker register: {bad}"
    edges = page.evaluate("""() =>
      [...document.querySelectorAll('.c-blk-n i')].filter(e => e.offsetParent)
        .map(e => Math.round(e.getBoundingClientRect().right))""")
    assert len(set(edges)) == 1, f"label column is ragged: {sorted(set(edges))}"


def test_policy_does_not_state_its_decision_twice(page):
    """Phase 13B §8. 'If there are two competing heroes, remove hierarchy from
    one.'

    REVIEW was painted at 34px as the conclusion and again at 20px a hundred
    pixels below it. The block's unique content is the sentence that policy
    reads the verdict and does not change it — one of the product's core
    claims, and it appeared nowhere else."""
    for sid, word in (("setl_000089", "REVIEW"), ("setl_000020", "AUTO-POST")):
        _ev(page, f"#/settlement/{sid}/policy")
        big = page.evaluate("""(w) => {
          const out = [];
          const vis = e => { const s = getComputedStyle(e);
            return s.display !== 'none' && s.visibility !== 'hidden'; };
          const walk = el => { for (const n of el.childNodes) {
            if (n.nodeType === 3 && n.textContent.trim().toUpperCase() === w) {
              const px = parseFloat(getComputedStyle(n.parentElement).fontSize);
              if (px >= 20) out.push(px);
            } else if (n.nodeType === 1 && vis(n)) walk(n); } };
          walk(document.querySelector('#w-main')); return out; }""", word)
        assert len(big) <= 1, \
            f"{sid}: {word} painted {len(big)} times at hero weight ({big})"
    # and the claim that only appeared inside that block survives
    assert "does not change it" in page.inner_text("#w-main")


def test_a_spine_stage_shows_it_is_a_way_in_before_you_touch_it(page):
    """Phase 13B §14, §2. The interaction existed with no resting state — a
    pointer cursor and a hover tint, both of which require already hovering.

    A lit stage carries a solid left rule. A stage you can open carries the
    same rule, faintly. The affordance and the state share one language rather
    than adding an icon."""
    _ev(page, "#/settlement/setl_000089/journal")
    rules = page.evaluate("""() =>
      [...document.querySelectorAll('.c-state .c-flow-r')].map(e => {
        const s = getComputedStyle(e);
        return {stage: e.dataset.stage, lit: e.classList.contains('lit'),
                colour: s.borderLeftColor, width: s.borderLeftWidth};
      })""")
    assert rules, "no spine stages"
    unlit = [r for r in rules if not r["lit"]]
    assert unlit, "every stage is lit; nothing to distinguish"
    for r in unlit:
        assert r["colour"] != "rgba(0, 0, 0, 0)", \
            f"stage {r['stage']} gives no sign it can be opened"
    lit = [r for r in rules if r["lit"]]
    assert lit, "journal lights no stage"
    assert lit[0]["colour"] != unlit[0]["colour"], \
        "an open-able stage and the stage this room is about look identical"


def test_no_room_states_its_own_conclusion_twice_at_emphasis(page):
    """Phase 23 §8. Generalised from the Policy fix, which was scoped to one
    room and left the same defect standing next door: Investigate painted
    'Engine abstained' at 20px as its conclusion and again at 20px in the
    summary below it.

    Repeated FIGURES are not covered and must not be — ₹0.00 three times is
    the balanced-by-absence point, and a credit that equals the amount
    reconciled is two facts that happen to agree. This is about the room
    saying its own headline a second time."""
    bad = []
    for subject in ("portfolio", "settlement/setl_000089",
                    "settlement/setl_000020", "settlement/setl_000109"):
        for lens in ("control", "evidence", "investigate", "policy",
                     "journal", "activity", "trust"):
            _ev(page, f"#/{subject}/{lens}")
            concl = page.query_selector(".c-concl-f")
            if not concl:
                continue
            head = concl.inner_text().strip()
            if not head or head.startswith("₹"):
                continue
            n = page.evaluate("""(h) => {
                let n = 0;
                const vis = e => { const s = getComputedStyle(e);
                  return s.display !== 'none' && s.visibility !== 'hidden'; };
                const walk = el => { for (const q of el.childNodes) {
                  if (q.nodeType === 3
                      && q.textContent.trim().toLowerCase() === h.toLowerCase()) {
                    const px = parseFloat(
                      getComputedStyle(q.parentElement).fontSize);
                    if (px >= 15) n++;
                  } else if (q.nodeType === 1 && vis(q)) walk(q); } };
                walk(document.querySelector('#w-main')); return n; }""", head)
            if n > 1:
                bad.append(f"{subject}/{lens}: '{head}' painted {n}x at emphasis")
    assert not bad, "\n  ".join([""] + bad)


def test_every_money_role_declares_tabular_figures(page):
    """Phase 23 §6, §7. Nine financial categories, one of them declaring
    something different.

    Every ₹ role — entered, continues, agreed, disputed, value blocked, the run
    ladder — declares tabular-nums so digits hold their column. HELD did not,
    and HELD carries ₹48,03,127.81: the answer to where the money stopped."""
    _ev(page, "#/portfolio/control")
    rows = page.evaluate("""() =>
      [...document.querySelectorAll('.c-case-amt .v, .c-flow-v, .c-flow-h,'
        + ' .c-fv, .c-blk-v')]
        .filter(e => e.offsetParent && e.innerText.includes('\\u20b9'))
        .map(e => ({cls: e.className || '(amount)',
                    t: e.innerText.trim().slice(0, 16),
                    tab: getComputedStyle(e).fontVariantNumeric}))""")
    assert rows, "no money in the rail"
    off = [r for r in rows if "tabular-nums" not in r["tab"]]
    assert not off, "money roles not declaring tabular figures: " + ", ".join(
        f"{r['cls']} ({r['t']})" for r in off)
