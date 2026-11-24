---
name: liplnwza-motion
description: สร้างวิดีโอโมชั่นแนวตั้ง LiplnwZa ตามมาตรฐาน v3.4 (Full-Canvas Paper Stage 720x1280 @ 24fps, มาสคอตเต็มตัว 16 ท่า, ซับสีรายคำกลางจอ, ช่องทีวี Lemo) โดยตรวจต้นฉบับ เสนอข้อเสนอให้ Philip อนุมัติ ใช้เอนจินใน Motion Kit แล้วเรนเดอร์ ตรวจคุณภาพ และส่งไฟล์ ใช้เมื่อขอสร้างหรือปรับคลิปโมชั่น ซับสีรายคำ หรือมาสคอตพิธีกรของ Philip
---

# LiplnwZa Motion (v3.4)

> **ไฟล์นี้เป็นตัวชี้เท่านั้น — ไม่ใช่สเปกแยกอีกฉบับ**
> สเปกหลักฉบับเดียวอยู่ที่ **`SKILL.md` ที่ราก repo** (`../../SKILL.md`)
> อ่านไฟล์นั้นก่อนทุกครั้ง ถ้าข้อความใดในไฟล์นี้ขัดกับสเปกหลัก ให้ยึดสเปกหลัก
> มาตรฐานงานใหม่คือ **v3.4 "Lean & Punchy" (ฟิลิปล็อก 2026-11-24)**:
> Full-Canvas Paper Stage 9:16 `720x1280 @ 24fps` + Headless Chromium CDP,
> มาสคอตเต็มตัว 16 ท่า + ปาก SVG 6 ทรง, 12 Animated Micro-Widgets,
> ช่องทีวี `media_clip_frame` สำหรับคลิปสั้น 4–6 วิจาก Lemo-Opuscar,
> ซับสีรายคำกึ่งกลางจอ `y=672` + Auto-Fit, Lip-Sync 2 โหมด
> (Studio/MFA และ Express/24fps), BGM ลิขสิทธิ์ตัวเอง 3 แนว + 2-pass `-14.5 LUFS`
>
> ⚠️ **สถานะเอนจิน: IMPORT PENDING** — สคริปต์/แอสเสต v3.4
> (`render_liplnwza_v3.py`, `stage_template.html`, `widgets.js`,
> `audio_mixer.py`, `mouth_anchors.json`, WebP 16 ท่า + 12 พร็อพ)
> ติดตั้งอยู่บน Gemini Task Web เท่านั้น ยังไม่มีใน repo นี้
> ถ้าไฟล์เอนจิน v3.4 ไม่อยู่ใน kit root ให้รายงานว่าเป็น planning-only
> สำหรับงาน v3.4 อย่าอ้างว่าเรนเดอร์ผ่าน เครื่องยนต์เก่า `renderer/kit.py`
> ใช้ได้เฉพาะงานเดิมที่ฟิลิประบุชื่อไว้เท่านั้น ห้ามสร้างงานใหม่บน SOP กระดาษเก่า
> รายการนำเข้าดูที่ `V34-IMPORT-CHECKLIST.md` ที่ราก repo

