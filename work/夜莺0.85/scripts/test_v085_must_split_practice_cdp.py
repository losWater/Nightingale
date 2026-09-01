#!/usr/bin/env python3
"""通过 Chrome DevTools Protocol 冒烟测试必拆字练习页面。"""

from __future__ import annotations

import json
import os
import time
import urllib.request

import websocket


def main() -> None:
    port = os.environ.get("NIGHTINGALE_CDP_PORT", "9333")
    targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=5))
    target = next(item for item in targets if "必拆字" in item.get("title", ""))
    ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=5)
    sequence = 0

    def call(method: str, params: dict | None = None) -> dict:
        nonlocal sequence
        sequence += 1
        ws.send(json.dumps({"id": sequence, "method": method, "params": params or {}}))
        while True:
            message = json.loads(ws.recv())
            if message.get("id") == sequence:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message.get("result", {})

    def evaluate(expression: str):
        result = call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        return result["result"].get("value")

    evaluate("localStorage.clear(); location.reload()")
    time.sleep(0.8)
    evaluate("document.querySelector('[data-mode=full]').click()")
    first = evaluate("({char:q().char,targets:targets(),count:document.querySelectorAll('.cell').length})")
    assert first["count"] == 4
    evaluate("['u','r','u'].forEach(k=>document.dispatchEvent(new KeyboardEvent('keydown',{key:k})));document.dispatchEvent(new KeyboardEvent('keydown',{key:'Backspace'}))")
    backspace = evaluate("({typed,failures,cells:[...document.querySelectorAll('.cell')].map(x=>x.textContent).join('')})")
    assert backspace == {"typed": "ur", "failures": 0, "cells": "ur"}
    evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Backspace'}));document.dispatchEvent(new KeyboardEvent('keydown',{key:'Backspace'}))")
    wrong = evaluate("['aaaa','zzzz','qqqq'].find(x=>!targets().includes(x))")
    for _ in range(5):
        evaluate(f"[...'{wrong}'].forEach(k=>document.dispatchEvent(new KeyboardEvent('keydown',{{key:k}})))")
        time.sleep(0.55)
    revealed = evaluate("({shown:split.classList.contains('show'),text:split.textContent,notice:notice.textContent})")
    assert revealed["shown"] and revealed["text"] and "五次" in revealed["notice"]
    correct = first["targets"][0]
    evaluate(f"[...'{correct}'].forEach(k=>document.dispatchEvent(new KeyboardEvent('keydown',{{key:k}})))")
    time.sleep(0.15)
    success = evaluate("({good:answer.classList.contains('good'),shown:split.classList.contains('show')})")
    assert success == {"good": True, "shown": True}
    time.sleep(1.05)
    after_full = evaluate("({char:q().char,state:JSON.parse(localStorage.getItem(STORE))})")
    assert after_full["char"] != first["char"] and after_full["state"]["full"]["index"] == 1

    evaluate("document.querySelector('#menu').click();document.querySelector('[data-mode=short]').click()")
    short = evaluate("({char:q().char,target:targets()[0],bars:document.querySelectorAll('.bar').length})")
    assert short["bars"] == 1
    evaluate(f"[...'{short['target']}'].forEach(k=>document.dispatchEvent(new KeyboardEvent('keydown',{{key:k}})))")
    time.sleep(1.1)
    saved = evaluate("JSON.parse(localStorage.getItem(STORE))")
    assert saved["full"]["index"] == 1 and saved["short"]["index"] == 1 and saved["lastMode"] == "short"
    call("Page.reload")
    time.sleep(0.8)
    persisted = evaluate("({mode,state:JSON.parse(localStorage.getItem(STORE)),continueHidden:document.querySelector('#continue').hidden})")
    assert persisted["mode"] == "short" and persisted["state"]["short"]["index"] == 1 and not persisted["continueHidden"]
    print(json.dumps({"first": first["char"], "backspace": backspace, "next": after_full["char"], "five_fail_split": revealed["text"],
                      "short_length": len(short["target"]), "progress_persisted": True}, ensure_ascii=False))
    ws.close()


if __name__ == "__main__":
    main()
