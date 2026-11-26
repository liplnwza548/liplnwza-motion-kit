---
name: liplnwza-motion
description: "LiplnwZa Motion Kit v3.6 Living Stage (backward-compatible with v3.4/v3.5): vertical 9:16 720x1280 @ 30fps/24fps Paper Stage (locked y=672 subtitles), 8 mascot blocking shots, 7 comic FX + sub-beat choreography, 16 poses + SVG mouths, custom_html + 15 widgets, Lemo TV/full_bleed slot, and 2-pass -14.5 LUFS audio."
---

# 🎬 LiplnwZa Motion Kit — Master Skill Specification (v3.4)

> **ไฟล์นี้คือแหล่งความจริงเดียว (single source of truth) ของมาตรฐานงานใหม่.**
> `skills/liplnwza-motion/SKILL.md` เป็นแค่ตัวชี้มาที่ไฟล์นี้ ห้ามตีความแยกกัน
> `START_HERE.md` คือคู่มือเริ่มต้นด่วน ส่วน `layouts/aot/SPEC.md` คือสเปกของ
> ตัวประกอบ AoT รุ่นเดิม (ดูหัวข้อสถานะเอนจินด้านล่าง) ถ้าเอกสารใดขัดกับ
> ไฟล์นี้สำหรับงานใหม่ ให้ยึดไฟล์นี้เป็นหลัก
>
> **เวอร์ชัน: v3.4 "Lean & Punchy" — ฟิลิปล็อก 2026-11-24**
> ที่มา: หน้า Notion "LiplnwZa Motion Kit v3.4 — Production Spec, Installed
> Skill & GitHub Sync Plan" (บันทึกผ่าน Gemini Task Web) + คำสั่งฟิลิป
> 2026-11-24 เนื้อหาที่ Gemini เขียนไว้ใน Notion ถือเป็นข้อเสนอจนกว่าฟิลิป
> จะยืนยันเอง — สเปกในไฟล์นี้คือส่วนที่ฟิลิปสั่งให้บันทึกไว้แล้ว
>
> ✅ **สถานะเอนจิน: IMPORTED 2026-11-24** — เอนจิน v3.4 นำเข้า repo นี้
> แล้วจาก export ของสกิล `liplnwza-motion` บน Gemini Task Web
> (คัดลอกแบบ byte-for-byte ตรวจรับตาม `V34-IMPORT-CHECKLIST.md`)
> เรนเดอร์ด้วย `renderer/render_liplnwza_v3.py` ได้เลย แต่ต้องผ่าน
> เกตเดียวในไฟล์นี้ก่อนเสมอ: ส่ง Beat Sheet ให้ฟิลิปอนุมัติก่อนสร้างงานจริง
> ห้ามเรนเดอร์ปลอม ห้ามสร้างแอสเสตปลอม

---

## 📌 กฎเหล็กของระบบ (Golden Rules)

