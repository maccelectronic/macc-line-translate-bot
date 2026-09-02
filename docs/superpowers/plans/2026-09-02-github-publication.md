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
rg -n 'TBD|TODO|implement later|fill in details' docs/superpowers/plans/2026-09-02-github-publication.md
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

- [ ] **Step 4: Check staged content for common live-secret assignments**

Run:

```bash
git diff --cached -- . ':!*.md' | rg 'LINE_CHANNEL_ACCESS_TOKEN=[^y]|LINE_CHANNEL_SECRET=[^y]|GEMINI_API_KEY=[^y]|AIza[0-9A-Za-z_-]{20,}'
```

Expected: no matches. The `.env.example` values remain obvious placeholders ending in `_here`.

- [ ] **Step 5: Validate Python syntax**

Run:

```bash
./venv/bin/python -m py_compile config.py main.py translator.py
```

Expected: exit code 0 and no output.

- [ ] **Step 6: Commit the application source**

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

Expected: `gh --version` reports an installed version.

- [ ] **Step 2: Authenticate using the existing browser session**

Run in an interactive terminal:

```bash
gh auth login --hostname github.com --git-protocol https --web
```

Expected: the browser-backed device authorization completes for the intended company account.

- [ ] **Step 3: Verify account and Git access configuration**

Run:

```bash
gh auth status
gh api user --jq '{login,name,bio,company,location,blog}'
```

Expected: authentication is active and the output identifies the intended account before any GitHub write.

### Task 4: Create and push the private repository

**Files:**
- Modify local Git metadata: `.git/config`

- [ ] **Step 1: Confirm the target repository does not already exist**

Run:

```bash
gh repo view macc-line-translate-bot --json nameWithOwner,visibility
```

Expected: a not-found response. If it exists, stop without changing it.

- [ ] **Step 2: Create the private repository and push `main`**

Run:

```bash
gh repo create macc-line-translate-bot --private --source=. --remote=origin --push --description "LINE bot for real-time Simplified Chinese ↔ Thai translation powered by Google Gemini."
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
