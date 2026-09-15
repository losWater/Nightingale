from pathlib import Path
import psutil,json,time,subprocess,sys,ctypes
p=Path(__file__).resolve().parent
ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
try:
 pending=json.loads((p/'扩容记录/等待进程.json').read_text())
 while True:
  alive=[]
  for v in pending:
   try:
    q=psutil.Process(v['pid'])
    if abs(q.create_time()-v['created'])<.1:alive.append(v)
   except psutil.Error:pass
  if not alive:break
  pending=alive
  print('Waiting for existing workers:',[v['pid'] for v in alive],flush=True)
  time.sleep(15)
 with (p/'controller_stdout.log').open('a',encoding='utf-8') as out,(p/'controller_stderr.log').open('a',encoding='utf-8') as err:
  c=subprocess.Popen([sys.executable,str(p/'controller.py')],cwd=p,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
  print('Controller restarted',c.pid,flush=True)
  time.sleep(5)
  assert c.poll() is None,'controller failed to restart'
  subprocess.Popen([sys.executable,str(p/'keep_awake.py')],cwd=p,creationflags=subprocess.CREATE_NO_WINDOW)
finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
