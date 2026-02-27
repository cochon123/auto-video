#!/bin/sh
set -euo pipefail

cd /home/cochon/Documents/auto-video

git add -A
git commit -m "Commit latest changes"

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin https://github.com/cochon123/auto-video.git
else
  git remote add origin https://github.com/cochon123/auto-video.git
fi

git branch -M main
git push -u origin main
