from pathlib import Path
import os,sys,json
p=Path(sys.argv[1] if len(sys.argv)>1 else os.environ.get("LIP_MOTION_ROOT", ".")).resolve()
ok=(p/"START_HERE.md").is_file() and (p/"renderer/kit.py").is_file()
print(json.dumps({"root":str(p),"runtime_found":ok},ensure_ascii=False))
sys.exit(0 if ok else 2)
