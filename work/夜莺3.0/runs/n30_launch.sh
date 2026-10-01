#!/bin/zsh
cd ~/Yozakura
export TOUR=n30 GROUPS=16 SQUADS=4 SQUAD_KINDS='proj,proj,proj,proj'
export WEIGHTS_EXTRA='{"scheme": "xiaohe", "shape_cost": 6000, "eq23": 0, "eq34": 0, "clash": true, "cross": 0, "p_cap": 0.04, "p_weight": 10000, "move_cost": 10, "clash_3500_1w": 200, "clash3_allow": 5, "clash_1500_3w": 30, "eff3500": 200, "eff3500_allow": 9}'
.venv/bin/python -W ignore tournament/runner.py init 2>&1 | grep -E '任务|留给词'
.venv/bin/python -u tournament/runner.py run
echo 全部完成
