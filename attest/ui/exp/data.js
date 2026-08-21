/* One data layer for all three compositions.
 *
 * Rule 1 of the experiment is that A, B and C read identical data. The cheapest
 * way to be wrong about that is to let each composition fetch for itself and
 * drift — one passing `type=portfolio`, another forgetting it, and a comparison
 * that is silently measuring two different runs.
 *
 * So the fetching lives here once. A composition receives a plain object and
 * decides only how it looks. If a composition needs a field this does not
 * return, that is a signal the experiment has stopped being about presentation.
 */
'use strict';

(() => {
  const api = p => fetch(p).then(r => r.json());
  const q = (S, extra) => `run=${S.run}${extra || ''}`;
  const sid = subject => encodeURIComponent(subject.id);

  /* The spine is a non-negotiable on every lens, so it is fetched for every
   * lens rather than by Control alone. Cached per subject+run: the shell's
   * guard already discards stale results, and re-requesting the same flow seven
   * times while a user walks the strip is waste the eye can see. */
  const spineCache = new Map();
  const spine = (subject, S) => {
    const key = `${S.run}/${subject.type}/${subject.id}/${S.review}/${S.exposure}`;
    if (!spineCache.has(key)) {
      spineCache.set(key, api(subject.type === 'portfolio'
        ? `/api/spine?${q(S)}&type=portfolio&review=${S.review}&exposure=${S.exposure}`
        : `/api/spine?${q(S)}&type=settlement&id=${sid(subject)}`));
    }
    return spineCache.get(key);
  };

  /* type/id must travel together. Omitting them silently returns the PORTFOLIO
   * view for a settlement subject — which renders as an empty lens rather than
   * an error, and is exactly the kind of quiet wrongness a comparison between
   * three compositions would otherwise blame on the design. */
  const scope = subject => subject.type === 'portfolio'
    ? '&type=portfolio'
    : `&type=settlement&id=${sid(subject)}`;

  const D = {
    spine,

    async control(subject, S) {
      if (subject.type === 'portfolio') {
        const [sp, actions, attention] = await Promise.all([
          spine(subject, S), api(`/api/actions?${q(S)}`), api(`/api/attention?${q(S)}`),
        ]);
        return { spine: sp, actions, attention };
      }
      const [sp, settlement] = await Promise.all([
        spine(subject, S), api(`/api/settlement?${q(S)}&id=${sid(subject)}`),
      ]);
      return { spine: sp, settlement };
    },

    async journal(subject, S) {
      const [sp, journal, settlement] = await Promise.all([
        spine(subject, S),
        api(`/api/journal?${q(S)}&review=${S.review}&exposure=${S.exposure}`),
        subject.type === 'portfolio' ? null
          : api(`/api/settlement?${q(S)}&id=${sid(subject)}`),
      ]);
      return { spine: sp, journal, settlement };
    },

    async evidence(subject, S) {
      const [sp, evidence, settlement] = await Promise.all([
        spine(subject, S),
        api(`/api/evidence?${q(S)}${scope(subject)}`),
        subject.type === 'portfolio' ? null
          : api(`/api/settlement?${q(S)}&id=${sid(subject)}`),
      ]);
      return { spine: sp, evidence, settlement };
    },

    async investigate(subject, S) {
      const [sp, investigation] = await Promise.all([
        spine(subject, S), api(`/api/investigation?${q(S)}${scope(subject)}`)]);
      return { spine: sp, investigation };
    },

    async policy(subject, S) {
      const [sp, decision] = await Promise.all([
        spine(subject, S), api(`/api/decision?${q(S)}${scope(subject)}`)]);
      return { spine: sp, decision };
    },

    async activity(subject, S) {
      const [sp, activity] = await Promise.all([
        spine(subject, S), api(`/api/activity?${q(S)}${scope(subject)}`)]);
      return { spine: sp, activity };
    },

    async trust(subject, S) {
      const [sp, claims] = await Promise.all([
        spine(subject, S), api(`/api/claims?${q(S)}`)]);
      return { spine: sp, claims };
    },

    settlement: (id, S) => api(`/api/settlement?${q(S)}&id=${encodeURIComponent(id)}`),
  };

  window.EXP_DATA = D;
  window.shellApi = window.shellApi || api;
})();
