#!/usr/bin/env python3
"""Portable LiplnwZa paper host renderer. Local files + JSON; no provider API."""
from pathlib import Path
from functools import lru_cache
from bisect import bisect_right
import argparse, hashlib, json, math, random, re, shutil, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, features, ImageOps
import audio_mix
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
from theme_config import load_theme
W,H,FPS=1080,1920,30
POSES=['explain','point_right','thinking','magnify','point_left','thumbs_up']
SHAPES=['CLOSED','AA','EE','OH','OO','FV']
LAYOUTS=['title','compare','list','media','summary']
THEME_DIGEST_VERSION=2
RENDER_POLICY_VERSION=1
CHIP_MAX_VISIBLE_SECONDS=1.2
CHIP_AVERAGE_MIN_SECONDS=0.4
CHIP_AVERAGE_MAX_SECONDS=0.7
CARD_POP_DURATION_S=.32
ITEM_STAGGER_S=.30
MASCOT_BREATHING_PERIOD_S=1.8
MASCOT_BREATHING_AMPLITUDE_PX=2.5
MASCOT_BLINK_PERIOD_S=3.7
MASCOT_BLINK_DURATION_S=.1
POP_MAX_SCALE=1.06
PROCEDURAL_ICON_SIZE=144
PROCEDURAL_ICONS=(
    'brain_ai','terminal','audio_wave','fire','ghost','arrow','star',
    'check','cross','chat','magnifier',
)
VISUAL_TEMPLATES=('hero_card','terminal_box','step_flow','feature_grid')
VISUAL_ELEMENT_TYPES=('icon',)
VISUAL_ELEMENT_SAFE_RADIUS=85
SFX_EVENT_POLICY='event_v1'
SFX_EVENT_MIN_GAP_S=.35
SFX_SAMPLE_RATE=48000
SFX_TRIGGER_MAP={
    'scene_title_enter':'pop',
    'hero_enter':'pop',
    'template_enter':'whoosh',
    'scene_card_enter':'whoosh',
    'media_panel_enter':'whoosh',
    'compare_card_enter':'pop',
    'summary_item_enter':'pop',
    'list_item_enter':'pop',
    'step_card_enter':'pop',
    'feature_card_enter':'pop',
    'visual_icon_cue':'click',
    'aside_highlight_enter':'ding',
    'cta_enter':'ding',
}

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

def render_policy_enabled(job):
    version=job.get('render_policy_version')
    if version is not None:
        if isinstance(version,bool) or version!=RENDER_POLICY_VERSION:raise ValueError(f'Unsupported render_policy_version: {version}')
        return True
    return False

def sfx_events_enabled(job):
    """Use event-driven SFX only on render policy v1 jobs or explicit opt-in."""
    policy=job.get('sfx_policy')
    if policy is not None and policy!=SFX_EVENT_POLICY:
        raise ValueError(f"sfx_policy must be {SFX_EVENT_POLICY!r} when specified")
    return render_policy_enabled(job) or policy==SFX_EVENT_POLICY

def is_draft_review(job):
    review=job.get('draft_review')
    if review is None:return False
    if not isinstance(review,dict) or set(review)!={'allow_draft','decoration_motion'}:
        raise ValueError('draft_review must contain allow_draft and decoration_motion')
    if review.get('allow_draft') is not True:raise ValueError('draft_review.allow_draft must be true')
    if review.get('decoration_motion') not in {'static','drift'}:
        raise ValueError('draft_review.decoration_motion must be static or drift')
    return True

def load_job_theme(job):
    review=job.get('draft_review')
    allow_draft=is_draft_review(job)
    theme=load_theme(ROOT,job.get('theme'),allow_draft=allow_draft)
    if allow_draft and review['decoration_motion']=='drift':
        for decoration in theme.get('decorations',[]):decoration['motion']='drift'
    return theme

def visible_caption_intervals(words):
    intervals=[]
    for word in words:
        start=float(word['start']);end=float(word['end'])
        intervals.append((start,min(end,start+CHIP_MAX_VISIBLE_SECONDS)))
    return intervals

def visible_caption_indices(words,intervals,t):
    starts=[word['start'] for word in words]
    active=bisect_right(starts,t)-1
    if active<0:return []
    group_start=(active//3)*3
    return [i for i in range(group_start,active+1) if intervals[i][0]<=t<intervals[i][1]]

def deterministic_motion(t,seed,item_id,amplitude_x=8.0,amplitude_y=6.0,period_s=7.0,scale_drift=0.02):
    """Stable slow drift from explicit inputs; independent of process hash/random state."""
    if not math.isfinite(float(t)) or period_s<=0:raise ValueError('Motion time and period must be finite and period positive')
    key=hashlib.sha256(f'{int(seed)}:{item_id}'.encode('utf-8')).digest()
    tau=2*math.pi/period_s
    phase_x=int.from_bytes(key[0:4],'big')/2**32*2*math.pi
    phase_y=int.from_bytes(key[4:8],'big')/2**32*2*math.pi
    phase_scale=int.from_bytes(key[8:12],'big')/2**32*2*math.pi
    dx=amplitude_x*math.sin(tau*t+phase_x)
    dy=amplitude_y*math.sin(tau*t*0.87+phase_y)
    scale=1+scale_drift*(.5+.5*math.sin(tau*t+phase_scale))
    return dx,dy,scale

def media_motion_transform(t,seed,item_id,image_size,viewport=(850,390),panel=(920,460)):
    dx,dy,scale=deterministic_motion(t,seed,item_id,8,6,7,.02)
    width,height=image_size
    # Inputs are first contained in the viewport. Keep the complete image within its
    # paper panel throughout drift, including still evidence and screen captures.
    fitted=min(viewport[0]/width,viewport[1]/height)
    rendered_w=width*fitted*scale;rendered_h=height*fitted*scale
    safe_x=max(0,(panel[0]-rendered_w)/2);safe_y=max(0,(panel[1]-rendered_h)/2)
    return max(-safe_x,min(safe_x,dx)),max(-safe_y,min(safe_y,dy)),scale

def _intersects(a,b):
    return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]

def decoration_is_safe(decoration,scene):
    cx,cy=decoration['center_px'];size=decoration['size_px']
    motion_margin=5 if decoration['motion']=='drift' else 0
    rect=(cx-size/2-motion_margin,cy-size/2-motion_margin,cx+size/2+motion_margin,cy+size/2+motion_margin)
    right=scene.get('right',False)
    protected=[
        (40,35,1040,350),          # brand, topic and title text
        (50,345,1030,900),         # evidence/media and content cards
        ((340 if right else 25),920,(1015 if right else 760),1570), # mascot/face/mouth
        (0,1570,1080,1745),        # caption chips and their text
        (0,1740,1080,1885),        # footer, numbers and progress
    ]
    if scene.get('aside'):
        protected.append((scene.get('_aside_x',650)-190,scene.get('_aside_y',1130)-125,
                          scene.get('_aside_x',650)+190,scene.get('_aside_y',1130)+125))
    if scene.get('cta'):
        protected.append((100,1405,980,1525))
    if 'media' in scene:
        protected.append((70,330,1010,920))
    return 0<=rect[0] and rect[1]>=0 and rect[2]<=W and rect[3]<=H and not any(_intersects(rect,zone) for zone in protected)

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
    try:
        base_theme=load_theme(ROOT,None)
        checks['base_theme']={'id':base_theme['id'],'version':base_theme['version'],'valid':True}
    except (ValueError,KeyError,TypeError,FileNotFoundError) as e:
        checks['base_theme']={'valid':False,'error':str(e)}
    checks['render_ready']=bool(checks['python_supported'] and shaping_ready and checks['ffmpeg'] and checks['ffprobe'] and checks['font'] and checks['mouth_rig_pose_assets']==12 and checks['mouth_rig_code_and_profiles'] and checks['base_theme']['valid'])
    return checks

def theme_dependencies(resolved_theme):
    """List every pinned file that can affect a themed render."""
    root=Path(resolved_theme['_kit_root']).resolve()
    rig=root/'assets/mascot/mouth_rig'
    paths=[
        Path(resolved_theme['_theme_path']),
        Path(resolved_theme['_theme_index_path']),
        Path(resolved_theme['_schema_path']),
        root/'library/index.json',
        root/'assets/fonts/Prompt-Bold.ttf',
        root/'assets/fonts/OFL.txt',
        root/'renderer/kit.py',
        root/'renderer/requirements.txt',
        root/'renderer/audio_mix.py',
        root/'renderer/theme_config.py',
        root/'renderer/theme_assets.py',
        rig/'profiles.json',
        rig/'rig_motion.py',
    ]
    paths += list((rig/'original').glob('*.png'))
    paths += list((rig/'clean').glob('*.png'))
    assets=resolved_theme.get('_resolved_assets',[])
    if not assets:
        background_asset=resolved_theme.get('background',{}).get('resolved_asset')
        assets=[background_asset] if background_asset else []
    for asset in assets:
        paths += [Path(asset['metadata_path']),Path(asset['path'])]
    _,runtime_files=resolve_runtime_mascot(resolved_theme)
    paths.extend(runtime_files)
    return sorted({p.resolve() for p in paths if p.is_file()})

