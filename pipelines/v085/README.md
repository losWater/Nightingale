# 0.8.5 构建入口

正式维护只需要记住一个命令：

```powershell
python .\pipelines\v085\rebuild.py
```

它从两张正式主表重建码前镜像、搜狗挂接表和手心挂接表。使用 `--check-only` 可以只检查必需输入，使用 `--skip-palm` 可以跳过手心文件。

当前入口委托给 `work/夜莺0.85/scripts/rebuild_v085_attachments.py`。这是迁移期的兼容层：外部命令已经稳定，内部实现将在通过逐项回归后迁入本目录。
