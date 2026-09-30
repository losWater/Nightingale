# 夜莺码

夜莺是一套基于小鹤双拼的音形输入方案：双拼音码＋首末字根，常用字可用简码。

当前正式版本为 **2.5**。[官网](https://loswater.github.io/Nightingale/) · [发布页与全部附件](https://github.com/losWater/Nightingale/releases/tag/v2.5)

## Rime 下载

**只建议使用 V5 版本。V5 模型：强烈推荐。** 形码和形码单字版仅供需要固定码表输入或单字练习的用户选择。

Windows 和 Mac 各有三个独立包，请按操作系统下载。**只建议使用 V5 版本。**

### Windows · 小狼毫（2026-09-30）

面向 **Windows x64 + 官方小狼毫 0.17.4**。三个实际 ZIP 已通过 Windows 官方引擎隔离部署与按键验证，V5 原生模型候选及整句上屏通过；不等于人工遍历所有应用。V5 不支持 32 位或原生 ARM64 宿主；其他宿主版本须另行验证。

| 版本 | 下载与用途 |
|---|---|
| **V5 版（强烈推荐）** | [Windows V5 包](https://github.com/losWater/Nightingale/releases/download/v2.5/Nightingale-Rime-2.5-windows-v5-20260930.zip)：本地整句模型、夜莺固定码序 |
| 形码版 | [Windows 形码包](https://github.com/losWater/Nightingale/releases/download/v2.5/Nightingale-Rime-2.5-windows-shape-20260930.zip)：无模型，最大四码、五码顶屏 |
| 形码单字版 | [Windows 单字包](https://github.com/losWater/Nightingale/releases/download/v2.5/Nightingale-Rime-2.5-windows-single-20260930.zip)：单字与夜莺快符，手动确认 |

[Windows 校验值](https://github.com/losWater/Nightingale/releases/download/v2.5/SHA256SUMS-windows-20260930.txt) · [引擎验证报告](https://github.com/losWater/Nightingale/releases/download/v2.5/windows-verification.json)

### Mac · 鼠须管（2026-09-28）

V5 原生引擎仅适用于 **Apple Silicon**。已在鼠须管 1.1.2 / librime 1.16.0 验证；Mac 包不能用于 Windows 或手机。

| 版本 | 下载与用途 |
|---|---|
| **V5 版（强烈推荐）** | [下载 V5 包](https://github.com/losWater/Nightingale/releases/download/v2.5/Nightingale-Rime-2.5-mac-v5-20260928.zip)：魔虎 V5 本地整句模型，保留夜莺固定码序 |
| 形码版 | [下载形码包](https://github.com/losWater/Nightingale/releases/download/v2.5/Nightingale-Rime-2.5-mac-shape-20260928.zip)：无模型，最大四码、五码顶屏 |
| 形码单字版 | [下载形码单字包](https://github.com/losWater/Nightingale/releases/download/v2.5/Nightingale-Rime-2.5-mac-single-20260928.zip)：纯单字与夜莺快符，手动确认上屏 |

[Mac 校验值](https://github.com/losWater/Nightingale/releases/download/v2.5/SHA256SUMS-mac-20260928.txt)。其他平台与历史附件保留供追溯；手机不在本次桌面发行范围。

安装前备份 Rime 用户目录；按包内 README 合并文件和方案列表，重新部署。不要覆盖个人词库、钉选及模型学习数据。V5 更换原生库后还须重启小狼毫算法服务或鼠须管。

## 魔虎原作者与声明

魔虎原作者：**fcxxxz**，项目为 [rime-mohu](https://github.com/fcxxxz/rime-mohu)。V5 模型、原生引擎及相关 Lua 为魔虎原作，**不是夜莺原创**。夜莺提供自己的码表、词图、候选混排和平台适配。

上游发行声明采用 GPL v3；具体文件另有声明的按原声明处理。包内保留 LICENSE-mohu 及 attribution/ 下的原始 README、模型说明和发布声明；适配源码在 [tools/rime_mac](tools/rime_mac)。不因界面改名而移除原作者署名。

## 学习与查询

[字根表](https://loswater.github.io/Nightingale/tools/roots.html) · [字根练习](https://loswater.github.io/Nightingale/tools/root-practice.html) · [拆分查询](https://loswater.github.io/Nightingale/tools/split.html) · [部件反查](https://loswater.github.io/Nightingale/tools/components.html)

Rime 中输入 ~ 或反引号后接全拼/小鹤双拼查询拆分；F2 筛选核心字。形码指固定码表输入方式，仍使用夜莺双拼＋首末根编码，不是虎码编码。

## 维护

[维护架构](MAINTENANCE.md) → [当前维护目录：夜莺2.5](夜莺2.5/README.md)。主表、拆分和修改台账以该目录为准；通用维护工具位于 tools/maintenance，Mac 适配工具位于 tools/rime_mac。

历史发布与旧维护记录保留供追溯，不作为当前构建入口。
