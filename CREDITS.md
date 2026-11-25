# Credits and licences

This repository holds build scripts and patches:

- `patches/vig8-ps4.patch`, against [sp00nznet/vig8](https://github.com/sp00nznet/vig8) at the commit in
  `patches/BASE.txt`: the PS4 app (`project/ps4/`), the code generation passes and the game fixes
  (`project/tools/`), and the code generator's function entries (`project/vig8_manifest.toml`)
- `patches/sdk-vig8.patch`, against MP3-PS4's PS4 SDK: [nx-mod/rexglue-sdk-nx](https://github.com/nx-mod/rexglue-sdk-nx)
  at the commit in `patches/BASE.txt` with [iHaiDeeZ/MP3-PS4](https://github.com/iHaiDeeZ/MP3-PS4)'s
  `patches/sdk-ps4.patch` (at the MP3-PS4 commit in `patches/BASE.txt`)
- `patches/host/`: two changes to the host build of the ReXGlue code generator (MP3-PS4's image dump, SDL without a
  display)
- `patches/mesa/`: two of ps4-kit's Mesa patches that aren't in the published kit yet
- `patches/ffmpeg/`: the PS4 configuration of FFmpeg (from MGR-PS4)
- `patches/fonts/`: the quick menu's font

`scripts/clone-vig8.sh` fetches the sources and applies the patches. The patched files keep their own licences.

| Part | Where | Licence |
|---|---|---|
| vig8 (sp00nznet): the ReXGlue recompilation of Vigilante 8 Arcade for Windows | the upstream repository; the patch adds `project/ps4/` and `project/tools/` and changes the manifest | MIT (upstream `LICENSE`) |
| [rexglue-sdk-nx](https://github.com/nx-mod/rexglue-sdk-nx) (nx-mod) on the [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk) v0.10.0 (Tom Clay), with portions from [Xenia](https://xenia.jp) (Ben Vanik and the Xenia contributors) | the SDK; MP3-PS4's patch adds the PS4 platform layer (from the MGR port) and MP3's fixes, this port's patch the changes for this game | BSD-3-Clause (the SDK's `LICENSE`) |
| The code generation passes of [mp3-nx](https://github.com/VasilkovND/mp3-nx) (VasilkovND), from gears2-nx and dantes-inferno-nx, with MP3-PS4's PS4 passes | `project/tools/`, added by the patch | GPL-3.0 (mp3-nx's `LICENSE`) |
| [FFmpeg](https://ffmpeg.org) (the XMA decoder) | the SDK's `thirdparty/FFmpeg`, from rexglue-sdk's submodule; `patches/ffmpeg/` is the PS4 configuration | LGPL-2.1-or-later (configured without GPL parts) |
| The SDK's other libraries (fmt, spdlog, toml++, Dear ImGui, xxHash, SIMDe, glslang, SPIRV-Tools, Vulkan Memory Allocator and the rest) | the SDK's `thirdparty`, from rexglue-sdk v0.10.0 (`c94f5eb`) and its submodules | their own licences, listed in rexglue-sdk's `THIRD_PARTY_NOTICES.md` |
| [Lato](https://www.latofonts.com) (Łukasz Dziedzic) | `patches/fonts/`, copied into `project/ps4/fonts/`: the quick menu's type; also the title of the README's banner | SIL Open Font License 1.1 (`patches/fonts/LICENSE-Lato.txt`) |
| [ps4-kit](https://github.com/iHaiDeeZ/ps4-kit) (iHaiDeeZ): toolchain setup, runtime, Mesa RADV for the PS4, VideoOut swapchain, crash log, profiler, packaging | linked at build time; `patches/mesa/` holds two of its Mesa patches | MIT |
| [Mesa](https://mesa3d.org) RADV | built by ps4-kit | MIT |
| [OpenOrbis](https://github.com/OpenOrbis) toolchain ([PacBrew](https://github.com/PacBrew)) | build host | GPL-3.0 (tools), the C library under its own licences |

This port's own code in the patches (the files in `project/ps4/`, `project/tools/patch_game_fixes.py`, and the
changes in the SDK) is under the licence of the folder it is in: BSD-3-Clause in the SDK, MIT in `project/ps4/` as in
the rest of vig8, GPL-3.0 in `project/tools/`. The build scripts and the rest of this repository are GPL-3.0
(`LICENSE`). `scripts/stfs-extract.py` comes from [MGR-PS4](https://github.com/iHaiDeeZ/MGR-PS4).

The game itself (code, art, sound, text) belongs to its owners. Nothing from it is in this repository: the build
reads your `default.xex` and the game's files on your own machine. The package's icon and background are drawn by
`scripts/make-icon.py` unless you put your own pictures in `sce_sys/local/`. The banner of this README is original art
drawn by `scripts/make-banner.py`.
