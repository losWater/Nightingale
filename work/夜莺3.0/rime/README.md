# NB46 单字试用方案（Rime）

`Rime/` 下是装进 `~/Library/Rime` 的文件：
- `yeying30_nb46_single.schema.yaml`：方案（以夜莺 2.5 单字版为模板；依赖其 `lua/yeying25_single_english_guard.lua`）。
- `yeying30_nb46_single.dict.yaml`：NB46 普通单字表 + 2.5 快符；嗯 en 为二简。
- `yeying30_nb46_freq.txt`：核心读音字频（调频插件按字频补空位用）。
- `lua/yeying30_nb46_adjust_*.lua`：手动调频插件。Control+数字 提到首选；Control+U 上移；Control+J/D 下移；Control+0 撤销上一步。
  记录写在 `~/Library/Rime/yeying30_nb46_adjust.tsv`。

`adjust_sim.py`：插件逻辑的 Python 复刻，重放记录查看每步状态。汇总记录：`release/summarize_adjust.py`。
