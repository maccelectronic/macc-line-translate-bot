# GitHub Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Safely publish the existing translation bot as the private `macc-line-translate-bot` GitHub repository and update the authenticated GitHub account with the approved MACC company profile.

**Architecture:** Treat publication as a guarded release: first prove sensitive and generated files are excluded, then establish browser-backed GitHub CLI authentication, commit the reviewed source, create and push the private repository, and finally update repository metadata and company profile fields. Every external write is followed by a read-back verification.

**Tech Stack:** Git, GitHub CLI, GitHub REST API, Python 3.12, LINE Bot SDK, Flask, Google Gemini SDK

---

## File Map

- Existing source to publish: `.env.example`, `.gitignore`, `README.md`, `README_TH.md`, `config.py`, `main.py`, `requirements.txt`, `translator.py`
- Existing design record: `docs/superpowers/specs/2026-09-02-github-publication-design.md`
- New execution record: `docs/superpowers/plans/2026-09-02-github-publication.md`
- Explicitly excluded: `.env`, `venv/`, `__pycache__/`, `*.pyc`, and `*.log`

### Task 1: Commit and verify the release plan

**Files:**
- Create: `docs/superpowers/plans/2026-09-02-github-publication.md`

- [ ] **Step 1: Scan the plan for incomplete instructions**

Run:

```bash
rg -n 'T[B]D|T[O]DO|implement l[a]ter|fill in d[e]tails' docs/superpowers/plans/2026-09-02-github-publication.md
```

Expected: no matches.

- [ ] **Step 2: Commit the execution plan**

Run:

```bash
git add docs/superpowers/plans/2026-09-02-github-publication.md
git commit -m "docs: add GitHub publication implementation plan"
```

Expected: one new documentation file is committed on `main`.

### Task 2: Verify the source release boundary

**Files:**
- Inspect: `.gitignore`
- Inspect: `.env.example`
- Inspect: all source files listed in the File Map
- Modify local Git metadata: `.git/config`

- [ ] **Step 1: Prove sensitive and generated paths are ignored**

Run:

```bash
git check-ignore -v .env venv/ __pycache__/main.cpython-312.pyc
```

Expected: every path is matched by a rule in `.gitignore`.

- [ ] **Step 2: Stage only the approved source files**

Run:

```bash
git add .env.example .gitignore README.md README_TH.md config.py main.py requirements.txt translator.py
```

Expected: command succeeds without staging `.env`, `venv/`, or `__pycache__/`.

- [ ] **Step 3: Inspect the exact staged file set**

Run:

```bash
git diff --cached --name-only
```

Expected: exactly the eight approved source files appear.

- [ ] **Step 4: Enforce approved placeholders across every staged file**

Run:

```bash
./venv/bin/python - <<'PY'
import os
import re
import subprocess
import sys

approved = {
    "LINE_CHANNEL_ACCESS_TOKEN": "LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here",
    "LINE_CHANNEL_SECRET": "LINE_CHANNEL_SECRET=your_line_channel_secret_here",
    "GEMINI_API_KEY": "GEMINI_API_KEY=your_gemini_api_key_here",
}
staged_bytes = subprocess.check_output(
    ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"]
)
staged = [os.fsdecode(path) for path in staged_bytes.split(b"\0") if path]
failures = []

if ".env.example" not in staged:
    failures.append(".env.example: required staged file is missing")
else:
    env_text = subprocess.check_output(
        ["git", "show", ":.env.example"], stderr=subprocess.DEVNULL
    ).decode("utf-8", errors="replace")
    env_lines = env_text.splitlines()
    for key, exact_line in approved.items():
        if env_lines.count(exact_line) != 1:
            failures.append(f".env.example: expected exactly one approved placeholder for {key}")

assignment = re.compile(
    r"(?<![A-Za-z0-9_])(LINE_CHANNEL_ACCESS_TOKEN|LINE_CHANNEL_SECRET|GEMINI_API_KEY)\s*="
)
gemini_token = re.compile(r"AIza[0-9A-Za-z_-]{20,}")

for path in staged:
    content = subprocess.check_output(
        ["git", "show", f":{path}"], stderr=subprocess.DEVNULL
    ).decode("utf-8", errors="replace")
    for line_number, line in enumerate(content.splitlines(), start=1):
        for match in assignment.finditer(line):
            key = match.group(1)
            if line.strip() != approved[key]:
                failures.append(f"{path}:{line_number}: disallowed assignment for {key}")
        if gemini_token.search(line):
            failures.append(f"{path}:{line_number}: value matches a Gemini API-key format")

if failures:
    print("Secret scan failed; no credential values are shown:", file=sys.stderr)
    for failure in failures:
        print(f"- {failure}", file=sys.stderr)
    sys.exit(1)

print(f"Secret scan passed for {len(staged)} staged files.")
PY
```