1. **ห้ามแตะโฟลเดอร์ `_archive/` เด็ดขาด:** โฟลเดอร์นี้เป็นคลังเก็บของเก่า (v0.1) ที่มีบั๊กมุมปากมาสคอต (ถ้า checkout ใดไม่มีโฟลเดอร์นี้ กฎนี้ก็ไม่มีผลอะไร)
2. **งานใหม่ใช้มาตรฐาน v3.4 ในไฟล์นี้เท่านั้น:** ห้ามสร้างงานใหม่บน SOP เก่าที่สอนใช้ `renderer/kit.py` แบบกระดาษ (`torn_paper`) อีก เครื่องยนต์เก่าที่อยู่ใน repo นี้ (`renderer/kit.py` v0.2.1 และ `layouts/aot/compose.py`) เป็น **legacy แช่แข็ง** — ใช้ได้เฉพาะงานเดิมที่ล็อกไว้และชุดทดสอบเท่านั้น ห้ามแก้พฤติกรรมเครื่องยนต์เก่าในงานอัปเกรดเอกสารนี้
3. **ห้ามเผยแพร่รายละเอียดการโคลนเสียง:** ไฟล์เสียงอ้างอิง, voice ID, ชื่อโมเดลเสียง, ค่า stability/similarity หรือรายละเอียดการโคลนเสียงใดๆ **ห้ามอยู่ใน repo นี้หรือที่สาธารณะ** รายละเอียดงานเสียงของเจ้าของเก็บไว้นอก repo เท่านั้น เสียงโคลนใช้กับคลิปคอนเทนต์เท่านั้น — **คลิปขายสินค้าใช้เสียงอัดจริงของฟิลิปเท่านั้น ห้ามใช้เสียงโคลน** ข้อนี้อยู่เหนือกฎอื่นทั้งหมด
4. **ฟิลิปอนุมัติบทและเสียงก่อนเรนเดอร์เสมอ** ห้ามเผยแพร่โดยไม่ได้รับอนุมัติ ห้ามเขียนทับไฟล์สำเร็จรูป — งานใหม่ทุกครั้งต้องเป็นไฟล์ใหม่
5. **ข้อความบนจอมาจากบทที่อนุมัติเท่านั้น** ห้ามคิดคำใหม่ใส่เอง

---

## 🏗️ สถาปัตยกรรม v3.4 (2-Tier Architecture)

- **Tier 1 — เวทีหลัก:** Full-Canvas Paper Stage 9:16 สไตล์ Warodom Paper-Cut Collage หนึ่งเวทีเต็มจอ
- **Tier 2 — ตัวละคร + วิดเจ็ต + จอทีวี:** มาสคอต LiplnwZa เต็มตัว + 12 Animated Micro-Widgets + ช่องจอทีวี `media_clip_frame` สำหรับฉายคลิปสั้นจากสกิล Lemo-Opuscar โดยไม่ทำให้เอกลักษณ์ช่องแตก
- **เอนจินเรนเดอร์:** Offline Headless Chromium CDP (`JPEG q=92`, Lazy WebP Loading, เร็ว ~7.2 fps, ใช้ฟอนต์ระบบ `NotoSansThai-Bold.ttf` ไม่ต้องพกไฟล์ `.ttf`)
- **เอาต์พุต:** H.264, `-movflags +faststart`, แบ่งเรนเดอร์ `--chunk-frames 120`
- **ไฟล์เอนจิน (นำเข้าแล้ว 2026-11-24):** `renderer/render_liplnwza_v3.py`, `renderer/stage_template.html`, `renderer/widgets.js`, `renderer/audio_mixer.py`, `assets_v3/mascot/mouth_anchors.json` + แอสเสต WebP ใน `assets_v3/` (ดูรายการตรวจรับใน `V34-IMPORT-CHECKLIST.md`) — ปาก 6 ทรงเป็น SVG แบบ procedural ที่ `widgets.js` สร้างขึ้น ไม่ใช่ไฟล์ SVG แยก

---

## 📐 เลย์เอาต์ที่ล็อก (720×1280 @ 24fps)

| โซน | ตำแหน่ง | กฎ |
| --- | --- | --- |
| ริบบิ้นบน | `y=144` | ป้ายหัวข้อของเวที |
| เวที 12 วิดเจ็ต | `y=214..659` | วิดเจ็ตแอนิเมชัน + พื้นหลังของเวที กล้องและทรานซิชั่นทำงานเฉพาะโซนนี้ |
| ซับสีรายคำ | **`y=672` กึ่งกลางจอ** | พ้นแถบ UI TikTok 100% + Auto-Fit กันล้นขอบ (ดูหัวข้อซับไตเติล) |
| มาสคอตเต็มตัว | ล่างซ้าย ขนาด `500px` | **ยืนนิ่งนอก Camera Rig** — หายใจเบาๆ `±2.2px` เท่านั้น ไม่เด้งตามเสียง |

