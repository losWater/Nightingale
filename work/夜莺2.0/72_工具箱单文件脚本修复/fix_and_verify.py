from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

W = Path(r"E:\夜莺2.0\work\夜莺2.0")
P = W / "72_工具箱单文件脚本修复"
U = W / "65_群友离线工具包"
B = P / "修复前备份"
B.mkdir(parents=True, exist_ok=True)

targets = [U / "夜莺2.0随身工具_单文件.html", U / "夜莺啾啾工具箱.html"]
report = {"问题": "内嵌页面的 </script> 提前终止单文件外层脚本", "文件": {}}

for path in targets:
    original = path.read_text(encoding="utf-8-sig")
    shutil.copy2(path, B / path.name)
    start = original.index("<script>const views=") + len("<script>")
    end_marker = "};const frames={}"
    end = original.index(end_marker, start) + 1
    payload = original[start:end]
    inner_closers = len(re.findall(r"</script\s*>", payload, re.I))
    if inner_closers != 6:
        raise AssertionError(f"{path.name}: expected 6 embedded script closers, got {inner_closers}")
    fixed_payload = re.sub(r"</script\s*>", r"<\\/script>", payload, flags=re.I)
    fixed = original[:start] + fixed_payload + original[end:]
    # An opening <script> string is harmless inside JavaScript raw text. Only a
    # literal closing tag terminates the outer HTML script element.
    if len(re.findall(r"</script\s*>", fixed, re.I)) != 1:
        raise AssertionError(f"{path.name}: raw script closer count is not 1")
    path.write_text(fixed, encoding="utf-8-sig")

    script = re.search(r"<script>([\s\S]*)</script>\s*</html>\s*$", fixed, re.I)
    if not script:
        raise AssertionError(f"{path.name}: cannot extract the sole outer script")
    check_file = P / (path.stem + "_外层脚本检查.js")
    check_file.write_text(script.group(1), encoding="utf-8")
    checked = subprocess.run(["node", "--check", str(check_file)], capture_output=True, text=True)
    if checked.returncode:
        raise AssertionError(checked.stderr)
    report["文件"][path.name] = {
        "修复内嵌结束标签": inner_closers,
        "外层script元素": 1,
        "HTML原始script闭标签": 1,
        "Node外层语法检查": "通过",
        "SHA256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }

report["状态"] = "两个单文件入口已修复；外层脚本不会被内嵌页面提前截断"
(P / "修复核验.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
