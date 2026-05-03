# Hermes Guard

A minimal permission control plane for [Hermes](https://github.com/NousResearch/hermes-agent).

Hermes Guard adds two things Hermes is still weak at:

- **Controllable permissions** — policy guardrails evaluated before every tool execution
- **Tag-first updates** — explicit version checkpoints with restore points and rollback

## What works today

- Policy checks for `read_file`, `write_file`, `patch`, and `terminal`
- `allow`, `deny`, and `confirm` outcomes
- Explicit grants via `guard grant`, `guard grants`, `guard revoke`
- Actionable next-step grant command on `confirm`
- Hermes pre-tool adapter and plugin entry
- Conservative terminal handling
- `guard update status`
- `guard update list`
- `guard update checkpoint`
- `guard update apply --tag <tag>`
- `guard update rollback`

## Quick start

```bash
cd /path/to/hermes-guard
uv venv .venv
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/python scripts/install_local_plugin.py

export PYTHONPATH="$(pwd):${PYTHONPATH}"
export HERMES_GUARD_POLICY_PATH="$HOME/.hermes/guard-policy.yaml"
export HERMES_GUARD_GRANTS_PATH="$HOME/.hermes/guard-grants.yaml"
export HERMES_GUARD_CHANNEL=cli
```

A practical starter policy lives at `examples/guard-policy.yaml`.
It allows normal workspace reads, writes, patches, and safe terminal commands on the CLI channel, while still denying `.env` and `secrets/` paths.

See `docs/local-hermes-integration.md` for the full local integration walkthrough.

## Common commands

```bash
# grants
.venv/bin/guard grant --channel cli --action write --path "/tmp/demo.txt" --lifetime persistent --grants-path "$HOME/.hermes/guard-grants.yaml"
.venv/bin/guard grant --channel cli --action write --path "/tmp/demo.txt" --lifetime session --session-id "<session-id>" --grants-path "$HOME/.hermes/guard-grants.yaml"
.venv/bin/guard grants --grants-path "$HOME/.hermes/guard-grants.yaml"
.venv/bin/guard revoke --id <grant-id> --grants-path "$HOME/.hermes/guard-grants.yaml"

# updates
.venv/bin/guard update status --repo-path "$HOME/.hermes/hermes-agent"
.venv/bin/guard update list --repo-path "$HOME/.hermes/hermes-agent"
.venv/bin/guard update checkpoint --repo-path "$HOME/.hermes/hermes-agent" --restore-dir "$HOME/.hermes/guard/restore-points"
.venv/bin/guard update apply --tag v2026.4.16 --repo-path "$HOME/.hermes/hermes-agent" --restore-dir "$HOME/.hermes/guard/restore-points"
.venv/bin/guard update rollback --repo-path "$HOME/.hermes/hermes-agent" --restore-dir "$HOME/.hermes/guard/restore-points"
```

> **Tip:** keep `--restore-dir` outside the target git repository so checkpoint files do not make the repo look dirty.

## Policy precedence

Rule evaluation order (highest priority first):

1. `deny` — including `except` sub-paths derived from broader `allow` rules
2. `confirm` — matched rule requires an explicit grant before proceeding
3. Dynamic grants — created via `guard grant`
4. `allow` — matched policy rule
5. Channel default
6. Global default

If no rule or default matches, Guard falls back to `confirm`.

## Docs

- [`SPEC.md`](SPEC.md) — scope and design constraints
- [`docs/local-hermes-integration.md`](docs/local-hermes-integration.md) — local Hermes setup walkthrough
- [`docs/alpha-manual-checklist.md`](docs/alpha-manual-checklist.md) — manual alpha validation checklist

## Non-goals

Hermes Guard is intentionally narrow. It is not:

- A full enterprise policy engine
- A broad approval workflow system
- A complete reproducible environment rollback system

## Alpha status

Still rough around the edges:

- Plugin install is still a bit manual
- Terminal policy is conservative by design
- Dependency rollback is best effort only
