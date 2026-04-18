# Hermes Guard v0.1 Spec

## 1. Product definition

Hermes Guard is a minimal control plane for Hermes.

v0.1 only solves two problems:
1. File permissions must be controllable before tool execution.
2. Hermes update/rollback must be controllable by version/tag instead of behaving like a blind sync-to-main flow.

Hermes Guard is not a full security framework.
Hermes Guard is not a full approval workflow system.
Hermes Guard is not a generalized audit/compliance product.

The design goal is simple:
- a normal Hermes user should be able to start using it with almost no extra learning cost
- the UX should feel like a natural extension of Hermes, not like a separate ops platform
- the default behavior should be conservative and predictable

Product promise for v0.1:
- allow a folder, but exclude some files/subpaths
- revoke previously granted permissions
- block risky actions before they execute
- update Hermes by tag, not just by main
- roll back to a recent restore point

## 2. Target user

Primary user:
- existing Hermes users
- private/self-hosted Hermes users
- users who want stronger trust boundaries without learning a large policy system
- users running Hermes through CLI and/or Telegram, with future Telegram hardening in mind

Non-goal for v0.1:
- enterprise multi-user RBAC
- cloud fleet policy management
- generalized remote secret governance

## 3. Success criteria

Hermes Guard v0.1 is successful if users can do all of the following with low friction:
1. allow access to a project folder
2. deny access to one or more sensitive files inside that folder
3. grant access temporarily or persistently
4. revoke access later
5. see what grants are active
6. update Hermes to a specific tag
7. roll back Hermes to the last restore point

Usability bar:
- if a Hermes user can already use slash commands, config files, and basic CLI commands, Hermes Guard should feel within the same difficulty range
- the user should not need to learn a complex DSL, policy language, or approval workflow for v0.1

## 4. Scope

### In scope

#### 4.1 Guard Policy
Only these Hermes tools are controlled in v0.1:
- `read_file`
- `write_file`
- `patch`
- `terminal`

Only these decision outcomes exist:
- `allow`
- `deny`
- `confirm`

`confirm` in v0.1 means:
- do not execute the action
- show a clear message
- tell the user which command to run to explicitly grant permission

#### 4.2 Update Manager Lite
Only these capabilities are in scope:
- show current version/tag/commit
- create restore point before update
- list available tags
- update to a specific tag
- roll back to the latest restore point

### Out of scope

- rich interactive approval workflow
- Telegram menu rewriting
- Telegram command hiding
- memory/skill versioning
- full dependency/environment reproducibility guarantee
- arbitrary shell command semantic analysis
- multi-user principal model
- enterprise policy distribution
- UI/TUI dashboard

## 5. UX principles

### 5.1 Simplicity over completeness
If a feature increases learning cost meaningfully, it does not belong in v0.1.

### 5.2 No silent surprise
Guard must never silently allow an action when policy resolution failed.
Guard must never silently mutate git state during update.

### 5.3 Explain every block
A block message must say:
- what action was blocked
- which canonical path/workdir was evaluated
- which channel triggered it
- which rule matched
- what the user can do next

### 5.4 Conservative by default
When Guard is unsure, it should `deny` or `confirm`, not `allow`.

### 5.5 Stay Hermes-shaped
Naming, commands, and config should feel familiar to Hermes users.
Prefer short commands and human-readable YAML over a complex policy engine.

## 6. User-facing commands

Minimum CLI surface for v0.1:

### Guard policy
- `guard grant ...`
- `guard revoke ...`
- `guard grants`
- `guard check ...` (optional but recommended if low effort)

### Update manager
- `guard update status`
- `guard update list`
- `guard update checkpoint`
- `guard update apply --tag <tag>`
- `guard update rollback`

Notes:
- keep naming flat and obvious
- avoid subcommands that require reading docs to understand
- if `guard check` adds too much scope, defer it

## 7. Policy model

### 7.1 Dimensions
Only three policy dimensions are supported in v0.1:
- `path`
- `action`
- `channel`

Use `channel` consistently. Do not mix `platform` and `channel` in v0.1.

Supported channels:
- `cli`
- `telegram`
- `cron`
- `mcp`
- `*`

Supported actions:
- `read`
- `write`
- `patch`
- `execute`

Tool-to-action mapping:
- `read_file` -> `read`
- `write_file` -> `write`
- `patch` -> `patch`
- `terminal` -> `execute`

### 7.2 Effects
Only three effects exist:
- `allow`
- `deny`
- `confirm`

There is no separate `allow_with_exceptions` effect.
`except` is just a condition that narrows a broader rule.

### 7.3 Rule file
Default policy file path:
- `~/.hermes/guard-policy.yaml`

