---
name: liplnwza-motion
description: "Autonomous Warodom paper-cut collage motion graphics video production system. Produces vertical (9:16, 1080x1920, 30fps) short-form videos featuring mascot LiplnwZa, Thai typography (Prompt-Bold), paper-cut sticker pills, procedural lip-sync, and automated technical QC."
---

# 🎨 LiplnwZa Motion Kit — Master Skill Specification

> **สำหรับ AI Agent ทุกตัว (BeAN Muse AI, ChatGPT, Gemini Spark, AGY):**  
> โฟลเดอร์นี้คือชุดสกิลแบบ All-in-One เมื่อได้รับมอบหมายให้สร้างวิดีโอโมชันกราฟิก ให้ทำตามคู่มือฉบับนี้อย่างเคร่งครัด

---

## 📌 กฎเหล็กของระบบ (Golden Rules)

1. **ห้ามแตะโฟลเดอร์ `_archive/` เด็ดขาด:** โฟลเดอร์นี้เป็นคลังเก็บของเก่า (v0.1) ที่มีบั๊กมุมปากมาสคอต
2. **ใช้เครื่องยนต์ใน `renderer/` เท่านั้น:** โค้ดใน `renderer/` (Motion Kit v0.2.1 — เวอร์ชันฐานปัจจุบันของชุดสกิลนี้) ได้รับการแพตช์ระบบปาก Clean Plate 6 ท่า, เกลี่ยขอบแก้ม, แก้บั๊กสระไทยบน Windows (`uharfbuzz`) และแก้บั๊ก FFmpeg `qc()` เรียบร้อยแล้ว
3. **หลักเสียงโคลนของเจ้าของเป็นหลัก (Clone-Voice-First):** เสียงหลักของสายผลิตคือ **เสียงโคลนของฟิลิปตามสูตร v2 ที่เจ้าของล็อกไว้** คลิปต้องสร้างโดยยึดเสียงพากย์เป็นศูนย์กลาง (Anchor) — ความยาวคลิป จังหวะตัดฉาก และการเด้งของซับไตเติลต้องผูกติดกับคลื่นเสียงพากย์เสมอ โดยไฟล์เสียงที่ใช้คือเสียงโคลนที่ผ่านการอนุมัติจากฟิลิปแล้ว หรือไฟล์เสียงอัดจริงเมื่อฟิลิปเป็นผู้ส่งมาเอง รายละเอียดงานเสียงและไฟล์เสียงอ้างอิงของเจ้าของเก็บไว้เฉพาะในโฟลเดอร์โปรเจกต์ส่วนตัวของเจ้าของเท่านั้น **ห้ามเผยแพร่ไฟล์เสียงอ้างอิงหรือรายละเอียดการโคลนเสียงไว้ใน repo นี้หรือที่สาธารณะ**

---

## 🛠️ โครงสร้างไฟล์ในชุดสกิล (Repository Architecture)

```text
liplnwza-motion-kit/
├── SKILL.md                          ← [คู่มือทักษะสำหรับ AI Agent ฉบับนี้]
├── README.md                         ← ภาพรวมคลังโค้ด, Quickstart, และคู่มือติดตั้ง
├── START_HERE.md                     ← คู่มือเริ่มต้นด่วนสำหรับมนุษย์และ AI
├── AGENTS.md                         ← สเปกแบรนด์, จานสี Warodom, และกฎการจัดองค์ประกอบภาพ
├── renderer/                         ← เครื่องยนต์เรนเดอร์หลัก
│   ├── kit.py                        ← CLI สั่งการ (doctor, validate, digest, render, qc) — รวมระบบ Clean Plate Lip-sync และตัวจัดรูปแบบข้อความไทย (HarfBuzz / uharfbuzz) ไว้ในไฟล์นี้
│   ├── new_job.py                    ← สร้างโฟลเดอร์งานใหม่ที่ jobs/<slug>/
│   └── prepare_cues.py               ← (ทางเลือก) จับเวลาคำ/ปากจากบทที่รู้อยู่แล้ว ต้องมีโมเดล faster-whisper แบบ local เท่านั้น ห้ามดาวน์โหลดเอง
│   # rig_motion.py อยู่ที่ assets/mascot/mouth_rig/ ไม่ได้อยู่ใน renderer/
├── assets/                           ← แอสเสตมาตรฐานประจำเครื่องยนต์
│   ├── mascot/mouth_rig/             ← รูป Clean Plate 6 ท่า + ปาก 6 รูปทรง + profiles.json
│   └── fonts/Prompt-Bold.ttf         ← ฟอนต์มาตรฐานบังคับสำหรับภาษาไทยและอังกฤษ
├── brand/                            ← คลังภาพมาสคอต LiplnwZa ต้นฉบับ
├── examples/                         ← งานตัวอย่างและเกณฑ์มาตรฐาน
│   └── benchmark15/                  ← วิดีโอ Benchmark 15s (job.json, voice.wav, words.json, visemes.json)
└── tests/                            ← ชุดทดสอบระบบอัตโนมัติ (test_runtime.py ผ่าน 7/7 ข้อ)
```

