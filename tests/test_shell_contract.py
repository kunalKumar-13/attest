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
    return pg.evaluate("[SHELL.subject.type + ':' + SHELL.subject.id, SHELL.lens]")


def test_changing_lens_leaves_the_subject_and_the_header_untouched(page):
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'control'})")
    page.wait_for_timeout(1500)
    before_subject, _ = _state(page)
    before_header = page.inner_text(".c-subject")

    page.click("[data-lens=journal]")
    page.wait_for_timeout(1500)
    after_subject, after_lens = _state(page)

    assert after_subject == before_subject
    assert after_lens == "journal"
    assert page.inner_text(".c-subject") == before_header


def test_changing_subject_leaves_the_lens_and_the_strip_untouched(page):
    page.evaluate("navigate({subject:{type:'portfolio',id:'portfolio'},lens:'journal'})")
    page.wait_for_timeout(1600)
    before_strip = page.inner_text(".c-lenses")

    page.click(".c-row.link")
    page.wait_for_timeout(1600)
    subject, lens = _state(page)

    assert subject.startswith("settlement:")
    assert lens == "journal", "the user already said what they wanted to know"
    assert page.inner_text(".c-lenses") == before_strip


def test_the_url_addresses_both_axes_and_a_reload_restores_them(page):
    page.evaluate("navigate({subject:{type:'settlement',id:'setl_000089'},lens:'control'})")
    page.wait_for_timeout(1600)
    assert page.evaluate("location.hash") == "#/settlement/setl_000089/control"

    page.reload(wait_until="networkidle")
    page.wait_for_function("() => SHELL.record", timeout=90000)
    page.wait_for_timeout(900)
    assert _state(page) == ["settlement:setl_000089", "control"]


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

    subject, lens = _state(page)
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

    subject, lens = _state(page)
    assert subject.startswith("source:")
    assert lens != "journal", "source does not support journal"
    assert page.query_selector(".c-notice"), "the fallback was not announced"
    assert "does not apply" in page.inner_text(".c-notice")


def test_the_shell_raised_no_script_errors(page):
    assert page.errors == []           # type: ignore[attr-defined]
