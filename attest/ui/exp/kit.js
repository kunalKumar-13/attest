/* Shared primitives that carry no visual opinion.
 *
 * Escaping, number formatting and DOM plumbing are the same problem in every
 * composition, and getting Indian digit grouping wrong three separate ways is
 * not an experiment. Everything that expresses a POINT OF VIEW — spacing,
 * surfaces, hierarchy, motion — belongs to the composition, not here.
 */
'use strict';

(() => {
  const esc = s => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  /* ₹1,00,036.83 — Indian grouping, decimals always present. A number that
   * drops its paise is a number an accountant cannot check. */
  const rupees = paise => {
    const n = Math.abs(Number(paise) || 0);
    const sign = Number(paise) < 0 ? '-' : '';
    const whole = String(Math.floor(n / 100));
    const frac = String(n % 100).padStart(2, '0');
    let head = whole.slice(0, -3), tail = whole.slice(-3);
    if (head) head = head.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
    return `${sign}₹${head ? head + ',' : ''}${tail || '0'}.${frac}`;
  };

  /* Compact for rails and axes where precision is not the job. */
  const short = paise => {
    const r = Math.abs(Number(paise) || 0) / 100;
    if (r >= 1e7) return `₹${(r / 1e7).toFixed(2)}Cr`;
    if (r >= 1e5) return `₹${(r / 1e5).toFixed(2)}L`;
    if (r >= 1e3) return `₹${(r / 1e3).toFixed(1)}k`;
    return `₹${r.toFixed(0)}`;
  };

  const pct = (a, b) => (!b ? 0 : Math.max(0, Math.min(100, (a / b) * 100)));
  const plural = (n, s, p) => `${n} ${n === 1 ? s : (p || s + 's')}`;

  /* MODEL ◇ · SOLVER ○ · ENGINE ● — hollow to filled. The progression IS the
   * argument, and it survives greyscale, which is why it is a shape. */
  const ACTOR = {
    model: ['◇', 'model'], solver: ['○', 'solver'], engine: ['●', 'engine'],
    policy: ['▪', 'policy'], system: ['·', 'system'], none: ['·', 'none'],
  };
  const actorMark = a => (ACTOR[String(a || '').toLowerCase()] || ACTOR.none)[0];

  /* Every state carries a shape as well as a colour. WCAG aside, the browser
   * contracts already assert policy is readable without colour. */
  const VERDICT_MARK = {
    PROVEN: '●', AMBIGUOUS: '◑', CONTRADICTED: '⊘', INSUFFICIENT: '○',
  };
  const verdictMark = v => VERDICT_MARK[String(v || '').toUpperCase()] || '·';

  const h = (html) => {
    const t = document.createElement('template');
    t.innerHTML = String(html).trim();
    return t.content.firstElementChild;
  };

  window.KIT = { esc, rupees, short, pct, plural, actorMark, verdictMark, h,
                 ACTOR, VERDICT_MARK };
})();
