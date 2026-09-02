# GitHub Publication Design

## Objective

Publish the existing LINE Chinese–Thai translation bot to a private GitHub repository and align the authenticated GitHub account's public profile with MACC Electronics (Thailand) Co., Ltd.

## Repository

- Name: `macc-line-translate-bot`
- Visibility: private
- Default branch: `main`
- Description: `LINE bot for real-time Simplified Chinese ↔ Thai translation powered by Google Gemini.`
- Topics: `line-bot`, `translation`, `thai`, `chinese`, `gemini`, `python`, `flask`

The existing project files will be committed without changing application behavior. The local `.gitignore` must exclude `.env`, virtual environments, Python bytecode, caches, logs, and operating-system metadata. Before any remote push, the staged and committed file lists will be checked to confirm that credentials and generated files are absent.

## GitHub Profile

- Display name: `MACC Electronics (Thailand) Co., Ltd.`
- Bio: `Commercial digital signage, kiosks, LED displays, and interactive display solutions in Thailand.`
- Company: `MACC Electronics (Thailand) Co., Ltd.`
- Location: `Bangkok, Thailand`
- Website: `https://maccthailand.com`

The profile location uses the concise city and country form appropriate for GitHub. The company's full street address remains available on the official website.

## Authentication and Publication Flow

GitHub CLI is not currently installed and no Git identity is configured. Install GitHub CLI from the operating system package source, then authenticate through GitHub's browser authorization flow using the account already signed into the local browser. Configure this repository's Git author as the approved company name and the public company contact email listed on the official website.

After authentication:

1. Inspect the authenticated account before making changes.
2. Commit the reviewed project files on `main`.
3. Create the private repository and push `main`.
4. Set the repository description and topics.
5. Update only the approved GitHub profile fields listed above.
6. Verify repository visibility, branch contents, remote URL, topics, and resulting profile fields through the GitHub API.

## Failure Handling

- Stop before pushing if `.env`, credentials, caches, or `venv/` appear in the tracked-file list.
- Do not overwrite an existing repository with the same name. If the name is already taken, pause and report the conflict.
- Do not change the GitHub username, avatar, public email visibility, social links, or other profile settings.
- If browser authorization requires direct user interaction, present the one-time code and wait for authorization before continuing.
- If profile or repository updates partially fail, report precisely what succeeded and retry only the failed operation.

## Verification

- Run Python compilation checks for the application modules.
- Confirm the Git working tree is clean after committing.
- Confirm ignored secrets and generated directories are not tracked.
- Confirm the GitHub repository is private and `main` matches the local commit.
- Read back the repository metadata, topics, and account profile fields from GitHub.
