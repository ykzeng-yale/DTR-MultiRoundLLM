# Experiments worker: portable handoff, 26 September 2026

Written by the experiments worker for LEAD-TRANSFER-01 (`8e0593b`). It supplements [START_HERE_20260926.md](START_HERE_20260926.md), which covers the research, the lead and the experiment record. This file covers what that package does not: how the worker operates, and the local-only state a `git clone` will not bring along. There are no credentials here, and none are needed beyond the machine's normal authenticated `git push`.

## State at transfer

- **Worker jobs:** none open. The last worker work was LEAD-PORT-02 (repair `1c807c3`, receipt `1ed48a9`), which the lead accepted in `95a4fd7`. The last MRL job before transfer was MRL-25 (`4931cb9`). *Update:* after transfer, Codex issued MRL-26 (`c072cdb`, LEAD-POLICY-16), a source-only PATCH/RETHINK renderer task; see COORDINATION.md for its status.
- **Run and lease:** none. No receiver process is owned by this project, and no shared-host lease is held.
- **E14:** NO-GO as the next efficacy stage. There have been zero real E14 receiver calls.
- **Protocol:** at transfer, freeze was on HOLD until the handling of public-pass and INCOMPLETE histories was set (LEAD-TRANSFER-01; worker notes `2e1d716` and `32e20b7`). *Update:* LEAD-POLICY-16 (`c072cdb`) keeps both recipes on every well-formed history and fixes the tri-state support law. Collection remains unreleased.
- **Worker's live record:** [experiments_status.md](../experiments_status.md). Its body is current, and its first `**Last updated:` line is the heartbeat, which a script rewrites every tick.
- **Health at transfer:** the full suite passed 1,677/1,677 on the populated worker host. A clean clone gives 1,635 passed, 0 failed and 42 explicit skips; the skips are missing-MBPP-source skips, not verification.

## Operating rules the worker followed

- Commit and push directly to `main` as `Yukang Zeng <ykzeng2019@gmail.com>`. Open no pull requests. Never force-push or push old or rewritten ancestry.
- Coordinate with the lead only through commits: entries in `COORDINATION.md` headed "Experiments → theory", plus the status page. The lead also mirrors its decisions as issue #3 comments.
- On every lead decision, record accepted, running, completed, blocked or superseded, with the real UTC time and the processed lead SHA. Verify the decision's cited hashes and numbers read-only before accepting. Raise exact contract conflicts; several were adopted (LEAD-POLICY-05, -12, -15).
- In the same commit as the acknowledgement, update the matching rows of the status page body. The heartbeat line alone is not a status report.
- No model, receiver, benchmark or download work without a **named lead release** that includes a numerical cap and, for receiver work, a verified shared-host lease. Run one sequential CPU worker unless told otherwise; parallel builders breached this in MRL-23.
- Never commit credentials or private data. Never pass scorer-only fields (private assertions, references, controls) into a prompt.
- Force-add evidence `.log` files (`git add -f`): `.gitignore` excludes `*.log`.

## Restarting the worker loop on a new machine

