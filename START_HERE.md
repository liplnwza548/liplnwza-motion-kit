# 🚀 START_HERE.md — คู่มือศูนย์กลางสำหรับ AI Agent ทุกตัว (BeAN Muse AI / ChatGPT / AGY)

> **อ่าน `SKILL.md` ที่ราก repo ก่อนเสมอ — นั่นคือสเปกหลักฉบับเดียว (v3.4)**
> มาตรฐานงานใหม่คือ **v3.4 "Lean & Punchy" (ฟิลิปล็อก 2026-11-24)**:
> Full-Canvas Paper Stage 9:16 `720x1280 @ 24fps` + Headless Chromium CDP,
> มาสคอตเต็มตัว 16 ท่า + ปาก SVG 6 ทรง, 12 Animated Micro-Widgets,
> ช่องทีวี `media_clip_frame` (คลิปสั้น 4–6 วิจาก Lemo-Opuscar),
> ซับสีรายคำกึ่งกลางจอ `y=672` + Auto-Fit, Lip-Sync 2 โหมด (Studio/MFA, Express/24fps),
> BGM ลิขสิทธิ์ตัวเอง 3 แนว + 2-pass `-14.5 LUFS`
>
> ✅ **สถานะเอนจิน: IMPORTED 2026-11-24** — เอนจิน v3.4 อยู่ใน repo นี้แล้ว
> (`renderer/render_liplnwza_v3.py` + แอสเสตใน `assets_v3/`)
> ตรวจรับตาม `V34-IMPORT-CHECKLIST.md` แล้ว เรนเดอร์แผ่น QA (`--qa-only`)
> ตรวจภาพก่อนเรนเดอร์เต็มเสมอ
> คำสั่ง `renderer/kit.py` ด้านล่างเป็นของเครื่องยนต์เก่า (legacy แช่แข็ง)
> ใช้ตรวจงานเดิม/เทสต์เท่านั้น ห้ามใช้เป็นเส้นทางหลักของงานใหม่
>
> **กฎเหล็ก:** ห้ามเผยแพร่รายละเอียดการโคลนเสียง (voice ID, ชื่อโมเดลเสียง,
> ค่า stability/similarity, ไฟล์เสียงอ้างอิง) ใน repo นี้หรือที่สาธารณะเด็ดขาด
> ฟิลิปอนุมัติบทและเสียงก่อนเรนเดอร์เสมอ ห้ามเผยแพร่โดยไม่ได้รับอนุมัติ

---

## 📁 โครงสร้างคลังโค้ด (Repository Structure)

```text
liplnwza-motion-kit/
├── README.md                         ← ภาพรวมคลังโค้ดและการติดตั้ง
├── START_HERE.md                     ← [อ่านไฟล์นี้เป็นอันดับแรก!]
├── SKILL.md                          ← สเปกหลัก v3.4 ฉบับเดียวสำหรับ AI Agents
├── V34-IMPORT-CHECKLIST.md           ← รายการตรวจรับการนำเข้าเอนจิน/แอสเสต v3.4
├── AGENTS.md                         ← สเปกยุคแรก (legacy) สำหรับสไตล์กระดาษ — อ่านหมายเหตุหัวไฟล์ก่อนใช้
├── renderer/                         ← เครื่องยนต์ใน repo
│   ├── v34_spec.py                   ← ค่าคงที่สเปก v3.4 ที่ล็อกไว้ (อ่านอย่างเดียว ไม่ใช่เอนจินเรนเดอร์)
│   ├── render_liplnwza_v3.py         ← [v3.4] เอนจินเรนเดอร์ CDP หลัก
│   ├── audio_mixer.py                ← [v3.4] มิกซ์เสียง + BGM + Foley + loudnorm
│   ├── stage_template.html           ← [v3.4] เทมเพลต Full-Canvas Paper Stage
│   ├── widgets.js                    ← [v3.4] 12 วิดเจ็ต + ปาก SVG แบบ procedural
│   ├── kit.py                        ← [LEGACY แช่แข็ง] CLI เครื่องยนต์กระดาษ v0.2.1
│   ├── new_job.py / prepare_cues.py / preflight.py / mfa_to_cues.py / ...
│   │                               ← [LEGACY] เครื่องมือด่านตรวจ/ประกอบเดิม — ใช้กับงานเดิมเท่านั้น
│   └── verify_manifest.py            ← ตรวจ manifest-sha256.json ของ repo + บัญชีภาพของงาน
├── assets_v3/                        ← [v3.4] มาสคอต 16 ท่า + พร็อพ 12 ชิ้น (WebP) + mouth_anchors.json
├── references/                       ← JOB_FORMAT / AUDIO_AND_TIMING / QUALITY / STYLE / WORKFLOW + scene_spec_schema.md (v3.4)
├── layouts/aot/                      ← [LEGACY แช่แข็ง] ตัวประกอบ AoT (compose.py, 1080x1920 @ 30fps) + SPEC.md
├── skills/liplnwza-motion/           ← ตัวชี้สเปกหลัก (SKILL.md) + กติกาควบคุมงาน + runtime/locate
├── assets/                           ← แอสเสตประจำเครื่องยนต์เดิม (mouth_rig, ฟอนต์ Prompt-Bold)
├── brand/                            ← คลังภาพมาสคอต LiplnwZa ต้นฉบับ
├── examples/                         ← งานตัวอย่างมาตรฐาน (benchmark15 = เทสต์เทคนิคเครื่องเก่าเท่านั้น)
└── tests/                            ← ชุดทดสอบระบบอัตโนมัติ (python -m unittest discover -s tests)
```

