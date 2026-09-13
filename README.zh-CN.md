# LSFG-VK ARM64

[English](README.md) | **简体中文**

面向 **Armada ARM64** 的 Decky 补帧插件，基于 [Decky LSFG-VK](https://github.com/xXJSONDeruloXx/decky-lsfg-vk)，支持简体中文和 lsfg-vk 2.0，可与原版插件同时安装。

[下载发布版](https://github.com/mydanyi/decky-lsfg-vk-arm64/releases/latest)

## 功能

- 简体中文界面，支持补帧倍率、光流比例、性能模式和配置档案。
- 基础 FPS 上限支持 D3D9、D3D10、D3D11 和 D3D12 的 DXVK／VKD3D 启动路径。
- 过载退让与帧节奏恢复默认开启，位于“性能模式”下方，支持两倍、三倍和四倍的提交间隔平滑。持续变慢时减少补帧，稳定后尝试恢复；保留保存的倍率和基础 FPS 上限，期间可能暂时只显示原始帧。已有手动关闭的设置会保留。
- 复制启动参数使用便携写法：`~/lsfg-arm64 %command%`。
- 发布 ZIP 内置修改版 ARM64 补帧核心，由插件自动安装。
- 独立的插件名称、配置、启动脚本和 Vulkan 层，可与 **Decky LSFG-VK** 共存。
- 使用 GPU 补帧。

## 安装与使用

需要 Armada ARM64、已安装的 Decky，以及 Steam 中的正版 **Lossless Scaling**。

1. 在 Steam 中打开 **Lossless Scaling → 属性 → 游戏版本与测试版**（部分客户端显示为“测试版”），选择 **`lsfg-vk`** 分支，等待下载／更新完成。所需的 `lsfg-vk.dll` 由该分支提供，插件会检测 Steam 安装目录中的文件。参见 [lsfg-vk 官方安装指南](https://lsfg-vk.dev/docs/installation/)。
2. 从 [发布页](https://github.com/mydanyi/decky-lsfg-vk-arm64/releases/latest) 下载插件 ZIP，在 Decky 开发者设置中从 ZIP 安装。GitHub 自动生成的 Source code 是源码包。
3. 打开或重新加载 **LSFG-VK ARM64**，等待包内核心自动安装，确认安装和 Lossless Scaling 检测状态正常。
4. 在插件中复制启动参数，粘贴到需要补帧的游戏启动选项中，并保留其他游戏专用参数。
5. 设置基础 FPS 上限及补帧倍率。修改基础 FPS 上限或补帧开关后，重新启动游戏。

每个游戏选择一个补帧插件的启动项。两版插件的配置独立，本版不自动导入或删除原版设置。此前安装了不带核心的 `-plugin-only.zip` 的用户，请用完整 ZIP 重新安装。

发布包内置 ARM64 核心，不包含商业 `lsfg-vk.dll`；该文件通过上述 Steam 分支取得。下载后可使用发布附件中的 `SHA256SUMS.txt` 核对 ZIP 完整性。

## 开发

源码仓库包含 Decky 插件和[原生核心补丁](native/README.md)。发布 ZIP 还包含修改版 ARM64 原生运行时。前端构建会生成 `dist/index.js`，不会编译原生运行时。

请使用仓库中已提交的依赖锁定文件。后端开发需要 Linux、Python 3.11 或更高版本，以及 Bash。

```sh
pnpm install --frozen-lockfile
pnpm test
pnpm exec tsc --noEmit
pnpm build
python3 -m unittest discover -s tests -v
```

打包目录为 `LSFG-VK ARM64`；原生运行时文件应放在该目录下的 `bin/liblsfg-vk-v2-arm64.so`。

## 致谢与许可

本社区分支基于 [xXJSONDeruloXx/decky-lsfg-vk](https://github.com/xXJSONDeruloXx/decky-lsfg-vk)。插件保留 Kurt Himebauch 及其他贡献者的 BSD-3-Clause 许可证和声明，详见 [LICENSE](LICENSE)。仓库保留了[上游 README](docs/UPSTREAM-README.md)，用于注明来源和历史参考。

[lsfg-vk](https://lsfg-vk.dev/) 原生组件使用独立的 CC BY-NC-ND 4.0 许可证，许可证随发布包提供。插件的许可证不替代原生组件的许可证。Lossless Scaling 及其 DLL 仍受各自条款约束。

感谢原版插件作者、lsfg-vk 贡献者、Lossless Scaling 开发者、Decky Loader 团队和 Armada 贡献者。本分支特有的问题请在[本仓库](https://github.com/mydanyi/decky-lsfg-vk-arm64/issues)反馈。

## 赞助与交流

- 爱发电赞助：[支持作者](https://afdian.com/a/meetmiku)
- QQ 粉丝群：**487945399**
- QQ 养老群：**477426414**
