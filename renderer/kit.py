#!/usr/bin/env python3
"""Portable LiplnwZa paper host renderer. Local files + JSON; no provider API."""
from pathlib import Path
from functools import lru_cache
from bisect import bisect_right
import argparse, hashlib, json, math, random, shutil, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features
ROOT=Path(__file__).resolve().parents[1]
FONT_PATH=ROOT/'assets/fonts/Prompt-Bold.ttf'
try:
    import uharfbuzz as hb
    _HB_FACE=hb.Face(FONT_PATH.read_bytes()) if FONT_PATH.is_file() else None
    _HB_FONT=hb.Font(_HB_FACE) if _HB_FACE else None
    _HB_UPEM=_HB_FACE.upem if _HB_FACE else 1000
    HAS_HB=bool(_HB_FONT)
except Exception:
    HAS_HB=False
MOUTH_RIG_ROOT=ROOT/'assets/mascot/mouth_rig'
sys.path.insert(0,str(MOUTH_RIG_ROOT))
from rig_motion import PoseMouthRig
W,H,FPS=1080,1920,30
INK='#181b26'; WHITE='#fffdf6'; RED='#f44336'; BLUE='#2264d8'; YELLOW='#ffd648'; GREEN='#38b577'
PALETTE=[YELLOW,BLUE,RED,GREEN]
POSES=['explain','point_right','thinking','magnify','point_left','thumbs_up']
SHAPES=['CLOSED','AA','EE','OH','OO','FV']
LAYOUTS=['title','compare','list','media','summary']

def run(cmd,**kw): return subprocess.run(cmd,check=True,**kw)
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve(jobdir,s):
    if not isinstance(s,str) or not s: raise ValueError('Missing file path')
    p=(jobdir/s).resolve()
    if not (p.is_relative_to(ROOT) or p.is_relative_to(jobdir)): raise ValueError(f'Path outside kit/job: {s}')
    if not p.is_file(): raise ValueError(f'Missing file: {p}')
    return p

def doctor():
    rig_files=[MOUTH_RIG_ROOT/'profiles.json',MOUTH_RIG_ROOT/'rig_motion.py']
    rig_files += [MOUTH_RIG_ROOT/sub/f'{p}.png' for sub in ['original','clean'] for p in POSES]
    has_raqm = bool(features.check('raqm'))
    shaping_ready = bool(has_raqm or HAS_HB)
    checks={'python':sys.version.split()[0],'python_supported':sys.version_info>=(3,11),'pillow_raqm':has_raqm,
            'uharfbuzz':HAS_HB,'text_shaping_ready':shaping_ready,'text_shaping_engine':'raqm' if has_raqm else ('uharfbuzz' if HAS_HB else 'none'),
            'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),
            'font':(ROOT/'assets/fonts/Prompt-Bold.ttf').is_file(),
            'mouth_rig_pose_assets':sum((MOUTH_RIG_ROOT/sub/f'{p}.png').is_file() for sub in ['original','clean'] for p in POSES),
            'mouth_rig_code_and_profiles':all(p.is_file() for p in rig_files[:2]),
            'legacy_mouth_sprites':sum((ROOT/'assets/mascot/rig'/f'{p}_{s}.png').is_file() for p in POSES for s in SHAPES)}
    checks['render_ready']=bool(checks['python_supported'] and shaping_ready and checks['ffmpeg'] and checks['ffprobe'] and checks['font'] and checks['mouth_rig_pose_assets']==12 and checks['mouth_rig_code_and_profiles'])
    return checks

def files_for(j,d):
    paths=[resolve(d,j[k]) for k in ['voice','words','visemes']]
    paths += [resolve(d,s['media']['path']) for s in j['scenes'] if 'media' in s]
    return sorted(set(paths))
def mouth_rig_files():
    return sorted([MOUTH_RIG_ROOT/'profiles.json',MOUTH_RIG_ROOT/'rig_motion.py']+
                  list((MOUTH_RIG_ROOT/'original').glob('*.png'))+
                  list((MOUTH_RIG_ROOT/'clean').glob('*.png')))
