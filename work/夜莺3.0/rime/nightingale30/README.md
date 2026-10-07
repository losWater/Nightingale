# 夜莺 3.0 Rime 包（试构建）

用夜莺仓库自己的构建工具出包，但不动正式仓库：
1. `python release/stage_nightingale30.py` 在 `~/.cache/yeying30-build` 搭一个仓库结构：assets、.cache 链到 ~/Nightingale；tools 复制一份并自动处理——
   - 标识去掉版本号：`yeying25_` → `yeying_`（方案 id、文件名、Lua 模块、用户词库名）。作者 2026-10-07：标识里不要写版本号，否则升级时要么残留旧版本号、要么不兼容。
   - 说明与注释里的 v2.5 → v3.0；验证脚本写死的 2.5 测试码换成 3.0（子 zie；尧 yce/ycee、翘 qneo、悄 qnv）。
2. `python ~/.cache/yeying30-build/tools/maintenance/build_mac.py --root ~/.cache/yeying30-build --verify`
3. `cd ~/.cache/yeying30-build && NIGHTINGALE_REPO=$PWD python3 tools/rime_mac/package_release.py --stamp YYYYMMDD`，再 `verify_release.py <publication/日期目录>`。

2026-10-07：三方案构建与验证全过，三个 ZIP 发布验证 PASS；方案 id 为 yeying_v5 / yeying_shape / yeying_single。
拆分原本只换了“拆分查询”的数据 D；工具箱其他视图仍是 2.5 的，待另行更新。
夜莺仓库 AGENTS.md / MAINTENANCE.md 里“schema_id 中的历史数字是兼容标识”的说法不符合作者本意，接入正式仓库时一并改掉。
