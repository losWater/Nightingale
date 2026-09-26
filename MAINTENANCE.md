# 维护架构

当前周期是 **夜莺2.5**：指 2.5 发布以后、下次发布以前的维护过程。只维护 maintenance.json 指向的目录。

```text
Nightingale/
├── maintenance.json              当前维护目录（唯一入口）
├── 夜莺2.5/
│   ├── 版本.json                 版本号与 active/archived 状态
│   ├── 主表/                    单字表、字词表、符号表、快符
│   ├── 配置/                    各版本需要保留的平台差异
│   ├── 资料/                    拆分唯一原本、规则与裁定背景
│   ├── 记录/                    修改台账、迁移说明、构建记录
│   ├── 产物/                    从主表生成，不手改、不入 Git
│   └── 备份/                    落盘前备份，不入 Git
├── tools/maintenance/           通用维护、导出、Mac构建、封存脚本
├── tools/rime_mac/              通用 Mac 适配器及真实引擎测试
├── assets/rime/                 固定的第三方适配器及元数据依赖
├── .cache/rime/                 本地大模型与运行库压缩包，不入 Git
└── work/夜莺2.0/                旧工作区，仅历史参考
```

通用脚本不复制进每个版本；主表文件不带版本号。未来新增夜莺2.6、夜莺3.0 时只更换当前目录指针，不再全仓库改名字。旧周期台账保留，新周期台账从空表开始，主表/资料/平台配置继承。

## 日常操作（在仓库根目录）

1. 将用户反馈翻译为 `夜莺2.5/记录/修改台账.tsv` 的待处理操作，使用原有15列格式。
2. 预演：`python3 tools/maintenance/apply_ledger.py`。
3. 确认后落盘：`python3 tools/maintenance/apply_ledger.py --apply`。备份、结果与前后 SHA256 都记在当前周期。
4. 导出文本和 Rime 数据：`python3 tools/maintenance/export.py`。
5. 构建并验证三个 Mac 方案：`python3 tools/maintenance/build_mac.py --verify`。
6. 查看 diff，按路径提交代码、主表和记录。是否安装、更新ZIP、发布分别决定；以上命令都不会安装或发布。

拆分显示修改：`python3 tools/maintenance/edit_split.py '字=根＋根'` 默认预演；`--apply --reason '原因'` 才备份、写入并追加台账。编码受影响时必须先核实并走两表改码，脚本不会擅自裁决。

平台差异不是第二套主表：例如 Mac 单字的子/自调整由 `配置/单字版差异.json` 保存，其他两个方案仍跟随官方主表。正式调整为全平台规则时，应迁入主表、追加台账并移除相应差异，不能反复叠加补丁。

## 版本发布后的封存

```sh
python3 tools/maintenance/rollover.py 2.6          # 只预演
python3 tools/maintenance/rollover.py 2.6 --apply  # 确认发布后执行
```

这不是发布命令，不上传附件、不推送代码、不修改已发布标签。它检查无待处理记录，然后封存旧目录、记录文件校验值与通用工具源码快照，复制主表/配置/资料到新目录并创建空台账，最后切换 maintenance.json。已有目标目录一律拒绝覆盖。

封存是工具层的写保护和校验清单，不是操作系统只读权限。以后不手动改封存目录；可以用 Git 和封存校验文件复核。封存工具快照用于历史复现，不是另一套活动脚本。

## 依赖与兼容边界

- Python 3.11+；Mac 引擎测试需要 clang 和标准安装路径的鼠须管（含 librime-lua）。维护主表本身仅依赖 Python 标准库。
- assets/rime 的小型基线ZIP只提供适配代码及语言元数据；固定字词表、当前全码、反查拆分都从当前目录重新生成，不从旧发布包继承候选表。
- 大文件 `rime-mohu-flypy-latest.zip`、`mohu-sentence-ngram-v5.bin.zip` 放 .cache/rime；固定地址和哈希见 assets/rime/mohu-release.json，不能随意用新版 latest 替换。
- yeying25_* 内部标识暂保留兼容；用户界面的版本名在完整构建时从版本.json取得。快符兼容中间文件的旧名字不代表另一个真源。
- 本次迁移打通主表维护、普通表导出、Mac三个方案及拆分维护。旧 Windows 全平台发布/官网脚本仍是历史工具，尚未迁入新入口，不应宣称 Windows/手机版已验证或运行它们发布。
- 规则文档保留历史裁定原文，其中旧路径只作来源追溯；日常操作以本页为准。

原 `/Users/ice2447/nightingale-mac` 只保留已安装包、备份和此前 Git 历史，后续不在两份仓库间双向维护。本仓库未推送。