def digest(j,d):
    # Covers the job, its media/cues, and the built-in mascot pose/clean-plate rig.
    h=hashlib.sha256(json.dumps(j,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
    for p in files_for(j,d): h.update(sha(p).encode())
    for p in mouth_rig_files():
        h.update(p.relative_to(ROOT).as_posix().encode());h.update(sha(p).encode())
    return h.hexdigest()

def validate(j,d,approved=False):
    errors=[]
    def need(ok,msg):
        if not ok: errors.append(msg)
    need(j.get('schema_version')==1,'schema_version must be 1')
    duration=j.get('duration',0);need(isinstance(duration,(int,float)) and 0<duration<=120,'duration must be 0–120s')
    need(bool(j.get('title')),'title required')
    for i,s in enumerate(j.get('scenes',[])):
        a=s.get('start',-1);b=s.get('end',-1)
        need(0<=a<b<=duration,f'scene {i}: invalid interval')
        need(s.get('layout') in LAYOUTS,f'scene {i}: unknown layout')
        need(s.get('pose','explain') in POSES,f'scene {i}: unknown pose')
        prev=j['scenes'][i-1]['end'] if i else 0
        need(abs(a-prev)<.001,f'scene {i}: gap/overlap')
        need(bool(s.get('title')),f'scene {i}: title required')
        for change in s.get('pose_changes',[]):
            need(change.get('pose') in POSES and 0<=change.get('at',-1)<b-a,f'scene {i}: invalid pose change')
        if 'media' in s:
            m=s['media'];need(m.get('kind') in ['image','video'],f'scene {i}: invalid media kind')
            need(m.get('role') in ['illustration','evidence','screen_recording'],f'scene {i}: media role required')
            need(bool(m.get('label')),f'scene {i}: visible media label required')
            need(bool(m.get('source_id')),f'scene {i}: media source_id required')
    need(bool(j.get('scenes')),'scenes required')
    if j.get('scenes'):need(abs(j['scenes'][-1]['end']-duration)<.001,'scenes must cover duration')
    try:
        files_for(j,d)
        voice_info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(resolve(d,j['voice']))]))
        need(float(voice_info['format']['duration'])<=duration+.03,'Voice is longer than video; do not cut speech implicitly')
        words=read(resolve(d,j['words']));v=read(resolve(d,j['visemes']))
        need(bool(words),'word cues required')
        for i,w in enumerate(words):
            need(bool(w.get('word')) and 0<=w['start']<w['end']<=duration,f'word {i}: invalid')
            if i:need(w['start']>=words[i-1]['end']-.001,f'word {i}: overlap')
        for i,c in enumerate(v):
            need(0<=c['start']<duration and c['shape'] in SHAPES,f'viseme {i}: invalid')
            if i:need(c['start']>=v[i-1]['start'],f'viseme {i}: not sorted')
        source_ids={s['id'] for s in j.get('sources',[])}
        for s in j.get('scenes',[]):
            if 'media' in s:need(s['media']['source_id'] in source_ids,'Unknown media source_id')
        for s in j.get('sources',[]):
            need(all(s.get(k) for k in ['id','origin','creator','license','usage','checked_date']),'Source fields missing')
        if approved:
            a=read(d/'approval.json')
            need(a.get('status')=='approved','Owner approval missing')
            need(a.get('job_digest')==digest(j,d),'Approval does not match this job/input version')
            need(bool(a.get('evidence')),'Approval evidence required')
    except (ValueError,KeyError,TypeError,FileNotFoundError) as e: errors.append(str(e))
    if errors: raise ValueError('\n'.join(errors))
    return {'valid':True,'duration':duration,'scenes':len(j['scenes']),'words':len(words),'job_digest':digest(j,d),'approval_checked':approved}

def ease(u):return 1-(1-max(0,min(1,u)))**3
def pop(u):
    if u<=0:return 0
    u=min(1,u);return 1+2.70158*(u-1)**3+1.70158*(u-1)**2
@lru_cache(maxsize=400)
def _hb_render_line(s, size):
    if not s or not _HB_FONT:
        return 0, 0, 0, 0, None, 0.0
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(_HB_FONT, buf)
    infos = buf.glyph_infos or []
    positions = buf.glyph_positions or []
    if not infos:
        return 0, 0, 0, 0, None, 0.0
    scale = size / _HB_UPEM
    rd = hb.RasterDraw()
    x = 0.0
    for info, pos in zip(infos, positions):
        rd.transform = (scale, 0, 0, -scale, x + pos.x_offset * scale, -pos.y_offset * scale)
        rd.draw_glyph(_HB_FONT, info.codepoint)
        x += pos.x_advance * scale
    img = rd.render()
    if not img or not img.extents:
        return 0, 0, 0, 0, None, x
    ext = img.extents
    arr = np.frombuffer(img.buffer, dtype=np.uint8).reshape((ext.height, ext.stride))[:, :ext.width]
    mask = Image.fromarray(arr, mode='L')
    return ext.width, ext.height, ext.x_origin, ext.y_origin, mask, x

