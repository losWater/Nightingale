from pathlib import Path
import hashlib
import json
import re
import shutil
import zipfile

W = Path(r"E:\夜莺2.0\work\夜莺2.0")
P = W / "73_班字架标注"
U = W / "65_群友离线工具包"
O = U / "夜莺2.0离线工具包"
B = P / "修改前备份"
B.mkdir(parents=True, exist_ok=True)


def patch_view(name: str, text: str) -> str:
    if name == "practice":
        old = "'衣':'衣（字架）'}[name]||name)"
        new = "'衣':'衣（字架）','玨':'班（字架）'}[name]||name)"
        if new in text:
            return text
        assert text.count(old) == 1
        text = text.replace(old, new)
    elif name == "roots":
        old = "<td>玨</td><td>王／丰</td><td>班、琴、瑟、斑</td>"
        new = "<td>班（字架）</td><td>王／丰</td><td>班、琴、瑟、斑</td>"
        if new in text:
            return text
        assert text.count(old) == 1
        text = text.replace(old, new)
    elif name == "image":
        # data-search keeps the canonical component name 玨; only visible text changes.
        old = "举字底、王、玨、玉、丰、龶"
        if text.count("举字底、王、班（字架）、玉、丰、龶") == 2:
            return text
        assert text.count(old) == 2
        text = text.replace(old, "举字底、王、班（字架）、玉、丰、龶")
    elif name in {"query", "components"}:
        if "const rootLabel=n=>n==='玨'?'班（字架）':n;" in text:
            return text
        # Keep data-root and matching on canonical 玨, change only visible labels.
        marker = "const esc=s=>String(s).replace"
        assert text.count(marker) == 1
        text = text.replace(marker, "const rootLabel=n=>n==='玨'?'班（字架）':n;" + marker)
        text = text.replace("<b>${esc(r.根)}</b><small>", "<b>${esc(rootLabel(r.根))}</b><small>")
        text = text.replace("<b>${esc(x.根)}</b><span>", "<b>${esc(rootLabel(x.根))}</b><span>")
        text = text.replace("首根：${esc(r.根[0].根)}", "首根：${esc(rootLabel(r.根[0].根))}")
        text = text.replace("末根：${esc(r.根.at(-1).根)}", "末根：${esc(rootLabel(r.根.at(-1).根))}")
    return text


view_files = {
    "query": "拆分查询.html",
    "components": "部件反查.html",
    "practice": "字根练习.html",
    "roots": "字根总表.html",
    "image": "字根图.html",
    "text": "完整拆分表.html",
}

for key, filename in view_files.items():
    path = O / filename
    original = path.read_text(encoding="utf-8-sig")
    if not (B / filename).exists():
        shutil.copy2(path, B / filename)
    updated = patch_view(key, original)
    path.write_text(updated, encoding="utf-8-sig")

wrappers = [U / "夜莺2.0随身工具_单文件.html", U / "夜莺啾啾工具箱.html"]
for path in wrappers:
    original = path.read_text(encoding="utf-8-sig")
    if not (B / path.name).exists():
        shutil.copy2(path, B / path.name)
    a = original.index("const views=") + len("const views=")
    b = original.index(";const frames={}", a)
    views = json.loads(original[a:b])
    for key in view_files:
        views[key] = patch_view(key, views[key])
    payload = json.dumps(views, ensure_ascii=False, separators=(",", ":"))
    payload = re.sub(r"</script\s*>", r"<\\/script>", payload, flags=re.I)
    updated = original[:a] + payload + original[b:]
    assert len(re.findall(r"</script\s*>", updated, re.I)) == 1
    path.write_text(updated, encoding="utf-8-sig")

# Refresh the package manifests before rebuilding the archive.
for manifest_name in ["文件核验.json", "构建核验.json"]:
    manifest_path = U / manifest_name
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    files = manifest.get("文件", manifest)
    for filename in list(files):
        target = O / filename
        if target.is_file():
            files[filename] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

# Rebuild the multipage archive from the updated folder.
zip_path = U / "夜莺2.0离线工具包.zip"
if not (B / zip_path.name).exists():
    shutil.copy2(zip_path, B / zip_path.name)
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(O.rglob("*")):
        if f.is_file():
            z.write(f, (Path(O.name) / f.relative_to(O)).as_posix())
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None

# Semantic verification: canonical data remains 玨; every user-facing root view labels it.
single = wrappers[1].read_text(encoding="utf-8-sig")
a = single.index("const views=") + len("const views=")
b = single.index(";const frames={}", a)
views = json.loads(single[a:b])
assert "'玨':'班（字架）'" in views["practice"]
assert "<td>班（字架）</td>" in views["roots"]
assert views["image"].count("班（字架）") == 2
assert "rootLabel(n" not in views["query"]  # guard against an accidental malformed name
assert "const rootLabel=n=>n==='玨'?'班（字架）':n;" in views["query"]
assert '"根": "玨"' in views["query"]

report = {
    "显示名": "班（字架）",
    "内部规范根名": "玨",
    "更新页面": ["拆分查询", "部件反查", "字根练习", "字根表", "字根图"],
    "完整拆分数据": "仍使用玨，不改编码与拆分",
    "单文件原始script闭标签": len(re.findall(r"</script\s*>", single, re.I)),
    "单文件SHA256": hashlib.sha256(wrappers[1].read_bytes()).hexdigest(),
    "离线包SHA256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
    "状态": "通过",
}
(P / "核验.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
