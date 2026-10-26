# เสียงและขอบคำ

ฐานคือเสียงที่ Philip ส่งหรือให้สิทธิ์ชัดเจน ไม่สร้าง/โคลนใหม่หรือเลือกบริการเสียเงินโดยพลการ งาน e-commerce อาจกำหนด human VO ให้ยึด brief ของงานนั้น อย่าใช้กติกา cloned VO ของ motion pilot แทนทุกโปรเจกต์

ทางเรนเดอร์ใช้ words/visemes ที่เตรียมแล้ว ไม่ดาวน์โหลดโมเดล ไม่มีการเร่งหรือตัดเสียงอัตโนมัติ หากเสียงมีช่องพัก ให้ตรวจช่วงเงียบจริงและทำรายการตัดแยก ไม่สั่ง silence removal ทั้งคลิปโดยไม่ฟัง

## เตรียมคำสำหรับเสียงใหม่
เลือกตามเครื่องมือที่มี: owner-provided timed cues / alignment provider ที่ได้รับอนุญาต / local optional alignment อย่าใช้เวลาหารเท่าหรือ SRT ระดับวลีแล้วเรียกว่า word sync

ตัวเลือก local ใน renderer/prepare_cues.py ต้องติดตั้ง renderer/optional-alignment-requirements.txt และจัดหา faster-whisper small model แยกเอง (ไม่บรรจุน้ำหนักใน kit) ใช้เฉพาะ model directory ที่มีอยู่ ไม่มี implicit model download

เตรียม segments.json เช่น [{"start":0,"end":8.2,"chips":["คำแรก","คำถัดไป"]}] แบ่งย่อหน้าตามช่วงเสียงจริง ทุก chunk <=29s รวมข้อความตรงบทที่รู้แล้ว ชื่อ/คำประสมอาจอยู่ชิปเดียว

```bash
python renderer/prepare_cues.py --voice jobs/ID/inputs/voice.wav --segments jobs/ID/segments.json --model /path/to/local/model --out jobs/ID
```

สคริปต์ใช้ known-script attention alignment ไม่ได้พิสูจน์ว่าเสียงอ่านตรงบท ต้องฟัง/เทียบ transcription อีกทาง ตรวจแก้คำและชื่อ/ตัวเลข มันสร้าง visemes จากเสียงอ่านประมาณในขอบคำ มีผลลัพธ์ pronunciation_guide และ timing_provenance ให้ตรวจ หากเครื่องไม่มี dependency/model ให้หยุดเฉพาะขั้นเตรียมคำและเสนอช่องทางที่มีจริง ห้ามทำเป็นว่าเรนเดอร์ตัวอย่างได้จึง align เสียงใหม่ได้ด้วย

## New-job caption visibility

Jobs created by `renderer/new_job.py` carry `render_policy_version=1`. A chip starts at its word cue and expires at `min(cue.end, cue.start+1.2s)`; prior chips in the group of three disappear at their own cue end. The renderer does not add a hold after the cue. Validation requires a 0.4–0.7s mean visible duration per clip; if the cues miss that range, re-align the words from the approved script and actual audio. A long indivisible cue is capped at 1.2s. Jobs without the version field keep their prior behavior.

## Optional BGM

BGM is job-local and opt-in. The selected source must have recorded rights evidence and Philip approval in `sources[]`, and the source file must cover the requested duration; looping is rejected. The renderer decodes and normalizes voice and BGM stems separately to -16 LUFS / -1 dBTP before mixing. It calculates a static bed gain from overlapping 0.4s voice windows so BGM stays at least 12dB below active narration, then applies sidechain compression, a 0.5s fade-in, and a 1.5s fade-out. The final mix targets -16 LUFS / -1 dBTP. If no BGM is selected, the voice/SFX path runs without a music input.
