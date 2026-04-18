# Local Hermes Integration

This document shows the smallest practical way to try Hermes Guard inside a local Hermes installation.

The goal is to let an existing Hermes user try the real Guard flow with minimal extra setup.

## Two Install Modes

Hermes can discover plugins from:

1. **User plugins** — `~/.hermes/plugins/<name>/`
2. **Project plugins** — `./.hermes/plugins/<name>/` (requires `HERMES_ENABLE_PROJECT_PLUGINS=true`)

For Hermes Guard, the easiest first try is user plugin mode.

## What Hermes Expects

A directory plugin needs:

- `plugin.yaml`
- `__init__.py`
- a `register(ctx)` function inside `__init__.py`

This repo already includes a minimal example under `examples/hermes-plugin/`.

## Recommended Local Test Flow

### 1. Create or reuse the local venv

From the repo root:

```bash
cd /path/to/hermes-guard
uv venv .venv
uv pip install --python .venv/bin/python -e '.[dev]'
```

If you want to pin a specific interpreter, pass `--python /path/to/python3.11` to `uv venv`.

### 2. Install the plugin into Hermes plugin discovery

Fastest way:

```bash
.venv/bin/python scripts/install_local_plugin.py
```

Manual user-plugin mode:

```bash
mkdir -p ~/.hermes/plugins/hermes_guard
cp examples/hermes-plugin/plugin.yaml ~/.hermes/plugins/hermes_guard/plugin.yaml
cp examples/hermes-plugin/__init__.py ~/.hermes/plugins/hermes_guard/__init__.py
```

Project plugin mode:

```bash
mkdir -p /path/to/your/project/.hermes/plugins/hermes_guard
cp examples/hermes-plugin/plugin.yaml /path/to/your/project/.hermes/plugins/hermes_guard/plugin.yaml
cp examples/hermes-plugin/__init__.py /path/to/your/project/.hermes/plugins/hermes_guard/__init__.py
export HERMES_ENABLE_PROJECT_PLUGINS=true
```

### 3. Export environment variables

```bash
export PYTHONPATH="$(pwd):${PYTHONPATH}"
export HERMES_GUARD_POLICY_PATH="$HOME/.hermes/guard-policy.yaml"
export HERMES_GUARD_GRANTS_PATH="$HOME/.hermes/guard-grants.yaml"
export HERMES_GUARD_CHANNEL=cli
```

### 4. Create a starter policy

Copy the example policy and adjust the workspace path:

```bash
cp examples/guard-policy.yaml ~/.hermes/guard-policy.yaml
# edit ~/.hermes/guard-policy.yaml — replace /path/to/workspace with your actual workspace path
```

Example `~/.hermes/guard-policy.yaml`:

```yaml
version: 1

defaults:
  global:
    read: deny
    write: deny
    patch: deny
    execute: confirm

channels:
  cli:
    read: allow
    write: confirm
    patch: confirm
    execute: confirm

rules:
  - id: allow-workspace-cli
    action: [read, write, patch, execute]
    channel: [cli]
    path: "/path/to/workspace/**"
    effect: allow
    except:
      - "/path/to/workspace/.env*"
      - "/path/to/workspace/**/.env*"
      - "/path/to/workspace/secrets/**"
      - "/path/to/workspace/**/secrets/**"
```

### 5. Start Hermes with the same environment

```bash
cd ~/.hermes/hermes-agent
PYTHONPATH="/path/to/hermes-guard:${PYTHONPATH}" \
HERMES_GUARD_POLICY_PATH="$HOME/.hermes/guard-policy.yaml" \
HERMES_GUARD_GRANTS_PATH="$HOME/.hermes/guard-grants.yaml" \
HERMES_GUARD_CHANNEL=cli \
venv/bin/python cli.py
```

Adjust the final launch command to however you normally start Hermes.

## First Smoke Test

Expected behavior with the example workspace policy:

| Scenario | Expected result |
|---|---|
| `read_file` inside the allowed workspace | Pass |
| `write_file` / `patch` inside the allowed workspace | Pass |
| `read_file` on a `.env` path inside the workspace | Block immediately |
| `terminal` with `git status` inside the workspace | Pass |
| `terminal` with `rm -rf build` inside the workspace | Confirm / block |

To demo the `confirm` → `grant` flow explicitly, remove `write` or `patch` from the workspace allow rule and retry.

## Using the Guard CLI While Testing

```bash
# List active grants
.venv/bin/guard grants --grants-path "$HOME/.hermes/guard-grants.yaml"

# Create a grant
.venv/bin/guard grant --channel cli --action write --path "/path/to/hermes-guard/SPEC.md" --lifetime session --grants-path "$HOME/.hermes/guard-grants.yaml"

# Revoke a grant
.venv/bin/guard revoke --id <grant-id> --grants-path "$HOME/.hermes/guard-grants.yaml"
```

Update manager:

```bash
.venv/bin/guard update status --repo-path "$HOME/.hermes/hermes-agent"
.venv/bin/guard update list --repo-path "$HOME/.hermes/hermes-agent"
.venv/bin/guard update checkpoint --repo-path "$HOME/.hermes/hermes-agent" --restore-dir "$HOME/.hermes/guard/restore-points"
.venv/bin/guard update apply --tag v2026.4.16 --repo-path "$HOME/.hermes/hermes-agent" --restore-dir "$HOME/.hermes/guard/restore-points"
.venv/bin/guard update rollback --repo-path "$HOME/.hermes/hermes-agent" --restore-dir "$HOME/.hermes/guard/restore-points"
```

> **Tip:** keep `--restore-dir` outside the target git repository so checkpoint files do not make the repo look dirty.

## What Already Works

- Hermes can load a Guard plugin entry
- The pre-tool hook calls Hermes Guard policy evaluation
- `allow` / `deny` / `confirm` map cleanly to Hermes block / no-block behavior
- Actionable `guard grant ...` hints are shown from real Hermes hook flow
- `status` / `list` / `checkpoint` / `apply` / `rollback` work from the Guard CLI

## Troubleshooting

### Hermes does not seem to load the plugin

- The plugin directory must be exactly `~/.hermes/plugins/hermes_guard/`
- Both `plugin.yaml` and `__init__.py` must exist there
- `PYTHONPATH` must include this repo path
- If using project plugins, `HERMES_ENABLE_PROJECT_PLUGINS=true` must be set

### Guard blocks everything with an internal error

- `HERMES_GUARD_POLICY_PATH` must point to a real YAML file
- `PYTHONPATH` must include this repo so `hermes_guard.plugin_entry` is importable
- This repo's venv must have dependencies installed

### Grants do not seem to take effect

- `HERMES_GUARD_GRANTS_PATH` must point to the same file used by the CLI
- The grant channel must match the running channel
- Session grants require the same `session_id`

### Update commands do not work

- The repo path must be a real git repository
- The repo must not be dirty unless you use `--allow-dirty`
- Tags must actually exist in that repository
- Rollback only works after at least one restore point has been created

## Current Limitations

- Plugin install flow is not polished yet
- Terminal policy is conservative, not deep shell analysis
- Dependency rollback is best effort only
- Update flow is tag-first and local-repo oriented
