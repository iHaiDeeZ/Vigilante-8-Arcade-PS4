#!/usr/bin/env bash
# Export the PS4 port's changes from the WSL checkouts into patches/ (run in WSL):
#   patches/vig8-ps4.patch   ~/vig8-build/src/vig8 against BASE.txt's vig8 commit (project/ps4, project/tools, the
#                            manifest's entries)
#   patches/sdk-vig8.patch   ~/vig8-build/src/sdk against MP3's PS4 SDK (rexglue-sdk-nx at BASE.txt's commit with
#                            MP3-PS4's patches/sdk-ps4.patch applied: the clone's HEAD)
# Neither checkout's index is touched (a temporary index each), nothing is committed. The game's files and what is made
# from them (generated code, image.bin) live outside both trees.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
V="$HOME/vig8-build"
SRC="${VIG8_SRC:-$V/src/vig8}"
SDK="${VIG8_SDK:-$V/src/sdk}"
base() { awk -v k="$1" '$1 == k { print $2 }' "$HERE/patches/BASE.txt"; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export GIT_INDEX_FILE="$TMP/vig8-index"
git -C "$SRC" read-tree "$(base vig8)"
# Python's caches go first (the codegen passes import each other; naming an ignored path in the pathspec makes git add
# fail). The quick menu's fonts (project/ps4/fonts, Lato, OFL) are kept as files in patches/fonts, not in the patch.
find "$SRC/project" -name __pycache__ -type d -prune -exec rm -rf {} +
git -C "$SRC" add -A -- . ':(exclude)project/ps4/fonts'
git -C "$SRC" diff --cached --binary "$(base vig8)" > "$HERE/patches/vig8-ps4.patch"
mkdir -p "$HERE/patches/fonts"
cp "$SRC/project/ps4/fonts/"* "$HERE/patches/fonts/"

export GIT_INDEX_FILE="$TMP/sdk-index"
git -C "$SDK" read-tree HEAD
# thirdparty/ is left out: build-vig8.sh fills it from rexglue-sdk v0.10.0 (and patches/ffmpeg), as MP3's build does.
git -C "$SDK" add -A -- . ':(exclude)thirdparty'
git -C "$SDK" diff --cached --binary HEAD -- . ':(exclude)thirdparty' > "$HERE/patches/sdk-vig8.patch"
unset GIT_INDEX_FILE

for p in vig8-ps4 sdk-vig8; do
    echo "patches/$p.patch: $(grep -c '^diff --git' "$HERE/patches/$p.patch") files, $(du -h "$HERE/patches/$p.patch" | cut -f1)"
done
