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
