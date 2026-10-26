# 🎨 LiplnwZa Motion Kit (v0.2.1)

> **Short-Form Motion Graphics Renderer & AI Agent Toolkit**
> ออกแบบมาเพื่อสร้างวิดีโอแนวตั้ง (9:16, 1080×1920, 30fps) สไตล์ **Warodom Paper-Cut Collage** โดยอัตโนมัติ ผสานมาสคอต LiplnwZa, ระบบปากขยับ Procedural Lip-sync, การจัดสระภาษาไทยไร้รอยต่อ และระบบตรวจคุณภาพ (QC) อัตโนมัติ

[![Version](https://img.shields.io/badge/version-v0.2.1-blue.svg)](https://github.com/liplnwza548/liplnwza-motion-kit/releases/tag/v0.2.1)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## ✨ จุดเด่นสำคัญ (Key Highlights)

- 🎭 **Clean-Plate Procedural Mouth Rig:** ระบบประกอบภาพปากตาม viseme ที่เตรียมไว้ สำหรับมาสคอต 6 ท่าหลัก (`explain`, `point_right`, `thinking`, `magnify`, `point_left`, `thumbs_up`) โดยแทนที่ภาพปากภายในพื้นที่ซ่อมที่กำหนด
- 🇹🇭 **Thai Typography:** ใช้ Pillow RAQM เมื่อมี หรือใช้ `uharfbuzz` เป็นทางเลือก ต้องตรวจผลบนเครื่องเป้าหมายก่อนส่งงาน
- ⚡ **Repeatable Rendering:** สร้าง movement และ SFX จากข้อมูลกับ seed ที่กำหนด; ความเหมือนกันระดับไบต์ยังไม่ได้ยืนยันข้ามระบบหรือ toolchain
- 📊 **Automated Technical QC:** ตรวจสอบความดังเสียงมาตรฐาน (-18 ถึง -14 LUFS, True Peak ≤ -1.0 dBTP), เช็ก Decode Error, สร้าง Contact Sheet สรุปภาพรวม และ Contact Cards สำหรับส่งตรวจงาน
- 🤖 **Provider-Neutral Agent Instructions (`SKILL.md`):** มีคำแนะนำกลางสำหรับ agent; การเชื่อมต่อและสิทธิ์ใช้งานต้องตรวจในระบบ agent แต่ละตัว

---

## 📁 โครงสร้างโปรเจกต์ (Repository Structure)

```text
liplnwza-motion-kit/
├── README.md                         # คู่มือภาพรวมและวิธีใช้งาน
├── SKILL.md                          # สเปกทักษะแบบละเอียดสำหรับ AI Agents
├── START_HERE.md                     # เช็กลิสต์เริ่มต้นด่วนสำหรับมนุษย์และ AI
├── AGENTS.md                         # สเปกแบรนด์ สัดส่วนมาสคอต และจานสี Warodom
├── renderer/                         # เครื่องยนต์เรนเดอร์หลัก
│   ├── kit.py                        # Unified CLI (doctor, validate, digest, render, qc) — รวมระบบจัดสระไทย (uharfbuzz) ไว้ในไฟล์นี้
│   ├── new_job.py                    # สร้างโฟลเดอร์งานใหม่ที่ jobs/<slug>/
│   ├── prepare_cues.py               # (ทางเลือก) จับเวลาคำ/ปากจากบทที่รู้อยู่แล้ว ดูหมายเหตุด้านล่าง
│   └── setup.ps1 / setup.sh          # ติดตั้ง venv + dependencies
│   # หมายเหตุ: rig_motion.py อยู่ที่ assets/mascot/mouth_rig/ ไม่ได้อยู่ใน renderer/
├── assets/                           # แอสเสตมาตรฐานประจำเครื่องยนต์
│   ├── mascot/mouth_rig/             # รูปคลีนเพลต 6 ท่า + ปาก 6 ทรง + profiles.json
│   └── fonts/Prompt-Bold.ttf         # ฟอนต์มาตรฐานบังคับ Prompt Bold
├── brand/                            # คลังภาพมาสคอต LiplnwZa ต้นฉบับ
├── examples/                         # ตัวอย่างงานมาตรฐาน
│   └── benchmark15/                  # ตัวอย่าง 15 วินาที พร้อม voice.wav และ visemes
└── tests/                            # ชุดทดสอบระบบอัตโนมัติ
    ├── test_runtime.py               # runtime contract tests
    ├── test_caption_motion_policy.py  # caption and motion policy tests
    ├── test_theme_runtime.py          # theme and visual runtime tests
    ├── test_event_sfx.py              # event-driven SFX tests
    ├── test_audio_mix.py              # audio mixing tests
    └── test_qc_validation.py          # QC, validator, and manifest regressions
```

---

## 🚀 เริ่มต้นใช้งานด่วน (Quick Start)

### 1. ความต้องการของระบบ (Prerequisites)
- **Python 3.11+** (ตัวตรวจ `doctor` ใน `kit.py` ต้องการอย่างน้อย 3.11 — ถ้าเอกสารจุดอื่นบอก 3.10 ให้ยึด 3.11 เป็นเกณฑ์จริง)
- **FFmpeg & FFprobe** ติดตั้งอยู่ในระบบและเรียกผ่าน PATH ได้
- ไลบรารี Python: ติดตั้งผ่าน `renderer/setup.ps1` (Windows) หรือ `renderer/setup.sh` ซึ่งลงจาก `renderer/requirements.txt` ให้ (Pillow, numpy; การจัดสระไทยใช้ RAQM ใน Pillow หรือ uharfbuzz ถ้ามี)

### 2. ตรวจสอบความพร้อมของระบบ (Doctor Check)
```bash
python renderer/kit.py doctor
```
เมื่อพร้อมใช้งานจะแสดงผล:
```json
{
  "python": "3.11.x",
  "text_shaping_ready": true,
  "mouth_rig_pose_assets": 12,
  "render_ready": true
}
```

### 3. รันชุดทดสอบระบบ (Run Tests)
```bash
python -m unittest discover -s tests
```
ผลลัพธ์จะแสดงจำนวนผ่าน ล้มเหลว และ skipped ของ checkout นั้น

### 4. ทดสอบเรนเดอร์ Benchmark (15 วินาที)
```bash
python renderer/kit.py render examples/benchmark15/job.json --out output-benchmark
```
วิดีโอที่ได้จะถูกบันทึกไว้ที่ `output-benchmark/video.mp4` พร้อมภาพสรุป `contact_sheet.jpg`

---

## 🛠 คำสั่ง CLI ทั้งหมด (CLI Reference)

| คำสั่ง | ตัวอย่างการใช้งาน | คำอธิบาย |
| :--- | :--- | :--- |
| `doctor` | `python renderer/kit.py doctor` | ตรวจสอบความพร้อมของ Python, FFmpeg, ฟอนต์ และ Rig Assets |
| `validate` | `python renderer/kit.py validate <job.json>` | ตรวจสอบโครงสร้างไฟล์ JSON และความถูกต้องของ Asset ที่ใช้อ้างอิง |
| `digest` | `python renderer/kit.py digest <job.json>` | คำนวณ SHA-256 แฮชของ Job เพื่อใช้ล็อกการอนุมัติใน `approval.json` |
| `render` | `python renderer/kit.py render <job.json> --out <dir>` | เรนเดอร์วิดีโอตัวเต็มความละเอียด 1080×1920 30fps |
| `preview` | `python renderer/kit.py preview <job.json> --out <dir>` | สร้างภาพตัวอย่างแต่ละฉากและ contact sheet สำหรับตรวจข้อความ/องค์ประกอบ |
| `qc` | `python renderer/kit.py qc <video.mp4>` | ตรวจสอบคุณภาพเชิงเทคนิค ความดังเสียง และ Decode Errors |

---

## 🤖 วิธีติดตั้งทักษะให้กับ AI Agents (AI Skill Integration)

หากคุณใช้งาน AI Agents เช่น **BeAN Muse AI, ChatGPT (Custom GPTs / Project), Claude Projects, Gemini Spark, หรือ AGY**:
1. ให้ AI Agent อ่านไฟล์ [SKILL.md](SKILL.md) เพื่อทำความเข้าใจระเบียบการทำงาน 4 ขั้นตอน:
   - **Step 1: Ingest & Analyze** — รับไฟล์เสียงจริง `voice.mp3` ของฟิลิป + Topic Brief
   - **Step 2: Pre-production Beat Sheet** — ออกแบบฉากและท่ามาสคอตส่งให้ฟิลิปอนุมัติ
   - **Step 3: Assembly & Automation** — สร้าง `words.json`, `visemes.json`, และ `job.json`
   - **Step 4: Render & Delivery** — เรนเดอร์วิดีโอและตรวจ QC ผ่าน `renderer/kit.py qc`
2. อ้างอิงสเปกภาพและจานสี Warodom ได้จาก [AGENTS.md](AGENTS.md)

---

## 📝 หมายเหตุเรื่อง `prepare_cues.py` (การจับเวลาคำ/ปาก)

- เป็นเครื่องมือ**ทางเลือก** สำหรับสร้าง `words.json` / `visemes.json` จากบทที่รู้อยู่แล้ว (known-script alignment)
- ใช้ได้เฉพาะเมื่อมีโมเดล faster-whisper เป็น**ไฟล์ local ในเครื่องอยู่แล้ว** และต้องระบุ path ของโมเดลเองเท่านั้น — สคริปต์ไม่ดาวน์โหลดโมเดลให้ และต้องลงแพ็กเกจเสริมใน `renderer/optional-alignment-requirements.txt` แยกต่างหาก
- ผลลัพธ์**ไม่ใช่**การถอดเสียงและไม่ใช่การตรวจว่าเสียงพากย์พูดตรงบท — ต้องให้เจ้าของงานฟังเทียบกับเสียงจริงและอนุมัติก่อนนำไปเรนเดอร์เสมอ

---

## 📄 ใบอนุญาต (License)

พัฒนาและดูแลโดยทีมงาน **LiplnwZa**  
ลิขสิทธิ์โค้ดเปิดเผยภายใต้ [MIT License](LICENSE) (ยกเว้นภาพมาสคอตและเครื่องหมายการค้า LiplnwZa สงวนสิทธิ์เฉพาะงานของช่อง LiplnwZa)
