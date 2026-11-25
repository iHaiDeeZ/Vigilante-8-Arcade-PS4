# Development notes

How this port is put together, what it changes, and what was found on the way. The build steps for players are in
the [README](../README.md).

## The game

| | |
|---|---|
| Base game | Xbox Live Arcade package `584108A8/000D0000/AB5401DD66BB4F43B9668C307DB47F449324963E58` (LIVE, 123.8 MB): 59 files, 118 MB unpacked. `default.xex` SHA-1 `b6e91b2c4563ce04699570dfe168220f148c0968` |
| DLC | `584108A8/00000002/58E81BC6F6A66C5F496295026302CB2183EE135E58` (LIVE, "High Octane Pack", 43.4 MB): `Config.ib`, `Garage.ibz`, `GroundHog.ibz`, `Strider.ibz`, `StuntTrack.ibz`, `TowMaster.ibz` |
| Code | 0x82090000-0x8238D8F8, about 3 MB of PowerPC and 8,000 functions (XDK libraries included: the D3D runtime is in 0x82131000-0x82152000) |

The packages are unpacked with `scripts/stfs-extract.py`.

## The route

| Part | PS4 |
|---|---|
| Code generator | ReXGlue **v0.10.0**, built for the host by `scripts/build-vig8.sh host` (rexglue-sdk at `c94f5eb` with `patches/host/`: an image dump for disassembly, SDL without a display; X11/Wayland development files unpacked by `scripts/host-deps.sh`, no root needed). vig8's manifest (`project/vig8_manifest.toml`, 22 function entries) with this layout's paths: 2 s, 60 recompiled units (62 MB), no traps |
| Passes (`project/tools`, from mp3-nx and MP3-PS4, GPL-3.0) | `patch_branch_traps.py`, `patch_vmx_exact.py` (1,013 vmaddfp, 9 vnmsubfp), `ps4_unfused_fma.py` (985 `std::fma` as a multiply and an add: the Jaguar has no FMA unit), `patch_stack_access.py` (69,087 guest stack accesses without volatile), then the speed passes: `patch_inline_calls.py` (7,202 helper calls inlined), `patch_local_regs.py` (guest registers in C++ locals in 8,061 functions; `LOCALREGS=0` skips it), `patch_phys_base.py`; last, `patch_game_fixes.py` (below) |
| PCH | `project/tools/make_ps4_pch.py`: per-thread interrupt locks, stack accesses, the physical window's host offset for the PS4, unfused VMADDFP/FMA |
| Runtime | MP3-PS4's PS4 SDK (rexglue-sdk-nx `f961303` + MP3-PS4's `patches/sdk-ps4.patch`: the MGR port's PS4 layer, the thread layout, the Xenos Vulkan fixes), with `patches/sdk-vig8.patch` |
| GPU | the SDK's Xenia-derived Xenos command processor on its Vulkan back end, on ps4-kit's RADV |
| App | `project/ps4` in the vig8 tree: `vig8_ps4_app.h` (paths, defaults), `vig8_ps4.cpp` (`/data/V8A`, settings, frame log, freeze report), `vig8_ps4_game.cpp` (overrides of game functions), `vig8_ps4_menu.cpp` (the quick menu), `vig8_ps4_achievements.cpp` |
| Package | title `VIGA00001`, data `/data/V8A`, `out/V8A-vXX.YY.pkg` = eboot + `game/` + `content/` (the DLC in the SDK's installed-content layout, `scripts/dlc-layout.py`, read from `/app0/content`) |

`scripts/clone-vig8.sh` makes the trees in `~/vig8-build/src` from GitHub and `patches/` (the commits in
`patches/BASE.txt`); `scripts/save-patch.sh` exports the two patches again from those trees with temporary indexes
(nothing is committed there). The game's files and everything made from them (the generated C++, `image.bin`, the
packages) stay outside this repository.

The eboot links ps4-kit's Mesa, which must have Mesa patches **0033** (the flight recorder keeps 32 submissions and
every shader's code) and **0034** (the tessellation factor ring, below): `patches/mesa/`, until the published kit has
them.

## Changes to the SDK (`patches/sdk-vig8.patch`)