class _HBFontWrapper:
    def __init__(self, size):
        self.size = size
    def getbbox(self, s):
        if not s: return (0, 0, 0, 0)
        w, h, xo, yo, mask, adv = _hb_render_line(s, self.size)
        return (0, 0, round(max(adv, w + xo)), h)

@lru_cache(maxsize=100)
def font(n):
    if features.check('raqm'):
        return ImageFont.truetype(str(FONT_PATH), n, layout_engine=ImageFont.Layout.RAQM)
    if HAS_HB:
        return _HBFontWrapper(n)
    return ImageFont.truetype(str(FONT_PATH), n)

def text(draw,box,value,size=70,color=INK):
    x,y,w,h=box;lines=str(value).split('\n')
    for size in range(size,17,-1):
        f=font(size);bb=[f.getbbox(s) for s in lines];hs=[b[3]-b[1] for b in bb];total=sum(hs)+(len(lines)-1)*size*.2
        if max(b[2]-b[0] for b in bb)<=w and total<=h:break
    if max(b[2]-b[0] for b in bb)>w or total>h:raise ValueError('Text cannot fit: '+value)
    yy=y+(h-total)/2
    for s,b,hh in zip(lines,bb,hs):
        draw_x=x+(w-(b[2]-b[0]))/2
        if isinstance(f,_HBFontWrapper):
            w_text,h_text,xo,yo,mask,adv=_hb_render_line(s,size)
            if mask:
                solid=Image.new('RGBA',mask.size,color)
                draw._image.paste(solid,(round(draw_x+xo),round(yy)),mask=mask)
        else:
            draw.text((draw_x-b[0],yy-b[1]),s,font=f,fill=color)
        yy+=hh+size*.2
    return size
