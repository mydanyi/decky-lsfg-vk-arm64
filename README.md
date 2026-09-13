# LSFG-VK ARM64

面向 **Armada ARM64** 的 Decky 补帧插件，基于 [Decky LSFG-VK](https://github.com/xXJSONDeruloXx/decky-lsfg-vk)，支持简体中文和 lsfg-vk 2.0，可与原版插件同时安装。

[下载发布版](https://github.com/mydanyi/decky-lsfg-vk-arm64/releases/latest)

## 功能

- 简体中文界面，支持补帧倍率、光流比例、性能模式和配置档案。
- 基础 FPS 上限支持 D3D9、D3D10、D3D11 和 D3D12 的 DXVK／VKD3D 启动路径。
- 发布 ZIP 内置修改版 ARM64 补帧核心，由插件自动安装。
- 独立的插件名称、配置、启动脚本和 Vulkan 层，可与 **Decky LSFG-VK** 共存。
- 使用 GPU 补帧。

## 安装与使用

需要 Armada ARM64、已安装的 Decky，以及 Steam 中的正版 **Lossless Scaling**。

1. 在 Steam 中打开 **Lossless Scaling → 属性 → 游戏版本与测试版**（部分客户端显示为“测试版”），选择 **`lsfg-vk`** 分支，等待下载／更新完成。所需的 `lsfg-vk.dll` 由该分支提供，插件会检测 Steam 安装目录中的文件。参见 [lsfg-vk 官方安装指南](https://lsfg-vk.dev/docs/installation/)。
2. 从 [Releases](https://github.com/mydanyi/decky-lsfg-vk-arm64/releases/latest) 下载插件 ZIP，在 Decky 开发者设置中从 ZIP 安装。GitHub 自动生成的 Source code 是源码包。
3. 打开或重新加载 **LSFG-VK ARM64**，等待包内核心自动安装，确认安装和 Lossless Scaling 检测状态正常。
4. 在插件中复制启动参数，粘贴到需要补帧的游戏启动选项中，并保留其他游戏专用参数。
5. 设置基础 FPS 上限及补帧倍率。修改基础 FPS 上限或补帧开关后，重新启动游戏。

每个游戏选择一个补帧插件的启动项。两版插件的配置独立，本版不自动导入或删除原版设置。此前安装了不带核心的 `-plugin-only.zip` 的用户，请用完整 ZIP 重新安装。

发布包内置 ARM64 核心，不包含商业 `lsfg-vk.dll`；该文件通过上述 Steam 分支取得。下载后可使用发布附件中的 `SHA256SUMS.txt` 核对 ZIP 完整性。

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

## 赞助与交流

- 爱发电赞助：[https://afdian.com/a/meetmiku](https://afdian.com/a/meetmiku)
- QQ 粉丝群：**487945399**
- QQ 养老群：**477426414**