- **กล้อง 4 แบบ** (`push_in`, `pull_out`, `focus_tv`, `punch_in`) และ **ทรานซิชั่นกระดาษ 4 แบบ** (`paper_slide`, `page_peel`, `whip_zoom`, `ink_flash`) ทำงานเฉพาะเวที Widget + พื้นหลังเท่านั้น ห้ามขยับมาสคอตหรือซับ
- มาสคอตต้อง settle ก่อนจุดตัดเสมอ โมชันห้ามวิ่งชนจุดตัดโดยไม่มีจังหวะหยุด

---

## 🎭 มาสคอต + ปาก + พร็อพ/บอทสมทบ

- **มาสคอตเต็มตัว 16 ท่า** — Mouthless Clean Plate WebP รวม 220.8 KB: `wave`, `pointer`, `clipboard`, `confident`, `magnify`, `laptop_focus`, `laptop_smile`, `cheer`, `facepalm`, `thinking_chin`, `shocked`, `holding_card`, `thumbs_up_full`, `newspaper_hold`, `shrug`, `idea_finger`
- **ปากเวกเตอร์ SVG 6 ทรง** (`CLOSED`, `AA`, `EE`, `OH`, `OO`, `FV`) ไร้รอยซ้อน เปลี่ยนท่าปากต่อเนื่อง ไม่สลับสไปรต์แบบตัดทันที ตำแหน่งปากอ้างอิง `mouth_anchors.json`
- **ชุดพร็อพ & บอทสมทบ 12 ชิ้น** — WebP โปร่งใส รวม 88.4 KB ใช้ Lazy Asset Loading: `bot_curious`, `bot_cheer`, `bot_shock`, `badge_alert`, `badge_check`, `badge_question`, `pointer_stick`, `clipboard`, `magnifying_glass`, `laptop`, `newspaper`, `lightbulb`
- **มาสคอตมาจาก master lock + rig เท่านั้น ห้ามเจนมาสคอตใหม่ด้วย AI** ท่าเพิ่มต้องมาจากร่างเดิม

---

## 🖼️ ภาพประกอบ — ภาพโค้ดล้วน + Lemo TV Slot เท่านั้น

- **ภาพประกอบของงานใหม่ = ภาพโค้ดล้วน (HTML/CSS/SVG + Animated Micro-Widgets) เท่านั้น** ห้ามใช้ภาพ AI-generated เป็นภาพหลัก ห้ามใช้ภาพถ่ายเป็นภาพหลัก (กฎเดียวกับ `layouts/aot/SPEC.md` ฉบับอัปเดต)
- **Lemo TV Slot (`media_clip_frame`):** ช่องจอทีวีกรอบกระดาษสำหรับแปะคลิปสั้น **4–6 วินาที** จากสกิล Lemo-Opuscar **ทั้ง 25 แบบ** ใช้กล้อง `focus_tv` ตอนฉาย คลิปที่แปะต้องมีสิทธิ์ใช้ชัดและบันทึกที่มาไว้ใน job manifest
- ทุกสื่อที่ใช้ต้องมีที่มาใน `media/_ที่มา.txt` และลงทะเบียนใน `job.json` ให้ครบตาม schema — อ่าน [คู่มือแหล่งสื่อและสิทธิ์](assets/ASSET_SOURCES.md) ก่อนเลือกสื่อทุกครั้ง อย่าอนุมัติหรือเผยแพร่ job ที่ยังตรวจ license ของไฟล์จริงไม่ครบ

---

## 💬 ซับไตเติลสีรายคำ

- วาง**กึ่งกลางจอที่ `y=672`** พ้นแถบ UI TikTok 100% พร้อม **Auto-Fit กันล้นขอบ**
- แยกเป็นคำ/วลีสั้นก่อนเรนเดอร์เสมอ ห้ามเอาประโยคยาวทั้งก้อนขึ้นเป็นชิปเดียว
- เวลาของคำมาจาก pipeline จับเวลาเท่านั้น (MFA Studio Mode หรือ Express Mode) ห้ามเขียนเวลาด้วยมือ ห้ามกะเวลาจากความยาวตัวอักษร
- ฟอนต์เรนเดอร์ของ v3.4 คือฟอนต์ระบบ `NotoSansThai-Bold.ttf` (ดูหัวข้อสถาปัตยกรรม) ส่วนงาน legacy ยังใช้ Prompt-Bold ตามสเปกเดิมของมัน

