#!/usr/bin/env bash
# The host code generator's X11/Wayland development files, unpacked without root (apt-get download + dpkg -x), as
# the MGR port's host-deps: libx11-xcb-dev and libwayland-dev (their runtime libraries are installed already).
set -euo pipefail
D="$HOME/vig8-build/host-deps"
R="$D/root"
mkdir -p "$D/debs" "$R"
cd "$D/debs"
for p in libx11-xcb-dev libwayland-dev; do
    ls ${p}_*.deb > /dev/null 2>&1 || apt-get download "$p"
done
for d in *.deb; do dpkg -x "$d" "$R"; done
# .pc files: the unpacked prefix instead of /usr.
for pc in $(find "$R" -name '*.pc'); do
    sed -i "s|^prefix=/usr\$|prefix=$R/usr|" "$pc"
done
# The .so links point at the installed runtime libraries.
L="$R/usr/lib/x86_64-linux-gnu"
for so in "$L"/*.so; do
    [ -L "$so" ] || continue
    target="$(readlink "$so")"
    if [ ! -e "$L/$target" ] && [ -e "/usr/lib/x86_64-linux-gnu/$target" ]; then
        ln -sfn "/usr/lib/x86_64-linux-gnu/$target" "$so"
    fi
done
ls -la "$L" | head -30
export PKG_CONFIG_PATH="$L/pkgconfig:$R/usr/share/pkgconfig"
pkg-config --cflags --libs x11-xcb wayland-client