def resolve_runtime_mascot(resolved_theme):
    """Return the approved runtime rig pinned by the selected mascot concept."""
    root=Path(resolved_theme['_kit_root']).resolve()
    concept=resolved_theme.get('resolved_mascot_concept')
    if not concept:return MOUTH_RIG_ROOT,[]
    metadata=read(concept['metadata_path'])
    runtime=metadata.get('runtime_rig')
    if not isinstance(runtime,dict) or runtime.get('status')!='approved':
        raise ValueError('Selected mascot concept has no approved runtime rig')
    manifest_rel=Path(runtime.get('manifest',''))
    if not manifest_rel.parts or manifest_rel.is_absolute() or '..' in manifest_rel.parts:
        raise ValueError('Runtime rig manifest path is invalid')
    manifest_path=(root/manifest_rel).resolve()
    if not manifest_path.is_relative_to(root) or not manifest_path.is_file():
        raise ValueError('Runtime rig manifest is missing or outside kit root')
    if sha(manifest_path)!=runtime.get('manifest_sha256'):
        raise ValueError('Runtime rig manifest hash mismatch')
    manifest=read(manifest_path)
    if manifest.get('status')!='approved' or manifest.get('version')!=runtime.get('version','v001'):
        raise ValueError('Runtime rig manifest is not approved or version-pinned')
    if set(manifest.get('poses',[]))!=set(POSES) or set(manifest.get('mouth_shapes',[]))!=set(SHAPES):
        raise ValueError('Runtime rig must cover all six approved poses and mouth shapes')
    base_rel=Path(manifest.get('base_path',''))
    if not base_rel.parts or base_rel.is_absolute() or '..' in base_rel.parts:
        raise ValueError('Runtime rig base path is invalid')
    base=(root/base_rel).resolve()
    if not base.is_relative_to(root):raise ValueError('Runtime rig base path escapes kit root')
    files=[manifest_path]
    for item in manifest.get('files',[]):
        rel=Path(item.get('path',''))
        if not rel.parts or rel.is_absolute() or '..' in rel.parts:
            raise ValueError('Runtime rig file path is invalid')
        path=(root/rel).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError(f'Runtime rig file is missing or outside its base: {rel.as_posix()}')
        if sha(path)!=item.get('sha256'):
            raise ValueError(f'Runtime rig file hash mismatch: {rel.as_posix()}')
        files.append(path)
    rig_root=base/'mouth_rig'
    if not (rig_root/'profiles.json').is_file() or not (rig_root/'rig_motion.py').is_file():
        raise ValueError('Runtime mascot mouth rig is incomplete')
    return rig_root,files

def files_for(j,d,resolved_theme=None):
    paths=[resolve(d,j[k]) for k in ['voice','words','visemes']]
    for key in ('script','segments','timing_provenance','pronunciation_guide'):
        if j.get(key):paths.append(resolve(d,j[key]))
    paths += [resolve(d,s['media']['path']) for s in j['scenes'] if 'media' in s]
    bgm=j.get('bgm')
    if bgm is not None:
        bgm_info=audio_mix.validate_bgm(j,d,j.get('duration',0))
        paths.append(bgm_info['path'])
    if j.get('theme') is not None or bgm is not None:
        resolved_theme=resolved_theme or load_job_theme(j)
        paths.extend(theme_dependencies(resolved_theme))
    return sorted(set(paths))
def mouth_rig_files():
    return sorted([MOUTH_RIG_ROOT/'profiles.json',MOUTH_RIG_ROOT/'rig_motion.py']+
                  list((MOUTH_RIG_ROOT/'original').glob('*.png'))+
                  list((MOUTH_RIG_ROOT/'clean').glob('*.png')))
def approval_digest_version(j):
    return THEME_DIGEST_VERSION if j.get('theme') is not None or j.get('bgm') is not None else 1

def digest(j,d,resolved_theme=None):
    # Keep v1 byte-for-byte compatible for existing jobs; themed/BGM jobs use the full v2 manifest.
    version=approval_digest_version(j)
    canonical=json.dumps(j,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    h=hashlib.sha256(canonical)
    if version==1:
        for p in files_for(j,d): h.update(sha(p).encode())
        for p in mouth_rig_files():
            h.update(p.relative_to(ROOT).as_posix().encode());h.update(sha(p).encode())
        return h.hexdigest()
    h.update(b'\0approval_digest_version=2\0')
    for p in files_for(j,d,resolved_theme):
        try: identity=p.relative_to(ROOT).as_posix()
        except ValueError: identity='job/'+p.relative_to(Path(d).resolve()).as_posix()
        h.update(identity.encode());h.update(b'\0');h.update(sha(p).encode());h.update(b'\0')
    return h.hexdigest()

def cue_matches_scene_word(cue,scene,words):
    if isinstance(cue,bool) or not isinstance(cue,(int,float)) or not math.isfinite(cue):return False
    start,end=scene.get('start'),scene.get('end')
    if isinstance(start,bool) or not isinstance(start,(int,float)) or isinstance(end,bool) or not isinstance(end,(int,float)):return False
    return any(isinstance(word.get('start'),(int,float)) and not isinstance(word['start'],bool) and math.isfinite(word['start']) and
               start<=word['start']<end and abs(float(word['start'])-cue)<.001 for word in words)

def opening_hero_card_is_valid(scene):
    return (scene.get('template')=='hero_card' and scene.get('icon') in PROCEDURAL_ICONS and
            isinstance(scene.get('headline'),str) and bool(scene['headline'].strip()) and len(scene['headline'].strip())<=48 and
            '\n' not in scene['headline'])

def visual_element_protected_zones(scene,job,theme):
    layout=theme['layout'];right=mascot_right_for_scene(job,scene)
    mascot=(340 if right else 25,920,1015 if right else 760,1570)
    caption=theme['captions'];caption_y=caption['y_px'];caption_h=caption['height_px']
    footer=layout['footer_box'];progress=layout['progress_box']
    zones=[
        ('title/header',(40,35,1040,350)),
        ('mascot',mascot),
        ('subtitle',(0,max(0,caption_y-caption_h/2-35),W,min(H,caption_y+caption_h/2+50))),
        ('footer',(max(0,footer[0]-16),max(0,footer[1]-16),min(W,footer[0]+footer[2]+16),min(H,footer[1]+footer[3]+16))),
        ('progress bar',(progress[0]-12,progress[1]-12,progress[2]+12,progress[3]+12)),
    ]
    if 'media' in scene:zones.append(('evidence area / media panel',(70,330,1010,920)))
    if scene.get('aside'):
        center=layout['aside_right_center_px'] if right else layout['aside_center_px']
        zones.append(('aside',(center[0]-190,center[1]-125,center[0]+190,center[1]+125)))
    if scene.get('cta'):
        center=layout['cta_center_px'];zones.append(('CTA',(center[0]-440,center[1]-60,center[0]+440,center[1]+60)))
    return zones

def validate_scene_visuals(scene,index,words,job,theme):
    errors=[]
    prefix=f'scene {index}: '
    template=scene.get('template')
    if 'template' in scene:
        if template not in VISUAL_TEMPLATES:
            errors.append(prefix+f'unknown template {template!r}; expected one of {", ".join(VISUAL_TEMPLATES)}')
        elif 'media' in scene:
            errors.append(prefix+'template cannot share the evidence/media panel with scene media')
        elif template=='hero_card':
            if scene.get('icon') not in PROCEDURAL_ICONS:
                errors.append(prefix+f"template hero_card: unknown icon {scene.get('icon')!r}")
            headline=scene.get('headline')
            if not isinstance(headline,str) or not headline.strip() or len(headline.strip())>48 or '\n' in headline:
                errors.append(prefix+'template hero_card requires a short one-line headline (1–48 characters)')
        elif template=='terminal_box':
            lines=scene.get('lines')
            if not isinstance(lines,list) or not 1<=len(lines)<=3:
                errors.append(prefix+'template terminal_box requires 1–3 short lines')
            else:
                footage_terms=('footage','event video','real video','actual video','actual event','real event','live capture','live stream',
                               'ฟุตเทจ','ภาพเหตุการณ์','วิดีโอเหตุการณ์','ภาพจริง','เหตุการณ์จริง','บันทึกเหตุการณ์','ถ่ายทอดสด','คลิปจริง')
                executable=re.compile(r"(^\s*(?:[$#>]|PS\s|C:\\)|\b(?:python[0-9.]*|bash|sh|zsh|node|npm|npx|pip|git|curl|wget|sudo|ffmpeg|echo|print|import|from|def|class|return|select|insert|update|delete|const|let|var|function|ls|cd|pwd|touch|mkdir|rmdir|rm|mv|cp|chmod|chown|cat|head|tail|grep|find|awk|sed|exit|exec|run)\b|[()\[\]{};=`]|&&|\|\|)",re.IGNORECASE)
                for line_index,line in enumerate(lines):
                    if not isinstance(line,str) or not line.strip() or len(line.strip())>56 or '\n' in line:
                        errors.append(prefix+f'template terminal_box line {line_index} must be short one-line display text')
                        continue
                    lowered=line.casefold()
                    if any(term in lowered for term in footage_terms):
                        errors.append(prefix+'terminal_box cannot claim real event footage')
                    if executable.search(line):
                        errors.append(prefix+'terminal_box lines must be inert display text, not executable code or commands')
        elif template=='step_flow':
            steps=scene.get('steps')
            if not isinstance(steps,list) or not 2<=len(steps)<=4:
                errors.append(prefix+'template step_flow requires 2–4 steps')
            else:
                cues=[]
                for step_index,step in enumerate(steps):
                    if not isinstance(step,dict) or set(step)!={'text','cue'}:
                        errors.append(prefix+f'step_flow step {step_index} must contain only text and cue')
                        continue
                    label=step.get('text');cue=step.get('cue')
                    if not isinstance(label,str) or not label.strip() or len(label.strip())>14 or '\n' in label:
                        errors.append(prefix+f'step_flow step {step_index} requires a short one-line text label')
                    if not cue_matches_scene_word(cue,scene,words):
                        errors.append(prefix+f'step_flow step {step_index}: cue must match a word start in scene {index}')
                    elif isinstance(cue,(int,float)) and not isinstance(cue,bool):cues.append(float(cue))
                if any(cues[i]>=cues[i+1] for i in range(len(cues)-1)):
                    errors.append(prefix+'step_flow cues must follow speaking order')
        elif template=='feature_grid':
            features=scene.get('features')
            if not isinstance(features,list) or not 2<=len(features)<=4:
                errors.append(prefix+'template feature_grid requires 2–4 features')
            else:
                cues=[]
                for feature_index,feature in enumerate(features):
                    if not isinstance(feature,dict) or set(feature)!={'icon','label','cue'}:
                        errors.append(prefix+f'feature_grid feature {feature_index} must contain only icon, label, and cue')
                        continue
                    if feature.get('icon') not in PROCEDURAL_ICONS:
                        errors.append(prefix+f"feature_grid feature {feature_index}: unknown icon {feature.get('icon')!r}")
                    label=feature.get('label');cue=feature.get('cue')
                    if not isinstance(label,str) or not label.strip() or len(label.strip())>14 or '\n' in label:
                        errors.append(prefix+f'feature_grid feature {feature_index} requires a short one-line label')
                    if not cue_matches_scene_word(cue,scene,words):
                        errors.append(prefix+f'feature_grid feature {feature_index}: cue must match a word start in scene {index}')
                    elif isinstance(cue,(int,float)) and not isinstance(cue,bool):cues.append(float(cue))
                if any(cues[i]>=cues[i+1] for i in range(len(cues)-1)):
                    errors.append(prefix+'feature_grid cues must follow speaking order')

    if 'visual_elements' not in scene:return errors
    elements=scene['visual_elements']
    if not isinstance(elements,list):
        errors.append(prefix+'visual_elements must be a list');return errors
    occupied=[]
    zones=visual_element_protected_zones(scene,job,theme)
    for element_index,element in enumerate(elements):
        element_prefix=prefix+f'visual element {element_index}: '
        if not isinstance(element,dict) or set(element)!={'type','icon','position','cue'}:
            errors.append(element_prefix+'must contain exactly type, icon, position, and cue');continue
        if element.get('type') not in VISUAL_ELEMENT_TYPES:
            errors.append(element_prefix+f"unknown type {element.get('type')!r}; expected 'icon'")
        if element.get('icon') not in PROCEDURAL_ICONS:
            errors.append(element_prefix+f"unknown icon {element.get('icon')!r}")
        if not cue_matches_scene_word(element.get('cue'),scene,words):
            errors.append(element_prefix+f'cue must match a word start in scene {index}')
        position=element.get('position')
        if not isinstance(position,list) or len(position)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in position):
            errors.append(element_prefix+'position must be [center_x, center_y] in frame pixels');continue
        x,y=map(float,position);r=VISUAL_ELEMENT_SAFE_RADIUS
        rect=(x-r,y-r,x+r,y+r)
        if rect[0]<0 or rect[1]<0 or rect[2]>W or rect[3]>H:
            errors.append(element_prefix+'position must keep the complete icon inside the frame')
        zone_hits=[]
        for zone_name,zone in zones:
            if _intersects(rect,zone):zone_hits.append(zone_name)
        for zone_name in zone_hits:
            errors.append(element_prefix+f'position overlaps protected {zone_name} zone')
        if any(_intersects(rect,prior) for prior in occupied):
            errors.append(element_prefix+'position overlaps another visual element')
        occupied.append(rect)
    return errors

