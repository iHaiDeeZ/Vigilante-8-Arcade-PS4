#!/usr/bin/env bash
# Build Vigilante 8 Arcade (Xbox 360 XBLA, title 584108A8) for the PS4 (ps4-kit, x86-64 Jaguar). Run in WSL:
#   scripts/build-vig8.sh host       the host code generator: rexglue-sdk v0.10.0 with MP3's dump-image patch, SDL3
#                                    with dummy drivers (no X11/Wayland packages on WSL)
#   scripts/build-vig8.sh codegen    the game's C++ from your default.xex, then the PS4 passes
#   scripts/build-vig8.sh app        the eboot (game code + SDK + its Xenos GPU on Vulkan + RADV)
#   scripts/build-vig8.sh pkg        out/V8A-vXX.YY.pkg (VIG8_VERSION=00.01): eboot, your game and the DLC inside
# The sources come from scripts/clone-vig8.sh.
#
# Port of sp00nznet/vig8 (the Windows x86-64 ReXGlue recompilation) done the MGR/MP3 way: the game's PowerPC code
# recompiled to C++ by ReXGlue v0.10.0's code generator and built for the Jaguar with ps4-kit's clang 21; the runtime
# is MP3's PS4 SDK (rexglue-sdk-nx with the MGR port's PS4 layer and MP3's fixes, iHaiDeeZ/MP3-PS4); the game's
# command ring drawn by the SDK's Xenia-derived Xenos emulation on its Vulkan back end, on the kit's RADV.
#
#   ~/vig8-build/src/vig8          sp00nznet/vig8, branch ps4 (project/ps4: the PS4 app; project/tools: the passes)
#   ~/vig8-build/src/sdk           the PS4 SDK, branch vig8
#   ~/vig8-build/src/rexglue-sdk   rexglue-sdk v0.10.0: third-party sources and the host code generator's tree
#   ~/vig8-build/game              your unpacked XBLA package (default.xex, data/ ...)
#   ~/vig8-build/dlc               your DLC packages, unpacked (one folder per package, named as the package file)
set -euo pipefail
source "$HOME/ps4-kit/toolchain/env.sh"
V="$HOME/vig8-build"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${VIG8_SRC:-$V/src/vig8}"
SDK="${VIG8_SDK:-$V/src/sdk}"
UP="${VIG8_REXGLUE_SDK:-$V/src/rexglue-sdk}"
GAME="${VIG8_GAME:-$V/game}"
CG="${VIG8_CODEGEN:-$V/codegen}"
REXGLUE="$V/src/rexglue-host/out/linux-amd64/rexglue"
TOOLS="$SRC/project/tools"
mkdir -p "$V/logs"

if [ ! -f "$SDK/thirdparty/fmt/CMakeLists.txt" ]; then
    rsync -a --ignore-existing --exclude=.git "$UP/thirdparty/" "$SDK/thirdparty/"
fi
# The PS4's FFmpeg configuration (from the MGR port): config.h picks config_ps4_x86_64.h for __PS4__.
for f in config.h config_ps4_x86_64.h; do
    cmp -s "$HERE/patches/ffmpeg/$f" "$SDK/thirdparty/FFmpeg/$f" || cp "$HERE/patches/ffmpeg/$f" "$SDK/thirdparty/FFmpeg/$f"
done

