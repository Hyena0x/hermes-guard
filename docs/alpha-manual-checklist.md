# Hermes Guard alpha manual checklist

Use this checklist before calling the current repo state a stable alpha snapshot.

## 1. Repo hygiene

- [ ] `README.md` matches the actual implemented feature set
- [ ] `SPEC.md` still matches the intended v0.1 scope
- [ ] `docs/local-hermes-integration.md` still works end to end
- [ ] `.gitignore` excludes local noise (`.venv`, `__pycache__`, `.pytest_cache`, `.DS_Store`)
- [ ] `LICENSE` exists

## 2. Test baseline

From the repo root:

```bash
.venv/bin/python -m pytest tests -q
```

- [ ] full test suite passes
- [ ] no unexpected warnings or flaky failures

## 3. Guard policy flow

Preconditions:
- Hermes Guard plugin installed into Hermes plugin discovery
- `PYTHONPATH` includes this repo
- `HERMES_GUARD_POLICY_PATH` and `HERMES_GUARD_GRANTS_PATH` are set

Checks:
- [ ] `read_file` on an allowed workspace file passes
- [ ] `read_file` on an excluded `.env` path blocks
- [ ] `write_file` in allowed workspace returns confirm/block with actionable `guard grant ...`
- [ ] `patch` in guarded workspace behaves consistently with `write_file`
- [ ] `guard grant ...` makes the intended action pass
- [ ] `guard grants` lists the new grant
- [ ] `guard revoke ...` removes it again

## 4. Terminal flow

Checks:
- [ ] safe CLI command like `git status` can pass in an allowed workspace
- [ ] risky command like `rm -rf build` confirms/blocks even in an allowed workspace
- [ ] chained command like `pwd && ls` confirms/blocks
- [ ] non-CLI channel stays more conservative than CLI

## 5. Hermes plugin integration

Checks:
- [ ] Hermes discovers `hermes_guard` plugin
- [ ] pre-tool hook returns `None` for allowed action
- [ ] pre-tool hook returns `{action: block, message: ...}` for deny/confirm action
- [ ] block message includes channel, action, matched rule, and next step when applicable

## 6. Update manager flow

Use a disposable git repo or a safe local test repo.

Checks:
- [ ] `guard update status --repo-path <repo>` prints repo state
- [ ] `guard update list --repo-path <repo>` prints tags
- [ ] `guard update checkpoint --repo-path <repo>` creates a restore point JSON + pip freeze file
- [ ] dirty repo causes `guard update apply --tag ...` to fail by default
- [ ] clean repo can `guard update apply --tag <tag>` successfully
- [ ] `guard update rollback` restores the latest restore point target

## 7. UX review

- [ ] success messages are short and clear
- [ ] failure messages are actionable
- [ ] confirm messages tell the user exactly what grant command to run
- [ ] command names still feel Hermes-like and low-friction

## 8. Alpha snapshot recommendation

When all boxes above are checked:

- [ ] initialize git if needed
- [ ] review `git status`
- [ ] commit the alpha snapshot
- [ ] tag or note it as the first local alpha milestone

Suggested first snapshot commit title:

```text
feat: ship Hermes Guard v0.1 alpha core
```
