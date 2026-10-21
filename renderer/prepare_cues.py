#!/usr/bin/env python3
"""Optional local known-script attention alignment; explicit local model only.
Not transcription verification. Paragraph chunks must be <=29 seconds.
"""
import argparse,json,subprocess,re
from pathlib import Path
import numpy as np

def norm(s):return ''.join(c for c in s if not c.isspace())
def main():
 p=argparse.ArgumentParser();p.add_argument('--voice',required=True);p.add_argument('--segments',required=True);p.add_argument('--model',required=True,help='Existing local faster-whisper model directory; no implicit downloads');p.add_argument('--out',required=True);a=p.parse_args()
 from faster_whisper import WhisperModel
 from faster_whisper.tokenizer import Tokenizer
 from pythainlp.transliterate import romanize
 model=Path(a.model).resolve()
 if not (model/'model.bin').is_file():raise ValueError('Provide a local model directory containing model.bin')
 segments=json.loads(Path(a.segments).read_text());out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 audio=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',a.voice,'-ar','16000','-ac','1','-f','f32le','-']),dtype=np.float32)
 m=WhisperModel(str(model),device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True);tok=Tokenizer(m.hf_tokenizer,True,task='transcribe',language='th');words=[]
 for chunk in segments:
  start,end=chunk['start'],chunk['end'];chips=chunk['chips'];script=''.join(chips)
  if not (0<=start<end<=len(audio)/16000+.001 and end-start<=29):raise ValueError('Invalid chunk range or longer than 29s')
  if not chips or not all(isinstance(c,str) and norm(c) for c in chips):raise ValueError('Nonempty lexical chips required')
  x=audio[round(start*16000):round(end*16000)];features=m.feature_extractor(x);enc=m.encode(features[:,:3000]);aligned=m.find_alignment(tok,[tok.encode(script)],enc,[len(x)//160])[0]
  chars=[(c,float(r['start'])+start,float(r['end'])+start) for r in aligned for c in r['word'] if not c.isspace()]
  if ''.join(c[0] for c in chars)!=norm(script):raise ValueError('Alignment text mismatch')
  cursor=0;pending=''
  for chip in chips:
   part=chars[cursor:cursor+len(norm(chip))];cursor+=len(norm(chip));s=min(c[1] for c in part);e=min(end,max(c[2] for c in part))
   if e<=s:pending+=chip;continue
   words.append(dict(word=pending+chip,start=round(s,4),end=round(e,4)));pending=''
  if pending:
   if not words:raise ValueError('No usable alignment')
   words[-1]['word']+=pending
 for i in range(len(words)-1):words[i]['end']=min(words[i]['end'],words[i+1]['start'])
 if not all(w['start']<w['end'] for w in words):raise ValueError('Zero-length cues; review chunks/chips')
 if norm(''.join(w['word'] for w in words))!=norm(''.join(''.join(c['chips']) for c in segments)):raise ValueError('Chip coverage mismatch')
 vm={'uea':['EE','AA'],'ue':['EE'],'oe':['EE'],'ia':['EE','AA'],'ua':['OO','AA'],'ae':['EE'],'ai':['AA','EE'],'ao':['AA','OO'],'a':['AA'],'e':['EE'],'i':['EE'],'o':['OH'],'u':['OO']};v=[];guide=[]
 for w in words:
  r=romanize(w['word'],engine='royin').lower().replace('ph','p');shapes=[];i=0
  while i<len(r):
   match=next((x for x in vm if r.startswith(x,i)),None)
   if match:shapes.extend(vm[match]);i+=len(match)
   else:
    if r[i] in 'mbp':shapes.append('CLOSED')
    elif r[i] in 'fv':shapes.append('FV')
    i+=1
  if not shapes:shapes=['EE']
  for k,s in enumerate(shapes):v.append(dict(start=round(w['start']+(w['end']-w['start'])*k/len(shapes),4),shape=s))
  v.append(dict(start=w['end'],shape='CLOSED'));guide.append(dict(word=w['word'],romanized=r,approximate_shapes=shapes))
 v.sort(key=lambda x:x['start'])
 for name,obj in [('words.json',words),('visemes.json',v),('pronunciation_guide.json',guide),('timing_provenance.json',dict(method='Known-script attention alignment using local faster-whisper small; pronunciation rules inside lexical intervals',review_required=True,limits='Not an acoustic phoneme recognizer. Latin names, numbers and Thai compounds may need hand corrections; forced alignment cannot verify that the voice actually said the script.'))]:
  (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
 print('Prepared',len(words),'chips; owner audiovisual review required')
if __name__=='__main__':main()
