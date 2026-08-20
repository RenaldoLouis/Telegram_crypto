#!/bin/zsh
# launchd wrapper for the local Claude scan (main.py). Mirrors the `scan` shell
# alias but runs WITHOUT an interactive shell (launchd sets almost no env, and
# shell aliases don't exist here). Loaded by com.user.cryptoscreener.plist,
# scheduled at 09:00 / 17:00 / 22:00 local.
#
# REQUIRES at run time:
#   - VPN UP — Bybit + Telegram are geo-blocked by the local ISP, so a scan with
#     VPN down fails at the data-fetch step. There is no VPN handling here.
#   - ANTHROPIC_API_KEY in .env (loaded by python-dotenv) — this is the ONLY run
#     that calls Claude, so it feeds the Claude side of the head-to-head.
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
REPO="/Users/renaldolouis/Documents/Personal/crypto-screener"
cd "$REPO" || exit 1

echo "=== scan run $(date) ==="

# Commit any stray LOG changes first so the rebase stays clean (matches alias).
# IMPORTANT: `git add logs/` ONLY — never `git add -A`. A scan must commit its own
# data outputs (setups/briefs/hot_list/performance), NEVER source-code edits that
# happen to be in the working tree (that sweeps WIP into a "save logs" commit).
git add logs/ && git commit -q -m "scan: save logs [skip ci]" 2>/dev/null
git pull --rebase --quiet

source venv/bin/activate
python main.py
scan_status=$?

git add logs/ && git commit -q -m "scan: update logs [skip ci]" 2>/dev/null
# Race-safe push: the CI bot also pushes to master every 2h. Rebase onto any
# concurrent commit and retry rather than failing on a non-fast-forward.
for i in 1 2 3; do
  git pull --rebase --quiet && git push --quiet && break || sleep 5
done
echo "=== done (main.py exit $scan_status) ==="
