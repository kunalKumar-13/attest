# CI

`gates.yml` is a GitHub Actions workflow. It lives here rather than in
`.github/workflows/` because pushing to that path needs a token with `workflow`
scope, and this repository is pushed with one that deliberately does not have it.

To enable it:

```bash
gh auth refresh -h github.com -s workflow
mkdir -p .github/workflows && git mv ci/gates.yml .github/workflows/gates.yml
git commit -m "enable CI" && git push
```

It runs the same two commands you can run locally, and they are the ones that
matter:

```bash
./.venv/bin/python -m pytest tests/ -q      # 59 property tests
./.venv/bin/python -m attest.eval.gate 250  # safety gates, exit 1 on regression
```

The workflow installs **no Rust toolchain**, on purpose. The engine has to run on
the numpy path with a narrower envelope, or the fallback is decorative.