---

## 👄 Lip-Sync 2 โหมด

- **Studio Mode:** อ่าน `visemes.json` จาก MFA (การจัดแนวเสียงกับบทที่อนุมัติแล้ว)
- **Express Mode:** สกัดท่าปาก 24fps จากคลื่นเสียง `vo_path` อัตโนมัติ ไม่ต้องมีไฟล์ visemes มาก่อน
- ทั้งสองโหมดขับปาก SVG 6 ทรงเดียวกัน — โหมดเป็นวิธีได้มาซึ่งท่าปาก ไม่ใช่คนละระบบปาก

---

## 🔊 เสียง & BGM (ลิขสิทธิ์ตัวเอง)

- **BGM 3 แนว สร้างอัตโนมัติใน `/tmp/liplnwza_v3_bgm/`:** `funk_brass` — **เพลงหลัก 118 BPM** (Cory Wong Funk + Brass Stabs), `warm_groove` (108 BPM), `mystery_pulse` (104 BPM)
- **Mid-Band Ducking (300Hz–4kHz)** ระหว่างเสียงพากย์กับ BGM + Foley ตามเหตุการณ์ภาพ
- **2-pass `-14.5 LUFS` + faststart** สำหรับงานใหม่ v3.4 (ค่า `-16 LUFS` ในสเปก/เกทเดิมใช้กับเครื่องยนต์ legacy เท่านั้น)
- **ไม่มีไฟล์เสียงจริง bundle ลง repo** และห้ามนำเสียงสังเคราะห์มาเสนอว่าเป็น SFX จริง — เสียงสังเคราะห์ใช้ทดสอบโค้ดใน `/tmp` ได้เท่านั้น

---

## ⚡ กระบวนการทำงาน 4 ขั้นตอน (SOP — v3.4)

### ขั้นที่ 1: รับ Input จากฟิลิป (Ingest & Analyze)
สิ่งที่ฟิลิปจะส่งมาให้:
1. **ไฟล์เสียงพากย์ที่ผ่านอนุมัติแล้ว** (`voice.mp3` หรือ `voice.wav`) — เสียงที่เจ้าของฟังอนุมัติแล้ว หรือไฟล์เสียงอัดจริงที่ฟิลิปส่งมาเอง
2. **หัวข้อ/เป้าหมายของคลิป** (Topic Brief)
3. **คลิปสำหรับช่องทีวี** (ถ้ามี — คลิปสั้น 4–6 วิจาก Lemo-Opuscar พร้อมที่มา/สิทธิ์)

### ขั้นที่ 2: วางแผนก่อนสร้าง (Pre-production Beat Sheet)
**ห้ามเรนเดอร์ทันที** ให้สร้างแผนฉากส่งให้ฟิลิปตรวจก่อน:
- แบ่งฉาก 5–6 ฉากย่อยตามจังหวะเว้นวรรคของเสียงพูด
- กำหนดวิดเจ็ต 12 ตัว กล้อง 4 แบบ ทรานซิชั่น 4 แบบ และช่องทีวี (ถ้ามี) ต่อฉาก
- เลือกท่ามาสคอต 16 ท่าให้ตรงกับอารมณ์ฉาก
- ส่ง Beat Sheet ให้ฟิลิปตรวจและรอคำสั่ง **"อนุมัติสร้าง"**

### ขั้นที่ 3: ประกอบไฟล์งาน (Assembly & Automation)
1. เตรียมชุดรับมอบเสียง: `voice.wav` + `words.json` (เวลาระดับคำที่ตรวจเทียบเสียงจริงแล้ว) + `visemes.json` (Studio Mode) — Express Mode สกัดท่าปากจากเสียงอัตโนมัติแทนได้
2. เขียน job spec ของงาน (ฉาก ข้อความ ท่า วิดเจ็ต กล้อง ทีวีสล็อต) ตาม schema ของเอนจิน v3.4 ใน `references/scene_spec_schema.md`
3. สร้างค่าอนุมัติ (job digest) ใส่ใน `approval.json` (`status: "approved"`) จากหลักฐานการอนุมัติของเจ้าของงานจริง ห้ามอนุมัติตัวเอง