- The Vision camera API built (`xboxkrnl_usbcam.cpp`: the game imports it), empty indirect buffers skipped, no
  `Reset()` of the image heap when the XEX is read (the three from sp00nznet's SDK fork).
- `content_marketplace_root`: DLC packages and headers under their own root (`/app0/content` on the PS4); saves stay in
  the content root. `ContentManager::ListContent` compares with `X_ERROR_SUCCESS` (a package without a header was
  listed uninitialised).
- `xboxkrnl::SetGuestSwapHook`, called at each VdSwap (the app's frame counter and freeze report);
  `XamShowAchievementsUI` with a hook (the game's Achievements item opens the quick menu's list).
- **Tessellation helper shaders** (`pipeline_cache.cpp`): their system constants at set 1 (they read set 0, the
  shared memory, so every adaptive factor came out 0 and every road patch was culled), the factors as
  `uintBitsToFloat`, the 8-in-16 swap only for k8in16.
- Command processor: the read pointer written back when an indirect buffer is fetched (`gpu_rptr_at_ib_fetch`; the
  game spun for ring space until a whole buffer had run), WAIT_REG_MEM polled every 100 us instead of 1 ms naps,
  a `[wait]` line saying what the waits are for.
- **`vblank_at_gpu_wait`** (`graphics_system.cpp`, live): each frame the game waits for a flag its vblank interrupt
  clears. A wait that hasn't matched asks for the coming guest vblank at once; the vsync thread fires it and skips
  its turn on the 60 Hz clock, so there is still one vblank each 1/60 s and only the phase moves. Worth 8-10 ms a
  frame.
- Per-draw work of the command processor: an IM_LOAD cache by guest address (the microcode compared before reuse),
  constant writes compared and stored four dwords at a time, the stage's last texture set tried before hashing,
  `gpu_rt_update_skip` (the render target update skipped when its registers equal the last one's), a sampler
  parameter memo and an MRU in front of the sampler map, power-of-two bucket counts for the hot maps, counters
  without locked instructions and part timers sampled one draw in 16.
- Measurements: `[cp]`, `[cpt]`, `[cpt2]`, `[cpt3]` and `[cp2]` lines every 10 s (draws, resolves, where the
  command processor's time goes, same-state draws, occlusion and VIZ queries, screen extent events, predicated
  packets left out), the GPU census (`rex_gpu_census_start`: every draw's render targets, textures and shaders for a
  few frames), `gpu_commands_core_cycle` (a test: the command processor moves to the next listed core after each
  stats line).
- `rex_gpu_set_swap_post_effect`: the FXAA setting, live.

## Fixes to the game's code (`project/tools/patch_game_fixes.py`)

The pass edits the generated C++ after the other passes. Each fix names its function and replaces exact pieces of
generated code; a missing anchor stops the build.

**The road patch subdivision.** `sub_8211F3B8` tests a ray against a curved road patch by subdividing it, with an
explicit work stack of 32 entries of 256 bytes at `r1+1392` in its 9,840-byte frame, and pushes a sub-patch
(`0x8211FB04`) while its projected extent is above a threshold, with no depth limit. An infinite or enormous extent
subdivided endlessly: about 110 entries, through the callers' frames to the thread's stack top (a write to guest
`0x70250000`, twenty minutes into a race). The fix pushes only while the next entry fits; a full stack leaves the
sub-patch out and logs `[fix] road patch subdivision`.

**The 3D scene's anti-aliasing.** The scene renderer `sub_820BE790` (per view, every frame) calls
`sub_82130D00(renderer, 4)`, which sets the MSAA mode every scene render target is created with (the global
`0x82482D90`), then `sub_82130D28(rects, 16, 8, 4, width, height, 0, 0)`, which halves the longer side until a
piece fits the 2048 EDRAM tiles (at 4x: `ceil(w/40) * ceil(h/8) * 8/4` tiles). At 1280x720 that is four quadrants
(640x384 and 640x336). With more than one piece, `sub_82130EA0` stores them on the renderer and its SetRenderTarget
wrapper starts the D3D runtime's **predicated tiling**:

- BeginTiling `sub_82140FD0` / EndTiling `sub_82141350`. While tiling, the runtime's draw functions (`sub_82134308`
  and its three siblings) emit, for every draw, `SET_BIN_MASK_LO 0xFFFFFFFF` (its address kept in a list), the
  predicated draw, `SET_BIN_MASK_LO 0x80000000`, a predicated `EVENT_WRITE_EXT` that writes the draw's screen extents
  into the list, and a predicated `EVENT_WRITE`.
- EndTiling records each tile's resolves (predicated with bin mask `3 << 2*tile`) and inserts a CPU callback
  (`sub_82151978`) that hands a "tiling program" to the runtime's worker threads (`sub_821517E8`). The program
  (interpreted by `sub_82151048`) kicks the recorded scene to the GPU once per tile (opcodes `0x86`/`0x87` loop over
  the tiles, `0x81` kicks an indirect buffer) and turns the extents into bin masks (`0x89`), so later tiles skip the
  draws outside them.

The SDK writes whole-screen extents for `EVENT_WRITE_EXT`, as Xenia does, so every mask stays "all tiles" and every
scene draw ran four times through the command processor, the port's bottleneck. Real extents would need each draw's
vertex shader run on the CPU (the SDK's `DrawExtentEstimator` interprets it per vertex, made for screen-space clears;
far too slow for thousands of 3D draws), and the first tile would still run every draw. Instead the fix replaces the
two `4`s with the `vig8_antialiasing` setting (`vig8_scene_msaa_begin`, `vig8_scene_msaa_samples` in
`vig8_ps4_game.cpp`). With one sample, 1280x720 needs 1,440 EDRAM tiles, so the renderer gets one piece and takes its
no-tiling branch (`loc_820BEC98`, the path it uses at SD resolutions, with a full-size render target), where the fix
also calls `sub_82130EA0(renderer, 0, 0)` so a switch from 4x clears the old pieces. FXAA (the SDK's swap effect)
smooths the edges; `vig8_antialiasing = 2` is the original.

## History

- **v00.01-v00.03**: the system ended the app at the first race frame. A live kernel log caught a GPU page fault
  (TC0 read of `0xff0000000`); ps4-kit's flight recorder (with Mesa patch 0033's 32-submission ring) pinned it to
  the game's first tessellated draw. On the PS4 the system programs `VGT_TF_MEMORY_BASE`, `VGT_TF_RING_SIZE` and
  `VGT_HS_OFFCHIP_PARAM` and ignores an app's writes; the tessellation factor ring is at the fixed address
  `0xFF0000000` (`sceGnmGetTheTessellationFactorRingBufferBaseAddress`), where the app must map memory. Mesa patch
  **0034** maps 256 KiB there at device init and points RADV's factor ring descriptor at it (the offchip ring
  8 MiB).
- **v00.04**: plays; roads and bridge decks missing (the tessellation helpers' constants, fixed in v00.05). Races
  17-27 fps, 2,000-3,100 draws a frame.
- **v00.05**: the tessellation fixes and the quick menu. The first profile showed the game thread spinning for ring
  space while the command processor napped in WAIT_REG_MEM.
- **v00.06**: MP3-PS4's speed passes; the read pointer at indirect buffer fetch and 100 us polling; achievements. The
  command processor became the only bottleneck, with one wait a frame left: the vblank.
- **v00.07**: `vblank_at_gpu_wait` (the frame's wait fell from 7.5-10 ms to 0.6 ms). Frame time about
  5.5 ms + 12 us a draw.
- **v00.08**: the road patch subdivision fix (the v00.07 crash); command processor shortcuts (about 9 us a draw).
- **v00.09**: more per-draw work cut, measurements. The command processor on core 6 or core 2 (the game thread's CPU
  module) made no difference. The game makes no occlusion or VIZ queries.
- **v00.10**: the predicated tiling found (above); the scene drawn once (`vig8_antialiasing`, FXAA by default).

Performance is set by the draw count: every Xbox 360 draw is translated to Vulkan on one CPU core (the seventh,
alone), at about 7-9 us each in v00.09, and the game's own thread needs a few microseconds a draw too. On a PS4 Pro,
Boost Mode (2.13 GHz) is assumed.

## Reading a session

- `/data/V8A/logs/vig8_NNN.log`: `[frames]` every 10 s; the command processor's `[cp]` (draws, resolves and
  submissions a frame), `[cpt]`/`[cpt2]`/`[cpt3]` (where its time goes), `[wait]`, `[cp2]`.
- `/data/V8A/profiles/profile_N.txt`: ps4-kit's CPU profiles (addresses relative to `.text`). Name them with
  `python3 ~/ps4-kit/scripts/profile.py --top 3000 --elf ~/vig8-build/oelf/vXX.YY.elf profile_N.txt`, then sum a
  thread by function with `python3 -I scripts/agg_profile.py profile_N.named.txt "GPU Commands"` (self time: the
  converted code has no frame pointers, so inclusive times are unreliable). The numbers restart each session: check
  the profile's module range against the ELF.
- `/data/V8A/profiles/census_N.txt`: the GPU census, by draw and resolve kind.
- `/data/V8A/crash.log`: the real fault of a crash (addresses relative to `.text` = eboot address - 0x400000, for
  `llvm-symbolizer`). The kernel log shows only the later SIGSYS. The SDK's log names the guest address of an
  "Unhandled guest access violation".
- A GPU fault ends the app without a crash log: capture GoldHEN's kernel log (TCP 3232) live during the test, and
  switch on the GPU fault recorder (`/data/Crema/gpu/flight`).

`tools/` has the small scripts used to read the game's code: `ppcdis.py` (disassembly of `codegen/image.bin`, the
loaded image, with capstone), `find_pm4.py` (the PM4 packet headers the code builds), `find_off.py` (loads and stores
at given offsets), `find_calls.py` (direct callers of a function), and `cp_periods.py` (the `[cp]` lines of a log as
a table, with a fit of the frame time against the draw count).
