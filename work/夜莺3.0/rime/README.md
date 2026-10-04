# NB46 单字试用方案（Rime）

`Rime/` 下是装进 `~/Library/Rime` 的文件：
- `yeying30_nb46_single.schema.yaml`：方案（以夜莺 2.5 单字版为模板；依赖其 `lua/yeying25_single_english_guard.lua`）。
- `yeying30_nb46_single.dict.yaml`：NB46 普通单字表 + 2.5 快符；嗯 en 为二简。
- `yeying30_nb46_freq.txt`：核心读音字频（调频插件按字频补空位用）。
- `lua/yeying30_nb46_adjust_*.lua`：手动调频插件（key 按键、filter 重排、translator 为调整过的码生成候选、data 规则）。Control+数字 提到首选；Control+U 上移；Control+J/D 下移；Control+0 撤销上一步。空出的简码位先还给码表原占位字，否则按字频补。
  记录写在 `~/Library/Rime/yeying30_nb46_adjust.tsv`。

`make_dict.py`：由普通单字表重新生成码表（保留快符等附加条目）。
`adjust_sim.py`：插件逻辑的 Python 复刻，重放记录查看每步状态。汇总记录：`release/summarize_adjust.py`。

## 反查（2026-10-05）
- 用法同 2.5：`` ` ``+全拼或双拼，列出该读音的字〔拆分 · 码〕。NB46 单字方案另有 F2 / `~~码`：列出以该码开头的常用字。
- 整句方案只支持 `` ` ``（整句引擎用 `~` 作暂存标记，不能用 `~~`/F2）。
- 数据：`python rime/make_lookup.py <码表> rime/Rime/lua/yeying30_{nb46,sentence}_lookup_data.lua [有一简1/0]`，改码后需重新生成。
- 依赖 2.5 已装的 `yeying25_mac_lookup_key.lua`、`yeying25_shape_lookup_input.lua`。
