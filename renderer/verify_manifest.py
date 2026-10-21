from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'manifest-sha256.json').read_text())
errors=[]
for name,expected in manifest.items():
 p=(root/name).resolve()
 if not p.is_relative_to(root) or not p.is_file():errors.append(name+': missing/invalid path');continue
 if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:errors.append(name+': hash mismatch')
print(json.dumps({'pass':not errors,'checked_files':len(manifest),'errors':errors},ensure_ascii=False,indent=2))
sys.exit(1 if errors else 0)
