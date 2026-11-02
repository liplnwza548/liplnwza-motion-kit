from pathlib import Path
import argparse,json,re
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args()
if not re.fullmatch('[a-z0-9][a-z0-9_-]{0,60}',a.name):p.error('Use a short lowercase ASCII job name')
d=ROOT/'jobs'/a.name;d.mkdir(parents=True,exist_ok=False)
(d/'inputs').mkdir()
for name,body in [('BRIEF.md','# Brief\n\nต้นฉบับ:\nเป้าหมาย:\nความยาว:\nเสียงที่ใช้:\nแหล่งข้อมูลและข้อจำกัด:\n'),('PROPOSAL.md','# Proposal for Philip\n\nประเด็นหลัก:\nบทพากย์:\nแนวภาพและที่มาสื่อ:\nเวลา/ต้นทุน:\nข้อเท็จจริงที่ยังไม่ยืนยัน:\n'),('SESSION.md','# Session\n\nสถานะ: รอเนื้อหา\nรุ่นชุด: 0.2.0\nหลักฐานอนุมัติ: ยังไม่มี\nขั้นถัดไป: รับเนื้อหา\n')]: (d/name).write_text(body,encoding='utf-8')
job=dict(schema_version=1,render_policy_version=1,title='REPLACE',topic_label='REPLACE',duration=30,voice='inputs/voice.wav',words='words.json',visemes='visemes.json',footer='REPLACE',sources=[],scenes=[dict(start=0,end=30,layout='title',title='REPLACE',body='REPLACE',pose='explain')])
(d/'job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2))
(d/'approval.json').write_text(json.dumps(dict(status='pending',job_digest=None,evidence=None),indent=2))
print(d)