1. หา kit root แบบจำกัด: ใช้ LIP_MOTION_ROOT หากกำหนด หรือ kit ใน workspace ที่ผู้ใช้แนบ ให้มี START_HERE.md และ SKILL.md ที่ราก ถ้าไม่พบ ใช้โฟลเดอร์ที่เจ้าของระบุ https://drive.google.com/drive/folders/1sbnVgJ-w9AfzKlm35wJQXO-vhJPSCRK5 เพื่อดาวน์โหลดชุด หรือขอให้แนบ ZIP อย่าค้น private filesystem ทั้งเครื่อง สำหรับ installed skill ให้เปิด references/runtime.md เมื่อไม่แน่ใจการหา runtime และใช้ scripts/locate_kit.py ตรวจเฉพาะตำแหน่งที่ระบุ
2. อ่าน SKILL.md ที่ราก repo (สเปกหลัก v3.4) แล้ว START_HERE.md, `layouts/aot/SPEC.md` (สเปกตัวประกอบเดิม — ส่วนที่ขัดกับ v3.4 ให้ยึด v3.4 สำหรับงานใหม่), references/WORKFLOW.md, STYLE.md; โหลด JOB_FORMAT.md เมื่อวางฉาก, AUDIO_AND_TIMING.md เมื่อเตรียมเสียง/คำ, ASSET_SOURCES.md เมื่อหาสื่อ, QUALITY.md ก่อนส่งออก
3. ตรวจความสามารถที่มีจริง: เปิดต้นฉบับ/Drive, ดาวน์โหลด, filesystem, Python/FFmpeg, render และส่งไฟล์ได้หรือไม่ ถ้าเอนจิน v3.4 ยังไม่ได้นำเข้า ให้รายงาน planning-only สำหรับงาน v3.4 อย่าอ้าง render pass; `python renderer/kit.py doctor` พิสูจน์เฉพาะเครื่องยนต์เก่าเท่านั้น
4. รับเนื้อหา เก็บต้นทางและตรวจข้อกล่าวสำคัญ ห้ามใช้ชื่อ/thumbnail แทนเนื้อหาทั้ง YouTube ถ้าเข้าถึงไม่ได้บอกข้อจำกัดและขอ transcript/ไฟล์ที่จำเป็น
5. สร้างงานตาม SOP ใน SKILL.md หลัก เสนอประเด็น บท เสียง ความยาว แนวภาพและสื่อ ต้นทุน/ข้อจำกัด ให้ Philip อนุมัติก่อนผลิตเต็ม ตัวอย่าง benchmark อนุมัติเฉพาะ technical test ของเครื่องเก่าเท่านั้น ห้ามใช้เป็นต้นแบบสไตล์
6. หลังอนุมัติ ทำงานย่อยที่ย้อนกลับได้เองให้จบ ใช้ assets ของ Philip ก่อน แล้วค่อยหาสื่อที่มีสิทธิ์ตรงงาน จดที่มา และ label evidence/illustration/screen_recording ชัด ภาพประกอบงานใหม่ต้องเป็นภาพโค้ดล้วน + ช่องทีวี Lemo ตามสเปกหลัก ห้ามใช้ภาพ AI-generated เป็นภาพหลัก ไม่ใส่ Warodom likeness/voice/footage/course assets
7. เตรียมเสียง words.json และ visemes.json จากเสียงจริง ไม่ใช้เวลาหารเท่าอ้าง sync ปากเป็น raster pronunciation approximation ไม่ใช่ rig 3D หรือ acoustic phoneme-perfect หากขาด alignment tools ให้บอกและเลือกทางที่มีจริง (Studio Mode ใช้ visemes.json จาก MFA; Express Mode สกัดท่าปาก 24fps จากเสียงอัตโนมัติ)
8. เติม job spec ตรวจ validate และ preview บันทึก approval.json จากหลักฐาน owner จริง พร้อม digest ของ job/inputs รุ่นนั้น ห้ามอนุมัติตัวเอง ถ้าสาระ/เสียงหลักเปลี่ยนให้กลับตรวจใหม่ แต่ไม่ขออนุมัติซ้ำเพียงเพราะรายละเอียดประกอบงานเดิมเสร็จแล้ว
9. Render ด้วยเอนจิน v3.4 เมื่อนำเข้าแล้ว แล้วดู/ฟังและตรวจ QC ตาม QUALITY.md และเกณฑ์ v3.4 ใน SKILL.md หลัก ส่ง MP4, SRT, ซอร์สที่ส่งต่อได้, sources และรายงานสิ่งที่ตรวจจริง เก็บ SESSION.md ให้ AI ตัวถัดไปทำต่อได้
10. ห้ามเผยแพร่ ซื้อบริการ ส่งหาคนอื่น โคลนเสียงใหม่ หรือเขียนทับต้นฉบับโดยไม่มีคำสั่งครอบคลุม ห้ามเรียกพร้อมโพสต์หากสิทธิ์/เนื้อหาค้างหรือฉบับเต็มยังไม่ผ่าน Philip ห้ามเผยแพร่รายละเอียดการโคลนเสียง (voice ID, ชื่อโมเดล, ค่า stability/similarity, ไฟล์เสียงอ้างอิง) ใน repo นี้หรือที่สาธารณะเด็ดขาด