Expected: exit code 0 and exactly `Secret scan passed for 8 staged files.` The check reads the complete indexed content of all eight staged files, including Markdown; requires exactly one approved assignment for each of the three placeholders in `.env.example`; rejects every other staged assignment to those names; and rejects any value matching the Gemini `AIza...` key format. Failure output identifies only the file, line number, and credential name or format, never the value.

- [ ] **Step 5: Configure the repository-local commit identity**

Run:

```bash
git config --local user.name 'MACC Electronics (Thailand) Co., Ltd.'
git config --local user.email 'maccsale1@gmail.com'
```

Expected: both commands exit 0 with no output and write only to this repository's `.git/config`.

- [ ] **Step 6: Verify the repository-local commit identity exactly**

Run:

```bash
test "$(git config --local --get user.name)" = 'MACC Electronics (Thailand) Co., Ltd.'
test "$(git config --local --get user.email)" = 'maccsale1@gmail.com'
git config --local --get user.name
git config --local --get user.email
```

Expected: both `test` commands exit 0. The final two commands print exactly:

```text
MACC Electronics (Thailand) Co., Ltd.
maccsale1@gmail.com
```

- [ ] **Step 7: Validate Python syntax**

Run:

```bash
./venv/bin/python -m py_compile config.py main.py translator.py
```

Expected: exit code 0 and no output.

- [ ] **Step 8: Commit the application source**

Run:

```bash
git commit -m "feat: add LINE Chinese-Thai translation bot"
```

Expected: the eight staged source files are committed.

### Task 3: Install and authenticate GitHub CLI

**Files:**
- No repository files changed

- [ ] **Step 1: Install GitHub CLI from the operating system package repository**

Run:

```bash
sudo apt-get update
sudo apt-get install -y gh
```

Expected: both commands exit 0.

- [ ] **Step 2: Verify the GitHub CLI installation**

Run:

```bash
gh --version
```

Expected: exit code 0 and output beginning with `gh version`.

- [ ] **Step 3: Authenticate with private-repository and profile-update scopes**

Run in an interactive terminal:

```bash
gh auth login --hostname github.com --git-protocol https --web --scopes repo,user
```

If GitHub CLI is already authenticated for the intended account, refresh that account instead:

```bash
gh auth refresh --hostname github.com --scopes repo,user
```

Expected: the browser-backed authorization completes for the intended company account and grants both `repo` for private-repository operations and `user` for `PATCH /user` profile updates.

- [ ] **Step 4: Verify account, Git access, and OAuth scopes without exposing the token**

Run:

```bash
gh auth status --hostname github.com
gh auth status --hostname github.com 2>&1 | rg "Token scopes:.*'repo'"
gh auth status --hostname github.com 2>&1 | rg "Token scopes:.*'user'"
gh api user --jq '{login,name,bio,company,location,blog}'
```

Expected: every command exits 0; the two filtered lines confirm `repo` and `user`; and the final output identifies the intended account before any GitHub write. Do not add `--show-token`: none of these commands prints the credential.

### Task 4: Create and push the private repository

**Files:**
- Modify local Git metadata: `.git/config`

