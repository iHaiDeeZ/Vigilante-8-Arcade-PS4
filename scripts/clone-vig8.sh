#!/usr/bin/env bash
# Fetch the sources the PS4 build needs into ~/vig8-build/src (run in WSL), at the commits in patches/BASE.txt:
#   src/vig8          sp00nznet/vig8, branch ps4, with patches/vig8-ps4.patch (project/ps4, project/tools, manifest)
#   src/sdk           nx-mod/rexglue-sdk-nx with iHaiDeeZ/MP3-PS4's patches/sdk-ps4.patch (MP3's PS4 SDK, committed),
#                     branch vig8 with patches/sdk-vig8.patch
#   src/rexglue-sdk   rexglue/rexglue-sdk v0.10.0: the third-party sources sdk/ does not carry, and the tree of the
#                     host code generator (scripts/build-vig8.sh host); ~/mp3-build/src/rexglue-sdk is used when there
# Re-running keeps existing checkouts (VIG8_SOURCE_RESET=1 starts vig8 and sdk over).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
S="$HOME/vig8-build/src"
base() { awk -v k="$1" '$1 == k { print $2 }' "$HERE/patches/BASE.txt"; }
commit() { git -C "$1" add -A && git -C "$1" -c user.name=vig8 -c user.email=vig8@localhost commit -q -m "$2"; }
mkdir -p "$S" "$HOME/vig8-build/logs"
ln -sfn "$HERE" "$HOME/vig8-build/proj"

if [ "${VIG8_SOURCE_RESET:-0}" = 1 ]; then rm -rf "$S/vig8" "$S/sdk"; fi

if [ ! -e "$S/rexglue-sdk" ]; then
    if [ -d "$HOME/mp3-build/src/rexglue-sdk/.git" ] \
        && [ "$(git -C "$HOME/mp3-build/src/rexglue-sdk" rev-parse HEAD)" = "$(base rexglue-sdk)" ]; then
        ln -s "$HOME/mp3-build/src/rexglue-sdk" "$S/rexglue-sdk"
    else
        git clone -q --recursive https://github.com/rexglue/rexglue-sdk "$S/rexglue-sdk"
        git -C "$S/rexglue-sdk" checkout -q "$(base rexglue-sdk)"
        git -C "$S/rexglue-sdk" submodule update -q --init --recursive
    fi
fi

if [ ! -d "$S/sdk/.git" ]; then
    git clone -q https://github.com/nx-mod/rexglue-sdk-nx "$S/sdk"
    git -C "$S/sdk" checkout -q -b ps4 "$(base rexglue-sdk-nx)"
    # MP3's PS4 SDK: the MP3 port's patch at the pinned commit (the local checkout's copy when it is that commit).
    MP3_PATCH="$S/sdk-ps4.patch"
    if [ -f "$HERE/../MP3/patches/sdk-ps4.patch" ] \
        && [ "$(git -C "$HERE/../MP3" rev-parse HEAD 2>/dev/null)" = "$(base MP3-PS4)" ]; then
        cp "$HERE/../MP3/patches/sdk-ps4.patch" "$MP3_PATCH"
    else
        curl -fsSL "https://raw.githubusercontent.com/iHaiDeeZ/MP3-PS4/$(base MP3-PS4)/patches/sdk-ps4.patch" -o "$MP3_PATCH"
    fi
    git -C "$S/sdk" apply --whitespace=nowarn "$MP3_PATCH"
    commit "$S/sdk" "PS4 port (MP3-PS4)"
    git -C "$S/sdk" checkout -q -b vig8
    git -C "$S/sdk" apply --whitespace=nowarn "$HERE/patches/sdk-vig8.patch"
fi

if [ ! -d "$S/vig8/.git" ]; then
    git clone -q https://github.com/sp00nznet/vig8 "$S/vig8"
    git -C "$S/vig8" checkout -q -b ps4 "$(base vig8)"
    git -C "$S/vig8" apply --whitespace=nowarn "$HERE/patches/vig8-ps4.patch"
    # The quick menu's fonts (Lato, SIL Open Font License), kept beside the patches.
    mkdir -p "$S/vig8/project/ps4/fonts"
    cp "$HERE/patches/fonts/"* "$S/vig8/project/ps4/fonts/"
fi
echo "sources ready in $S"