### ขั้นที่ 4: สั่งเรนเดอร์และตรวจ QC (Render & Delivery)
1. เรนเดอร์ด้วยเอนจิน v3.4 (`renderer/render_liplnwza_v3.py`) ที่ 720×1280 @ 24fps แบบ `--chunk-frames 120` — เรนเดอร์แผ่น QA (`--qa-only`) ตรวจภาพก่อนเรนเดอร์เต็มเสมอ
2. ตรวจ QC ตามเกณฑ์ด้านล่างจากไฟล์ MP4 จริง ไม่ใช่จากแผน
3. ส่ง MP4, SRT, ซอร์สที่ส่งต่อได้, sources และรายงานสิ่งที่ตรวจจริง เก็บ SESSION.md ให้ AI ตัวถัดไปทำต่อได้

---

## 🎯 เกณฑ์การผ่าน QC ที่ต้องรายงานเจ้าของงาน (งานใหม่ v3.4)
- [ ] ขนาดภาพ: 720×1280 (9:16 แนวตั้ง), 24 fps, faststart
- [ ] Decode Errors: 0
- [ ] ความดังเสียง: 2-pass −14.5 LUFS (True Peak ≤ −1.0 dBTP) วัดจาก MP4 จริง
- [ ] ซับไตเติล: อยู่กึ่งกลาง y=672, Auto-Fit ไม่ล้นขอบ, เด้งคำต่อคำตรงเสียงพูด, ตัวอักษรไทยสระ/วรรณยุกต์ไม่ซ้อนทับ
- [ ] มาสคอต: ยืนนิ่งนอก Camera Rig มีแค่หายใจ ±2.2px ปาก SVG ขยับตามเสียงจริง ไร้รอยซ้อน
- [ ] กล้อง/ทรานซิชั่น: ทำงานเฉพาะเวที Widget + พื้นหลัง ไม่ขยับมาสคอตหรือซับ
- [ ] ภาพประกอบ: โค้ดล้วน + ช่องทีวีตามสิทธิ์เท่านั้น ไม่มีภาพ AI-generated เป็นภาพหลัก

---

## 🔒 ด่านตรวจสายพาน P0/P1 (ใช้กับทุกเอนจิน — เครื่องมือที่ระบุคือชุดปัจจุบันใน repo)

เครื่องมือเหล่านี้เป็นด่านตรวจก่อน/หลังประกอบ แยกจาก QC ท้ายคลิป — ห้ามใช้แทนกัน และห้ามข้ามด่านใดด่านหนึ่งโดยไม่บอกเจ้าของงาน เอนจิน v3.4 ที่นำเข้าต้องบังคับใช้หลักการเดียวกันนี้:

