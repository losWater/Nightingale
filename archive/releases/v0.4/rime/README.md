# 夜莺码 Rime 方案 v0.4

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
5. `Ctrl+\`（或 F4）切到"夜莺码"

Linux ibus-rime 用 `~/.config/ibus/rime/`，Windows 小狼毫用 `%APPDATA%\Rime\`，步骤相同。

## 键位约定

- 空格上屏首选；`;` 二选、`'` 三选；`-`/`=` 翻页；数字键直选
- 最长四码，精确匹配出词（不显示补全候选），候选顺序固定不随使用调整
- 想要四码唯一自动上屏：在 `yeying.schema.yaml` 的 `speller` 段取消 `auto_select` 两行注释
- 想让常用字按使用频率前移：`translator/enable_user_dict` 改 `true`

## 更新

Windows 侧 `python scripts/nightingale.py rebuild` 会重生成本目录；把两份 yaml 覆盖到 Rime 目录后重新部署即可。
