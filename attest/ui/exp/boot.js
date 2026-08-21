/* Wires a composition into the existing shell.
 *
 * The shell owns SUBJECT × LENS × CONTEXT, the URL, the async guard, the
 * origin-keyed motion and focus restoration. None of that is under experiment,
 * so none of it is duplicated three times: a composition supplies only how
 * things look, and this adapts that to the interfaces shell.js already expects
 * (SubjectHeader and LensStrip are classes with update(), not functions).
 */
'use strict';

(() => {
  const K = window.KIT;
  const COMP = window.COMPOSITION;
  if (!COMP) throw new Error('no composition loaded');

  class SubjectHeader {
    constructor(host) { this.host = host; this.host.className = 'x-subject'; }
    update(rec) {
      if (!rec) return;
      // Patch rather than replace: the header is one of the three things that
      // must not blink when the lens changes.
      const html = COMP.C.SubjectHeader(rec);
      if (this._last === html) return;
      this._last = html;
      this.host.innerHTML = html;
    }
  }

  class LensStrip {
    constructor(host, onPick) {
      this.host = host;
      this.host.className = 'x-lenses';
      this.host.setAttribute('role', 'tablist');
      host.addEventListener('click', e => {
        const b = e.target.closest('[data-lens]');
        if (b) onPick(b.dataset.lens);
      });
      host.addEventListener('keydown', e => {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft'
            && e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
        const bs = [...host.querySelectorAll('[data-lens]')];
        const i = bs.findIndex(b => b.classList.contains('on'));
        const fwd = e.key === 'ArrowRight' || e.key === 'ArrowDown';
        const n = bs[i + (fwd ? 1 : -1)];
        if (n) { e.preventDefault(); n.focus(); onPick(n.dataset.lens); }
      });
    }
    update(lenses, active) {
      const html = COMP.C.LensStrip(lenses || [], active);
      if (this._last === html) return;
      this._last = html;
      this.host.innerHTML = html;
      this.host.querySelectorAll('[data-lens]').forEach(b => {
        b.setAttribute('role', 'tab');
        b.setAttribute('aria-selected', b.classList.contains('on') ? 'true' : 'false');
      });
    }
  }

  window.C = Object.assign({}, COMP.C, { SubjectHeader, LensStrip });

  Object.entries(COMP.lenses).forEach(([key, impl]) => {
    // A lens that declares no subjects serves both.
    if (!impl.subjects) impl.subjects = ['portfolio', 'settlement'];
    window.defineLens(key, impl);
  });

  document.documentElement.dataset.composition = COMP.id;
  window.addEventListener('DOMContentLoaded', () => window.bootShell());
  if (document.readyState !== 'loading') window.bootShell();
})();
