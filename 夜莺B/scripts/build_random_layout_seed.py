#!/usr/bin/env python3
"""从Chai mapping_space生成可复现且经全量约束验证的随机起点。"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import yaml


EQUAL = {"是", "==", "is"}
NOT_EQUAL = {"不是", "!=", "not"}


def condition_holds(condition: dict, mapping: dict) -> bool:
    try:
        element, op, value = condition["element"], condition["op"], condition["value"]
    except KeyError as exc:
        raise ValueError(f"条件缺少字段 {exc.args[0]}：{condition}") from exc
    if element not in mapping:
        raise ValueError(f"条件引用未知元素：{element}")
    if op in EQUAL:
        return mapping[element] == value
    if op in NOT_EQUAL:
        return mapping[element] != value
    raise ValueError(f"未知条件操作符：{op}")


def allowed(arrangement: dict, mapping: dict) -> bool:
    return all(condition_holds(condition, mapping)
               for condition in arrangement.get("condition", []))


def validate_space(space: dict, base_mapping: dict) -> dict[str, set[str]]:
    if not isinstance(space, dict) or not space:
        raise ValueError("mapping_space必须是非空映射")
    dependencies: dict[str, set[str]] = {str(element): set() for element in space}
    known = set(map(str, base_mapping)) | set(dependencies)
    for element, choices in space.items():
        if not isinstance(choices, list) or not choices:
            raise ValueError(f"元素候选必须是非空列表：{element}")
        for choice in choices:
            if not isinstance(choice, dict) or "value" not in choice:
                raise ValueError(f"候选缺少value：{element}/{choice}")
            for condition in choice.get("condition", []):
                reference = str(condition.get("element", ""))
                op = condition.get("op")
                if reference not in known:
                    raise ValueError(f"条件引用未知元素：{element} -> {reference}")
                if op not in EQUAL | NOT_EQUAL:
                    raise ValueError(f"未知条件操作符：{op}")
                if reference in dependencies:
                    dependencies[str(element)].add(reference)
    return dependencies


def dependency_order(dependencies: dict[str, set[str]]) -> list[str]:
    state: dict[str, int] = {}
    order: list[str] = []
    stack: list[str] = []

    def visit(element: str) -> None:
        if state.get(element) == 2:
            return
        if state.get(element) == 1:
            start = stack.index(element)
            raise ValueError("条件依赖存在环：" + " -> ".join(stack[start:] + [element]))
        state[element] = 1
        stack.append(element)
        for dependency in sorted(dependencies[element]):
            visit(dependency)
        stack.pop()
        state[element] = 2
        order.append(element)

    for element in dependencies:
        visit(element)
    return order


def generate_mapping(space: dict, base_mapping: dict, rng: random.Random) -> tuple[dict, dict]:
    dependencies = validate_space(space, base_mapping)
    order = dependency_order(dependencies)
    mapping = dict(base_mapping)
    selected: dict[str, dict] = {}

    # 空间内元素必须由本轮选择产生；移除模板旧值，防止条件误读旧布局。
    for element in space:
        mapping.pop(element, None)

    def solve(position: int) -> bool:
        if position == len(order):
            return True
        element = order[position]
        choices = list(space[element])
        rng.shuffle(choices)
        for choice in choices:
            if not allowed(choice, mapping):
                continue
            mapping[element] = choice["value"]
            selected[element] = choice
            if solve(position + 1):
                return True
            selected.pop(element, None)
            mapping.pop(element, None)
        return False

    if not solve(0):
        raise ValueError("mapping_space不存在满足全部条件的布局")
    validate_mapping(space, mapping, selected)
    return mapping, selected


def validate_mapping(space: dict, mapping: dict, selected: dict[str, dict] | None = None) -> None:
    for element, choices in space.items():
        matches = [choice for choice in choices if choice.get("value") == mapping.get(element)]
        if not matches:
            raise ValueError(f"最终映射不在候选空间：{element}={mapping.get(element)!r}")
        chosen = selected.get(element) if selected is not None else None
        candidates = [chosen] if chosen is not None else matches
        if not any(allowed(choice, mapping) for choice in candidates):
            raise ValueError(f"最终映射违反条件：{element}={mapping[element]!r}")


def mapping_space(config: dict) -> dict:
    generated = config.get("generated_mapping_space")
    legacy = config.get("form", {}).get("mapping_space")
    if generated is not None and legacy is not None and generated != legacy:
        raise ValueError("generated_mapping_space与form.mapping_space冲突")
    return generated if generated is not None else legacy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()

    config = yaml.safe_load(args.template.read_text(encoding="utf-8"))
    space = mapping_space(config)
    mapping, _ = generate_mapping(space, config["form"]["mapping"], random.Random(args.seed))
    config["form"]["mapping"] = mapping
    config.setdefault("experiment", {})["random_seed"] = args.seed

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(
        config, allow_unicode=True, sort_keys=False, width=10_000
    ), encoding="utf-8")
    print(f"output={args.output.resolve()}")
    print(f"randomized_elements={len(space)} seed={args.seed}")


if __name__ == "__main__":
    main()
