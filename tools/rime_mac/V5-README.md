# 夜莺 2.5 · V5（强烈推荐 · Mac Apple Silicon）

只建议使用 V5 版本。形码、形码单字版仅供明确需要固定码表或单字练习的用户选择。

新增独立方案「夜莺2.5·V5」，原「夜莺2.5·Mac」保留，Control+反引号可切换对照。
横排样式沿用本机鼠须管设置。

本版使用魔虎官方 latest 发布的 ARM64 引擎、配套 Lua 和 V5 u8 模型
（TCSKNM04，模型文件约 390 MB），本地运行，无需网络服务。
模型输出候选带 V5 注释；短码/固定词组仍优先遵循夜莺 2.5 码表。
使用夜莺码表生成首末根词图，不使用虎码辅助码。

默认开启上下文整句，模型只在长于四键的输入中参与整句候选；简码、四码词序不改。
开启「简词整句」时回到原生 Rime 短词组合；超过 96 键也使用原生 Rime 兜底。
V5 有独立的整句用户词典和学习快照，钉选/主动造词与基础版共享。
不包含魔虎另行提供的神经语义重排模型。

## 来源和改动

- 夜莺数据：https://github.com/losWater/Nightingale/releases/tag/v2.5
- 魔虎原作者：fcxxxz。V5 模型、原生引擎和相关 Lua 来自魔虎 rime-mohu，不是夜莺原创：https://github.com/fcxxxz/rime-mohu
- 魔虎引擎/Lua/模型：https://github.com/fcxxxz/rime-mohu/releases/tag/latest
- 上游代码许可见 LICENSE-mohu（GPL v3）。
- Lua 适配改私有模块/数据目录名、V5 候选标记，并读取候选条数设置（四条）；保留上游引擎算法。
- build_v5.py 与 src/ 保存适配构建来源，v5-manifest.json 保存资产校验值。

## 安装

首次安装先按 README.md 安装基础方案。复制本包 yeying25_v5.schema.yaml、
lua/yeying25_v5_*.lua、整个 yeying25_v5 目录到 Rime 用户目录相应位置。
在 default.custom.yaml 的 patch/schema_list 添加 `- {schema: yeying25_v5}`。
已有同名安装时保留 yeying25_v5/config 中的个人学习数据。
重新部署后选「夜莺2.5·V5」。引擎更新时需要完全退出并重启鼠须管。
若浏览器下载的动态库受隔离限制，只对本包 yeying25_v5/runtime 解除隔离。

已在 Apple Silicon Mac 的鼠须管 1.1.2 / librime 1.16.0 验证。此包不适用于 Windows、Intel Mac 或手机。首次选方案需要加载模型。
上游原始 README、模型说明及发布声明保存在 attribution/，不因方案显示名调整而删除。原文件中的魔虎目录和安装方式是上游资料；安装夜莺请遵循本包 README.md。
