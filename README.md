# 夜莺码

夜莺是一套基于小鹤双拼的音形输入方案：双拼音码＋首末字根，常用字可用简码。

当前正式版本为 **3.1**（2026-10-15）。[官网](https://loswater.github.io/Nightingale/) · [发布页与全部附件](https://github.com/losWater/Nightingale/releases/tag/v3.1) · [更新日志](https://loswater.github.io/Nightingale/changelog.html)

## Rime 下载

**只建议使用 V5 版本。V5 模型：强烈推荐。** 形码和形码单字版仅供需要固定码表输入或单字练习的用户选择。Windows 和 Mac 各有三个独立包，请按操作系统下载，不能混装。

### Windows · 小狼毫

面向 **Windows x64 + 官方小狼毫 0.17.4**，已在官方引擎上实际部署并按键验证。V5 不支持 32 位或原生 ARM64 宿主。

| 版本 | 下载与用途 |
|---|---|
| **V5 版（强烈推荐）** | [下载](https://github.com/losWater/Nightingale/releases/download/v3.1/Nightingale-Rime-3.1-windows-v5-20261015.zip)：本地整句模型，保留夜莺固定码序 |
| 形码版 | [下载](https://github.com/losWater/Nightingale/releases/download/v3.1/Nightingale-Rime-3.1-windows-shape-20261015.zip)：无模型，最大四码、五码顶屏 |
| 形码单字版 | [下载](https://github.com/losWater/Nightingale/releases/download/v3.1/Nightingale-Rime-3.1-windows-single-20261015.zip)：单字与夜莺快符，手动确认上屏 |

[校验值](https://github.com/losWater/Nightingale/releases/download/v3.1/SHA256SUMS-windows-20261015.txt) · [引擎验证报告](https://github.com/losWater/Nightingale/releases/download/v3.1/windows-verification.json)

### Mac · 鼠须管

V5 原生引擎仅适用于 **Apple Silicon**；Mac 包不能用于 Windows 或手机。

| 版本 | 下载与用途 |
|---|---|
| **V5 版（强烈推荐）** | [下载](https://github.com/losWater/Nightingale/releases/download/v3.1/Nightingale-Rime-3.1-mac-v5-20261015.zip)：本地整句模型，保留夜莺固定码序 |
| 形码版 | [下载](https://github.com/losWater/Nightingale/releases/download/v3.1/Nightingale-Rime-3.1-mac-shape-20261015.zip)：无模型，最大四码、五码顶屏 |
| 形码单字版 | [下载](https://github.com/losWater/Nightingale/releases/download/v3.1/Nightingale-Rime-3.1-mac-single-20261015.zip)：单字与夜莺快符，手动确认上屏 |

[校验值](https://github.com/losWater/Nightingale/releases/download/v3.1/SHA256SUMS-mac-20261015.txt)

**安装**：把整个包解压到 Rime 用户文件夹（同名文件覆盖），点“重新部署”，用 Ctrl+` 切换到夜莺方案。包里的 default.custom.yaml 已列好夜莺的三个方案，装几个包、先后顺序都不影响；它会替换原有的 default.custom.yaml，如果还用着别的方案，部署后把它们加回方案列表。安装前建议备份用户文件夹；V5 更换原生库后须重启小狼毫算法服务或鼠须管。

从 2.5 升级：3.x 的方案标识不再带版本号（yeying_v5、yeying_shape、yeying_single），以后升级直接覆盖即可；2.5 的 yeying25_* 方案可以从方案列表里移除。3.x 有 46 组字根相对 2.x 换了键位，建议先用[字根练习](https://loswater.github.io/Nightingale/tools/root-practice.html)的“只练改动过的根”过一遍。

### 其他输入法与工具

- [手心 · 搜狗 · 冰凌 · Bime 等平台码表](https://github.com/losWater/Nightingale/releases/download/v3.1/Nightingale-3.1-tables-20261015.zip)
- [啾啾工具箱 · 单文件](https://github.com/losWater/Nightingale/releases/download/v3.1/Nightingale-Toolbox-3.1-20261015.html)：拆分查询、部件反查、字根练习、字根表、字根图、完整拆分表，离线可用

## 魔虎原作者与声明

魔虎原作者：**fcxxxz**，项目为 [rime-mohu](https://github.com/fcxxxz/rime-mohu)。V5 模型、原生引擎及相关 Lua 为魔虎原作，**不是夜莺原创**。夜莺提供自己的码表、词图、候选混排和平台适配。

上游发行声明采用 GPL v3；具体文件另有声明的按原声明处理。包内保留 LICENSE-mohu 及 attribution/ 下的原始 README、模型说明和发布声明；适配源码在 [tools/rime_mac](tools/rime_mac)。不因界面改名而移除原作者署名。

## 学习与查询

[字根表](https://loswater.github.io/Nightingale/tools/roots.html) · [字根练习](https://loswater.github.io/Nightingale/tools/root-practice.html) · [拆分查询](https://loswater.github.io/Nightingale/tools/split.html) · [部件反查](https://loswater.github.io/Nightingale/tools/components.html)

Rime 中输入 ~ 或反引号后接全拼/小鹤双拼查询拆分；F2 筛选核心字。形码指固定码表输入方式，仍使用夜莺双拼＋首末根编码，不是虎码编码。

## 维护

`main` 承载站点与发布页，以及 **2.x 周期**的维护链（`maintenance.json` → `夜莺2.5` → `rollover.py`）。

**正式版 3.x 的码表不在这里。** 3.1 的码表、拆分、构建与发布都在 [work/yeying30-nb46](https://github.com/losWater/Nightingale/tree/work/yeying30-nb46/work/夜莺3.0) 分支的 `work/夜莺3.0` 目录维护：发布流程见其中的 [`release/发布流程.md`](https://github.com/losWater/Nightingale/blob/work/yeying30-nb46/work/夜莺3.0/release/发布流程.md)，入口见该分支根目录的 `AGENTS.md` 与 `MAINTENANCE.md`。要改正式版的字、码、词、简码，先切到该分支。

`main` 上的 [维护架构](MAINTENANCE.md) 与 [夜莺2.5](夜莺2.5/README.md) 供 2.x 追溯与历史构建使用。