- **ก่อนประกอบ — `renderer/preflight.py`**: ตรวจ hash เสียงที่ล็อกไว้, คำต่อกันเท่าบทเป๊ะ, provenance ตรง, บัญชีภาพครบ (ชื่อตรง manifest เท่านั้น ห้ามเดาชื่อไฟล์แบบ glob), ขอบบีตตรง onset ภายใน 0.02 วิ, จำนวนเฟรมจากความยาวเสียงจริง ถ้าผิดข้อใดข้อหนึ่งให้หยุดทันที ห้ามประกอบต่อ
- **จับเวลาด้วย MFA — `renderer/mfa_to_cues.py`**: รับไฟล์ MFA JSON + บท + merge-map ของงานนั้น แล้วออกชิปพร้อม provenance sidecar ต่อตัวอักษรต้องเท่าบทเป๊ะ ไม่งั้น fail ดังๆ ไม่เดา ข้อมูลคำ/merge-map เป็นของงานนั้นๆ ห้าม hardcode ลงเครื่องมือกลาง
- **ปากซ้ำเวลา — `renderer/dedup_visemes.py`**: รวม viseme ให้เหลือตัวเดียวต่อ timestamp (ตัวสุดท้ายชนะอย่างชัดเจน) ก่อนส่งให้ rig — ห้ามให้ rig เลือกตามลำดับไฟล์แบบเงียบๆ
- **QC ภาพตามเฟรม — `tests/qc.py`**: ดึงเฟรมตามเลขเฟรมเท่านั้น จุดตัด = `ceil(boundary × fps)` ตรวจ 3 เฟรมต่อจุดตัด (ก่อน/ที่/หลังจุดตัด)
- **หลังเรนเดอร์ — `renderer/post_render_gate.py`**: loudnorm 2-pass บนไฟล์ mp4 แล้ว gate จากไฟล์ mp4 จริง (ไม่ใช่จาก wav): ความยาว ±0.05 วิ, จำนวนเฟรมครบ, ค่า LUFS/TP ตามเกณฑ์ของเอนจินที่ใช้ กับดักที่วัดมาแล้ว: โหมด linear ไม่จำกัดพีคจริง จึงต้องตั้งเป้า TP −2.0 ในฟิลเตอร์ + บังคับ AAC 192k ไม่งั้นพีคทะลุได้
- **บัญชีภาพงาน — `renderer/verify_manifest.py --job-manifest`**: ตรวจบัญชีภาพของงาน (ไฟล์ครบ, สถานะ accepted, sha ตรง, ขนาดขั้นต่ำตามสเปกของเอนจินที่ใช้, ไฟล์ที่ถูกตีกลับต้องไม่อยู่ในโฟลเดอร์ภาพที่ใช้ประกอบ)
- **วินัยสคริปต์เสียง**: สคริปต์รันเสียงทุกตัวต้องขึ้นต้นด้วย `set -euo pipefail`, ออกด้วย exit code ของตัวเจนเสียงทันทีถ้าพัง (ห้ามให้คำสั่งท้ายไฟล์กลบโค้ดพังจนรายงานว่าสำเร็จ), copy takes ไปโฟลเดอร์ถาวรทันทีที่เจนจบแล้วตรวจจำนวนไฟล์ครบก่อนจบสคริปต์
- **กลไก guard ของ offset**: เครื่องมือกลางห้าม hardcode ค่า offset ใดๆ เป็น default — แต่ละงานล็อกค่าของตัวเองไว้ใน manifest ของงาน และ preflight ตรวจว่าค่าไม่ขยับโดยไม่มี sync test ที่เจ้าของงานตัดสิน การเปลี่ยน offset เป็นเรื่อง P2 ต้องให้เจ้าของงานตัดสินแยกต่างหาก
- **บทเรียนจากสายประกอบที่แก้แล้ว (ห้ามทำซ้ำ)**: จุดตัดต้องเป็นเลขเฟรมจำนวนเต็ม, เฟรมแรกต้องเป็นบีตแรกเสมอ, หน้าต่างแถวซับห้ามซ้อนกัน, จำนวนเฟรมต้องคำนวณจากเสียงจริง, path ต้องสัมพัทธ์จากไฟล์สคริปต์, โซนชิปกับมาสคอตต้องห่างกันอย่างน้อย 20px

---

## 🛠️ โครงสร้างไฟล์ใน repo (Repository Architecture)

