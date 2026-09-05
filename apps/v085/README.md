# 0.9.1 离线应用

0.9.1发布包包含以下离线网页。这里记录它们的生成器与发布位置，避免把内嵌大数据的HTML误当作唯一源码。

|应用|生成器或模板|发布物|
|---|---|---|
|编码反查|`templates/reverse_lookup.html`＋`work/夜莺0.85/scripts/build_reverse_lookup.py`|`releases/v0.9.1/04_查询与练习/夜莺码v0.9.1编码反查.html`|
|拆分查询|`templates/split_lookup.html`＋`work/夜莺0.85/scripts/build_v085_release.py`|`releases/v0.9.1/04_查询与练习/夜莺码v0.9.1拆分查询.html`|
|部件查字|`templates/component_lookup.html`＋`work/夜莺0.85/scripts/build_v085_component_lookup.py`|`releases/v0.9.1/04_查询与练习/夜莺码v0.9.1部件查字.html`|
|字根练习|`templates/root_practice.html`＋`work/夜莺0.85/scripts/build_v085_release.py`|`releases/v0.9.1/04_查询与练习/夜莺码v0.9.1字根练习器.html`|
|必拆字练习|`templates/must_split_practice.html`＋`work/夜莺0.85/scripts/build_v085_must_split_practice.py`|`releases/v0.9.1/04_查询与练习/必拆字/夜莺码v0.9.1必拆字练习.html`|

五个离线工具均已完成模板抽离。发布HTML始终留在`releases/`，模板负责页面外壳，生成器负责写入当前方案数据。

模板迁移回归在临时目录生成页面，不自动覆盖冻结发布页。发布页只有在明确进行版本维护并刷新发布清单时才重建。
