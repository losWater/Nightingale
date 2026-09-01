# Pipelines

这里将统一保存夜莺的构建、审计与发布程序。

重构目标：所有脚本通过公共路径配置访问`schema`，禁止散落硬编码的版本目录。当前脚本在验证迁移前仍保留于`work/夜莺0.85/scripts`等原路径。

- `v085/rebuild.py`：0.8.5正式派生表的稳定入口。
- `v085/README.md`：维护命令和迁移状态。
- `verify.py`：检查0.8.5入口并运行根目录单元测试。

仓库级快速门禁：

```powershell
python .\pipelines\verify.py
```
