# SCANZ-BOT Migration Plan (Group GitHub & OpSec)

This guide outlines the steps to migrate the SCANZ-BOT to a Group/Organization GitHub repository while maintaining strict operational security (OpSec).

## 🔒 1. Operational Security (OpSec) Pre-Flight
Before pushing any code, ensures no secrets are leaked.

- [x] **Check `.gitignore`**: Verified to exclude `.env`, `venv/`, and `__pycache__/`.
- [x] **Scan for Hardcoded Secrets**: Search code for keys (e.g., specific tokens, IDs that shouldn't be public).
    - *Action*: Run `grep -r "token" .` or similar to double-check.
- [x] **Secret Management Strategy**:
    - **Production**: Use `.env` file on the server (never committed).
    - **Sharing**: Share the `.env` contents via secure password manager (1Password, Bitwarden) notes, NOT Discord/Slack.

## 🚀 2. Migration Steps

### A. Create Remote Repository
1.  Log in to the **SCANZ Organization GitHub**.
2.  Create a **New Repository**: `SCANZ-BOT`.
3.  **Visibility**: **Private** (Critical for bot security).
4.  Do *not* initialize with README/gitignore (we have them).

### B. Push Local Code
Run these commands in your local terminal:

```bash
# remove old origin if it exists
git remote remove origin 

# Add new organization remote
git remote add origin https://github.com/WeSCANZ/SCANZ-BOT.git

# Verify branch is main
git branch -M main

# Push
git push -u origin main
```

### C. Server Update
The server needs to know about the new repo to pull updates.

1.  SSH into the Home Lab server (LXC Container).
2.  Update the git remote:
    ```bash
    cd /opt/discord-bots/scanz-bot
    git remote set-url origin https://github.com/WeSCANZ/SCANZ-BOT.git
    ```
3.  **Authentication**: If the repo is Private, the server needs a **Deploy Key** or **Personal Access Token (PAT)** to pull.
    - *Recommended*: Add the server's SSH Public Key as a **Deploy Key** in the GitHub Repo Settings.

## 👥 3. Team Access & Branch Protection
1.  **Invite Members**: Add authorized devs to the Repo (Settings > Collaborators).
2.  **Branch Protection Rules** (Settings > Branches):
    - **Pattern**: `main`
    - [x] Require a pull request before merging (Prevent accidental direct pushes).
    - [x] Require approvals (1 or 2).

## 📝 Updates to Workflow
- **Developers**: Clone -> Create Branch (`feature/xyz`) -> Push -> Open PR -> Merge.
- **Webhook**: Update the GitHub Webhook settings in the new repo to point to your deployment endpoint.
