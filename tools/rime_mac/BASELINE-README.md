# 夜莺 2.5 · Mac 首版

以作者正式发布的 Nightingale-Rime-2.5-light-20260922.zip 为数据来源。
本包使用鼠须管自带的 Rime 原生整句与用户词典，不依赖魔虎 V5 原生引擎或外部模型。
参考魔虎的固定码表与整句分流方式，保留夜莺的首末根和正式固定码序。
它是供日常试打的基础版本，不是魔虎主力版完整功能移植。

## 使用

- 切换方案：Control + 反引号，选择「夜莺2.5·Mac」。
- 单字简码、四码和词组：沿用夜莺 2.5；长输入支持小鹤双拼整句。
- 空格选首项，分号选第二项，单引号选第三项；数字选词。
- 方括号或 Page Up / Page Down 翻页。
- 两至四码后 F2：核心字查询；Mac 功能键设置下可能需要 Fn+F2。
- 反引号或 ~ 加全拼/小鹤双拼：拆分查询。
- Ctrl+数字：钉选；Ctrl+Enter：按夜莺编码规则主动造词。
- 方案菜单可开启「简词整句」，默认关闭；例如 wxhni → 我喜欢你。
  此模式会增加双拼长句的切分歧义，正常双拼整句建议保持关闭。

固定码序不随使用频率漂移，整句用户词典可学习。主动造词和钉选使用独立文件。
这一版不启用旧包的固定码自动造词，避免日常选词改变固定码候选集合；可主动造词。
原生整句没有 V5 模型加持，首选准确率需要实打检验。

## 安装与回退

包内 yeying25_mac 开头的 YAML 复制至 ~/Library/Rime，lua 下文件复制至用户目录的 lua。
在 default.custom.yaml 的 patch/schema_list 中增加 `- {schema: yeying25_mac}`，重新部署。
保留已有 schema_list，不要覆盖用户原有 default.custom.yaml 或 squirrel.custom.yaml。
回退时切换回原方案即可；安装器会备份改动前的方案列表配置。

## 来源

- 夜莺 2.5：https://github.com/losWater/Nightingale/releases/tag/v2.5
- 魔虎参考：https://github.com/fcxxxz/rime-mohu
- 本包码表、查询和钉选代码来源于夜莺正式发布，保留来源注释。
- 本次只供作者本机验证；未向 GitHub 发布。

开发目录中执行 `python3 build.py` 可重建包，manifest.json 记录源包与文件校验值。