---

## ⚡ ขั้นตอนมาตรฐานเมื่อได้รับคำสั่ง "สร้างวิดีโอใหม่" (v3.4)

### สัญญาชุดรับมอบเสียง

ชุดรับมอบเสียงที่ต้องส่งให้ Motion Kit มี 3 รายการ:

1. `inputs/voice.wav` — เสียงพากย์สำเร็จรูปที่ประกอบทุกท่อนเสร็จแล้ว
2. `words.json` — ข้อมูลเวลาเริ่ม/จบระดับคำที่ตรวจเทียบกับเสียงจริงแล้ว
3. `visemes.json` — ข้อมูลเวลารูปปากสำหรับเสียงเดียวกัน (Studio Mode; Express Mode สกัดท่าปาก 24fps จากเสียงอัตโนมัติแทนได้)

Motion Kit ไม่สร้างเสียงพากย์และไม่ถอดเสียงให้อัตโนมัติในขั้นรับมอบนี้ ผู้ส่งมอบต้องประกอบเสียงให้เสร็จก่อน แล้วจึงทำ/ส่งข้อมูลเวลาและรูปปากที่สอดคล้องกับ `inputs/voice.wav` เครื่องมือประกอบมาตรฐานของสายเดิมคือ [`renderer/assemble_voice.py`](renderer/assemble_voice.py); เครื่องมือนี้ประกอบ WAV ที่มีอยู่และไม่สร้างเสียงหรือถอดคำพูด ส่วน `prepare_cues.py` เป็นตัวช่วย known-script alignment แบบเลือกใช้ ไม่ใช่ตัวถอดเสียง

### ลำดับงาน

1. **อ่านสเปกหลัก:** `SKILL.md` (v3.4) → `layouts/aot/SPEC.md` (กฎภาพประกอบ/ชิป — ส่วนที่ขัดกับ v3.4 ให้ยึด v3.4 สำหรับงานใหม่)
2. **ตรวจสถานะเอนจิน:** ไฟล์เอนจิน v3.4 ต้องครบ (`renderer/render_liplnwza_v3.py`, `assets_v3/mascot/` 16 ท่า, `assets_v3/props/` 12 ชิ้น) ถ้าขาดให้รายงานให้ฟิลิปทราบ ห้ามเรนเดอร์ปลอม
3. **Pre-production Beat Sheet:** แบ่งฉาก 5–6 ฉากตามจังหวะเสียง กำหนดวิดเจ็ต กล้อง ทรานซิชั่น ช่องทีวี และท่ามาสคอต 16 ท่า ส่งให้ฟิลิปตรวจและรอคำสั่ง **"อนุมัติสร้าง"**
4. **ประกอบไฟล์งาน:** เตรียมชุดรับมอบเสียง 3 รายการ + job spec ตาม schema ของเอนจิน v3.4 + `approval.json` (job digest จากหลักฐานการอนุมัติของเจ้าของงานจริง ห้ามอนุมัติตัวเอง)
5. **เรนเดอร์และตรวจ QC (เมื่อเอนจินพร้อม):** เรนเดอร์ 720×1280 @ 24fps แบบ `--chunk-frames 120` ตรวจ QC จากไฟล์ MP4 จริงตามเกณฑ์ v3.4 ใน `SKILL.md` (ซับกลางจอ y=672 + Auto-Fit, มาสคอตนิ่งนอก Camera Rig, 2-pass −14.5 LUFS, faststart)

### ตรวจเครื่องยนต์เก่า (legacy เท่านั้น — ไม่ใช่เส้นทางงานใหม่)

```bash
python renderer/kit.py doctor
```
*(ต้องได้ `"render_ready": true` — พิสูจน์เฉพาะเครื่องยนต์เก่า `kit.py` เท่านั้น)*

```bash
python -m unittest discover -s tests
python renderer/verify_manifest.py
```
*(ชุดทดสอบ + ตรวจ manifest ของ repo ต้องผ่านก่อนส่งงานทุกครั้ง)*