def validate(j,d,approved=False,resolved_theme=None):
    errors=[]
    def need(ok,msg):
        if not ok: errors.append(msg)
    need(j.get('schema_version')==1,'schema_version must be 1')
    duration=j.get('duration',0);need(isinstance(duration,(int,float)) and 0<duration<=120,'duration must be 0–120s')
    need(bool(j.get('title')),'title required')
    policy_on=render_policy_enabled(j)
    try:sfx_events_enabled(j)
    except ValueError as e:errors.append(str(e))
    for i,s in enumerate(j.get('scenes',[])):
        a=s.get('start',-1);b=s.get('end',-1)
        need(0<=a<b<=duration,f'scene {i}: invalid interval')
        need(s.get('layout') in LAYOUTS,f'scene {i}: unknown layout')
        need(s.get('pose','explain') in POSES,f'scene {i}: unknown pose')
        if 'right' in s:need(isinstance(s['right'],bool),f'scene {i}: right must be boolean')
        if policy_on and s.get('right') is True:
            need(j.get('allow_mascot_side_switch') is True,
                 f'scene {i}: right-side mascot requires allow_mascot_side_switch=true')
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
    need(isinstance(j.get('allow_mascot_side_switch',False),bool),
         'allow_mascot_side_switch must be boolean')
    if j.get('scenes'):
        first=j['scenes'][0]
        visible_title=first.get('show_title',True) is True and bool(str(first.get('title','')).strip())
        media=first.get('media')
        hero_media=isinstance(media,dict) and media.get('kind') in {'image','video'} and bool(media.get('path'))
        need(visible_title or hero_media or opening_hero_card_is_valid(first),
             'scene 0: first 3 seconds must show a title or hero visual (visible scene title or media)')
    try:
        resolved_theme=resolved_theme or load_job_theme(j)
        variant_ids={v.get('id') for v in resolved_theme.get('background_variants',[])}
        for i,s in enumerate(j.get('scenes',[])):
            if 'background_variant' in s:
                need(s.get('background_variant') in variant_ids,f'scene {i}: unknown background_variant')
        files_for(j,d,resolved_theme)
        if j.get('bgm') is not None:audio_mix.validate_bgm(j,d,duration)
        voice_info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(resolve(d,j['voice']))]))
        need(float(voice_info['format']['duration'])<=duration+.03,'Voice is longer than video; do not cut speech implicitly')
        words=read(resolve(d,j['words']));v=read(resolve(d,j['visemes']))
        need(bool(words),'word cues required')
        need(bool(v),'viseme cues are required; visemes must not be empty')
        for i,s in enumerate(j.get('scenes',[])):
            errors.extend(validate_scene_visuals(s,i,words,j,resolved_theme))
        for i,w in enumerate(words):
            need(bool(w.get('word')) and 0<=w['start']<w['end']<=duration,f'word {i}: invalid')
            if i:need(w['start']>=words[i-1]['end']-.001,f'word {i}: overlap')
        if policy_on and words:
            intervals=visible_caption_intervals(words)
            average=sum(end-start for start,end in intervals)/len(intervals)
            if not CHIP_AVERAGE_MIN_SECONDS<=average<=CHIP_AVERAGE_MAX_SECONDS:
                need(False,f'New-job chip visibility average is {average:.3f}s; re-align approved word cues to 0.4–0.7s per clip')
        for i,c in enumerate(v):
            need(0<=c['start']<duration and c['shape'] in SHAPES,f'viseme {i}: invalid')
            if i:need(c['start']>=v[i-1]['start'],f'viseme {i}: not sorted')
        source_ids={s['id'] for s in j.get('sources',[])}
        for s in j.get('scenes',[]):
            if 'media' in s:need(s['media']['source_id'] in source_ids,'Unknown media source_id')
        for s in j.get('sources',[]):
            need(all(s.get(k) for k in ['id','origin','creator','license','usage','checked_date']),'Source fields missing')
        if 'show_brand' in j:need(isinstance(j['show_brand'],bool),'show_brand must be boolean')
        for i,s in enumerate(j.get('scenes',[])):
            for key in ('show_title','show_topic_label'):
                if key in s:need(isinstance(s[key],bool),f'scene {i}: {key} must be boolean')
        if approved:
            a=read(d/'approval.json')
            if is_draft_review(j):
                need(j.get('bgm') is None,'Review-only draft jobs cannot add BGM')
                need(a.get('status')=='pending','Review-only jobs must not claim full-job approval')
                need(a.get('review_only') is True,'Review-only approval record required')
                need(a.get('review_digest')==digest(j,d,resolved_theme),'Review digest does not match this job/input version')
                need(bool(a.get('evidence')),'Prior approval evidence required for review render')
            else:
                need(a.get('status')=='approved','Owner approval missing')
                version=approval_digest_version(j)
                need(a.get('approval_digest_version',1)==version,'Approval digest version does not match this job')
                need(a.get('job_digest')==digest(j,d,resolved_theme),'Approval does not match this job/input version')
                need(bool(a.get('evidence')),'Approval evidence required')
    except (ValueError,KeyError,TypeError,FileNotFoundError) as e: errors.append(str(e))
    if errors: raise ValueError('\n'.join(errors))
    return {'valid':True,'duration':duration,'scenes':len(j['scenes']),'words':len(words),'job_digest':digest(j,d,resolved_theme),'approval_digest_version':approval_digest_version(j),'approval_checked':approved,'review_only':bool(approved and is_draft_review(j))}