Example:

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
  telegram:
    read: confirm
    write: deny
    patch: deny
    execute: deny

rules:
  - id: allow-workspace-readwrite-cli
    action: [read, write, patch]
    channel: [cli]
    path: "/path/to/workspace/**"
    effect: allow
    except:
      - "/path/to/workspace/**/.env*"
      - "/path/to/workspace/**/secrets/**"

  - id: deny-hermes-env
    action: [read, write, patch]
    channel: ["*"]
    path: "~/.hermes/.env"
    effect: deny
```

### 7.4 Dynamic grants
Dynamic grants are stored separately from static policy.

File path:
- `~/.hermes/guard-grants.yaml`

Why separate files:
- keep the default policy readable
- keep user-granted exceptions easy to list and revoke
- avoid mutating the main policy file for every operational decision

Example:

```yaml
version: 1
grants:
  - id: grant-20260417-docs-write
    action: [write, patch]
    channel: [cli]
    path: "/path/to/docs/**"
    effect: allow
    lifetime: session
    session_id: "abc123"
    created_at: "2026-04-17T21:00:00Z"
```

Supported lifetimes in v0.1:
- `session`
- `persistent`

If a stable `session_id` cannot be extracted from Hermes runtime context, session grant creation should fail clearly and ask the user to use a persistent grant instead.

## 8. Rule resolution

Rule priority is fixed and must not be configurable in v0.1:

1. most specific `deny` or `except`
2. most specific `confirm`
3. most specific `allow`
4. channel default
5. global default

Implementation guidance:
- internally compile `except` into effective deny sub-rules if that simplifies evaluation
- “most specific” should be deterministic, preferably based on path specificity after canonicalization
- exact path beats broad glob
- narrower nested glob beats wider glob

## 9. Path safety requirements

This is a hard engineering requirement.

Before matching any path-based rule for `read_file`, `write_file`, or `patch`, Guard must canonicalize the target path using the equivalent of:
- `expanduser`
- `abspath`
- `realpath`

The goal is to remove ambiguity from:
- `~`
- relative paths
- `..`
- symlink traversal

Canonical path matching is required to prevent policy bypass.

If canonicalization fails:
- do not allow
- return `confirm` or `deny`
- log the failure

## 10. Terminal policy in v0.1

Terminal is handled more conservatively than file tools.

### v0.1 behavior
- CLI channel: only obviously safe/read-only commands may be `allow`
- non-CLI channels: default to `confirm` or `deny`
- if the command contains redirection, chaining, subshells, or path ambiguity, it should not be auto-allowed
- if no clear target path can be determined, do not auto-allow
- even inside an allowed workspace, destructive shell operations should not be auto-allowed

Do not attempt a “smart” shell parser in v0.1.
Do not pretend to understand arbitrary shell syntax.

Practical implementation approach:
- keep a small safe/read-only allowlist for CLI
- everything else falls back to `confirm`
- on non-CLI channels, be stricter by default

Examples of likely safe/read-only CLI commands:
- `pwd`
- `which`
- `date`
- `uname`
- `git status`
- `git diff`
- `python --version`

Examples that should default to `confirm`:
- anything with `>` / `>>`
- anything with `&&` / `||` / `;`
- `rm`, `mv`, `chmod`, `chown`
- `git reset --hard`
- `git clean -fd`
- package install/uninstall
- service/process control

## 11. Failure handling and safety mode

Guard must never crash or deadlock Hermes.

Hard requirement:
- the outermost pre-tool hook must be wrapped in a broad exception handler
- if Guard itself throws, Hermes main process must survive
- the current controlled action must fail closed
- the failure must be logged clearly

Fail-closed rule for v0.1:
- if policy evaluation is broken, malformed, or incomplete, do not silently allow the action
- return `deny` or `confirm`

## 12. Logging

v0.1 only needs minimal operational logs.

Recommended log file:
- `~/.hermes/guard.log`

Each log event should include at least:
- timestamp
- tool name
- action
- channel
- canonical path or workdir
- decision
- matched rule id
- session id if known
- error summary if any

Non-goal:
- do not build a heavy audit analytics system in v0.1

## 13. Update Manager Lite

### 13.1 Product goal
Move Hermes update behavior from “sync with main” toward “explicit versioned update by tag”.

### 13.2 Repo assumptions
Default Hermes repo path for local use:
- `~/.hermes/hermes-agent`

Guard must first verify the target is a git repo.
If `.git` is missing or invalid:
- disable update features cleanly
- do not crash
- show a human-readable message

### 13.3 Dirty working tree rule
Default behavior:
- if the git working tree is dirty, abort update
- do not auto-stash
- do not auto-reset
- require explicit opt-in via `--allow-dirty` for any dirty-tree flow

This is intentional. Guard is a control layer, not an automation layer that makes hidden git decisions.

### 13.4 Restore point
Before update or explicit checkpoint, create a restore point.

Recommended location:
- `~/.hermes/guard/restore-points/<timestamp>.json`

A restore point should include at least:
- created_at
- repo_path
- git_branch
- git_commit
- git_tag if any
- Hermes `__version__`
- Hermes `__release_date__`
- dirty status
- python executable path
- `python --version`
- path to saved `pip freeze` output

`pip freeze` output can be stored alongside the JSON.

### 13.5 Update source strategy
v0.1 is tag-first.

Default update semantics:
- fetch tags
- list tags
- user chooses a tag
- checkout tag

Do not default to updating from `main`.
Tracking `main` can be a future explicit advanced mode.

Note:
- when checking out a tag, detached HEAD is normal
- status output should explain this clearly to users

### 13.6 Rollback semantics
`guard update rollback` rolls code back to the latest restore point.

Guarantees:
- code rollback: strong guarantee
- dependency rollback: best effort only

Rollback flow:
1. load latest restore point
2. checkout saved commit/tag
3. attempt dependency restore if practical
4. report clearly what was restored and what remains best effort

## 14. Suggested file structure

```text
hermes-guard/
  SPEC.md
  README.md
  pyproject.toml
  hermes_guard/
    __init__.py
    cli.py
    policy.py
    policy_store.py
    path_rules.py
    pre_tool_hook.py
    terminal_policy.py
    grants.py
    update_manager.py
    restore_points.py
    logging_utils.py
    models.py
  examples/
    guard-policy.yaml
  tests/
    test_cli_grants.py
    test_cli_update.py
    test_example_policy.py
    test_grants.py
    test_hermes_adapter.py
    test_imports.py
    test_path_rules.py
    test_plugin_entry.py
    test_policy_core.py
    test_pre_tool_hook.py
    test_terminal_policy.py
    test_update_manager.py
