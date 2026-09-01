#!/usr/bin/env bun
/** 使用项目实际libchai WASM校验配置，而不只做YAML结构检查。 */
import fs from "node:fs";
import yaml from "../../../repos/webchai/node_modules/js-yaml/index.js";
import init, { validate } from "../../../repos/webchai/node_modules/libchai/chai.js";

const path = process.argv[2];
if (!path) throw new Error("用法：bun validate_chai_config_native.ts <config.yaml>");
await init();
const config = yaml.load(fs.readFileSync(path, "utf8"));
const roundTripped = validate(config) as Record<string, unknown>;
const report = { status: "pass", config: path, name: (roundTripped.info as any)?.name };
if (process.argv[3]) fs.writeFileSync(process.argv[3], JSON.stringify(report, null, 2) + "\n", "utf8");
console.log(JSON.stringify(report));