def ease(u):return 1-(1-max(0,min(1,u)))**3
def pop(u):
    if u<=0:return 0
    u=min(1,u);return 1+2.70158*(u-1)**3+1.70158*(u-1)**2

def card_pop_scale(age_s):
    if age_s<=0:return 0
    u=min(1,age_s/CARD_POP_DURATION_S)
    overshoot=max(0.0,pop(u)-u)
    return .85+.15*u+.215*overshoot

def staggered_item_age(elapsed_s,index,count,scene_duration_s):
    if count<=1:return elapsed_s-.1
    interval=min(ITEM_STAGGER_S,max(0.0,scene_duration_s)/(count+1))
    return elapsed_s-.1-index*interval

def mascot_breathing_y(time_s):
    return MASCOT_BREATHING_AMPLITUDE_PX*math.sin(2*math.pi*time_s/MASCOT_BREATHING_PERIOD_S)

def mascot_blink_active(time_s):
    if time_s<0:return False
    return time_s%MASCOT_BLINK_PERIOD_S<MASCOT_BLINK_DURATION_S

def mascot_right_for_scene(job,scene):
    right=scene.get('right',False)
    if render_policy_enabled(job) and not job.get('allow_mascot_side_switch',False):return False
    return bool(right)

def blink_eyes(image,eye_centers):
    """Close both eyes with a soft PIL eyelid overlay anchored to registered eyes."""
    if len(eye_centers)!=2:raise ValueError('Eye blinking requires two registration anchors')
    source=np.asarray(image.convert('RGBA'))
    height,width=source.shape[:2]
    centers=[(float(x),float(y)) for x,y in eye_centers]
    eye_distance=float(np.linalg.norm(np.asarray(centers[0])-np.asarray(centers[1])))
    radius_x=round(min(27,max(21,eye_distance*.34)));radius_y=20
    result=image.convert('RGBA').copy()
    for cx,cy in centers:
        ix,iy=round(cx),round(cy)
        top_y=max(0,min(height-1,iy-radius_y-3));bottom_y=max(0,min(height-1,iy+radius_y+3))
        def skin_sample(x,y):
            patch=source[max(0,y-3):min(height,y+4),max(0,x-3):min(width,x+4),:3].astype(np.int16)
            if patch.size==0:return np.array([244,184,153],dtype=np.float64)
            skin=(patch[:,:,0]>patch[:,:,1]*1.12)&(patch[:,:,1]>patch[:,:,2]*1.05)&(patch[:,:,0]>145)&(patch[:,:,1]>75)
            pixels=patch[skin]
            return np.median(pixels,axis=0).astype(np.float64) if len(pixels)>=3 else np.array([244,184,153],dtype=np.float64)
        top_color=skin_sample(ix,top_y);bottom_color=skin_sample(ix,bottom_y)
        left_color=skin_sample(max(0,ix-radius_x-4),iy);right_color=skin_sample(min(width-1,ix+radius_x+4),iy)
        left=max(0,ix-radius_x);right=min(width,ix+radius_x+1)
        upper=max(0,iy-radius_y);lower=min(height,iy+radius_y+1)
        patch_w=right-left;patch_h=lower-upper
        if patch_w<=0 or patch_h<=0:continue
        vertical=np.linspace(0,1,patch_h,dtype=np.float64)[:,None,None]
        vertical_colors=top_color[None,None,:]*(1-vertical)+bottom_color[None,None,:]*vertical
        horizontal=np.linspace(-1,1,patch_w,dtype=np.float64)[None,:,None]
        horizontal_colors=left_color[None,None,:]*(1-(horizontal+1)/2)+right_color[None,None,:]*((horizontal+1)/2)
        colors=(vertical_colors*.72+horizontal_colors*.28)*(1-.05*horizontal**2)
        rgba=np.empty((patch_h,patch_w,4),dtype=np.uint8)
        rgba[:,:,:3]=np.clip(colors,0,255).astype(np.uint8)
        rgba[:,:,3]=255
        lid=Image.fromarray(rgba,'RGBA')
        mask_scale=4
        mask_hi=Image.new('L',(patch_w*mask_scale,patch_h*mask_scale),0)
        ImageDraw.Draw(mask_hi).ellipse((1,1,patch_w*mask_scale-2,patch_h*mask_scale-2),fill=255)
        mask=mask_hi.resize((patch_w,patch_h),Image.Resampling.LANCZOS)
        mask=mask.filter(ImageFilter.GaussianBlur(.35))
        region=result.crop((left,upper,right,lower))
        result.paste(Image.composite(lid,region,mask),(left,upper))
        line=Image.new('RGBA',(width*mask_scale,height*mask_scale),(0,0,0,0))
        draw=ImageDraw.Draw(line)
        points=[]
        for step in range(25):
            dx=-radius_x+3+step*(2*radius_x-6)/24
            y=cy+2-5*(1-(dx/radius_x)**2)
            points.append((round((cx+dx)*mask_scale),round(y*mask_scale)))
        draw.line(points,fill=(119,58,45,205),width=round(2*mask_scale),joint='curve')
        result.alpha_composite(line.resize((width,height),Image.Resampling.LANCZOS))
    return result
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