---

## ⚡ กระบวนการทำงาน 4 ขั้นตอน (Standard Operating Procedure - SOP)

### ขั้นที่ 1: รับ Input จากฟิลิป (Ingest & Analyze)
สิ่งที่ฟิลิปจะส่งมาให้:
1. **ไฟล์เสียงพากย์ที่ผ่านอนุมัติแล้ว** (`voice.mp3` หรือ `voice.wav`) — เสียงโคลนของฟิลิป (สูตร v2) ที่เจ้าของฟังอนุมัติแล้ว หรือไฟล์เสียงอัดจริงที่ฟิลิปส่งมาเอง
2. **หัวข้อ/เป้าหมายของคลิป** (Topic Brief)
3. **รูปภาพหรือวิดีโอประกอบ** (ถ้ามี)

### ขั้นที่ 2: วางแผนก่อนสร้าง (Pre-production Beat Sheet)
**ห้ามเรนเดอร์ทันที** ให้สร้างแผนฉากส่งให้ฟิลิปตรวจก่อน:
- แบ่งฉากเป็น 5–6 ฉากย่อยตามจังหวะเว้นวรรคของเสียงพูด
- กำหนดป้ายริบบิ้นหัวข้อด้านบน (`torn_paper`)
- เลือกท่าทางมาสคอตให้ตรงกับอารมณ์ฉาก:
  - `thinking` (ตั้งคำถาม / สงสัย)
  - `point_right` / `point_left` (ชี้ประเด็น / ชี้การ์ด)
  - `magnify` (ส่องดูหลักฐาน / เจาะลึก)
  - `explain` (อธิบายหลักการ)
  - `thumbs_up` (สรุปผล / ชวนกดติดตาม)
- ส่ง Beat Sheet ให้ฟิลิปตรวจและรอคำสั่ง **"อนุมัติสร้าง"**

### ขั้นที่ 3: ประกอบไฟล์งาน (Assembly & Automation)
เมื่อได้รับอนุมัติ ให้สร้างโฟลเดอร์งานใหม่ด้วย `python renderer/new_job.py <slug>` (จะได้โฟลเดอร์ `jobs/<slug>/` ที่รากของ repo):
1. วางไฟล์เสียง `voice.mp3`
2. ถอดคำและวัดคลื่นเสียงสร้าง `words.json` (25–30 คำ) และ `visemes.json` (60–90 ท่าปาก) — ใช้ `renderer/prepare_cues.py` ช่วยได้เฉพาะเมื่อมีโมเดล faster-whisper แบบ local ในเครื่องอยู่แล้วเท่านั้น (ห้ามดาวน์โหลดเอง) และผลของมันเป็น known-script alignment ไม่ใช่การตรวจว่าเสียงพูดตรงบท เจ้าของต้องฟังเทียบเสียงจริงก่อนใช้
3. เขียนไฟล์ `job.json` ตาม Schema v1
4. สร้างค่าอนุมัติ:
   ```bash
   python renderer/kit.py digest jobs/<slug>/job.json
   ```
   นำค่าแฮชที่ได้ไปใส่ใน `approval.json` (`status: "approved"`, `job_digest: "..."`)

### ขั้นที่ 4: สั่งเรนเดอร์และตรวจ QC (Render & Delivery)
```bash
# 1. ตรวจสอบความถูกต้องของข้อมูล
python renderer/kit.py validate jobs/<slug>/job.json

# 2. เรนเดอร์วิดีโอ
python renderer/kit.py render jobs/<slug>/job.json --out jobs/<slug>/output

# 3. ไม่ต้องมิกซ์เสียงแยก: ขั้น render มิกซ์เสียงพากย์ + SFX และ loudnorm ให้แล้ว และรัน QC ให้ในตัว (ไม่มีไฟล์ postmix.py ในชุดปัจจุบัน)

# 4. (ทางเลือก) รันคำสั่งตรวจคุณภาพซ้ำกับไฟล์ที่เรนเดอร์ได้
python renderer/kit.py qc jobs/<slug>/output/video.mp4
```

---

## 🎯 เกณฑ์การผ่าน QC ที่ต้องรายงานเจ้าของงาน
- [ ] ขนาดภาพ: 1080×1920 (9:16 แนวตั้ง), 30 fps
- [ ] Decode Errors: 0
- [ ] ความดังเสียง: Integrated Loudness ระหว่าง -18 ถึง -14 LUFS (True Peak ≤ -1.0 dBTP)
- [ ] ปากมาสคอต: แก้มเนียน ไร้รอยแผลข้างแก้มในท่า thumbs_up และปากอ้าพูดตามเสียงจริง
- [ ] ซับไตเติล: เด้งคำต่อคำตรงเสียงพูด และตัวอักษรไทยสระ/วรรณยุกต์ไม่ซ้อนทับ