```text
liplnwza-motion-kit/
├── SKILL.md                          ← [สเปกหลักฉบับนี้ — แหล่งความจริงเดียวของ v3.4]
├── skills/liplnwza-motion/SKILL.md   ← ตัวชี้มาที่ SKILL.md หลัก + กติกาควบคุมงาน (ห้ามตีความแยก)
├── START_HERE.md                     ← คู่มือเริ่มต้นด่วน (อ่านไฟล์นี้ก่อนเมื่อเริ่มงานใหม่)
├── V34-IMPORT-CHECKLIST.md           ← รายการตรวจรับการนำเข้าเอนจิน/แอสเสต v3.4
├── README.md                         ← ภาพรวมคลังโค้ด, Quickstart, และคู่มือติดตั้ง
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
├── layouts/aot/                      ← [LEGACY แช่แข็ง] ตัวประกอบ AoT (compose.py, 1080x1920 @ 30fps) + SPEC.md
├── assets/                           ← แอสเสตมาตรฐาน (มาสคอต mouth_rig เดิม, ฟอนต์ Prompt-Bold)
├── brand/                            ← คลังภาพมาสคอต LiplnwZa ต้นฉบับ
├── examples/                         ← งานตัวอย่างและเกณฑ์มาตรฐาน (benchmark15 = เทสต์เทคนิคเครื่องเก่าเท่านั้น)
├── references/                       ← JOB_FORMAT / AUDIO_AND_TIMING / QUALITY / STYLE / WORKFLOW
└── tests/                            ← ชุดทดสอบระบบอัตโนมัติ (รันด้วย python -m unittest discover -s tests)
```

---

## 📜 ประวัติเวอร์ชันย่อ

- **v0.2.1** — เครื่องยนต์กระดาษ `renderer/kit.py` + Clean Plate rig 6 ท่า (สเปกเดิมอยู่ใน `AGENTS.md`)
- **AoT layout (ล็อก 2026-11-02)** — เลย์เอาต์หลักของงานเดิม: บนกรอบภาพ / กลางซับชิป / ล่างมาสคอต 1080×1920 @ 30fps ตัวประกอบ `layouts/aot/compose.py`
- **v3.4 (ล็อก 2026-11-24; เอนจินนำเข้าแล้ว 2026-11-24)** — มาตรฐานงานใหม่ในไฟล์นี้: Full-Canvas Paper Stage 720×1280 @ 24fps + CDP + 12 วิดเจ็ต + ช่องทีวี Lemo — รายละเอียดการเปลี่ยนแต่ละครั้งดูใน `CHANGELOG.md`
---

## 🚀 อัปเกรด v3.5 Modular & v3.6 "Living Stage" (ต่อยอดจากฐาน v3.4 — Backward-Compatible 100%)

> **ฟิลิปล็อกทิศทาง 2026-11-26:** คงเอกลักษณ์ **พื้นกระดาษตาราง v3.4 + ริบบิ้น + ดาว + ซับสีรายคำกลางจอ `y=672` (พ้น UI TikTok)** ไว้ครบ 100% แต่ปลดล็อกให้เวทีมีชีวิตไม่ซ้ำเทมเพลตเดิม (ทุกสเปก v3.4 เดิมยังรันได้เหมือนเดิมทุกพิกเซล)

### 1. v3.5 Modular Knobs (opt-in)
- `theme` (ระดับ spec หรือราย beat): `show_stars`, `show_ribbon`, `ribbon_style` (`glass_tag` ค่าเริ่มต้นใหม่ | `pill` | `torn`), `bg_color`, `bg_css`, `css`, `chips_y`, `mascot_mode` (`standard` | `mini_left` | `mini_right` | `hidden`)
- `layout` (ราย beat): `standard` (v3.4 เดิม) | `split` | `full_stage`
- `widget.type: "custom_html"`: สร้างฉากเฉพาะตอนด้วย HTML/CSS/SVG ได้อิสระ (รองรับ `{{AGE}}`, `{{PROGRESS}}`, `{{PCT}}`)
- `media_clip_frame`: รองรับ `fit: "full_bleed"` (720×1280 เต็มจอสำหรับคลิป Lemo-Opuscar 100 สไตล์)

