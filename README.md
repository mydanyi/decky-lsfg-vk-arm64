# LSFG-VK ARM64

**English** | [简体中文](README.zh-CN.md)

A Decky frame generation plugin for **Armada ARM64**, based on [Decky LSFG-VK](https://github.com/xXJSONDeruloXx/decky-lsfg-vk). It supports Simplified Chinese and lsfg-vk 2.0, and can be installed alongside the original plugin.

[Download the latest release](https://github.com/mydanyi/decky-lsfg-vk-arm64/releases/latest)

## Features

- Simplified Chinese interface with controls for the frame generation multiplier, flow scale, performance mode, and configuration profiles.
- Base FPS limit support for D3D9, D3D10, D3D11, and D3D12 through DXVK / VKD3D launch paths.
- A modified ARM64 frame generation runtime bundled in the release ZIP and installed automatically by the plugin.
- Separate plugin name, configuration, launch script, and Vulkan layer, allowing this version to coexist with **Decky LSFG-VK**.
- GPU-based frame generation.

## Installation and usage

Requires Armada ARM64, an existing Decky installation, and a legitimate copy of **Lossless Scaling** on Steam.

1. In Steam, open **Lossless Scaling → Properties → Game Versions & Betas** (shown as **Betas** in some clients), select the **`lsfg-vk`** branch, and wait for the download or update to finish. This branch provides the required `lsfg-vk.dll`, which the plugin detects in the Steam installation directory. See the [official lsfg-vk installation guide](https://lsfg-vk.dev/docs/installation/).
2. Download the plugin ZIP from [Releases](https://github.com/mydanyi/decky-lsfg-vk-arm64/releases/latest) and install it from ZIP through Decky's developer settings. GitHub's automatically generated Source code downloads are source archives.
3. Open or reload **LSFG-VK ARM64**, wait for the bundled runtime to install automatically, and confirm that installation and Lossless Scaling detection succeed.
4. Copy the launch options from the plugin and paste them into the launch options of the game you want to use frame generation with. Preserve any other game-specific options.
5. Set the base FPS limit and frame generation multiplier. Restart the game after changing the base FPS limit or toggling frame generation.

Use the launch options of one frame generation plugin per game. The two plugins keep separate configurations; this version does not automatically import or delete the original plugin's settings. If you previously installed a `-plugin-only.zip` without the runtime, reinstall using the complete ZIP.

The release includes the ARM64 runtime but does not include the commercial `lsfg-vk.dll`; obtain that file through the Steam branch described above. Use the attached `SHA256SUMS.txt` to verify the downloaded ZIP's integrity.

## Development

The source repository contains the Decky plugin. Release ZIPs additionally bundle the modified ARM64 native runtime. The frontend build produces `dist/index.js`; it does not compile the native runtime.

Use the committed lockfile. Backend development requires Python 3.11+ and Bash on Linux.

```sh
pnpm install --frozen-lockfile
pnpm test
pnpm exec tsc --noEmit
pnpm build
python3 -m unittest discover -s tests -v
```

The package directory is `LSFG-VK ARM64`; the native payload belongs at `bin/liblsfg-vk-v2-arm64.so` within that directory.

## Attribution and licensing

This community fork is based on [xXJSONDeruloXx/decky-lsfg-vk](https://github.com/xXJSONDeruloXx/decky-lsfg-vk). The plugin retains Kurt Himebauch's and the contributors' BSD-3-Clause license and notices; see [LICENSE](LICENSE). The [upstream README](docs/UPSTREAM-README.md) is retained for attribution and historical reference.

The [lsfg-vk](https://lsfg-vk.dev/) native component has its own CC BY-NC-ND 4.0 license, included in the release archive. The plugin license does not replace the native component's license. Lossless Scaling and its DLL remain subject to their own terms.

Thanks to the original plugin authors, lsfg-vk contributors, Lossless Scaling developers, Decky Loader team and Armada contributors. Report issues specific to this fork in [this repository](https://github.com/mydanyi/decky-lsfg-vk-arm64/issues).

## Support and community

- Sponsorship: [Afdian](https://afdian.com/a/meetmiku)
- QQ fan group: **487945399**
- QQ casual chat group: **477426414**
