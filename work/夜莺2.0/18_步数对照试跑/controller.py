from pathlib import Path
import sys,copy,msvcrt,ctypes,traceback
P=Path(__file__).resolve().parent;T=P.parent/'15_自动晋级赛';sys.path.insert(0,str(T))
from common import *
source=(T/'controller.py').read_text(encoding='utf-8').split('def finish(')[0]
ns={'__file__':str(P/'controller.py')};exec(source,ns);ns['ROOT']=P;ns['STATE']=P/'status.json';ns['SET']=copy.deepcopy(SET)
ns['status'].__globals__['__builtins__']=__builtins__
if __name__=='__main__':
 lock=(P/'controller.lock').open('a+b');lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 try:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
  results=ns['batch'](read(P/'cards.json'),2)
  import subprocess
  subprocess.run([sys.executable,str(P/'report.py')],cwd=P,check=True)
  ns['status']('complete',completed=15,report=str(P/'步数对照结果.html'))
 except Exception:
  error=traceback.format_exc();(P/'controller_error.txt').write_text(error,encoding='utf-8');ns['status']('needs_attention',error=error[-3000:]);raise
 finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