@lru_cache(maxsize=150)
def paper(w,h,color,seed):
    r=random.Random(seed);pts=[];pad=9
    for x in range(pad,w-pad,max(10,w//20)):pts.append((x,pad+r.randint(-5,5)))
    for y in range(pad,h-pad,max(10,h//20)):pts.append((w-pad+r.randint(-5,5),y))
    for x in range(w-pad,pad,-max(10,w//20)):pts.append((x,h-pad+r.randint(-5,5)))
    for y in range(h-pad,pad,-max(10,h//20)):pts.append((pad+r.randint(-5,5),y))
    im=Image.new('RGBA',(w,h));dr=ImageDraw.Draw(im)
    dr.polygon([(x+6,y+6) for x,y in pts],fill=INK);dr.line(pts+[pts[0]],fill=WHITE,width=11,joint='curve');dr.polygon(pts,fill=color);dr.line(pts+[pts[0]],fill=INK,width=4,joint='curve')
    return im

def layer(im,a,cx,cy,scale=1,angle=0):
    if scale<=0:return
    a=a.resize((max(1,round(a.width*scale)),max(1,round(a.height*scale))),Image.Resampling.BICUBIC)
    if angle:a=a.rotate(angle,Image.Resampling.BICUBIC,expand=True)
    im.alpha_composite(a,(round(cx-a.width/2),round(cy-a.height/2)))
def sign(im,cx,cy,w,h,value,color=WHITE,size=70,age=1,angle=0,seed=1):
    a=paper(w,h,color,seed).copy();text(ImageDraw.Draw(a),(26,20,w-52,h-40),value,size,INK if color in [WHITE,YELLOW] else WHITE)
    layer(im,a,cx,cy,pop(age/.32),angle)
@lru_cache(maxsize=4)
def background(i):
    im=Image.new('RGBA',(W,H),['#f3dfdc','#d7e9db','#dce6f5','#f4e9ce'][i%4]);d=ImageDraw.Draw(im)
    for x in range(0,W,52):d.line((x,0,x,H),fill=(120,95,90,40),width=2)
    for y in range(0,H,52):d.line((0,y,W,y),fill=(120,95,90,40),width=2)
    return im

def star(im,x,y,r,color,t):
    pts=[]
    for i in range(16):
        a=t*.25+i*math.pi/8;rr=r if i%2==0 else r*.38;pts.append((x+math.cos(a)*rr,y+math.sin(a)*rr))
    d=ImageDraw.Draw(im);d.polygon(pts,fill=color);d.line(pts+[pts[0]],fill=INK,width=5,joint='curve')
@lru_cache(maxsize=36)
def sprite(pose,shape):return Image.open(ROOT/'assets/mascot/rig'/f'{pose}_{shape}.png').convert('RGBA')

def make_sfx(duration,scenes,path,gain=1):
    sr=48000;s=np.zeros((round(duration*sr),2));rng=np.random.default_rng(90);events=[]
    for c in scenes:
        for off,k in [(.02,'swish'),(.3,'pop'),(.82,'tap'),(1.4,'pop'),(2.3,'ding')]:
            if c['start']+off+.32<c['end']:events.append((c['start']+off,k))
    for t,k in events:
        dur={'swish':.25,'pop':.13,'tap':.1,'ding':.3}[k];u=np.arange(round(dur*sr))/sr
        n=rng.normal(0,1,len(u));f=np.fft.rfftfreq(len(u),1/sr);spec=np.fft.rfft(n)*((f>650)&(f<5500));noise=np.fft.irfft(spec,n=len(u))
        if k=='swish':sig=noise*np.sin(np.pi*u/dur)**1.5;peak=.20
        elif k=='pop':sig=(np.sin(2*np.pi*(1050*u-2300*u*u))+.15*noise)*np.exp(-u*35);peak=.19
        elif k=='tap':sig=(.7*np.sin(2*np.pi*670*u)+.4*noise)*np.exp(-u*60);peak=.18
        else:sig=(np.sin(2*np.pi*1046*u)+.35*np.sin(2*np.pi*1568*u))*np.exp(-u*12);peak=.13
        sig*=peak*gain/(np.max(np.abs(sig))+1e-9);sig*=np.clip(np.minimum(u/.003,(dur-u)/.006),0,1)
        start=round(t*sr);end=min(len(s),start+len(sig));s[start:end]+=sig[:end-start,None]/math.sqrt(2)
    with wave.open(str(path),'wb') as w:w.setparams((2,2,sr,0,'NONE','not compressed'));w.writeframes((np.clip(s,-1,1)*32767).astype('<i2').tobytes())
    return [{'time':t,'sound':k} for t,k in events]

class Composition:
    def __init__(self,job,out):
        self.jobpath=job;self.d=job.parent;self.j=read(job);self.out=out;out.mkdir(parents=True,exist_ok=True)
        validate(self.j,self.d);self.words=read(resolve(self.d,self.j['words']));self.wt=[w['start'] for w in self.words]
        self.v=read(resolve(self.d,self.j['visemes']));self.vt=[v['start'] for v in self.v];self.ct=[s['start'] for s in self.j['scenes']]
        self.duration=self.j['duration'];self.media={}
        self.voice=out/'voice_pcm.wav'
        run(['ffmpeg','-y','-v','error','-i',str(resolve(self.d,self.j['voice'])),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(self.voice)])
        with wave.open(str(self.voice),'rb') as w:self.audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
        self.mouth_rig=PoseMouthRig(MOUTH_RIG_ROOT,self.voice,resolve(self.d,self.j['visemes']),resolve(self.d,self.j['words']))
        self.mouth_rig.write_registration(out/'mouth_rig_registration.json')
        for i,c in enumerate(self.j['scenes']):
            if 'media' not in c:continue
            m=c['media'];p=resolve(self.d,m['path'])
            if m['kind']=='image':self.media[i]=[Image.open(p).convert('RGBA')]
            else:
                dest=out/'media_cache'/str(i);dest.mkdir(parents=True,exist_ok=True)
                vf='fps=30,scale=850:390:force_original_aspect_ratio=decrease,format=rgba'
                if m.get('green_screen'):vf+=',colorkey=0x00FF00:0.16:0.06'
                run(['ffmpeg','-y','-v','error','-ss',str(m.get('in',0)),'-i',str(p),'-t',str(c['end']-c['start']),'-vf',vf,'-threads','1',str(dest/'%05d.png')])
                self.media[i]=sorted(dest.glob('*.png'))
                if not self.media[i]:raise ValueError('No decoded media frames')
    def mouth(self,t):
        i=bisect_right(self.vt,t)-1
        if i<0:return 'CLOSED'
        a=max(0,int((t-.018)*48000));b=min(len(self.audio),int((t+.018)*48000))
        rms=np.sqrt(np.mean(self.audio[a:b]**2)) if b>a else 0
        return self.v[i]['shape'] if rms>=.007 else 'CLOSED'
    def captions(self,im,t):
        active=bisect_right(self.wt,t)-1
        if active<0 or t>self.words[active]['end']+.5:return
        ids=list(range(active//3*3,active+1));ww=[max(112,font(80).getbbox(self.words[i]['word'])[2]+68) for i in ids]
        while len(ids)>1 and sum(ww)+18*(len(ids)-1)>960:ids.pop(0);ww.pop(0)
        scale=min(1,960/(sum(ww)+18*(len(ids)-1)));x=(W-(sum(ww)+18*(len(ids)-1))*scale)/2
        for i,width in zip(ids,ww):
            width=round(width*scale);a=paper(width,140,PALETTE[i%4],800+i).copy()
            text(ImageDraw.Draw(a),(16,16,width-32,108),self.words[i]['word'],round(80*scale),INK if i%4==0 else WHITE)
            layer(im,a,x+width/2,1635,pop((t-self.words[i]['start'])/.14) if i==active else 1,2 if i%2 else -2);x+=width+18*scale
    def frame(self,t):
        idx=max(0,bisect_right(self.ct,t)-1);c=self.j['scenes'][idx];u=t-c['start'];im=background(idx).copy()
        sign(im,228,92,360,87,'LiplnwZa',WHITE,48,1,-2,101)
        sign(im,850,92,330,87,self.j.get('topic_label',self.j['title']),BLUE,37,1,2,102)
        sign(im,540,255,942,182,c['title'],RED if idx%3 else BLUE,84,u+.2,-1,103)
        layout=c['layout']
        if layout in ['title','summary']:
            sign(im,540,555,875,320,c.get('body',''),YELLOW if layout=='title' else WHITE,100,u-.1,1,200)
        elif layout=='compare':
            cards=c.get('items',['',''])
            for k,v in enumerate(cards[:2]):sign(im,292+k*495,575,430,330,v,PALETTE[k],72,u-.15-k*.2,(-1)**k*3,210+k)
        elif layout=='list':
            for k,v in enumerate(c.get('items',[])[:4]):sign(im,540,450+k*120,860,110,v,PALETTE[k],57,u-.1-k*.3,(-1)**k*2,220+k)
        if idx in self.media:
            arr=self.media[idx];a=arr[min(len(arr)-1,max(0,int(u*FPS)))]
            if isinstance(a,Path):
                with Image.open(a) as pic:a=pic.convert('RGBA')
            a=a.copy();a.thumbnail((850,390),Image.Resampling.LANCZOS)
            sign(im,540,580,920,460,'',WHITE,50,1,1,230)
            layer(im,a,540,580,(.98+.02*ease(u/.4))*min(850/a.width,390/a.height),1)
            label=c['media']['label'];sign(im,540,847,880,65,label,WHITE,30,1,-1,231)
        right=c.get('right',False);age=u;pose=c.get('pose','explain')
        for change in c.get('pose_changes',[]):
            if u>=change['at']:pose=change['pose'];age=u-change['at']
        enter=ease(age/.28);cx=(710 if right else 375)+(1-enter)*(110 if right else -110)
        layer(im,self.mouth_rig.frame(pose,t),cx,1210+math.sin(t*3)*7,700/550,math.sin(t*1.8))
        if c.get('aside'):sign(im,265 if right else 820,1130,355,230,c['aside'],YELLOW,64,u-.4,-4 if right else 4,240)
        if c.get('cta'):sign(im,540,1465,880,100,c['cta'],WHITE,52,u-.7,-1,241)
        for k,(x,y,r) in enumerate([(960,400,36),(85,1450,40),(965,1490,27)]):star(im,x+math.sin(t*1.6+k)*7,y,r,PALETTE[k],t)
        self.captions(im,t);text(ImageDraw.Draw(im),(75,1765,930,64),self.j.get('footer',''),29)
        dr=ImageDraw.Draw(im);dr.rounded_rectangle((90,1850,990,1860),radius=5,fill=WHITE);dr.rounded_rectangle((90,1850,max(96,90+900*t/self.duration),1860),radius=5,fill=INK)
        return im.convert('RGB')
    def preview(self):
        points=[min(c['end']-.05,c['start']+1.2) for c in self.j['scenes']]
        sheet=Image.new('RGB',(360*min(3,len(points)),660*math.ceil(len(points)/3)),'#eee')
        for i,t in enumerate(points):
            im=self.frame(t);im.save(self.out/f'scene_{i+1:02}.jpg',quality=94);sheet.paste(im.resize((360,640)),((i%3)*360,(i//3)*660))
            ImageDraw.Draw(sheet).text(((i%3)*360+8,(i//3)*660+643),f'{t:.2f}s',fill='black')
        sheet.save(self.out/'contact_sheet.jpg',quality=94)
        # Exercise every caption and layout text box, not just selected previews.
        for w in self.words:self.frame(min(self.duration-.001,w['start']+.1))
        return points
    def export_srt(self):
        def stamp(t):
            n=round(t*1000);h,n=divmod(n,3600000);m,n=divmod(n,60000);s,ms=divmod(n,1000);return f'{h:02}:{m:02}:{s:02},{ms:03}'
        out=[]
        for i,w in enumerate(self.words,1):out.extend([str(i),f'{stamp(w["start"])} --> {stamp(w["end"])}',w['word'],''])
        (self.out/'subtitles.srt').write_text('\n'.join(out),encoding='utf-8')
    def render(self):
        validate(self.j,self.d,True);self.export_srt();events=make_sfx(self.duration,self.j['scenes'],self.out/'sfx.wav',self.j.get('sfx_gain',1));write(self.out/'sfx_events.json',events)
        target=self.out/'video.mp4';n=round(self.duration*FPS)
        cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r','30','-i','pipe:0','-i',str(self.voice),'-i',str(self.out/'sfx.wav'),'-filter_complex',f'[1:a]aformat=channel_layouts=stereo,apad,atrim=duration={self.duration}[v];[v][2:a]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1:LRA=7[a]','-map','0:v','-map','[a]','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-t',str(self.duration),'-movflags','+faststart','-threads','3',str(target)]
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for i in range(n):
                p.stdin.write(self.frame(i/FPS).tobytes())
                if i%90==0:print(f'FRAME {i}/{n}',flush=True)
            p.stdin.close()
            if p.wait()!=0:raise RuntimeError('FFmpeg render failed')
        except BaseException:p.kill();p.wait();raise
        return target

def qc(path):
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)]))
    run(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],stdout=subprocess.DEVNULL)
    audio=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-af','loudnorm=I=-16:TP=-1:LRA=7:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    pos=audio.stderr.rfind('{');end=audio.stderr.rfind('}')+1;loud=json.loads(audio.stderr[pos:end])
    v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['r_frame_rate'],v['codec_name'])==(W,H,'30/1','h264')
    assert a['sample_rate']=='48000' and a['channels']==2
    assert int(v['nb_read_frames'])==round(float(info['format']['duration'])*30)
    assert -18<=float(loud['input_i'])<=-14 and float(loud['input_tp'])<=-1
    r={'technical_pass':True,'decode_errors':0,'video':{k:v[k] for k in ['codec_name','width','height','r_frame_rate','nb_read_frames']},'audio':{k:a[k] for k in ['codec_name','sample_rate','channels']},'duration':info['format']['duration'],'loudness':loud,'sha256':sha(path),'limits':['Automated checks do not certify factual accuracy, usage rights, subjective lip sync, or publication approval.']}
    write(path.parent/'qc.json',r);return r

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['doctor','validate','digest','preview','render','qc']);p.add_argument('path',nargs='?');p.add_argument('--out');args=p.parse_args()
    if args.command=='doctor':
        result=doctor();print(json.dumps(result,indent=2));return 0 if result['render_ready'] else 2
    if not args.path:p.error('path required')
    path=Path(args.path).resolve()
    if args.command=='qc':result=qc(path)
    else:
        j=read(path);d=path.parent
        if args.command=='digest':print(digest(j,d));return 0
        if args.command=='validate':result=validate(j,d)
        else:
            if not doctor()['render_ready']:raise ValueError('Run doctor and resolve missing dependencies')
            if args.command=='render':validate(j,d,True)
            dest=Path(args.out).resolve() if args.out else d/'output'
            if args.command=='render' and (dest/'video.mp4').exists():raise ValueError('Output video exists; use a new --out directory to preserve the earlier version')
            comp=Composition(path,dest);points=comp.preview()
            result={'previews':points,'path':str(comp.out)}
            if args.command=='render':result['video']=str(comp.render());result['qc']=qc(comp.out/'video.mp4')
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,AssertionError,subprocess.CalledProcessError,KeyError) as e:print('ERROR:',e,file=sys.stderr);sys.exit(2)