### 2. v3.6 Living Stage (แนะนำสำหรับงานใหม่)
- **30fps + สีมาตรฐานสตรีมมิง:** ส่ง `--fps 30` หรือใส่ `"fps": 30` ใน `scene_spec.json` — เรนเดอร์ออก `yuv420p` (`color_range=tv`, `bt709`) และซิงก์ `visemes.json` + Lemo clips ที่ 30fps อัตโนมัติ
- **8 มุมกล้องมาสคอต (`beat.mascot_shot` — ทุกมุมเว้นพ้นซับ `y=672`):** `left_standard`, `right_standard`, `center_stage`, `closeup_left`, `closeup_right`, `closeup_center`, `peek_left`, `peek_right` + ท่าเปิดตัว `mascot_enter` (`pop` | `slide_left` | `slide_right` | `rise`) และสลับฝั่งคู่หู `sidekick_pos` อัตโนมัติไม่ให้ชนกัน
- **7 Comic FX (`beat.comic_fx`) + ฟองคำพูด (`mascot_bubble` / `sidekick_bubble`):** `sunburst`, `speed_lines`, `stamp_slam`, `comic_burst`, `magnifying_lens`, `arrow_callout`, `speech_bubble` พร้อมเสียง Foley อัตโนมัติใน `audio_mixer.py` (`synth_stamp_thud`, `synth_boing`, `synth_cash_ding`) และ `beat.sfx_cues`
- **Sub-Beat Choreography (`data-at` / `data-anim` ใน `custom_html`):** รองรับ `pop`, `slam`, `slide-up/left/right`, `count`, `bar`, `strike`, `type`, `fade` (deterministic 100% ทุกเฟรม)
- **3 วิดเจ็ตคอมมิกใหม่ใน `WIDGET_MAP`:** `evidence_card`, `live_calc_receipt`, `bar_compare`

### 3. กฎป้องกันบั๊กถาวร (Regression Guards)
1. **ห้ามใช้ `mascot_flip: true` กับมาสคอตที่เสื้อมีตัวหนังสือ** (เช่นคำว่า `LipinwZa` บนฮู้ด จะกลับด้านอ่านไม่ออก)
2. **ห้ามซ้ำ `mascot_shot` ติดกันเกิน 2 บีต** และทุกบีตที่ยาวเกิน 2.5 วิ ควรมีจังหวะภาพย่อย (`data-at` หรือ `comic_fx`) อย่างน้อย 2 จุด
3. **เอฟเฟกต์หมุนเต็มจอ (`sunburst` ฯลฯ — `PM-v36-sunburst-clip`):** ต้องใช้ `<svg>` สี่เหลี่ยมจัตุรัสศูนย์กลาง `(0,0)` ขนาดใหญ่กว่า `2 × (max_corner_dist + camera_margin)` (`3200×3200`, `r=1600`) และให้ `#bg-fx-layer` เป็นตัวคลิปหลังหมุนเท่านั้น (`speed_lines` ต้อง `rOut >= 1400`)
4. **พร็อพสติกเกอร์ (`assets_v3/props/*.webp`):** ทุกไฟล์ต้องมีขอบโปร่งใสครบทั้ง 4 ด้าน (`edge_touch == 0`, ตรวจด้วย `tests/test_v36_living_stage.py`)
5. **ความปลอดภัยโค้ด/คลังสาธารณะ:** ห้ามใส่ API keys หรือรายละเอียดโคลนเสียง (voice ID / model / stability / reference audio) ลงใน repo เด็ดขาด

- **v3.5 Modular & v3.6 Living Stage (2026-11-26)** — เพิ่ม `theme`/`layout`/`custom_html`/`full_bleed` (v3.5), 8 มุมมาสคอต + 7 Comic FX + Sub-Beat + 3 วิดเจ็ตใหม่ + `30fps` + `yuv420p tv` + แก้ `sunburst`/`speed_lines` ครอบเต็มจอ (`PM-v36-sunburst-clip`) + ซ่อมขอบบอท 3 ตัว (`edge_touch == 0`) + ปรับพาดหัว `Glass Floating Tag` + Clean Cutout มาสคอต 16 ท่าไร้ขอบขาว & จูน `mouth_anchors.json` — เทสต์ผ่าน 22/22 ข้อ
