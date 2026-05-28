# GitHub Upload Guide

## Option A: Upload using GitHub web UI

1. Create a GitHub account or sign in.
2. Click **New repository**.
3. Repository name: `cc-agent-brain`.
4. Description: `A local Wiki-first second brain system for Claude Code`.
5. Choose **Public**.
6. Do not initialize with README, license, or gitignore if you will push this local folder with Git.
7. Create repository.
8. Push local files with Git commands.

## Option B: Push with Git command line

```bash
cd cc-agent-brain
git init
git add .
git commit -m "init: local wiki-first second brain for Claude Code"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/cc-agent-brain.git
git push -u origin main
```

## Option C: Use GitHub CLI

```bash
cd cc-agent-brain
gh repo create cc-agent-brain --public --source=. --remote=origin --push
```

## After publishing

- Check README rendering.
- Check that personal files are not included.
- Add topics such as `claude-code`, `second-brain`, `wiki`, `agent`, `memory`, `local-first`.
- Create a release `v0.1.0` if everything looks correct.
