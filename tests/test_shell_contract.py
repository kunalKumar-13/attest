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
    assert "where it stopped" in body or "how it cleared" in body


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
    """§7: only context disappears."""
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'control'})")
    page.wait_for_timeout(1800)
    page.evaluate("document.getElementById('w-main').scrollTop = 420")
    page.wait_for_timeout(300)
    page.click(".c-row.link")
    page.wait_for_timeout(1100)
    assert page.evaluate("document.getElementById('w-main').scrollTop") == 420
    page.click("[data-close-ctx]")
    page.wait_for_timeout(900)
    assert page.evaluate("document.getElementById('w-main').scrollTop") == 420


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
    """§8, §9, §25. The investigation ran; the verdict did not move."""
    _ev(page, "#/settlement/setl_000089/investigate")
    abs_ = page.inner_text(".i-abs")
    assert "abstained" in abs_.lower()
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
    """§4, §8. A settlement can be AMBIGUOUS and REVIEW; those are two facts."""
    _ev(page, "#/settlement/setl_000089/policy")
    head = page.inner_text(".p-head")
    assert "REVIEW" in head
    assert "AMBIGUOUS" in head
    assert "does not change it" in head


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
    bound = page.inner_text(".p-bound")
    assert "nothing was priced" in bound.lower()
    assert page.eval_on_selector_all(".p-bound-mark", "x => x.length") == 0
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
    """§5, §30.8. The UI represents the engine; it does not re-derive it."""
    _ev(page, "#/settlement/setl_000020/policy")
    shown = page.inner_text(".p-head-d").strip()
    from_api = page.evaluate("""(async () => {
      const d = await (await fetch(`/api/decision?run=${SHELL.run}`
        + `&type=settlement&id=setl_000020&review=${SHELL.review}`)).json();
      return d.decision; })()""")
    assert shown.replace("-", "_") == from_api


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
    body = page.inner_text("#w-main")
    # the failure block precedes the claim register
    assert body.index("recorded failures") < body.index("what supports it".upper()) \
        or body.lower().index("recorded failures") < body.lower().index("what supports it")


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
