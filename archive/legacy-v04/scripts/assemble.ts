/**
 * headless 拆分/组装驱动：给定 chai 配置 yaml，输出全部字词的元素序列。
 *
 * 用法: bun scripts/assemble.ts <config.yaml> <output.tsv>
 * 输出: 每行 = 词 \t {"element":..,"index":..} ... \t 频率
 *
 * 注意：hanzi-chai 内部大量 Map 按对象同一性查找，因此整条管线必须
 * 共享同一个 原始字库 实例和同一批 拼音元素/名称映射，不能用库里
 * 各自新建实例的便捷封装（获取字库/获取决策与决策空间/获取字形分析结果）。
 */
import { writeFileSync } from "fs";
import {
  获取原始词典,
  获取原始字库,
  读取配置,
  计算拼音分析与元素映射,
  合并拼写运算,
  决策图,
  计算全部合法元素与元素映射,
  获取组装结果,
  获取自定义分析与元素映射,
} from "../repos/webchai/packages/hanzi-chai/src/index.js";
import {
  下转换,
  标准化自定义,
  构建强类型决策与决策空间,
  构建强类型自定义分析,
} from "../repos/webchai/packages/hanzi-chai/src/utils.js";
import { 合并分类器 } from "../repos/webchai/packages/hanzi-chai/src/classifier.js";
import { 分析拼音 } from "../repos/webchai/packages/hanzi-chai/src/pinyin.js";

const [configPath, outputPath, charsetPath] = process.argv.slice(2);
if (!configPath || !outputPath) {
  console.error("用法: bun scripts/assemble.ts <config.yaml> <output.tsv> [限定字集文件]");
  process.exit(1);
}

const 配置 = 读取配置(configPath);

// 1. 唯一的原始字库实例（含配置内联字符）与词典
const 原始字库 = 获取原始字库(Object.values(配置.data?.repertoire ?? {}) as any);
let 原始词典 = 获取原始词典(undefined);
if (charsetPath) {
  const cs = new Set<string>();
  for (const line of require("fs").readFileSync(charsetPath, "utf-8").split("\n")) {
    const c = line.replace(/^﻿/, "").split("\t")[0];
    if (c && [...c].length === 1) cs.add(c);
  }
  原始词典 = (原始词典 as any).filter((e: any) => {
    const w = e.词 ?? e.word ?? "";
    return [...w].length === 1 && cs.has(w);
  });
  console.error(`字集过滤: ${cs.size} 字 → 词典 ${(原始词典 as any).length} 条`);
}
const 词典 = 原始字库.校验词典(原始词典);

// 2. 字库（字形确定）
const 如字库 = 原始字库.确定(
  标准化自定义(配置.data?.glyph_customization ?? {}),
  配置.data?.transformers ?? [],
  (配置.data?.glyph_sources ?? ["G"]) as any,
);
if (!如字库.ok) throw 如字库.error;
const 字库 = 如字库.value;

// 3. 唯一的一批拼音元素 + 拼音分析
const 拼写运算表 = 合并拼写运算(配置.algebra);
const { 拼音元素映射, 拼音分析映射 } = 计算拼音分析与元素映射(词典, 拼写运算表);
const 拼音分析 = 分析拼音(拼音分析映射, 词典);
console.error(`拼音分析: ${拼音分析.length} 条`);

// 4. 唯一的名称映射（分类器用配置合并版）
const 分类器 = 合并分类器(配置.analysis?.classifier);
const 字符列表 = [...字库].map(({ 字符 }) => 字符);
const { 自定义元素映射 } = 获取自定义分析与元素映射({}, 原始字库);
const { 名称映射 } = 计算全部合法元素与元素映射(字符列表, 分类器, 拼音元素映射, 自定义元素映射);

// 5. 决策（共享名称映射）
const { 决策, 决策空间 } = 构建强类型决策与决策空间(
  配置.form.mapping,
  配置.form.mapping_space ?? {},
  名称映射,
);
const 如线性化 = new 决策图(决策).线性化();
if (!如线性化.ok) throw 如线性化.error;

// 6. 字形分析（直接调用 字库.分析，避免封装函数内部重建决策）
const { 自定义分析映射, 动态自定义分析映射 } = 构建强类型自定义分析(
  字库,
  原始字库,
  名称映射,
  配置.analysis?.customize ?? {},
  配置.analysis?.dynamic_customize ?? {},
);
const 汉字集合 = 原始字库.获取汉字集合(词典);
const 如字形分析 = 字库.分析(
  {
    决策,
    决策空间,
    线性化决策: 如线性化.value,
    自定义分析映射,
    动态自定义分析映射,
    分析配置: 配置.analysis ?? {},
  } as any,
  汉字集合,
);
if (!如字形分析.ok) throw 如字形分析.error;
let 非空 = 0;
for (const [, v] of (如字形分析.value as any).分析结果) if ((v as any[]).length) 非空++;
console.error(`字形分析: ${非空}/${(如字形分析.value as any).分析结果.size} 非空`);

// 7. 组装
const 如组装结果 = 获取组装结果(配置, 决策, 决策空间, 如线性化.value, 拼音分析, 如字形分析.value);
if (!如组装结果.ok) throw 如组装结果.error;

// 可选：完整拆分序列导出（第4参数存在时写 <output>.splits.tsv）
if (charsetPath) {
  const sp: string[] = [];
  for (const [字符, 分析列表] of (如字形分析.value as any).分析结果) {
    if (!分析列表.length) continue;
    const a = 分析列表[0];
    const 序列 = (a.字根序列 ?? []).map((g: any) =>
      g && g.字符 && g.字符.获取名称 ? g.字符.获取名称() : (g.获取名称 ? g.获取名称() : String(g)));
    if (序列.length) sp.push(字符.获取名称() + "\t" + 序列.join(" "));
  }
  writeFileSync(outputPath + ".splits.tsv", sp.join("\n"), "utf-8");
  console.error(`拆分序列已输出 ${sp.length} 条`);
}

const lines: string[] = [];
for (const 条目 of 如组装结果.value) {
  const 词 = 条目.词.map((v: any) => v.获取名称()).join("");
  const 元素 = 条目.元素序列.元素序列.map((e: any) => JSON.stringify(下转换(e))).join(" ");
  lines.push(`${词}\t${元素}\t${条目.频率}`);
}
writeFileSync(outputPath, lines.join("\n"), "utf-8");
console.error(`已输出 ${lines.length} 条到 ${outputPath}`);
