# LSFG-VK ARM64

I maintain this fork for **Armada on ARM64 handhelds**, based on [xXJSONDeruloXx/decky-lsfg-vk](https://github.com/xXJSONDeruloXx/decky-lsfg-vk) v0.12.8 (`e997a3f`). It is not an official Lossless Scaling, lsfg-vk, Armada or Decky release.

**This repository contains plugin source, not the complete private test package.** The separately licensed modified native engine and commercial DLL are not published here. Cloning this repository does not provide a ready-to-install frame-generation runtime.

## What changed

- Simplified Chinese UI, status messages and locale handling, with English retained.
- lsfg-vk 2.0 runtime/profile translation and matching DLL detection.
- ARM64 installation handling, preservation of existing profiles, and automatic replacement of stale engines/launchers when a native payload is supplied.
- Removal of obsolete 1.x presentation/HDR controls; a runtime explanation replaces them.
- Base FPS slider up to 72, propagated to both DXVK and VKD3D; zero clears inherited caps.
- Correct layer enable/disable behavior and cleanup of stale experimental environment variables.
- Armada-compatible launch wrapping and a tested launch-option normalization utility.
- Coexistence with the original plugin through owned names: `.config/lsfg-vk-arm64`, `lsfg-arm64`, `liblsfg-vk-arm64.so` and the `VK_LAYER_LSFGVK_ARM64_frame_generation` layer; legacy Flatpak extension management is no longer offered.
- Read/write failures remain visible instead of silently presenting editable default settings.
- r5 removes automatic experimental paired pacing, preserves ordinary driver caps, and upgrades r4 launchers even when the native core is identical.

The plugin is renamed to **LSFG-VK ARM64** so it can be installed alongside the original plugin without either overwriting the other; each game should use only one launcher.

## Physical-device validation

I tested the private **r5** package on a **KONKR Pocket FIT Elite — SM8750 / Snapdragon 8 Elite / Adreno 830**, running Armada ARM64. On **2026-09-11**, I confirmed that the final in-game visual test passed. This was a real physical handheld, not an emulator.

The r5 backend/launch suite passed 70 tests; its extracted private package passed 10 installation lifecycle tests. Ordinary game launch was checked after deployment. These results do not certify every game, other handhelds, or complete elimination of frametime outliers.

Experimental paired pacing remains disabled in the normal launcher. This fork does not implement adaptive frame generation, a minimum-input-FPS threshold, or NPU acceleration. See [r5 notes](docs/R5.md).

## Runtime requirements and installation boundary

- Armada ARM64 with a working Decky installation.
- A compatible lsfg-vk 2.0 ARM64 runtime, obtained and used under its own license.
- A legitimate Lossless Scaling installation and the matching `lsfg-vk.dll`. The old `Lossless.dll` is not interchangeable and must not simply be renamed.

For a locally assembled package, the installer expects the native engine at `bin/liblsfg-vk-v2-arm64.so`. This file is deliberately not tracked or downloaded by this fork. Without a supplied runtime payload, the source checkout alone cannot install the engine. Old automatic binary downloads have been removed so a build cannot silently bundle the legacy engine.

On an Armada system with the default `armada` account, the game launch entry is:

```text
/var/home/armada/lsfg-arm64 /usr/libexec/armada/armada-game-launch %command%
```

**Co-installation note:** this fork uses its own config directory (`.config/lsfg-vk-arm64`), launcher (`~/lsfg-arm64`), library (`liblsfg-vk-arm64.so`) and Vulkan layer. It can coexist with the original LSFG plugin: choose one launcher per game, and each plugin's settings and profiles stay separate.

Assemble this fork in its own Decky package directory, `LSFG-VK ARM64`, rather than the original `Decky LSFG-VK` directory. Earlier ARM64 builds used the original identity and shared files. This renamed version leaves those files and settings in place and starts with independent settings; it does not import or delete them automatically. Paste the new launch option only into games that should use this fork. The co-installation change has automated test coverage; the r5 physical-device results above do not validate simultaneous installation of the renamed version.

Use the plugin's copied launch options for a different user home. Preserve other game-specific arguments. Restart the game after changing base FPS or toggling frame generation. A setting is an upper limit, not a guarantee that the game reaches that rate.

## Development

Use the committed lockfile; no dependency version changes are required by this fork. Frontend checks use the existing TypeScript dependency. Backend tests require Python 3.11+ and Bash on Linux.

```sh
pnpm install --frozen-lockfile
pnpm test
pnpm exec tsc --noEmit
pnpm build
python3 -m unittest discover -s tests -v
```

The frontend build produces `dist/index.js`; it does not build or supply the separate native engine. No ready-to-install public release is provided by this source synchronization.

## 中文说明

这是我针对 Armada ARM64 掌机维护的适配分支，不只是汉化：还包含 2.0 配置适配、安装升级、限帧、开关及启动链修复。

r5 已在 KONKR Pocket FIT Elite 真机完成我的画面验收。这里公开的是插件源码与测试，不包含修改版补帧核心、商业 DLL 或完整私人测试 ZIP，不能把 GitHub 的源码下载包当作可直接安装的插件包。

共存说明：本插件使用独立的配置目录（`.config/lsfg-vk-arm64`）、启动脚本（`~/lsfg-arm64`）和 Vulkan 层，可与原版插件共存；每个游戏只选择一个启动项，两者的设置与配置档案相互独立。

组装安装包时使用独立的 `LSFG-VK ARM64` 插件目录。此前 ARM64 测试版与原版同名并共用文件，新版会保留这些旧文件，不自动迁移或删除旧设置；需要使用本版的游戏，请重新复制本版启动项。本次改名共存尚未进行真机验收，上文 r5 的验收结果不代表新版共存验收。

## Attribution and licensing

The plugin retains Kurt Himebauch's and the contributors' **BSD-3-Clause** license and notices; see [LICENSE](LICENSE). The [original README](docs/UPSTREAM-README.md) is retained as historical upstream documentation, not current instructions for this ARM64 fork.

The separately developed lsfg-vk core has its own license. The 2.0 revision used in the private test carried **CC BY-NC-ND 4.0**; the plugin's BSD license does not grant permission to distribute modified core builds. Neither modified core source/binaries nor the proprietary Lossless Scaling DLL are included in this synchronization.

Thanks to the original plugin authors, lsfg-vk contributors, Lossless Scaling developers, Decky Loader team, Armada contributors, and community testers. Please report issues specific to this fork in [this repository](https://github.com/mydanyi/decky-lsfg-vk-arm64/issues).
