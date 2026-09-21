# Rime 挂接（夜莺2.5）

- `Rime_轻量版/`：轻量版全部文件（Rime 原生整句），解压即用，详见其中 使用说明.md。
- 主力版「夜莺主力」：**主体是魔虎（rime-mohu，作者 晴，https://github.com/fcxxxz/rime-mohu ，GPL v3）**，整句引擎、V5 模型与全部功能脚本是魔虎作者的成果，夜莺换上了自己的码表、词库、辅码、拆分；文件改用 yeying 名字以便与魔虎原版共存，出处逐文件注明（包内有声明与改动清单）。约 450MB，不入 git：见 GitHub Release ' + TAG + ' 附件 `Nightingale-Rime-2.5-main-20260922.zip`；本地留存在 `发布包/`（已 gitignore，中文文件名）。
- 手机版（轻量版 + 万象 LTS 语法模型 `wanxiang-lts-zh-hans.gram`，约 360MB，供同文/仓输入法等手机 Rime）：Release 附件 `Nightingale-Rime-2.5-mobile-20260922.zip`；魔虎 V5 引擎只有 Windows 版，手机用不了。
- 轻量版与手机版：Ctrl+数字 钉选、二字自动造词、Ctrl+Enter 主动造词；主力版用魔虎自带的置顶与加词。三版共有：反引号双拼/波浪号全拼反查、F2、40 条快符。
- 校验：`发布包/校验值SHA256.txt`。