def text(draw,box,value,size,color):
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
@lru_cache(maxsize=400)
def paper(w,h,color,seed,cache_key,ink_color,paper_color,border_px,outline_px,shadow_x,shadow_y,roughness_px,padding_px):
    r=random.Random(seed);pts=[];pad=padding_px
    for x in range(pad,w-pad,max(10,w//20)):pts.append((x,pad+r.randint(-roughness_px,roughness_px)))
    for y in range(pad,h-pad,max(10,h//20)):pts.append((w-pad+r.randint(-roughness_px,roughness_px),y))
    for x in range(w-pad,pad,-max(10,w//20)):pts.append((x,h-pad+r.randint(-roughness_px,roughness_px)))
    for y in range(h-pad,pad,-max(10,h//20)):pts.append((pad+r.randint(-roughness_px,roughness_px),y))
    im=Image.new('RGBA',(w,h));dr=ImageDraw.Draw(im)
    dr.polygon([(x+shadow_x,y+shadow_y) for x,y in pts],fill=ink_color);dr.line(pts+[pts[0]],fill=paper_color,width=outline_px,joint='curve');dr.polygon(pts,fill=color);dr.line(pts+[pts[0]],fill=ink_color,width=border_px,joint='curve')
    return im

def layer(im,a,cx,cy,scale=1,angle=0):
    if scale<=0:return
    a=a.resize((max(1,round(a.width*scale)),max(1,round(a.height*scale))),Image.Resampling.BICUBIC)
    if angle:a=a.rotate(angle,Image.Resampling.BICUBIC,expand=True)
    im.alpha_composite(a,(round(cx-a.width/2),round(cy-a.height/2)))
def sign(im,cx,cy,w,h,value,color,size,age,angle,seed,theme,text_color):
    cards=theme['cards'];palette=theme['palette']
    shadow=cards['shadow_offset_px']
    a=paper(w,h,color,seed,theme['_cache_key'],palette['ink'],palette['paper'],cards['border_px'],cards['outline_px'],shadow[0],shadow[1],cards['roughness_px'],cards['padding_px']).copy()
    text(ImageDraw.Draw(a),(26,20,w-52,h-40),value,size,text_color)
    scale=card_pop_scale(age) if theme.get('_render_policy_enabled',False) else pop(age/CARD_POP_DURATION_S)
    layer(im,a,cx,cy,scale,angle)

def draw_procedural_icon(name,theme,size=PROCEDURAL_ICON_SIZE):
    """Draw an original paper-cut icon with PIL only and colors from the active theme."""
    if name not in PROCEDURAL_ICONS:raise ValueError(f'Unknown procedural icon: {name!r}')
    if isinstance(size,bool) or not isinstance(size,int) or size<16:raise ValueError('Procedural icon size must be an integer >= 16')
    base=PROCEDURAL_ICON_SIZE;scale=3;canvas_size=base*scale
    palette=theme['palette'];ink=ImageColor.getrgb(palette['ink']);paper_color=ImageColor.getrgb(palette['paper'])
    accents=[ImageColor.getrgb(value) for value in palette['accents']];accent,secondary=accents[:2]
    art=Image.new('RGBA',(canvas_size,canvas_size),(0,0,0,0));d=ImageDraw.Draw(art)
    p=lambda v:round(v*scale)
    def box(coords):return tuple(p(v) for v in coords)
    def poly(points,fill,outline=ink,width=7):
        coords=[(p(x),p(y)) for x,y in points]
        d.polygon(coords,fill=fill)
        d.line(coords+[coords[0]],fill=outline,width=p(width),joint='curve')
    def ellipse(coords,fill,outline=ink,width=7):d.ellipse(box(coords),fill=fill,outline=outline,width=p(width))
    def roundbox(coords,radius,fill,outline=ink,width=7):d.rounded_rectangle(box(coords),radius=p(radius),fill=fill,outline=outline,width=p(width))

    if name=='brain_ai':
        poly([(29,50),(35,36),(48,30),(60,33),(71,22),(86,26),(95,37),(108,40),(115,53),(109,66),(114,79),(105,92),(93,96),(82,110),(67,105),(57,113),(45,105),(33,99),(29,86),(24,75),(28,63)],accent)
        d.line([(p(71),p(29)),(p(70),p(104))],fill=ink,width=p(5),joint='curve')
        d.line([(p(48),p(42)),(p(56),p(50)),(p(52),p(61))],fill=secondary,width=p(5),joint='curve')
        d.line([(p(89),p(40)),(p(82),p(50)),(p(91),p(58))],fill=secondary,width=p(5),joint='curve')
        d.ellipse(box((60,66,66,72)),fill=paper_color);d.ellipse(box((77,76,83,82)),fill=paper_color)
    elif name=='terminal':
        roundbox((22,28,122,112),12,accent,width=8)
        d.rounded_rectangle(box((29,35,115,55)),radius=p(7),fill=paper_color)
        for x,color in zip((39,52,65),accents[1:]):d.ellipse(box((x,41,x+7,48)),fill=color)
        d.line([(p(38),p(76)),(p(49),p(84)),(p(38),p(92))],fill=paper_color,width=p(7),joint='curve')
        d.line([(p(57),p(92)),(p(88),p(92))],fill=paper_color,width=p(7))
    elif name=='audio_wave':
        roundbox((20,32,124,112),22,paper_color,width=7)
        heights=(20,34,50,30,61,40,23,49,31)
        for i,height in enumerate(heights):
            x=34+i*10
            d.line([(p(x),p(72-height/2)),(p(x),p(72+height/2))],fill=accent if i%2==0 else secondary,width=p(6))
    elif name=='fire':
        poly([(72,18),(84,40),(103,47),(113,68),(108,92),(91,111),(66,117),(43,108),(29,90),(31,70),(45,52),(54,34),(60,54)],accent)
        poly([(73,59),(86,75),(82,93),(69,103),(55,96),(54,82),(64,68)],secondary,width=5)
    elif name=='ghost':
        poly([(33,106),(34,62),(38,47),(49,35),(64,29),(80,31),(94,41),(104,56),(108,75),(108,106),(93,96),(80,107),(66,97),(51,108)],paper_color)
        d.ellipse(box((52,59,61,71)),fill=ink);d.ellipse(box((81,59,90,71)),fill=ink)
        d.ellipse(box((69,82,78,91)),fill=accent)
    elif name=='arrow':
        poly([(18,56),(77,56),(77,32),(126,72),(77,112),(77,88),(18,88)],accent,width=8)
    elif name=='star':
        points=[]
        for i in range(10):
            angle=-math.pi/2+i*math.pi/5;radius=54 if i%2==0 else 25
            points.append((72+math.cos(angle)*radius,72+math.sin(angle)*radius))
        poly(points,accent,width=7)
    elif name=='check':
        ellipse((20,20,124,124),accent,width=8)
        d.line([(p(43),p(74)),(p(63),p(93)),(p(103),p(48))],fill=paper_color,width=p(13),joint='curve')
    elif name=='cross':
        ellipse((20,20,124,124),accent,width=8)
        d.line([(p(47),p(47)),(p(97),p(97))],fill=paper_color,width=p(13))
        d.line([(p(97),p(47)),(p(47),p(97))],fill=paper_color,width=p(13))
    elif name=='chat':
        roundbox((23,25,121,96),18,accent,width=8)
        poly([(43,89),(38,116),(65,95)],accent,width=6)
        for x in (48,68,88):d.ellipse(box((x,56,x+9,65)),fill=paper_color)
    elif name=='magnifier':
        d.ellipse(box((22,18,91,87)),fill=paper_color,outline=ink,width=p(9))
        d.ellipse(box((36,32,77,73)),fill=accent,outline=secondary,width=p(4))
        d.line([(p(77),p(80)),(p(116),p(119))],fill=ink,width=p(18))
        d.line([(p(77),p(80)),(p(116),p(119))],fill=accent,width=p(10))

    mask=art.getchannel('A')
    shadow_mask=Image.new('L',mask.size,0);shadow_mask.paste(mask,(p(6),p(7)))
    paper_mask=mask.filter(ImageFilter.MaxFilter(31));ink_mask=mask.filter(ImageFilter.MaxFilter(17))
    result=Image.new('RGBA',mask.size,(0,0,0,0))
    for color,alpha in ((ink,shadow_mask),(paper_color,paper_mask),(ink,ink_mask)):
        fill=Image.new('RGBA',mask.size,(*color,255));result.paste(fill,(0,0),alpha)
    result.alpha_composite(art)
    return result.resize((size,size),Image.Resampling.LANCZOS)

def _template_card(theme,w,h,fill,seed):
    cards=theme['cards'];palette=theme['palette'];shadow=cards['shadow_offset_px']
    return paper(w,h,fill,seed,theme['_cache_key'],palette['ink'],palette['paper'],cards['border_px'],cards['outline_px'],shadow[0],shadow[1],cards['roughness_px'],cards['padding_px']).copy()

def _template_text(card,box,value,size,color):
    text(ImageDraw.Draw(card),box,value,size,color)

def draw_template(im,scene,elapsed_s,scene_duration_s,theme):
    """Render one explicit visual template using batch 1 card pop timing."""
    name=scene['template'];palette=theme['palette'];text_colors=theme['text_colors']
    accents=palette['accents'];ink=palette['ink'];paper_color=palette['paper']
    if name=='hero_card':
        card=_template_card(theme,860,350,accents[0],310)
        icon=draw_procedural_icon(scene['icon'],theme,180);card.alpha_composite(icon,(48,83))
        _template_text(card,(265,65,545,215),scene['headline'],67,text_colors['accents'][0])
        layer(im,card,540,665,card_pop_scale(elapsed_s),-1)
    elif name=='terminal_box':
        card=_template_card(theme,860,370,paper_color,320)
        draw=ImageDraw.Draw(card);draw.rounded_rectangle((14,14,846,82),radius=18,fill=accents[1])
        _template_text(card,(36,22,575,50),'SIMULATED WORKFLOW',34,text_colors['accents'][1])
        for x,color in zip((770,798,826),accents[:3]):draw.ellipse((x,37,x+15,52),fill=color,outline=ink,width=2)
        line_y=118
        for line_index,line in enumerate(scene['lines']):
            draw.rectangle((42,line_y+19,60,line_y+37),fill=accents[line_index%len(accents)])
            _template_text(card,(78,line_y,745,62),line,47,ink)
            line_y+=78
        layer(im,card,540,670,card_pop_scale(elapsed_s),0)
    elif name=='step_flow':
        steps=scene['steps'];count=len(steps);width=min(390,math.floor((900-85*(count-1))/count));gap=(900-width*count)/(count-1)
        left=(W-900)/2;centers=[left+width/2+i*(width+gap) for i in range(count)]
        y=660
        for i,step in enumerate(steps):
            card=_template_card(theme,width,250,accents[i%len(accents)],330+i)
            _template_text(card,(24,28,width-48,194),step['text'],55,text_colors['accents'][i%len(accents)])
            age=elapsed_s-(step['cue']-scene['start'])
            layer(im,card,centers[i],y,card_pop_scale(age),(-1)**i*2)
            if i<count-1:
                arrow=draw_procedural_icon('arrow',theme,66)
                arrow_age=elapsed_s-(steps[i+1]['cue']-scene['start'])
                layer(im,arrow,(centers[i]+centers[i+1])/2,y,card_pop_scale(arrow_age))
    elif name=='feature_grid':
        features=scene['features'];count=len(features)
        positions={2:[(320,655),(760,655)],3:[(235,555),(845,555),(540,795)],4:[(310,550),(770,550),(310,790),(770,790)]}[count]
        card_w=370 if count==2 else 300;card_h=190 if count==2 else 174
        for i,(feature,(cx,cy)) in enumerate(zip(features,positions)):
            card=_template_card(theme,card_w,card_h,paper_color,350+i)
            icon=draw_procedural_icon(feature['icon'],theme,108);card.alpha_composite(icon,(18,(card_h-108)//2))
            _template_text(card,(132,35,card_w-150,card_h-70),feature['label'],39,ink)
            age=elapsed_s-(feature['cue']-scene['start'])
            layer(im,card,cx,cy,card_pop_scale(age),(-1)**i*1.5)
    else:raise ValueError(f'Unsupported visual template: {name!r}')

@lru_cache(maxsize=48)
def _grid_background(cache_key,i,colors,enabled,step,color,opacity,width):
    im=Image.new('RGBA',(W,H),colors[i%len(colors)]);d=ImageDraw.Draw(im)
    if enabled:
        rgb=ImageColor.getrgb(color);fill=(*rgb,round(opacity*255))
        for x in range(0,W,step):d.line((x,0,x,H),fill=fill,width=width)
        for y in range(0,H,step):d.line((0,y,W,y),fill=fill,width=width)
    return im
@lru_cache(maxsize=12)
def _image_background(cache_key,path):
    with Image.open(path) as source:
        return ImageOps.fit(source.convert('RGBA'),(W,H),method=Image.Resampling.LANCZOS)
def background(i,theme,scene=None):
    bg=theme['background'];cache_key=theme['_cache_key']
    variant_id=scene.get('background_variant') if scene else None
    if variant_id:
        variant=next(v for v in theme.get('background_variants',[]) if v['id']==variant_id)
        return _image_background(cache_key+':'+variant_id,str(variant['resolved_asset']['path']))
    if bg['mode']=='image':
        return _image_background(cache_key,str(bg['resolved_asset']['path']))
    grid=bg['grid']
    return _grid_background(cache_key,i,tuple(bg['colors']),grid['enabled'],grid['step_px'],grid['color'],grid['opacity'],grid['width_px'])

def star(im,x,y,r,color,t,ink_color):
    pts=[]
    for i in range(16):
        a=t*.25+i*math.pi/8;rr=r if i%2==0 else r*.38;pts.append((x+math.cos(a)*rr,y+math.sin(a)*rr))
    d=ImageDraw.Draw(im);d.polygon(pts,fill=color);d.line(pts+[pts[0]],fill=ink_color,width=5,joint='curve')
@lru_cache(maxsize=36)
def sprite(pose,shape):return Image.open(ROOT/'assets/mascot/rig'/f'{pose}_{shape}.png').convert('RGBA')

def plan_sfx_event_candidates(duration,scenes,*,render_policy_on=False):
    """Map visible batch 1/2 entrance cues to one procedural SFX candidate each."""
    candidates=[]
    priorities={
        'scene_title_enter':80,'hero_enter':90,'template_enter':55,
        'scene_card_enter':45,'media_panel_enter':55,'compare_card_enter':65,
        'summary_item_enter':70,'list_item_enter':70,'step_card_enter':70,
        'feature_card_enter':70,'visual_icon_cue':90,
        'aside_highlight_enter':95,'cta_enter':100,
    }

    def add(scene_index,event,time_s,target):
        time_s=float(time_s)
        if event not in SFX_TRIGGER_MAP:
            raise ValueError(f'No SFX trigger mapping for {event!r}')
        if 0<=time_s<float(duration):
            candidates.append({
                'time':time_s,'sound':SFX_TRIGGER_MAP[event],'event':event,
                'scene':scene_index,'target':target,'priority':priorities[event],
            })

    for scene_index,scene in enumerate(scenes):
        start=float(scene['start']);scene_duration=float(scene['end'])-start
        if scene.get('show_title',True):
            add(scene_index,'scene_title_enter',start,'scene_title')

        template=scene.get('template')
        if template:
            add(scene_index,'hero_enter' if template=='hero_card' else 'template_enter',start,template)
            if template=='step_flow':
                for item_index,step in enumerate(scene.get('steps',[])):
                    add(scene_index,'step_card_enter',step['cue'],f'step:{item_index}')
            elif template=='feature_grid':
                for item_index,feature in enumerate(scene.get('features',[])):
                    add(scene_index,'feature_card_enter',feature['cue'],f'feature:{item_index}')
        elif 'media' in scene:
            add(scene_index,'media_panel_enter',start,'media_panel')
        elif scene.get('layout')=='compare':
            for item_index,_ in enumerate(scene.get('items',['',''])[:2]):
                add(scene_index,'compare_card_enter',start+.15+item_index*.2,f'compare_card:{item_index}')
        elif scene.get('layout')=='list' and scene.get('items'):
            items=scene['items'];interval=min(ITEM_STAGGER_S,max(0.0,scene_duration)/(len(items)+1))
            for item_index,_ in enumerate(items[:4]):
                add(scene_index,'list_item_enter',start+.1+item_index*interval,f'list_item:{item_index}')
        elif scene.get('layout')=='summary' and render_policy_on and scene.get('items'):
            items=scene['items'][:4];interval=min(ITEM_STAGGER_S,max(0.0,scene_duration)/(len(items)+1))
            for item_index,_ in enumerate(items):
                add(scene_index,'summary_item_enter',start+.1+item_index*interval,f'summary_item:{item_index}')
        else:
            add(scene_index,'scene_card_enter',start+.1,'scene_card')

        if scene.get('aside'):
            add(scene_index,'aside_highlight_enter',start+.4,'aside')
        if scene.get('cta'):
            add(scene_index,'cta_enter',start+.7,'cta')
        for element_index,element in enumerate(scene.get('visual_elements',[])):
            add(scene_index,'visual_icon_cue',element['cue'],f'visual_icon:{element_index}')

    return sorted(candidates,key=lambda event:(event['time'],-event['priority'],event['scene'],event['target']))

def schedule_sfx_events(candidates,min_gap_s=SFX_EVENT_MIN_GAP_S):
    """Keep at most one sound per visual event and suppress crowded near-simultaneous hits."""
    scheduled=[]
    for candidate in sorted(candidates,key=lambda event:(event['time'],-event['priority'])):
        if not scheduled or candidate['time']-scheduled[-1]['time']>=min_gap_s:
            scheduled.append(candidate)
        elif candidate['priority']>scheduled[-1]['priority']:
            scheduled[-1]=candidate
    return [{key:value for key,value in event.items() if key!='priority'} for event in scheduled]

def _filtered_noise(noise,sample_rate,low_hz,high_hz):
    freqs=np.fft.rfftfreq(len(noise),1/sample_rate)
    spectrum=np.fft.rfft(noise)
    transition=max(120.0,min(low_hz*.35,(sample_rate/2-high_hz)*.35,900.0))
    low=np.clip((freqs-low_hz+transition)/transition,0,1)
    high=np.clip((high_hz+transition-freqs)/transition,0,1)
    return np.fft.irfft(spectrum*low*high,n=len(noise))

def _whoosh_noise(sample_count,sample_rate,rng):
    """Short overlap-add noise sweep with a moving bandpass filter."""
    frame_size=1024;hop=256;window=np.hanning(frame_size)
    freqs=np.fft.rfftfreq(frame_size,1/sample_rate)
    output=np.zeros(sample_count,dtype=np.float64);weight=np.zeros(sample_count,dtype=np.float64)
    starts=range(0,sample_count,hop)
    for start in starts:
        frame=rng.normal(0,1,frame_size)
        progress=min(1.0,start/max(1,sample_count-1))
        center=320.0*(8200.0/320.0)**progress
        low=max(100.0,center/1.65);high=min(sample_rate*.48,center*1.65)
        transition=max(100.0,min(low*.3,(sample_rate/2-high)*.3,700.0))
        band=np.clip((freqs-low+transition)/transition,0,1)*np.clip((high+transition-freqs)/transition,0,1)
        filtered=np.fft.irfft(np.fft.rfft(frame)*band,n=frame_size)*window
        end=min(sample_count,start+frame_size);length=end-start
        output[start:end]+=filtered[:length]
        weight[start:end]+=window[:length]**2
    return np.divide(output,np.sqrt(weight),out=np.zeros_like(output),where=weight>1e-8)

def procedural_sfx_clip(sound,rng,sample_rate=SFX_SAMPLE_RATE):
    """Generate a Foley-style placeholder clip; swap this source for licensed WAVs later."""
    durations={'whoosh':.25,'pop':.11,'ding':.38,'click':.035}
    if sound not in durations:raise ValueError(f'Unknown procedural SFX: {sound!r}')
    duration=durations[sound];count=round(duration*sample_rate);time=np.arange(count,dtype=np.float64)/sample_rate
    if sound=='whoosh':
        signal=_whoosh_noise(count,sample_rate,rng)*np.sin(np.pi*time/duration)**1.25
        target_peak=.12
    elif sound=='pop':
        noise=_filtered_noise(rng.normal(0,1,count),sample_rate,500,7500)
        low_thump=_filtered_noise(rng.normal(0,1,count),sample_rate,90,520)
        envelope=np.exp(-time*42)*(1-np.exp(-time*1400))
        signal=(.78*noise+.34*low_thump)*envelope
        target_peak=.15
    elif sound=='ding':
        fundamental=660.0
        signal=np.zeros(count,dtype=np.float64)
        for harmonic,amplitude,decay in ((1,.48,5.0),(2,.31,6.5),(3,.19,8.0),(4,.12,10.0),(5,.075,12.0)):
            signal+=amplitude*np.sin(2*np.pi*fundamental*harmonic*time)*np.exp(-time*decay)
        transient=_filtered_noise(rng.normal(0,1,count),sample_rate,1800,10000)
        signal+=.045*transient*np.exp(-time*95)
        target_peak=.115
    else:
        noise=_filtered_noise(rng.normal(0,1,count),sample_rate,2400,14000)
        envelope=np.exp(-time*180)*(1-np.exp(-time*2400))
        signal=noise*envelope
        target_peak=.075

    edge=np.clip(time/.0015,0,1)*np.clip((duration-time)/.008,0,1)
    signal*=edge
    peak=float(np.max(np.abs(signal))) if len(signal) else 0.0
    if peak>1e-12:signal*=target_peak/peak
    return signal

def make_event_sfx(duration,scenes,path,gain=1,*,render_policy_on=False):
    sample_rate=SFX_SAMPLE_RATE
    mix=np.zeros((round(duration*sample_rate),2),dtype=np.float64)
    candidates=plan_sfx_event_candidates(duration,scenes,render_policy_on=render_policy_on)
    events=schedule_sfx_events(candidates)
    rng=np.random.default_rng(301)
    for event in events:
        signal=procedural_sfx_clip(event['sound'],rng,sample_rate)*float(gain)/math.sqrt(2)
        start=round(event['time']*sample_rate);end=min(len(mix),start+len(signal))
        if end>start:mix[start:end]+=signal[:end-start,None]
    with wave.open(str(path),'wb') as output:
        output.setparams((2,2,sample_rate,0,'NONE','not compressed'))
        output.writeframes((np.clip(mix,-1,1)*32767).astype('<i2').tobytes())
    return events

def make_sfx(duration,scenes,path,gain=1,*,event_driven=False,render_policy_on=False):
    if event_driven:
        return make_event_sfx(duration,scenes,path,gain,render_policy_on=render_policy_on)

    # Preserve the original fixed-offset sound path byte-for-byte for legacy jobs.
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
        self.theme=load_job_theme(self.j)
        self.policy_on=render_policy_enabled(self.j);self.theme['_render_policy_enabled']=self.policy_on
        validate(self.j,self.d,resolved_theme=self.theme);self.words=read(resolve(self.d,self.j['words']));self.wt=[w['start'] for w in self.words]
        self.caption_intervals=visible_caption_intervals(self.words)
        self.v=read(resolve(self.d,self.j['visemes']));self.vt=[v['start'] for v in self.v];self.ct=[s['start'] for s in self.j['scenes']]
        self.duration=self.j['duration'];self.media={}
        self.decoration_images=[]
        for decoration in self.theme.get('decorations',[]):
            path=decoration['resolved_asset']['path']
            with Image.open(path) as source:self.decoration_images.append(source.convert('RGBA'))
        self.voice=out/'voice_pcm.wav'
        run(['ffmpeg','-y','-v','error','-i',str(resolve(self.d,self.j['voice'])),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(self.voice)])
        with wave.open(str(self.voice),'rb') as w:self.audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
        self.mouth_rig_root,_=resolve_runtime_mascot(self.theme)
        self.mouth_rig=PoseMouthRig(self.mouth_rig_root,self.voice,resolve(self.d,self.j['visemes']),resolve(self.d,self.j['words']))
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
        if active<0:return
        if self.policy_on:
            ids=visible_caption_indices(self.words,self.caption_intervals,t)
            if not ids:return
        else:
            if t>self.words[active]['end']+.5:return
            ids=list(range(active//3*3,active+1))
        cfg=self.theme['captions']
        ww=[max(112,font(cfg['font_size_px']).getbbox(self.words[i]['word'])[2]+68) for i in ids]
        while len(ids)>1 and sum(ww)+cfg['gap_px']*(len(ids)-1)>cfg['max_width_px']:ids.pop(0);ww.pop(0)
        scale=min(1,cfg['max_width_px']/(sum(ww)+cfg['gap_px']*(len(ids)-1)));x=(W-(sum(ww)+cfg['gap_px']*(len(ids)-1))*scale)/2
        palette=self.theme['palette'];text_colors=self.theme['text_colors'];cards=self.theme['cards'];shadow=cards['shadow_offset_px']
        for i,width in zip(ids,ww):
            accent_index=cfg['fill_palette_indexes'][i%len(cfg['fill_palette_indexes'])]
            text_key=cfg['text_palette_keys'][i%len(cfg['text_palette_keys'])]
            fill=palette['accents'][accent_index]
            text_color=palette['ink'] if text_key=='ink' else palette['paper']
            width=round(width*scale)
            a=paper(width,cfg['height_px'],fill,800+i,self.theme['_cache_key'],palette['ink'],palette['paper'],cards['border_px'],cards['outline_px'],shadow[0],shadow[1],cards['roughness_px'],cards['padding_px']).copy()
            pad=cfg['padding_px'];text(ImageDraw.Draw(a),(pad,pad,width-2*pad,cfg['height_px']-2*pad),self.words[i]['word'],round(cfg['font_size_px']*scale),text_color)
            layer(im,a,x+width/2,cfg['y_px'],pop((t-self.words[i]['start'])/.14) if i==active else 1,2 if i%2 else -2);x+=width+cfg['gap_px']*scale
    def frame(self,t):
        idx=max(0,bisect_right(self.ct,t)-1);c=self.j['scenes'][idx];u=t-c['start'];im=background(idx,self.theme,c).copy()
        palette=self.theme['palette'];text_colors=self.theme['text_colors'];layout=self.theme['layout'];motion=self.theme['motion']
        accents=palette['accents'];ink=palette['ink'];paper_color=palette['paper']
        scene_for_safety=dict(c)
        right=mascot_right_for_scene(self.j,c)
        scene_for_safety['right']=right
        scene_for_safety['_aside_x']=layout['aside_right_center_px'][0] if right else layout['aside_center_px'][0]
        scene_for_safety['_aside_y']=layout['aside_right_center_px'][1] if right else layout['aside_center_px'][1]
        for deco_index,(decoration,asset) in enumerate(zip(self.theme.get('decorations',[]),self.decoration_images)):
            safety_decoration=decoration
            if self.policy_on:
                safety_decoration={**decoration,'size_px':math.ceil(decoration['size_px']*POP_MAX_SCALE)}
            if not decoration_is_safe(safety_decoration,scene_for_safety):continue
            x,y=decoration['center_px'];scale=1.0
            if decoration['motion']=='drift':
                dx,dy,scale=deterministic_motion(t,motion['seed'],f"decoration-{deco_index}-{decoration['id']}",5,4,6,.02)
                x+=dx;y+=dy
            if x-decoration['size_px']/2<0 or x+decoration['size_px']/2>W or y-decoration['size_px']/2<0 or y+decoration['size_px']/2>H:continue
            sticker=asset.copy();sticker.thumbnail((decoration['size_px'],decoration['size_px']),Image.Resampling.LANCZOS)
            if self.policy_on:scale*=card_pop_scale(u)
            layer(im,sticker,x,y,scale)
        if self.j.get('show_brand',True):
            sign(im,*layout['brand_center_px'],360,87,'LiplnwZa',paper_color,48,1,-2,101,self.theme,text_colors['paper'])
        if c.get('show_topic_label',True):
            sign(im,*layout['topic_center_px'],330,87,self.j.get('topic_label',self.j['title']),accents[1],37,1,2,102,self.theme,text_colors['accents'][1])
        title_index=1 if idx%3==0 else 2
        if c.get('show_title',True):
            sign(im,*layout['title_center_px'],942,182,c['title'],accents[title_index],84,u+.2,-1,103,self.theme,text_colors['accents'][title_index])
        scene_layout=c['layout']
        if 'template' in c:
            draw_template(im,c,u,c['end']-c['start'],self.theme)
        elif scene_layout=='title':
            sign(im,*self.theme['layout']['content_center_px'],875,320,c.get('body',''),accents[0],100,u-.1,1,200,self.theme,text_colors['accents'][0])
        elif scene_layout=='summary':
            summary_items=c.get('items',[])[:4] if self.policy_on else []
            if summary_items:
                if c.get('body'):
                    sign(im,540,420,875,90,c['body'],paper_color,60,u-.1,1,200,self.theme,text_colors['paper'])
                scene_duration=c['end']-c['start']
                for k,value in enumerate(summary_items):
                    age=staggered_item_age(u,k,len(summary_items),scene_duration)
                    sign(im,540,530+k*90,860,80,value,accents[k],48,age,(-1)**k*2,220+k,self.theme,text_colors['accents'][k])
            else:
                sign(im,*self.theme['layout']['content_center_px'],875,320,c.get('body',''),paper_color,100,u-.1,1,200,self.theme,text_colors['paper'])
        elif scene_layout=='compare':
            cards=c.get('items',['',''])
            for k,v in enumerate(cards[:2]):sign(im,292+k*495,575,430,330,v,accents[k],72,u-.15-k*.2,(-1)**k*3,210+k,self.theme,text_colors['accents'][k])
        elif scene_layout=='list':
            items=c.get('items',[])[:4];scene_duration=c['end']-c['start']
            for k,v in enumerate(items):
                age=staggered_item_age(u,k,len(items),scene_duration) if self.policy_on else u-.1-k*.3
                sign(im,540,450+k*120,860,110,v,accents[k],57,age,(-1)**k*2,220+k,self.theme,text_colors['accents'][k])
        if idx in self.media:
            arr=self.media[idx];a=arr[min(len(arr)-1,max(0,int(u*FPS)))]
            if isinstance(a,Path):
                with Image.open(a) as pic:a=pic.convert('RGBA')
            a=a.copy();a.thumbnail((850,390),Image.Resampling.LANCZOS)
            media_enter=card_pop_scale(u) if self.policy_on else 1
            sign(im,540,580,920,460,'',paper_color,50,u if self.policy_on else 1,1,230,self.theme,text_colors['paper'])
            media_scale=(.98+.02*ease(u/.4))*min(850/a.width,390/a.height)*media_enter
            media_x=540;media_y=580
            if self.policy_on:
                dx,dy,drift_scale=media_motion_transform(t,self.theme['motion']['seed'],f"scene-{idx}-media",a.size)
                media_x+=dx;media_y+=dy;media_scale=min(1.05,media_scale*drift_scale)
            layer(im,a,media_x,media_y,media_scale,1)
            label=c['media']['label'];sign(im,540,847,880,65,label,paper_color,30,u-.18 if self.policy_on else 1,-1,231,self.theme,text_colors['paper'])
        age=u;pose=c.get('pose','explain')
        for change in c.get('pose_changes',[]):
            if u>=change['at']:pose=change['pose'];age=u-change['at']
        mascot_center=layout['mascot_right_center_px'] if right else layout['mascot_center_px']
        enter=ease(age/.28);cx=mascot_center[0]+(1-enter)*(110 if right else -110)
        mascot_frame=self.mouth_rig.frame(pose,t)
        if self.policy_on and mascot_blink_active(t):
            mascot_frame=blink_eyes(mascot_frame,self.mouth_rig.registration[pose]['source_eye_centers'])
            pose_data=self.mouth_rig.pose_data[pose]
            if pose_data['occluder'].getbbox():mascot_frame=Image.composite(pose_data['original'],mascot_frame,pose_data['occluder'])
        bob=mascot_breathing_y(t) if self.policy_on else math.sin(t*motion['mascot_bob_rate'])*motion['mascot_bob_px']
        layer(im,mascot_frame,cx,mascot_center[1]+bob,700/550,math.sin(t*1.8))
        if c.get('aside'):
            aside_center=self.theme['layout']['aside_right_center_px'] if right else self.theme['layout']['aside_center_px']
            sign(im,*aside_center,355,230,c['aside'],accents[0],64,u-.4,-4 if right else 4,240,self.theme,text_colors['accents'][0])
        if c.get('cta'):sign(im,*self.theme['layout']['cta_center_px'],880,100,c['cta'],paper_color,52,u-.7,-1,241,self.theme,text_colors['paper'])
        for element in c.get('visual_elements',[]):
            age=t-element['cue']
            if age<0:continue
            icon=draw_procedural_icon(element['icon'],self.theme)
            layer(im,icon,*element['position'],card_pop_scale(age))
        for k,(x,y,r) in enumerate([(960,400,36),(85,1450,40),(965,1490,27)]):
            x+=math.sin(t*1.6+k)*7
            star_safety={'center_px':[x,y],'size_px':2*r+14,'motion':'drift'}
            if not self.policy_on or decoration_is_safe(star_safety,scene_for_safety):star(im,x,y,r,accents[k],t,ink)
        self.captions(im,t);footer_box=self.theme['layout']['footer_box'];text(ImageDraw.Draw(im),tuple(footer_box),self.j.get('footer',''),29,ink)
        x0,y0,x1,y1=self.theme['layout']['progress_box'];dr=ImageDraw.Draw(im)
        dr.rounded_rectangle((x0,y0,x1,y1),radius=min(5,(y1-y0)//2),fill=paper_color)
        progress_width=round((x1-x0)*max(0,min(1,t/self.duration)))
        if progress_width>0:
            fill_x1=x0+progress_width;radius=min(5,progress_width//2,(y1-y0)//2)
            dr.rounded_rectangle((x0,y0,fill_x1,y1),radius=radius,fill=ink)
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
        validate(self.j,self.d,True);self.export_srt();events=make_sfx(
            self.duration,self.j['scenes'],self.out/'sfx.wav',self.j.get('sfx_gain',1),
            event_driven=sfx_events_enabled(self.j),render_policy_on=self.policy_on,
        );write(self.out/'sfx_events.json',events)
        bgm_info=audio_mix.validate_bgm(self.j,self.d,self.duration) if self.j.get('bgm') is not None else None
        bgm_stem=audio_mix.prepare_bgm_stem(bgm_info,self.duration,self.out/'bgm_pcm.wav')
        voice_stem=self.voice
        if bgm_info:
            voice_stem=audio_mix.normalize_stem(self.voice,self.out/'voice_normalized.wav',self.duration)
            bgm_stem=audio_mix.normalize_stem(bgm_stem,self.out/'bgm_normalized.wav',self.duration)
            requested_gain=bgm_info['gain_db']
            effective_gain,duck_analysis=audio_mix.safe_bgm_gain(voice_stem,bgm_stem,requested_gain)
            bgm_info={**bgm_info,'requested_gain_db':requested_gain,'gain_db':effective_gain,'duck_analysis':duck_analysis}
            write(self.out/'mix_report.json',audio_mix.mix_report(bgm_info))
        target=self.out/'video.mp4';n=round(self.duration*FPS)
        cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r','30','-i','pipe:0','-i',str(voice_stem),'-i',str(self.out/'sfx.wav')]
        if bgm_stem:cmd+=['-i',str(bgm_stem)]
        cmd+=['-filter_complex',audio_mix.build_audio_filter(self.duration,bgm_info),'-map','0:v','-map','[a]','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-t',str(self.duration),'-movflags','+faststart','-threads','3',str(target)]
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
    report_path=Path(path).parent/'qc.json'
    # Invalidate any previous pass report before starting a new check. If probing,
    # decoding, or measurement fails, the sidecar must not retain a stale pass.
    write(report_path,{'technical_pass':False,'status':'incomplete','errors':['QC did not complete']})
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)]))
    run(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],stdout=subprocess.DEVNULL)
    audio=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-af','loudnorm=I=-16:TP=-1:LRA=7:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    pos=audio.stderr.rfind('{');end=audio.stderr.rfind('}')+1;loud=json.loads(audio.stderr[pos:end])
    v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio')
    errors=[]
    video_spec=(W,H,'30/1','h264')
    video_actual=(v.get('width'),v.get('height'),v.get('r_frame_rate'),v.get('codec_name'))
    if video_actual!=video_spec:
        errors.append(f'Video must be H.264 {W}x{H} at 30 fps; found {video_actual[3]} {video_actual[0]}x{video_actual[1]} at {video_actual[2]} fps')
    if a.get('sample_rate')!='48000' or a.get('channels')!=2:
        errors.append(f'Audio must be 48000 Hz stereo; found {a.get("sample_rate")} Hz, {a.get("channels")} channels')
    expected_frames=round(float(info['format']['duration'])*FPS)
    actual_frames=int(v.get('nb_read_frames',-1))
    if actual_frames!=expected_frames:
        errors.append(f'Video frame count must match duration at {FPS} fps; found {actual_frames}, expected {expected_frames}')
    integrated=float(loud['input_i']);true_peak=float(loud['input_tp'])
    if not -18<=integrated<=-14:
        errors.append(f'Integrated loudness must be between -18 and -14 LUFS; found {integrated:.2f} LUFS')
    if true_peak>-1:
        errors.append(f'True peak must be at or below -1 dBTP; found {true_peak:.2f} dBTP')
    report={'technical_pass':not errors,'decode_errors':0,'video':{k:v.get(k) for k in ['codec_name','width','height','r_frame_rate','nb_read_frames']},'audio':{k:a.get(k) for k in ['codec_name','sample_rate','channels']},'duration':info['format']['duration'],'loudness':loud,'sha256':sha(path),'limits':['Automated checks do not certify factual accuracy, usage rights, subjective lip sync, or publication approval.']}
    if errors:report['errors']=errors
    write(report_path,report)
    if errors:raise ValueError('; '.join(errors))
    return report

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