```

## 15. Implementation constraints

### Must have
- canonical real-path resolution before rule matching
- strict three-value decision model
- grants file must handle concurrent reads/writes safely
- update manager must degrade cleanly outside git repos
- dirty tree must abort by default
- restore point must record `python --version`
- outermost hook exception boundary must protect Hermes process

### Should have
- deterministic rule specificity scoring
- clear rule-id-based block messages
- simple and conservative terminal handling
- explicit session grant behavior when session_id exists

### Must avoid
- silent allow on policy failure
- automatic stash/reset in default update flow
- adding more decision types in v0.1
- mixing `platform` and `channel` terminology
- building a complex approval system in v0.1

## 16. Example block message

```text
Blocked by Hermes Guard.
Action: read
Channel: telegram
Path: /path/to/project/.env
Matched rule: deny-hermes-env
Reason: sensitive path is denied on this channel.
Next step: use CLI or create a narrower explicit grant if you really want this.
```

For `confirm` outcomes, the message should directly suggest a next command, for example:

```text
Hermes Guard requires explicit permission before this write.
Action: write
Channel: cli
Path: /path/to/demo/config.yaml
Matched rule: cli-write-default-confirm
Next step: guard grant --channel cli --action write --path "/path/to/demo/config.yaml" --lifetime session
```

## 17. MVP development order

### Phase 1: core policy
1. data models
2. path canonicalization
3. rule matching and specificity
4. grants persistence
5. pre-tool hook for read/write/patch

### Phase 2: terminal control
1. conservative terminal classification
2. CLI safe command allowlist
3. fallback to confirm/deny
4. log integration

### Phase 3: update manager
1. status/list/checkpoint
2. restore point persistence
3. apply by tag
4. rollback latest restore point

### Phase 4: docs/examples
1. README
2. sample policy
3. simple setup instructions for Hermes users
4. troubleshooting notes

## 18. Open questions intentionally deferred

These are deferred on purpose and should not block v0.1:
- exact Hermes plugin packaging/distribution shape
- Telegram-specific command/menu hardening
- memory/skill version protection
- update channels beyond tag-first
- more advanced shell/path extraction
- richer policy simulation/check tooling

## 19. Definition of done for v0.1

Hermes Guard v0.1 is done when:
- a Hermes user can install it without learning a new heavy workflow
- policy file + grants file are enough to control file access
- grants can be listed and revoked
- file exceptions inside allowed folders work correctly
- canonical path traversal cannot bypass policy
- terminal is conservatively guarded
- update status/list/apply/rollback work against tagged Hermes versions
- docs explain the system in a way that feels no harder than learning Hermes itself
