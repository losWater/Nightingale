from pathlib import Path
import ctypes,json,time,psutil
p=Path(__file__).resolve().parent
try:
 ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
 while True:
  try:
   s=json.loads((p/'status.json').read_text(encoding='utf-8'))
   if s['stage'] in ['complete','needs_attention'] or not psutil.pid_exists(s['pid']):break
  except (OSError,ValueError,KeyError):pass
  time.sleep(30)
finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
