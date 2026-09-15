# 夜莺网站

无第三方运行依赖的静态网站，支持移动端、明暗主题与键盘操作。

本地预览：

```powershell
python apps/website/build.py
python -m http.server 8765 --bind 127.0.0.1 --directory .tmp/website-preview
```

浏览器打开 http://127.0.0.1:8765 。生成目录位于 `.tmp/website-preview`，不提交。

构建来源为 `releases/v2.0`；作者文章读取 `素材/作者的话.md`。构建依赖 Python Markdown（`pip install Markdown`），浏览器运行无需依赖。

正式网站：https://loswater.github.io/Nightingale/ 。GitHub Pages 使用 gh-pages 分支根目录，发布时上传 `.tmp/website-preview` 的构建结果。码表与 Rime 包在 v2.0 Release 附件。

## 2.0 改版（2026-09-16）

- 首页：发布状态、方案数据（130 组字根、前 1500 字选重 0、字词冲突 55→0）、下载区指向 v2.0 Release 附件（Rime 主力/轻量、各平台码表、啾啾工具箱）、更新日志指向 `releases/v2.0/夜莺2.0升级日志.md`。
- 工具页：从 `releases/v2.0/04_查询与练习/离线工具包/` 复制拆分查询、部件反查、字根练习、完整拆分表、字根图，另发布啾啾工具箱单文件（`tools/toolbox.html`）；每页右下角加返回首页链接。1.0 的编码反查并入拆分查询（输入编码即可），必拆字练习不再提供。
- 字根表：由 `04_查询与练习/离线工具包/字根练习.html` 内嵌的 404 条根形数据（根、键、组、例字，与工具箱同一份定稿）生成，按组名分组、组名首段为主根，130 组 / 404 根形，沿用主根版 / 归并版两种展示与搜索、打印。`03_字根与拆分/夜莺2.0当前完整根表.json` 是 07 阶段的旧表（仍含已删的古组），不作构建来源。
- 性能页：数据改为 `performance-data.json`（2.0 重算，脚本 `work/夜莺2.0/118_官网2.0/compute_performance.py`），包含码长分布、选重、全码非首选、加权键长与当量、键位负担、左右手、互击与跨排，以及字词冲突（前 1500 字 × 前 10000 词）。1.0 的截图转录数据与字词冲突复算文件不再随站发布。
- 网站源文件在工作区 `work/夜莺2.0/118_官网2.0/site/` 维护，`sync_to_repo.py` 同步到本目录后再构建。
