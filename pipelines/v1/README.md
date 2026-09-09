# 夜莺1.0发布包构建

运行 `python pipelines/v1/prepare.py` 生成 `releases/v1.0`、`releases/夜莺1.0.zip` 和SHA256文件。此脚本只打包，不执行Git推送或线上发布。

离线字根表模板位于assets，构建不依赖尚未发布的网站。改码后先重建真源的挂接和查询工具，再执行打包及仓库检查。
