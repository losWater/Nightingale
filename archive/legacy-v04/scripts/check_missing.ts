/** 盘点配置引用了哪些当前字库里不存在的字符 */
import { 获取原始字库, 读取配置 } from "../repos/webchai/packages/hanzi-chai/src/index.js";

const 配置 = 读取配置(process.argv[2]!);
const 原始字库 = 获取原始字库();
const known = new Set<string>();
for (const item of 原始字库 as any) known.add(String.fromCodePoint(item.unicode));
console.error(`当前字库字符数: ${known.size}`);

const inline = new Set(Object.keys(配置.data?.repertoire ?? {}));
const referenced = new Map<string, string>(); // char -> 来源
function ref(c: string, src: string) {
  if (c.length === 0) return;
  for (const ch of c) {
    if (!known.has(ch) && !inline.has(ch) && !referenced.has(ch)) referenced.set(ch, src);
  }
}
const gc = 配置.data?.glyph_customization ?? {};
for (const [k, v] of Object.entries(gc) as any) {
  ref(k, `glyph_customization 键`);
  if (v.operandList) for (const op of v.operandList) ref(op, `glyph_customization[${[...k].map(c=>"U+"+c.codePointAt(0)!.toString(16)).join()}].operand`);
  if (v.source) ref(v.source, `glyph_customization source`);
}
for (const k of Object.keys(配置.form?.mapping ?? {})) if (!k.includes("-") && k.length <= 2) ref(k, "form.mapping");
for (const [k, v] of Object.entries(配置.form?.grouping ?? {})) { ref(k, "form.grouping键"); ref(String(v), "form.grouping值"); }
const cz = (配置.analysis as any)?.customize ?? {};
for (const [k, arr] of Object.entries(cz) as any) { ref(k, "customize键"); for (const c of arr) ref(c, `customize[${k}]`); }

console.log(`缺失字符 ${referenced.size} 个:`);
for (const [c, src] of referenced) {
  console.log(`U+${c.codePointAt(0)!.toString(16).toUpperCase()}\t${src}`);
}
