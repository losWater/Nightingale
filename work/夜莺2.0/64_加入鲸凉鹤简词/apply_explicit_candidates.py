from pathlib import Path
import json
def apply(combined,short_only=False,normalize=None):
 targets=json.loads((Path(__file__).parent/'码位人工指定.json').read_text(encoding='utf-8'))
 migrated={}
 for code,terms in targets.items():
  for term in terms:
   target=normalize(term,code) if normalize else code
   migrated.setdefault(target,[])
   if term not in migrated[target]:migrated[target].append(term)
 for code,terms in migrated.items():
  if short_only and len(code)>=4:continue
  current=combined.get(code,[])
  assert all(t in current for t in terms),(code,terms,current)
  combined[code]=terms+[t for t in current if t not in terms]
 return combined
