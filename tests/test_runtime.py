"""Contract/integration tests for the portable kit; no internet or API required."""
from pathlib import Path
import copy,json,shutil,subprocess,sys,tempfile,unittest,wave
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'renderer'));import kit
class RuntimeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='_runtime_test_',dir=ROOT/'tests');self.d=Path(self.temp.name)
  shutil.copytree(ROOT/'examples/benchmark15',self.d,dirs_exist_ok=True,ignore=shutil.ignore_patterns('output','reference','media_cache','__pycache__'))
  self.j=kit.read(self.d/'job.json')
 def tearDown(self):self.temp.cleanup()
 def test_approved_job_and_approval_rejection(self):
  self.assertTrue(kit.validate(self.j,self.d,True)['valid'])
  changed=copy.deepcopy(self.j);changed['title']='หัวข้อใหม่ที่ยังไม่อนุมัติ'
  with self.assertRaisesRegex(ValueError,'Approval does not match'):kit.validate(changed,self.d,True)
  a=kit.read(self.d/'approval.json');a['status']='pending';kit.write(self.d/'approval.json',a)
  with self.assertRaisesRegex(ValueError,'Owner approval missing'):kit.validate(self.j,self.d,True)
 def test_bad_inputs_do_not_silently_render(self):
  j=copy.deepcopy(self.j);j['scenes'][1]['start']+=.2
  with self.assertRaisesRegex(ValueError,'gap/overlap'):kit.validate(j,self.d)
  words=kit.read(self.d/'words.json');words[0]['end']=words[1]['end'];kit.write(self.d/'words.json',words)
  with self.assertRaisesRegex(ValueError,'overlap'):kit.validate(self.j,self.d)
 def test_long_voice_and_missing_media(self):
  with wave.open(str(self.d/'too_long.wav'),'wb') as w:w.setparams((1,2,48000,0,'NONE','not compressed'));w.writeframes(np.zeros(16*48000,dtype='<i2').tobytes())
  j=copy.deepcopy(self.j);j['voice']='too_long.wav'
  with self.assertRaisesRegex(ValueError,'Voice is longer'):kit.validate(j,self.d)
  j=copy.deepcopy(self.j);j['scenes'][1]['media']['path']='missing.png'
  with self.assertRaisesRegex(ValueError,'Missing file'):kit.validate(j,self.d)
 def test_new_topic_list_and_pose_switch(self):
  j=copy.deepcopy(self.j);j['title']='สำรองไฟล์';j['topic_label']='เก็บงานให้ปลอดภัย';j['scenes'][0].update(layout='list',title='สำรองไฟล์อย่างไร',items=['แยกอีกแห่ง','ลองเปิดไฟล์'],pose_changes=[dict(at=1,pose='thinking')]);kit.write(self.d/'job.json',j)
  c=kit.Composition(self.d/'job.json',self.d/'output');self.assertEqual(c.frame(1.4).size,(1080,1920))
 def test_all_six_clean_plate_mouth_profiles(self):
  c=kit.Composition(self.d/'job.json',self.d/'mouth-rig-check')
  self.assertTrue((self.d/'mouth-rig-check'/'mouth_rig_registration.json').is_file())
  self.assertEqual(set(c.mouth_rig.pose_data),set(kit.POSES))
  self.assertEqual(set(c.mouth_rig.registration),set(kit.POSES))
  for pose in kit.POSES:
   data=c.mouth_rig.pose_data[pose]
   self.assertGreaterEqual(c.mouth_rig.registration[pose]['min_eye_correlation'],.72)
   original=np.asarray(data['original']);base=np.asarray(data['base']);mask=np.asarray(data['mask'])
   self.assertTrue(np.array_equal(original[mask==0],base[mask==0]),pose)
   self.assertEqual(c.mouth_rig.frame(pose,1.0).size,data['original'].size)
  delta=np.abs(np.diff(c.mouth_rig.parameter_timeline,axis=0))
  self.assertTrue(np.all(delta<=np.array([240,240,7,8])/120+1e-6))
  self.assertEqual(c.frame(1.4).size,(1080,1920))
 def test_existing_export_is_preserved(self):
  dest=self.d/'previous';dest.mkdir();f=dest/'video.mp4';f.write_bytes(b'old-version-sentinel')
  r=subprocess.run([sys.executable,str(ROOT/'renderer/kit.py'),'render',str(self.d/'job.json'),'--out',str(dest)],capture_output=True,text=True)
  self.assertEqual(r.returncode,2);self.assertIn('Output video exists',r.stderr);self.assertEqual(f.read_bytes(),b'old-version-sentinel')
 def test_video_and_green_screen(self):
  # Original synthetic fixture, not third-party stock or a pretend real event.
  movie=self.d/'fixture.mp4';p=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','240x160','-r','30','-i','pipe:0','-c:v','libx264','-pix_fmt','yuv420p',str(movie)],stdin=subprocess.PIPE)
  for i in range(30):
   im=Image.new('RGB',(240,160),'#00ff00');ImageDraw.Draw(im).rectangle((60+i,50,160+i,130),fill='#f02020');p.stdin.write(im.tobytes())
  p.stdin.close();self.assertEqual(p.wait(),0)
  for keyed in [False,True]:
   j=copy.deepcopy(self.j);j['scenes'][1]['media'].update(path='fixture.mp4',kind='video',green_screen=keyed)
   kit.write(self.d/'job.json',j);c=kit.Composition(self.d/'job.json',self.d/('keyed' if keyed else 'plain'))
   with Image.open(c.media[1][0]) as im:
    arr=np.asarray(im.convert('RGBA'));self.assertTrue(arr[:,:,3].max()>250)
    self.assertEqual(arr[5,5,3]<10,keyed)
   self.assertEqual(c.frame(3.2).size,(1080,1920))
if __name__=='__main__':unittest.main(verbosity=2)
