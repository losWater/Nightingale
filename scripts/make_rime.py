# -*- coding: utf-8 -*-
"""夜莺码 Rime 方案生成器（Mac 鼠须管 / Linux ibus-rime / Win 小狼毫 通用）

数据源: releases/v0.4/夜莺码v0.4字词总表.txt（查询权威全量：单字简码/全码 + 词 + 四字简拼 + 快符补丁，已按候选顺序排好）
输出:   releases/v0.4/rime/yeying.schema.yaml  方案定义
        releases/v0.4/rime/yeying.dict.yaml    码表（sort: original，严格保持总表顺序=候选顺序）
        releases/v0.4/rime/README.md           部署说明
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
REL = BASE / "releases/v0.4"
OUT = REL / "rime"
OUT.mkdir(exist_ok=True)

# 版本号取自版本说明当前版标题
ver = "0.4"
m = re.search(r"^## v([\d.]+)（当前版", open(BASE / "releases/版本说明.md", encoding="utf-8").read(), re.M)
if m:
    ver = m.group(1)

SCHEMA = f"""# 夜莺码 · Rime 方案（自动生成，勿手改：scripts/make_rime.py）
# 音形方案：小鹤双拼声韵 + 首末根形码两位，最长四码
schema:
  schema_id: yeying
  name: 夜莺码
  version: "{ver}"
  author:
    - 夜莺码项目
  description: |
    小鹤双拼 + 首末字根形码，单字最长四码；
    一/二/三简 + 词全码 + 四字词声母简拼，候选顺序与搜狗自定义短语版完全一致。
  dependencies: []

switches:
  - name: ascii_mode
    reset: 0
    states: [ 中文, 西文 ]
  - name: full_shape
    states: [ 半角, 全角 ]
  - name: ascii_punct
    states: [ 。，, ．， ]

engine:
  processors:
    - ascii_composer
    - recognizer
    - key_binder
    - speller
    - punctuator
    - selector
    - navigator
    - express_editor
  segmentors:
    - ascii_segmentor
    - matcher
    - abc_segmentor
    - punct_segmentor
    - fallback_segmentor
  translators:
    - punct_translator
    - table_translator

speller:
  alphabet: zyxwvutsrqponmlkjihgfedcba
  delimiter: " '"
  max_code_length: 4
  # 想要"四码唯一自动上屏"就把下面两行取消注释
  # auto_select: true
  # auto_select_unique_candidate: true

translator:
  dictionary: yeying
  enable_charset_filter: false
  enable_sentence: false
  enable_encoder: false
  encode_commit_history: false
  enable_completion: false      # 只出精确匹配，与搜狗自定义短语行为一致
  enable_user_dict: false       # 固定候选顺序（想让常用字自动前移就改 true）
  initial_quality: 1

key_binder:
  bindings:
    - {{ when: has_menu, accept: semicolon, send: 2 }}     # 分号=二选
    - {{ when: has_menu, accept: apostrophe, send: 3 }}    # 引号=三选
    - {{ when: has_menu, accept: minus, send: Page_Up }}
    - {{ when: has_menu, accept: equal, send: Page_Down }}

punctuator:
  import_preset: default

recognizer:
  import_preset: default

menu:
  page_size: 5
  alternative_select_keys: "1234567890"
"""

# ---- 码表 ----
rows = []
n_skip = 0
for line in open(REL / "夜莺码v0.4字词总表.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 2 or not p[0] or not p[1]:
        continue
    w, code = p[0], p[1]
    if not re.fullmatch(r"[a-z]{1,4}", code):
        n_skip += 1
        continue
    rows.append((w, code))

dict_head = f"""# 夜莺码码表（自动生成：scripts/make_rime.py，数据源=字词总表）
# sort: original → 同码候选顺序 = 本文件行序 = 总表顺序
---
name: yeying
version: "{ver}"
sort: original
use_preset_vocabulary: false
columns:
  - text
  - code
...
"""
with open(OUT / "yeying.dict.yaml", "w", encoding="utf-8", newline="\n") as f:
    f.write(dict_head)
    for w, code in rows:
        f.write(f"{w}\t{code}\n")
with open(OUT / "yeying.schema.yaml", "w", encoding="utf-8", newline="\n") as f:
    f.write(SCHEMA)

README = f"""# 夜莺码 Rime 方案 v{ver}

自动生成，内容与 Windows 搜狗自定义短语版候选顺序一致（数据源：字词总表）。

## 安装（Mac · 鼠须管 Squirrel）

1. 安装 [鼠须管](https://rime.im/download/)
2. 把本目录的 `yeying.schema.yaml`、`yeying.dict.yaml` 复制到 `~/Library/Rime/`
3. 在 `~/Library/Rime/default.custom.yaml` 里加入（没有就新建）：

   ```yaml
   patch:
     schema_list:
       - schema: yeying
   ```

4. 菜单栏 鼠须管 → 重新部署（首次编译码表约十几秒）
5. `Ctrl+\\`（或 F4）切到"夜莺码"

Linux ibus-rime 用 `~/.config/ibus/rime/`，Windows 小狼毫用 `%APPDATA%\\Rime\\`，步骤相同。

## 键位约定

- 空格上屏首选；`;` 二选、`'` 三选；`-`/`=` 翻页；数字键直选
- 最长四码，精确匹配出词（不显示补全候选），候选顺序固定不随使用调整
- 想要四码唯一自动上屏：在 `yeying.schema.yaml` 的 `speller` 段取消 `auto_select` 两行注释
- 想让常用字按使用频率前移：`translator/enable_user_dict` 改 `true`

## 更新

Windows 侧 `python scripts/nightingale.py rebuild` 会重生成本目录；把两份 yaml 覆盖到 Rime 目录后重新部署即可。
"""
with open(OUT / "README.md", "w", encoding="utf-8", newline="\n") as f:
    f.write(README)
print(f"Rime 方案: {len(rows)} 条码表（跳过非法码 {n_skip}）→ {OUT}")
