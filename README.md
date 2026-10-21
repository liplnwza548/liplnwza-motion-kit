# 🎨 LiplnwZa Motion Kit (v0.2.1)

> **Autonomous Short-Form Motion Graphics Engine & AI Agent Skill**  
> ออกแบบมาเพื่อสร้างวิดีโอแนวตั้ง (9:16, 1080×1920, 30fps) สไตล์ **Warodom Paper-Cut Collage** โดยอัตโนมัติ ผสานมาสคอต LiplnwZa, ระบบปากขยับ Procedural Lip-sync, การจัดสระภาษาไทยไร้รอยต่อ และระบบตรวจคุณภาพ (QC) อัตโนมัติ

[![Version](https://img.shields.io/badge/version-v0.2.1-blue.svg)](https://github.com/liplnwza548/liplnwza-motion-kit/releases/tag/v0.2.1)
[![Tests](https://img.shields.io/badge/tests-7%2F7%20passing-brightgreen.svg)](tests/test_runtime.py)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## ✨ จุดเด่นสำคัญ (Key Highlights)

- 🎭 **Clean-Plate Procedural Mouth Rig:** ระบบมาสคอต 6 ท่าหลัก (`explain`, `point_right`, `thinking`, `magnify`, `point_left`, `thumbs_up`) ผสานระบบ Clean-Plate ลบปากเก่าเนียนสนิท ไร้รอยแผลที่มุมแก้ม พร้อมสเกลปากที่รองรับการอ้ากว้างอย่างเป็นธรรมชาติ
- 🇹🇭 **HarfBuzz Thai Typography:** ระบบจัดสระและวรรณยุกต์ภาษาไทยขั้นสูง รองรับ OpenType `GSUB`/`GPOS` อัตโนมัติผ่าน `uharfbuzz` หมดปัญหาสระลอยหรือสระซ้อนทับกันบนระบบปฏิบัติการ Windows, macOS และ Linux
- ⚡ **100% Deterministic Repeatability:** เรนเดอร์ซ้ำได้ผลลัพธ์ระดับบิตต่อบิต (Byte-for-byte SHA-256 match)
- 📊 **Automated Technical QC:** ตรวจสอบความดังเสียงมาตรฐาน (-18 ถึง -14 LUFS, True Peak ≤ -1.0 dBTP), เช็ก Decode Error, สร้าง Contact Sheet สรุปภาพรวม และ Contact Cards สำหรับส่งตรวจงาน
- 🤖 **Universal AI Skill Spec (`SKILL.md`):** พร้อมใช้งานร่วมกับ AI Agents ทุกตัว เช่น **BeAN Muse AI, ChatGPT, Claude, Google Gemini Spark, Antigravity (AGY)**

---

## 📁 โครงสร้างโปรเจกต์ (Repository Structure)

```text
liplnwza-motion-kit/
├── README.md                         # คู่มือภาพรวมและวิธีใช้งาน
├── SKILL.md                          # สเปกทักษะแบบละเอียดสำหรับ AI Agents
├── START_HERE.md                     # เช็กลิสต์เริ่มต้นด่วนสำหรับมนุษย์และ AI
├── AGENTS.md                         # สเปกแบรนด์ สัดส่วนมาสคอต และจานสี Warodom
├── renderer/                         # เครื่องยนต์เรนเดอร์หลัก
│   ├── kit.py                        # Unified CLI (doctor, validate, digest, render, qc)
│   ├── rig_motion.py                 # ระบบประกอบปาก Clean Plate และ Motion
│   ├── text_layout.py                # ระบบจัดวางฟอนต์ไทยและป้ายข้อความ
│   └── ...
├── assets/                           # แอสเสตมาตรฐานประจำเครื่องยนต์
│   ├── mascot/mouth_rig/             # รูปคลีนเพลต 6 ท่า + ปาก 6 ทรง + profiles.json
│   └── fonts/Prompt-Bold.ttf         # ฟอนต์มาตรฐานบังคับ Prompt Bold
├── brand/                            # คลังภาพมาสคอต LiplnwZa ต้นฉบับ
├── examples/                         # ตัวอย่างงานมาตรฐาน
│   └── benchmark15/                  # ตัวอย่าง 15 วินาที พร้อม voice.wav และ visemes
└── tests/                            # ชุดทดสอบระบบอัตโนมัติ
    └── test_runtime.py               # รัน 7 การทดสอบครอบคลุมทุกฟังก์ชัน
```

---

## 🚀 เริ่มต้นใช้งานด่วน (Quick Start)

### 1. ความต้องการของระบบ (Prerequisites)
- **Python 3.10+**
- **FFmpeg & FFprobe** ติดตั้งอยู่ในระบบและเรียกผ่าน PATH ได้
- ไลบรารี Python:
  ```bash
  pip install Pillow uharfbuzz
  ```

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
python -m unittest tests/test_runtime.py
```
*(ผลลัพธ์ต้องขึ้น `OK` ผ่านครบ 7/7 ข้อ)*

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
| `preview` | `python renderer/kit.py render <job.json> --preview` | เรนเดอร์พรีวิวรวดเร็ว 540×960 |
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

## 📄 ใบอนุญาต (License)

พัฒนาและดูแลโดยทีมงาน **LiplnwZa**  
ลิขสิทธิ์โค้ดเปิดเผยภายใต้ [MIT License](LICENSE) (ยกเว้นภาพมาสคอตและเครื่องหมายการค้า LiplnwZa สงวนสิทธิ์เฉพาะงานของช่อง LiplnwZa)
