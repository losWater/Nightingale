#!/bin/zsh
cd ~/Yozakura
until [ "$(ls runs/n30/*/n30eval.json 2>/dev/null | wc -l | tr -d ' ')" -ge 256 ]; do sleep 60; done
echo "$(date +%H:%M) 第一轮评测完成"
.venv/bin/python -W ignore tournament/n30_rank.py round1 2>&1 | grep -v -i warn
echo "$(date +%H:%M) 开始第二轮"
.venv/bin/python -W ignore -u tournament/n30_rank.py round2 2>&1 | grep -v -i warn | tail -8
echo "$(date +%H:%M) 第二轮完成"
