# 夜莺码

夜莺是一套基于小鹤双拼的音形输入方案：乱序字根，拆分直观，常用字无重，常用字词避重。

当前正式版本为 **1.0**，采用 **G8C12** 键位布局。

**[夜莺官网](https://loswater.github.io/Nightingale/)** · **[下载与使用说明](https://github.com/losWater/Nightingale/releases/tag/v1.0)** · [作者的话](https://loswater.github.io/Nightingale/author.html) · [1.0升级日志](releases/v1.0/夜莺1.0升级日志.txt)

欢迎加入qq群聊交流：**835527851**。

## 下载与使用

推荐从 [1.0 Release 发布页](https://github.com/losWater/Nightingale/releases/tag/v1.0)下载，优先选择文件名含 **f2** 的最新完整包或 Rime 包。旧附件保留供回退。

### Rime 包（推荐使用）

- **主力版（测试）**：搭载魔虎 V5 整句模型，支持双拼整句及简词整句；包内同时提供轻量、形码模式。
- **轻量版**：不带外部整句模型，保留原生整句和用户词典；包内同时提供形码模式。
- **形码模式**：四码定长输入，不使用整句模型。

当前发布包面向 **Windows x64 小狼毫**，已在小狼毫0.17.4环境测试。主力模型引擎为 Windows 专用；macOS、手机端尚未适配验证。

三个方案均支持拆分查询：

- 输入 `~` 或反引号，再输入全拼或小鹤双拼，如 `~han`、`~hj`，查看单字拆分及编码。
- 输入两位双拼或三码后按 **F2**，仅列出符合当前编码的核心字，不混入词组或扩展字。
- F2 开启后可继续输入、退格和翻页，例如 `yc` → F2 → `b`，筛选符合 `ycb` 的字。选字上屏后退出；再按 F2 保留当前编码恢复普通候选，Esc 取消。

主力模型包约380 MiB，轻量包约4.6 MiB；当前完整包包含主力模型，约401 MiB。需要较小下载体积时，可以单独下载轻量包。

### 手心输入法（方便上手）

配合小鹤双拼，分别从自定义短语、辅助码入口导入夜莺文件，即可使用手心自身的词库和整句输入。辅助码提供 UTF-8、Unicode 两版，选一份导入即可。曲的辅助码保留 `ea en ex` 三组，已修复四组辅助码导致的导入卡死问题。

详见[手心使用说明](releases/v1.0/02_输入法挂接/手心输入法/README.md)。

搜狗等其他输入法的配套目前功能并不全面，不十分推荐使用。**小胖、多多等输入法的配套会尽快上线。**

## 学习与查询

第一次接触夜莺，建议先看字根表，再进行字根和必拆字练习。

[字根表与归并字根表](https://loswater.github.io/Nightingale/tools/roots.html) · [字根练习](https://loswater.github.io/Nightingale/tools/root-practice.html) · [必拆字练习](https://loswater.github.io/Nightingale/tools/split-practice.html) · [拆分查询](https://loswater.github.io/Nightingale/tools/split.html) · [编码反查](https://loswater.github.io/Nightingale/tools/reverse.html) · [部件查字](https://loswater.github.io/Nightingale/tools/components.html)

[性能介绍](https://loswater.github.io/Nightingale/performance.html)列明统计口径：纳入简码后前1500字选重为0，前6000字加权选重率为0.03%。完整包也提供可直接打开的离线工具。

## 编码原理

```text
abxy = 小鹤双拼音码 ab + 首根 x + 末根 y
```

完整说明见：[首末根原理](docs/principles/首末根原理.md)与[选词原理](docs/principles/选词原理.md)。

字架思路受虎码字架方案启发。夜莺结合自己的根集和规范拆分进行了逐字适配，不将字架概念视为夜莺原创。详见：[1.0字架说明](releases/v1.0/03_字根与拆分/夜莺码v1.0字架说明.txt)。

## 当前仓库结构

```text
docs/             原理、使用说明、维护与发布文档
schema/           方案配置与真源入口（迁移中）
pipelines/        构建、审计及基础发布程序
apps/website/     已上线网站的源码与构建入口
data/maintenance/ 后续人工裁决与容错补丁
tests/            自动校验与发布检查
releases/v1.0/    当前1.0正式资料
releases/v0.9.1/  旧版维护资料
work/rime_v1/    Rime构建、反查功能及测试工作目录
archive/          历史版本与研究归档
```

结构迁移尚未全部完成。部分根集、规范拆分及生成脚本仍位于 `work/重开工程` 与 `work/夜莺0.85`；Rime 的后续容错与候选调整还会读取 `data/maintenance`。维护时请区分正式发布快照和后续补丁。

维护者入口：[仓库架构](docs/maintainer-guide/仓库架构.md) · [实战维护记录](releases/v1.0/05_维护与裁决/实战发现的问题.txt)。

网站构建：

```powershell
python -m pip install Markdown
python apps/website/build.py
```

输出位于 `.tmp/website-preview`；正式网站由 `gh-pages` 分支部署。

`pipelines/v09/rebuild.py` 是旧版派生表重建入口；`pipelines/v1/prepare.py` 从旧维护目录准备1.0基础资料，不能单独替代当前包含 Rime 后续功能的完整发布流程。Rime 发布相关程序位于 `work/rime_v1/tools`，运行时还需要本地参考数据及模型文件。

## 历史版本与数据维护

[历史发布](https://github.com/losWater/Nightingale/releases)继续保留，包含0.9.1及0.8.5阶段资料；早期废弃方案位于 [archive/releases](archive/releases/)，用于追溯设计过程，不建议新用户安装。

根集、规范拆分、字音和人工裁决共同生成正式码表，再生成输入法挂接、查询和练习资料。派生文件不能反向成为真源；历史裁决中的撤销与覆盖，以后续记录为准。
