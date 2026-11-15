#!/bin/bash
# Privacy scan for this repository: run before every push and review each hit.
# usage: bash tools/privacy_scan.sh [--history]
cd "$(git rev-parse --show-toplevel)" || exit 1
PAT='[A-Za-z]:\\+Users\\+[^\\<"]+|/Users/[A-Za-z0-9._-]+|@(gmail|outlook|hotmail|yahoo|icloud)\.|ghp_[A-Za-z0-9]{20,}|github_pat_|gho_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY|xox[bp]-|DESKTOP-[A-Z0-9]{5,}|\b7656119[0-9]{10}\b'
echo "== tracked files"
git ls-files -z | xargs -0 grep -IPn "$PAT" -- 2>/dev/null | cut -c1-200
if [ "$1" = "--history" ]; then
  echo "== every file version in history"
  git rev-list --all --objects | awk 'NF>1{print $1" "$2}' | sort -u -k1,1 | while read s p; do
    git cat-file -p "$s" | grep -IPo "$PAT" | sed "s|^|$p: |"
  done | sort | uniq -c
fi
echo "== done (the regex line in this script and in release_tools/validate_release.py may match itself)"