1. Clone, and set the identity as in START_HERE. Then run `uv sync --locked` to recreate `.venv`, which the tests and the heartbeat use.
2. Read every commit since the tag `handoff-2026-09-26`. Then acknowledge anything unprocessed before doing anything else.
3. Recreate the two helper scripts below outside the repository, for example in a scratch directory. **macOS periodically deletes old files under `/tmp`**, which removed the watcher once; keep the scripts somewhere persistent, or recreate them when a run exits with code 127.
4. Loop. Run `poll_origin.sh` in the background. When it wakes, `git fetch` and inspect any new lead commit (and issue #3). Then run `heartbeat.sh`, and re-arm **exactly one** watcher; two overlapping watchers were seen once.
5. The unauthenticated GitHub REST API allows about 60 requests per hour per IP, and it returned 403 once. Query the issue endpoint (`/issues/3`, which has a `comments` count) only when a new commit arrives; `git fetch` is unaffected.

`poll_origin.sh` wakes on a new `origin/main` commit, or after 30 minutes:

```bash
#!/bin/bash
REPO="${REPO:-$HOME/DTR-MultiRoundLLM}"
cd "$REPO" || exit 2
end=$(( $(date +%s) + 1800 ))
while [ "$(date +%s)" -lt "$end" ]; do
  sha=$(git ls-remote origin refs/heads/main 2>/dev/null | cut -f1)
  if [ -n "$sha" ] && ! git cat-file -e "$sha^{commit}" 2>/dev/null; then
    echo "WAKE new_remote_commit $sha $(date -u +%FT%TZ)"; exit 0
  fi
  sleep 60
done
echo "WAKE half_hour_tick $(date -u +%FT%TZ)"
```

`heartbeat.sh` rewrites only the status line, then commits and pushes. Usage: `heartbeat.sh "<last processed lead sha>" "<one-line news>"`. **Repaired in MRL-26:** the author identity comes from the clone's own configuration, set **once per clone** (`git config user.name "Yukang Zeng"` and `git config user.email "ykzeng2019@gmail.com"`, as in START_HERE). There are no `git -c` overrides and no `pull --rebase --autostash … || true`. The script fetches, then inspects `main` against `origin/main`. It fast-forwards when possible and makes an ordinary ancestry-preserving merge when needed. It stops with a factual report on the wrong branch or identity, on unrelated working changes or a merge conflict (after `git merge --abort`), and if `origin/main` moved before the push. It never auto-stashes, force-pushes or masks an error. The single tolerated working-tree line is the old host's pre-existing, app-owned deletion of `.claude/scheduled_tasks.lock`, which is never staged; a fresh clone will not have it. Edit the fixed wording in the Python block when the E14 status changes.

```bash
#!/bin/bash
# Status heartbeat (MRL-26 repaired): rewrite only the status line of docs/experiments_status.md, commit, push.
# Identity comes from the clone's configured user.name/user.email; no -c overrides. No autostash, no masked errors,
# no force-push. Stops with a factual report on wrong branch/identity, unrelated working changes or a merge conflict.
# Usage: heartbeat.sh "<last processed lead sha>" "<one-line news>"
set -euo pipefail
REPO="${REPO:-$HOME/DTR-MultiRoundLLM}"
cd "$REPO"
[ "$(git config user.name)" = "Yukang Zeng" ] && [ "$(git config user.email)" = "ykzeng2019@gmail.com" ] || { echo "STOP: clone identity is not configured (git config user.name/user.email)"; exit 3; }
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "STOP: not on main"; exit 3; }
# The only tolerated change: this host's pre-existing, app-owned deletion of .claude/scheduled_tasks.lock (never staged).
dirty=$(git status --porcelain | grep -v '^ D \.claude/scheduled_tasks\.lock$' || true)
[ -z "$dirty" ] || { echo "STOP: unrelated working changes present:"; echo "$dirty"; exit 3; }
git fetch -q origin main
if git merge-base --is-ancestor HEAD origin/main; then
  git merge -q --ff-only origin/main
elif ! git merge-base --is-ancestor origin/main HEAD; then
  git merge -q --no-edit origin/main || { git merge --abort; echo "STOP: merge conflict with origin/main; nothing committed"; exit 3; }
fi
NOW=$(date -u +%FT%TZ)
.venv/bin/python - "$NOW" "$1" "$2" <<'PYEOF'
import re, sys
from pathlib import Path
now, lead, news = sys.argv[1:4]
p = Path("docs/experiments_status.md"); s = p.read_text()
new = (f"**Last updated: {now}** — **Heartbeat (watcher tick {now}).** Last lead commit processed: `{lead}`. {news} "
       "Watcher: **running**, re-armed each tick, wakes on every lead commit and at most every 30 min while this desktop "
       "session is open; the separate half-hourly scheduler has not fired since 2026-09-23T08:10:19Z. Run/lease: **none**. "
       "E14 N1/S1 batch: **NO-GO accepted** (LEAD-POLICY-06); source/mock kept as an instrument artifact with no execution allowance. "
       "Codex owns all scientific design and release decisions.")
s, n = re.subn(r"^\*\*Last updated: .*$", new, s, count=1, flags=re.M)
assert n == 1; p.write_text(s)
PYEOF
git add docs/experiments_status.md
git commit -q -m "Status heartbeat $NOW: watcher running, no run/lease, E14 NO-GO accepted"
git fetch -q origin main
git merge-base --is-ancestor origin/main HEAD || { echo "STOP: origin/main moved during the heartbeat; committed locally, not pushed"; exit 3; }
git push -q origin main
git log --oneline -1
```

## Local state that does not move with Git

- **The pinned MBPP source cache** (`work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl`, and on the old host also `work/sources/mbpp_full.jsonl`), plus the host-local `work/` call logs. They are gitignored. Reacquire the source only under [mbpp_source_acquisition_20260925.md](../mbpp_source_acquisition_20260925.md), with SHA256 `ccf64cea…`, after a separate lead review. The committed [seed inventories](../../results/e14_seed_inventory_lead_committed_20260923.json) describe the logs.
- **The worker's scratch scripts,** reproduced above.
- **The worker's private notes (agent memory).** They are not in the repository. The durable lessons are in the rules above and in [experiments_status.md](../experiments_status.md) §5.2.
- **The previous desktop session's watcher.** It stops when that session is closed. The status line then stops advancing; that means the worker is not running, not that nothing happened. Do not assume a live receipt from the old laptop after its last heartbeat.
