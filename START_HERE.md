# 🚀 START_HERE.md — คู่มือศูนย์กลางสำหรับ AI Agent ทุกตัว (BeAN Muse AI / ChatGPT / AGY)

> **กฎเหล็กข้อที่ 1:** ห้ามใช้ไฟล์ใด ๆ ในโฟลเดอร์ `_archive/` เด็ดขาด (เพราะเป็นรุ่นเก่า v0.1 ที่ยังมีรอยปะขอบปากมาสคอต)
> **กฎเหล็กข้อที่ 2:** ให้ใช้เครื่องยนต์เรนเดอร์ในโฟลเดอร์ **`renderer/`** เท่านั้น (ไม่มีโฟลเดอร์ `engine/` ในชุดปัจจุบัน) ซึ่งได้รับการแก้ไขบั๊กปาก `thumbs_up`/`thinking`, บั๊กสระไทยบน Windows (`uharfbuzz`) และบั๊ก FFmpeg QC เรียบร้อยแล้ว

---

## 📁 โครงสร้างคลังโค้ด (Repository Structure)

```text
liplnwza-motion-kit/
├── README.md                         ← ภาพรวมคลังโค้ดและการติดตั้ง
├── START_HERE.md                     ← [อ่านไฟล์นี้เป็นอันดับแรก!]
├── SKILL.md                          ← สเปกทักษะเต็มรูปแบบสำหรับ AI Agents
├── AGENTS.md                         ← สเปกแบรนด์และกฎเหล็กสไตล์ Warodom Collage
├── renderer/                         ← เครื่องยนต์เรนเดอร์หลัก v0.2.1
│   ├── kit.py                        ← CLI หลัก (doctor, validate, digest, render, qc) — รวมตัวจัดสระภาษาไทยผ่าน uharfbuzz ไว้ในไฟล์นี้
│   ├── new_job.py                    ← สร้างโฟลเดอร์งานใหม่ที่ jobs/<slug>/
│   └── prepare_cues.py               ← (ทางเลือก) จับเวลาคำ/ปากจากบทที่รู้อยู่แล้ว ต้องมีโมเดล faster-whisper แบบ local เท่านั้น
│   # rig_motion.py อยู่ที่ assets/mascot/mouth_rig/ ไม่ได้อยู่ใน renderer/
├── assets/                           ← แอสเสตประจำเครื่องยนต์
│   ├── mascot/mouth_rig/             ← ระบบ Clean-Plate + Procedural Mouth Rig 6 ท่า
│   └── fonts/Prompt-Bold.ttf         ← ฟอนต์มาตรฐานบังคับสำหรับภาษาไทยและอังกฤษ
├── brand/                            ← คลังภาพมาสคอต LiplnwZa ต้นฉบับ
├── examples/                         ← งานตัวอย่างมาตรฐาน
│   └── benchmark15/                  ← ชุดทดสอบ Benchmark 15s (job.json, voice.wav, words.json, visemes.json)
└── tests/                            ← ชุดทดสอบระบบอัตโนมัติ (test_runtime.py ผ่าน 7/7 ข้อ)
```

---

## ⚡ ขั้นตอนมาตรฐานเมื่อได้รับคำสั่ง "สร้างวิดีโอใหม่"

1. **Pre-flight Check (ตรวจความพร้อมระบบ):**
   ```bash
   python renderer/kit.py doctor
   ```
   *(ต้องได้ `"render_ready": true`)*
2. **ทดสอบเรนเดอร์ตัวอย่าง Benchmark (15 วินาที):**
   ```bash
   python renderer/kit.py render examples/benchmark15/job.json --out examples/benchmark15/output-test
   ```
3. **สร้างโฟลเดอร์งานใหม่ใน `jobs/<slug>/`:**
   เตรียมไฟล์ 5 รายการ:
   - `job.json` (โครงสร้างฉาก ข้อความ และท่ามาสคอต `explain`, `point_right`, `thinking`, `magnify`, `point_left`, `thumbs_up`)
   - `voice.wav` หรือ `voice.mp3` (เสียงพากย์จริงของฟิลิป)
   - `words.json` (เวลาซับรายคำที่วัดจากคลื่นเสียงจริงระดับมิลลิวินาที)
   - `visemes.json` (ตารางขยับปาก 6 ท่า: `CLOSED`, `AA`, `EE`, `OH`, `OO`, `FV` โดยต้องใส่ `CLOSED` ที่ตัวสะกดแม่กม/กบ)
   - `approval.json` (ใส่ค่า `job_digest` ที่ได้จาก `python renderer/kit.py digest jobs/<slug>/job.json`)
4. **Validate & Render:**
   ```bash
   python renderer/kit.py validate jobs/<slug>/job.json
   python renderer/kit.py render jobs/<slug>/job.json --out jobs/<slug>/output-v01
   ```
5. **ตรวจ QC อัตโนมัติ:**
   ```bash
   python renderer/kit.py qc jobs/<slug>/output-v01/video.mp4
   ```
   - ตรวจ `contact_sheet.jpg` และค่า `technical_pass: true` ในรายงาน QC