- [ ] **Step 1: Accept only an explicit HTTP 404 as proof that the target is absent**

Run:

```bash
OWNER="$(gh api user --jq '.login')"
test -n "$OWNER"
CHECK_OUTPUT="$(mktemp)"
if gh api --include --silent "repos/${OWNER}/macc-line-translate-bot" >"$CHECK_OUTPUT" 2>&1; then
  rm -f "$CHECK_OUTPUT"
  printf 'Repository already exists: %s/macc-line-translate-bot; stop.\n' "$OWNER" >&2
  exit 1
fi
HTTP_STATUS="$(awk 'toupper($1) ~ /^HTTP\// {status=$2} END {print status}' "$CHECK_OUTPUT")"
rm -f "$CHECK_OUTPUT"
if test "$HTTP_STATUS" != '404'; then
  printf 'Repository check returned HTTP %s, not 404; stop without creating anything.\n' "${HTTP_STATUS:-unknown}" >&2
  exit 1
fi
printf 'Confirmed absent: %s/macc-line-translate-bot (HTTP 404).\n' "$OWNER"
```

Expected: exit code 0 and exactly `Confirmed absent: OWNER/macc-line-translate-bot (HTTP 404).`, with `OWNER` replaced by the authenticated login. A successful lookup means the repository exists and stops the plan. Authentication, permission, rate-limit, server, and transient failures do not produce an explicit 404 and therefore also stop the plan. `gh api` sends credentials internally; the command captures only response headers and diagnostics and never prints the token.

- [ ] **Step 2: Create the private repository and push `main`**

Run:

```bash
OWNER="$(gh api user --jq '.login')"
test -n "$OWNER"
gh repo create "$OWNER/macc-line-translate-bot" --private --source=. --remote=origin --push --description "LINE bot for real-time Simplified Chinese ↔ Thai translation powered by Google Gemini."
```

Expected: GitHub creates the repository, adds `origin`, and pushes local `main`.

- [ ] **Step 3: Add approved repository topics**

Run:

```bash
gh repo edit --add-topic line-bot --add-topic translation --add-topic thai --add-topic chinese --add-topic gemini --add-topic python --add-topic flask
```

Expected: all seven topics are accepted.

### Task 5: Update the approved company profile fields

**Files:**
- No repository files changed

- [ ] **Step 1: Apply the company identity to the authenticated profile**

Run:

```bash
gh api --method PATCH user \
  -f 'name=MACC Electronics (Thailand) Co., Ltd.' \
  -f 'bio=Commercial digital signage, kiosks, LED displays, and interactive display solutions in Thailand.' \
  -f 'company=MACC Electronics (Thailand) Co., Ltd.' \
  -f 'location=Bangkok, Thailand' \
  -f 'blog=https://maccthailand.com'
```

Expected: GitHub returns the updated user document. Username, avatar, email visibility, and social links remain unchanged.

### Task 6: Verify the completed publication

**Files:**
- No files changed

- [ ] **Step 1: Verify local repository state and remote alignment**

Run:

```bash
git status --short
git remote -v
git rev-parse HEAD
git rev-parse origin/main
```

Expected: working tree output is empty, `origin` points to the new GitHub repository, and both commit hashes match.

- [ ] **Step 2: Verify sensitive files were never committed**

Run:

```bash
git log --all --name-only --pretty=format: | sort -u | rg '(^|/)(\.env|venv|__pycache__)(/|$)|\.pyc$'
```

Expected: no matches.

- [ ] **Step 3: Verify GitHub repository settings**

Run:

```bash
gh repo view --json nameWithOwner,description,visibility,url,defaultBranchRef,repositoryTopics
```

Expected: the repository is private, the default branch is `main`, the description matches the approved text, and all approved topics are present.

- [ ] **Step 4: Verify GitHub profile settings**

Run:

```bash
gh api user --jq '{login,name,bio,company,location,blog}'
```

Expected: name, bio, company, location, and blog match the approved company profile exactly.
