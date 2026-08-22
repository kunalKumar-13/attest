/* Wires a prototype into the existing shell.
 *
 * The shell owns SUBJECT × LENS × CONTEXT, the URL, the async guard, the
 * origin-keyed motion, focus return and scroll persistence. None of that is
 * under experiment and none of it is duplicated three times — a prototype
 * supplies only composition, and this adapts it to the interfaces shell.js
 * already expects.
 *
 * Each prototype decides where the case object LIVES (rail, line, or queue
 * row), which is the whole point of the experiment, so SubjectHeader and
 * LensStrip render into whatever slot that prototype's HTML provides.
 */
'use strict';

(() => {
  const P = window.PROTOTYPE;
  if (!P) throw new Error('no prototype loaded');

  class SubjectHeader {
    constructor(host) { this.host = host; this.host.className = 'p-subject'; }
    update(rec) {
      if (!rec || rec.error) return;
      this.rec = rec;
      this.paint();
    }
    /* The shell hands the spine down separately; the prototype decides
     * whether the case object shows it. */
    stage(stopped, spine) { this.stopped = stopped; this.spine = spine; this.paint(); }
    paint() {
      if (!this.rec) return;
      const html = P.C.CaseObject(this.rec, this.spine, this.stopped, window.SHELL);
      if (this._last === html) return;
      this._last = html;
      this.host.innerHTML = html;
    }
  }

  class LensStrip {
    constructor(host, onPick) {
      this.host = host;
      this.host.className = 'p-lenses';
      host.addEventListener('click', e => {
        const b = e.target.closest('[data-lens]');
        if (b) onPick(b.dataset.lens);
      });
      host.addEventListener('keydown', e => {
        const keys = ['ArrowRight', 'ArrowLeft', 'ArrowUp', 'ArrowDown'];
        if (!keys.includes(e.key)) return;
        const bs = [...host.querySelectorAll('[data-lens]')];
        const i = bs.findIndex(b => b.classList.contains('on'));
        const fwd = e.key === 'ArrowRight' || e.key === 'ArrowDown';
        const n = bs[i + (fwd ? 1 : -1)];
        if (n) { e.preventDefault(); n.focus(); onPick(n.dataset.lens); }
      });
    }
    update(lenses, active) {
      const html = P.C.Instruments(lenses || [], active);
      if (this._last === html) return;
      this._last = html;
      this.host.innerHTML = html;
      this.host.querySelectorAll('[data-lens]').forEach(b => {
        b.setAttribute('role', 'tab');
        b.setAttribute('aria-selected', b.classList.contains('on') ? 'true' : 'false');
      });
    }
  }

  window.C = Object.assign({}, P.C, { SubjectHeader, LensStrip });
  /* The shell renders the spine into #w-spine for every lens. A prototype that
   * carries the spine inside its case object returns nothing here, which
   * leaves #w-spine empty and `:empty` removes it from the layout. */
  if (!window.C.StateSpine) window.C.StateSpine = () => '';

  Object.entries(P.lenses).forEach(([key, impl]) => {
    if (!impl.subjects) impl.subjects = ['portfolio', 'settlement'];
    window.defineLens(key, impl);
  });

  document.documentElement.dataset.prototype = P.id;
  const go = () => window.bootShell();
  if (document.readyState === 'loading')
    window.addEventListener('DOMContentLoaded', go);
  else go();
})();
