/**
 * Nightingale 0.8 structural audit adapter.
 *
 * This file contains no Nightingale split decisions. It loads one generated
 * Chai config, analyzes an explicit character list, and writes the first root
 * sequence returned by hanzi-chai for every requested character.
 */
import { writeFileSync, readFileSync } from "fs";
import {
  获取原始字库,
  读取配置,
  决策图,
  计算全部合法元素与元素映射,
  获取自定义分析与元素映射,
} from "../../../repos/webchai/packages/hanzi-chai/src/index.js";
import {
  标准化自定义,
  构建强类型决策与决策空间,
  构建强类型自定义分析,
} from "../../../repos/webchai/packages/hanzi-chai/src/utils.js";
import { 合并分类器 } from "../../../repos/webchai/packages/hanzi-chai/src/classifier.js";

const [configPath, charsetPath, outputPath] = process.argv.slice(2);
if (!configPath || !charsetPath || !outputPath) {
  console.error("usage: bun chai_split_runner.ts <config.yaml> <charset.txt> <output.json>");
  process.exit(2);
}

const config = 读取配置(configPath);
const raw = 获取原始字库(Object.values(config.data?.repertoire ?? {}) as any);
const determined = raw.确定(
  标准化自定义(config.data?.glyph_customization ?? {}),
  config.data?.transformers ?? [],
  (config.data?.glyph_sources ?? ["G"]) as any,
);
if (!determined.ok) throw determined.error;
const repertoire = determined.value;

const requested = readFileSync(charsetPath, "utf-8")
  .replace(/^\uFEFF/, "")
  .split(/\r?\n/)
  .map((x) => x.trim())
  .filter(Boolean);
const requestedSet = new Set(requested);
const characters = new Set<any>();
const unresolved: string[] = [];
for (const value of requested) {
  const found = raw.校验(value)?.character;
  if (found) characters.add(found);
  else unresolved.push(value);
}
if (unresolved.length) {
  throw new Error(`characters absent from Chai repertoire: ${unresolved.join(" ")}`);
}

const classifier = 合并分类器(config.analysis?.classifier);
const characterList = [...repertoire].map(({ 字符 }) => 字符);
const { 自定义元素映射 } = 获取自定义分析与元素映射({}, raw);
const { 名称映射 } = 计算全部合法元素与元素映射(
  characterList,
  classifier,
  new Map(),
  自定义元素映射,
);
const { 决策, 决策空间 } = 构建强类型决策与决策空间(
  config.form.mapping,
  config.form.mapping_space ?? {},
  名称映射,
);
const linearized = new 决策图(决策).线性化();
if (!linearized.ok) throw linearized.error;
const { 自定义分析映射, 动态自定义分析映射 } = 构建强类型自定义分析(
  repertoire,
  raw,
  名称映射,
  config.analysis?.customize ?? {},
  config.analysis?.dynamic_customize ?? {},
);
const analyzed = repertoire.分析(
  {
    决策,
    决策空间,
    线性化决策: linearized.value,
    自定义分析映射,
    动态自定义分析映射,
    分析配置: config.analysis ?? {},
  } as any,
  characters,
);
if (!analyzed.ok) throw analyzed.error;

const rows: Record<string, string[]> = {};
const strokeCounts: Record<string, number> = {};
const missingStrokeDebug: Record<string, unknown[]> = {};
const topLevel: Record<string, unknown> = {};
for (const [character, analyses] of (analyzed.value as any).分析结果) {
  const name = character.获取名称();
  // Chai also analyzes dependency components. They are useful internally but
  // are not part of this counterfactual's declared observation set.
  if (!requestedSet.has(name)) continue;
  const first = analyses[0];
  const roots = first?.字根序列 ?? [];
  rows[name] = roots.map((root: any) => root.字符?.获取名称?.() ?? root.获取名称?.() ?? String(root));
  const counts = roots.map((root: any) =>
    Array.isArray(root?.笔画列表) ? root.笔画列表.length
      : typeof root?.获取笔画列表 === "function" ? root.获取笔画列表().length
      : root?.constructor?.name === "笔画" ? 1
      : root?.constructor?.name === "二笔" ? 2
      : undefined
  );
  if (counts.every((x: number | undefined) => x !== undefined)) {
    strokeCounts[name] = counts.reduce((sum: number, x: number) => sum + x, 0);
  } else {
    missingStrokeDebug[name] = roots.map((root: any) => ({
      constructor: root?.constructor?.name,
      keys: root ? Object.keys(root) : [],
      character: root?.字符?.获取名称?.(),
    }));
  }
  if (first?.类型 === "复合体" && first.复合体) {
    const orderedParts = first.复合体.按首笔排序部分();
    topLevel[name] = {
      type: "compound",
      operator: first.复合体.结构描述字符,
      visual_parts: (first.复合体.部分列表 ?? []).map((part: any) => part?.字符?.获取名称?.()),
      parts: orderedParts.map((part: any) => part?.字符?.获取名称?.()),
    };
  } else {
    topLevel[name] = { type: "component", parts: [] };
  }
}
writeFileSync(outputPath, JSON.stringify({
  requested: requested.length,
  analyzed_with_dependencies: (analyzed.value as any).分析结果.size,
  rows,
  stroke_counts: strokeCounts,
  missing_stroke_debug: missingStrokeDebug,
  top_level: topLevel,
}, null, 2), "utf-8");