case "${1:-}" in
host)
    H="$V/src/rexglue-host"
    if [ ! -d "$H" ]; then
        # Without the repository's own .git (1.2 GB); the submodules' .git files stay (the SDK's CMake checks them).
        rsync -a --exclude=/.git "$UP/" "$H/"
        for p in "$HERE"/patches/host/*.patch; do
            (cd "$H" && patch -p1 --forward --quiet < "$p")
        done
    fi
    # The SDK's ui library wants x11-xcb and wayland-client (pkg-config) even with SDL headless: libx11-xcb-dev and
    # libwayland-dev, installed or unpacked into host-deps/root (scripts/host-deps.sh, no root needed).
    HD="$V/host-deps/root"
    [ -f "$HD/usr/lib/x86_64-linux-gnu/pkgconfig/x11-xcb.pc" ] || bash "$HERE/scripts/host-deps.sh"
    export PKG_CONFIG_PATH="$HD/usr/lib/x86_64-linux-gnu/pkgconfig:$HD/usr/share/pkgconfig"
    cmake -S "$H" -B "$H/out/host" -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang-21 -DCMAKE_CXX_COMPILER=clang++-21 \
        -DCMAKE_C_FLAGS=-march=x86-64-v2 -DCMAKE_CXX_FLAGS=-march=x86-64-v2 \
        -DCMAKE_SHARED_LINKER_FLAGS="-L$HD/usr/lib/x86_64-linux-gnu" -DCMAKE_EXE_LINKER_FLAGS="-L$HD/usr/lib/x86_64-linux-gnu" \
        -DREXGLUE_USE_VULKAN=ON -DREXGLUE_ENABLE_TRACY=OFF -DREXGLUE_SDL_HEADLESS=ON \
        > "$V/logs/configure-host.log" 2>&1 || { tail -40 "$V/logs/configure-host.log"; exit 1; }
    ninja -C "$H/out/host" rexglue > "$V/logs/build-host.log" 2>&1 \
        || { grep -E "error:|FAILED" "$V/logs/build-host.log" | head -40; exit 1; }
    echo "host built: $REXGLUE"
    ;;
codegen)
    [ -x "$REXGLUE" ] || { echo "run '$0 host' first" >&2; exit 1; }
    [ -f "$GAME/default.xex" ] || { echo "no $GAME/default.xex (unpack your XBLA package there)" >&2; exit 1; }
    mkdir -p "$CG/game"
    cmp -s "$GAME/default.xex" "$CG/game/default.xex" || cp "$GAME/default.xex" "$CG/game/default.xex"
    # vig8's manifest (its function entries) with this layout's paths.
    sed -e 's|"\.\./extracted/default\.xex"|"game/default.xex"|' -e 's|"\.\./extracted"|"game"|' \
        -e 's|"\.\./generated/default"|"generated/default"|' "$SRC/project/vig8_manifest.toml" > "$CG/vig8_manifest.toml"
    grep -q '"game/default.xex"' "$CG/vig8_manifest.toml" || { echo "manifest paths not rewritten" >&2; exit 1; }
    # A name the SDK already defines as __imp__<name> would replace the game's function with that stub.
    for n in $(sed -n 's/.*name = "\([A-Za-z_0-9]*\)".*/\1/p' "$CG/vig8_manifest.toml"); do
        case "$n" in sub_*) continue ;; esac
        if grep -rqE "__imp__$n\b" "$SDK/src" "$SDK/include"; then
            echo "codegen: the SDK already defines __imp__$n; rename it in the manifest" >&2; exit 1
        fi
    done
    # Generated and patched in a staging folder, then only the files whose text changed are copied over generated/
    # (the others keep their dates, so Ninja rebuilds only those units).
    ST="$CG/staging"
    rm -rf "$ST"
    mkdir -p "$ST"
    cp "$CG/vig8_manifest.toml" "$ST/"
    ln -s ../game "$ST/game"
    echo "== codegen"
    (cd "$ST" && REX_DUMP_IMAGE="$CG/image.bin" "$REXGLUE" --force codegen vig8_manifest.toml > "$CG/codegen.log" 2>&1) || {
        tail -20 "$CG/codegen.log"; exit 1; }
    GEN="generated/default"
    # The codegen's traps for branches it could not tie up, as gotos and tail calls (MP3's pass, from ds3-nx).
    (cd "$ST" && python3 -I "$TOOLS/patch_branch_traps.py" $GEN/*.cpp) > "$CG/patch_branch_traps.log" || {
        cat "$CG/patch_branch_traps.log"; exit 1; }
    head -1 "$CG/patch_branch_traps.log"
    # vmaddfp/vnmsubfp as REX_VMADDFP/REX_VNMSUBFP (unfused on the Jaguar by the PS4 PCH), the fmadd family as REX_FMA:
    # the Jaguar has no FMA unit, std::fma would be libm's software one.
    (cd "$ST" && python3 -I "$TOOLS/patch_vmx_exact.py" $GEN/vig8_recomp.*.cpp) > "$CG/patch_vmx_exact.log"
    tail -1 "$CG/patch_vmx_exact.log"
    (cd "$ST" && python3 -I "$TOOLS/ps4_unfused_fma.py" $GEN/vig8_recomp.*.cpp) > "$CG/ps4_unfused_fma.log"
    tail -1 "$CG/ps4_unfused_fma.log"
    # Guest stack accesses without volatile (REX_SLOAD/REX_SSTORE in the PCH).
    (cd "$ST" && python3 -I "$TOOLS/patch_stack_access.py" $GEN/*.cpp) > "$CG/patch_stack_access.log"
    tail -1 "$CG/patch_stack_access.log"
    # The converted code's own speed (v00.06; MP3-PS4's passes, from gears2-nx and dantes-inferno-nx, GPL-3.0; MP3's
    # mp3/CPU_OPTIMIZATION.md explains them), in MP3's order:
    #   patch_inline_calls.py  same-file calls to functions no hook replaces call the body; the register save/restore
    #                          helpers (__savegprlr_N ...) become always-inline copies (vig8_inline_helpers.h)
    #   patch_local_regs.py    every guest register in a host local, ctx exact only at calls and returns, for the
    #                          registers a callee or caller can see (LOCALREGS=0 skips it)
    #   patch_phys_base.py     register + displacement accesses take the 0xE0000000 heap's offset from their base
    #                          register, not from every address (the game's 0xE0000000 constants are region masks)
    # The functions the PS4 sources name (REX_EXTERN hooks) keep their calls through the alias.
    HOOK_DIRS="$SRC/project/ps4 $SDK/src $SDK/include"
    (cd "$ST" && python3 -I "$TOOLS/patch_inline_calls.py" $HOOK_DIRS -- $GEN/vig8_recomp.*.cpp) \
        > "$CG/patch_inline_calls.log"
    tail -1 "$CG/patch_inline_calls.log" | cut -c1-200
    if [ "${LOCALREGS:-1}" = 1 ]; then
        (cd "$ST" && python3 -I "$TOOLS/patch_local_regs.py" $GEN/vig8_inline_helpers.h $HOOK_DIRS \
            -- $GEN/vig8_recomp.*.cpp) > "$CG/patch_local_regs.log" 2>&1 || { tail -20 "$CG/patch_local_regs.log"; exit 1; }
        tail -1 "$CG/patch_local_regs.log"
    fi
    (cd "$ST" && python3 -I "$TOOLS/patch_phys_base.py" $GEN/vig8_recomp.*.cpp) > "$CG/patch_phys_base.log"
    tail -1 "$CG/patch_phys_base.log"
    # Fixes to the game's own code (v00.08: the road patch subdivision's work stack, the v00.07 crash; v00.10: the
    # 3D scene's MSAA samples as the vig8_antialiasing setting - one pass instead of 4 tiles). A fix whose
    # anchor is missing stops the build.
    (cd "$ST" && python3 -I "$TOOLS/patch_game_fixes.py" $GEN/vig8_recomp.*.cpp) > "$CG/patch_game_fixes.log" 2>&1 \
        || { cat "$CG/patch_game_fixes.log"; exit 1; }
    tail -1 "$CG/patch_game_fixes.log"
    python3 -I - "$ST/$GEN" "$CG/$GEN" <<'PY'
import filecmp, os, shutil, sys
new, old = sys.argv[1:]
os.makedirs(old, exist_ok=True)
names = set(os.listdir(new))
changed = 0
for n in sorted(names):
    a, b = os.path.join(new, n), os.path.join(old, n)
    if not os.path.isfile(b) or not filecmp.cmp(a, b, shallow=False):
        shutil.copy2(a, b)
        changed += 1
for n in set(os.listdir(old)) - names:
    os.remove(os.path.join(old, n))
print(f"generated/default: {changed} of {len(names)} files changed")
PY
    rm -rf "$ST"
    grep -E "Codegen summary|functions|error" "$CG/codegen.log" | tail -5 || true
    echo "codegen: $(ls "$CG"/generated/default/*.cpp | wc -l) files in $CG/generated/default, image $CG/image.bin"
    ;;
app)
    [ -f "$CG/generated/default/sources.cmake" ] || { echo "run '$0 codegen' first" >&2; exit 1; }
    B="${VIG8_APP_BUILD:-$V/build-app}"
    echo "== configure"
    ps4_cmake -S "$SRC/project/ps4" -B "$B" -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PROJECT_vig8_INCLUDE="$PS4_KIT/ps4-kit.cmake" -DPS4_KIT_NETFS=OFF \
        -DREXSDK_DIR="$SDK" -DVIG8_CODEGEN_DIR="$CG" -DREXGLUE_PLATFORM_PS4=ON -DREXGLUE_BUILD_HOST_TOOLS=OFF \
        -DREXGLUE_USE_VULKAN=ON -DREXGLUE_ENABLE_TRACY=OFF -DREXGLUE_BUILD_TESTS=OFF \
        -DVIG8_VERSION="${VIG8_VERSION:-00.00}" \
        > "$V/logs/configure-app.log" 2>&1 || { tail -40 "$V/logs/configure-app.log"; exit 1; }
    # Each generated unit takes ~1.5 GB of RAM to compile (the MGR port's measure).
    mem_mb=$(( $(awk '/^MemAvailable:/ {print $2}' /proc/meminfo) / 1024 ))
    JOBS=$(( mem_mb / 1500 )); [ "$JOBS" -lt 1 ] && JOBS=1; [ "$JOBS" -gt "$(nproc)" ] && JOBS=$(nproc)
    echo "== build (${VIG8_TARGETS:-vig8_eboot}, -j$JOBS)"
    ninja -C "$B" -k 0 -j"$JOBS" ${VIG8_TARGETS:-vig8_eboot} > "$V/logs/build-app.log" 2>&1 \
        || { grep -E "error:|FAILED|undefined symbol|missing module" "$V/logs/build-app.log" | head -80; exit 1; }
    echo "app built"
    ;;
pkg)
    # out/V8A-vXX.YY.pkg: the eboot, your unpacked game as game/ and your DLC as content/ (the SDK's installed-content
    # layout, read from /app0/content). Such a package holds your game: it goes to your own console and nowhere else.
    VERSION="${VIG8_VERSION:-00.00}"
    B="${VIG8_APP_BUILD:-$V/build-app}"
    EBOOT="$B/vig8_eboot/eboot.bin"
    [ -f "$EBOOT" ] || { echo "no $EBOOT: run '$0 app' first" >&2; exit 1; }
    [ -f "$GAME/default.xex" ] || { echo "no $GAME/default.xex" >&2; exit 1; }
    STAGE="$V/stage"
    rm -rf "$STAGE"
    mkdir -p "$STAGE/sce_sys" "$STAGE/game"
    cp "$EBOOT" "$STAGE/eboot.bin"
    # sce_sys/local/ (your own pictures, game art: kept out of the repository) before sce_sys/ (original art).
    for f in icon0.png pic1.png; do
        if [ -f "$HERE/sce_sys/local/$f" ]; then
            cp "$HERE/sce_sys/local/$f" "$STAGE/sce_sys/"
        elif [ -f "$HERE/sce_sys/$f" ]; then
            cp "$HERE/sce_sys/$f" "$STAGE/sce_sys/"
        fi
    done
    [ -f "$STAGE/sce_sys/icon0.png" ] || { echo "no sce_sys/icon0.png in $HERE" >&2; exit 1; }
    for entry in "$GAME"/*; do
        case "$(basename "$entry")" in .extracted) continue ;; esac
        cp -al "$entry" "$STAGE/game/" 2>/dev/null || cp -a "$entry" "$STAGE/game/"
    done
    # The DLC: unpacked in VIG8_DLC, its package files (their headers) in VIG8_DLC_PACKAGES - your console's
    # Content/0000000000000000/584108A8/00000002, copied into this folder (kept out of the repository).
    DLC="${VIG8_DLC:-$V/dlc}"
    DLC_PACKAGES="${VIG8_DLC_PACKAGES:-$HERE/584108A8/00000002}"
    if [ -n "$(ls -A "$DLC" 2>/dev/null)" ]; then
        python3 -I "$HERE/scripts/dlc-layout.py" "$DLC_PACKAGES" "$DLC" "$STAGE/content"
    else
        echo "warning: no DLC in $DLC: the package has the base game only" >&2
    fi
    echo "in the package: $(cd "$STAGE" && du -sh game content 2>/dev/null | tr '\t\n' '  ')"
    PKG="$(bash "$PS4_KIT/scripts/make-pkg.sh" "$STAGE" VIGA00001 "Vigilante 8 Arcade" "$VERSION" V8A "$PSB/out" | tail -1)"
    mkdir -p "$HERE/out" "$V/oelf"
    cp "$PKG" "$HERE/out/V8A-v$VERSION.pkg"
    cp "$B/vig8" "$V/oelf/v$VERSION.elf" 2>/dev/null || true
    ls -la "$HERE/out/V8A-v$VERSION.pkg"
    ;;
*)
    echo "usage: $0 host|codegen|app|pkg" >&2
    exit 2
    ;;
esac
