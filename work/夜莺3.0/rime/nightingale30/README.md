# 夜莺 3.0 Rime 包（试构建）

用夜莺仓库自己的构建工具出包，但不动正式仓库：
1. `python release/stage_nightingale30.py` 在 `~/.cache/yeying30-build` 搭一个仓库结构（assets、.cache 链到 ~/Nightingale，tools 为副本）和 `夜莺3.0` 维护目录。
2. 把本目录两个 `*.3.0.py` 覆盖到搭台目录 `tools/rime_mac/` 下的同名文件（去掉 `.3.0`）。它们只改了写死的 2.5 测试码：子 zip→zie；尧/翘改为 3.0 码（戈无点在 E：尧 yce/ycee，翘 qneo，悄 qnv）。
3. `python ~/.cache/yeying30-build/tools/maintenance/build_mac.py --root ~/.cache/yeying30-build --verify`
4. `cd ~/.cache/yeying30-build && NIGHTINGALE_REPO=$PWD python3 tools/rime_mac/package_release.py --stamp YYYYMMDD`，再用 `verify_release.py <publication/日期目录>` 验证。

2026-10-07 结果：三方案构建与验证全过；三个 ZIP 发布验证 PASS（V5 / 形码 / 形码单字）。方案 id 仍为 yeying25_*（夜莺仓库的兼容标识），显示名为“夜莺3.0”。
拆分原本只换了“拆分查询”的数据 D（3.0 拆分、NB46 键位、3.0 编码）；工具箱其他视图仍是 2.5 的，待另行更新。
