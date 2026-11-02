"""Verify a manifest against files on disk.

Default mode (no arguments) is unchanged: it checks the repo's own
manifest-sha256.json (one sha256 per tracked file).

Job mode (--job-manifest <path> --job-root <dir>) checks a JOB image
manifest instead -- the format ported from the Kurt P0-1 gate:
{"beats": {name: {"file": relpath, "sha256": hex, "status": "accepted"}},
 "rejected": [{"file": relpath, ...}]}
Rules ported with it: a beat's file must exist, be marked accepted,
and match its recorded sha256, and be at least 1024x768; a rejected
file must NOT sit in the job's images directory itself (rejected files
live in a separate rejected/ folder). Names must match the manifest
exactly -- glob fallback to a similarly-named file is banned, because
it can silently pick an older, rejected render.
Usage: python3 renderer/verify_manifest.py [--job-manifest images.json --job-root JOBDIR [--images-dir images]]
"""
from pathlib import Path
import argparse,hashlib,json,sys

def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda: f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()

def check_job_manifest(manifest_path,job_root,images_dir=None):
 manifest=json.loads(Path(manifest_path).read_text())
 errors=[];checked=0
 for name,entry in sorted(manifest.get('beats',{}).items()):
  checked+=1;p=(job_root/entry['file']).resolve()
  if entry.get('status')!='accepted':errors.append(f'{name}: status is not accepted');continue
  if not p.is_file():errors.append(f'{name}: missing {entry["file"]}');continue
  if sha256(p)!=entry['sha256']:errors.append(f'{name}: hash mismatch');continue
  try:
   from PIL import Image
   with Image.open(p) as im:
    if im.size[0]<1024 or im.size[1]<768:errors.append(f'{name}: below 1024x768 ({im.size})')
  except Exception as e:errors.append(f'{name}: unreadable image ({e})')
 rejected={Path(r['file']).name for r in manifest.get('rejected',[])}
 if images_dir is not None:
  stray=[q.name for q in Path(images_dir).glob('*.webp') if q.name in rejected]
  if stray:errors.append(f'rejected files inside images dir: {stray}')
 return {'pass':not errors,'checked_files':checked,'errors':errors}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--job-manifest');ap.add_argument('--job-root',default='.');ap.add_argument('--images-dir');a=ap.parse_args()
 if a.job_manifest:
  result=check_job_manifest(a.job_manifest,Path(a.job_root).resolve(),Path(a.images_dir).resolve() if a.images_dir else None)
  print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(1 if not result['pass'] else 0)
 root=Path(__file__).resolve().parents[1]
 manifest=json.loads((root/'manifest-sha256.json').read_text())
 errors=[]
 for name,expected in manifest.items():
  p=(root/name).resolve()
  if not p.is_relative_to(root) or not p.is_file():errors.append(name+': missing/invalid path');continue
  if sha256(p)!=expected:errors.append(name+': hash mismatch')
 print(json.dumps({'pass':not errors,'checked_files':len(manifest),'errors':errors},ensure_ascii=False,indent=2))
 sys.exit(1 if errors else 0)

if __name__=='__main__':main()
