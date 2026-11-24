# V34 Import Checklist — เอนจินและแอสเสต v3.4 ที่ต้องนำเข้า repo นี้

> **สถานะ: รอนำเข้า (IMPORT PENDING)** — ไฟล์ทั้งหมดในรายการนี้ติดตั้งอยู่
> เป็นสกิล `liplnwza-motion` v3.4 บน Gemini Task Web เท่านั้น
> ยังไม่มีไฟล์ใดใน repo นี้ (ตรวจแล้ว 2026-11-24: ค้นทั้ง VM ไม่พบไฟล์เหล่านี้)
> ห้ามสร้างไฟล์เหล่านี้ขึ้นมาเอง ห้ามเจนแอสเสตทดแทน
> การนำเข้าต้องมาจาก export ของสกิลที่ติดตั้งแล้วเท่านั้น
>
> สเปกที่ไฟล์เหล่านี้ต้องทำให้ตรง: `SKILL.md` ที่ราก repo + `renderer/v34_spec.py`
> เมื่อนำเข้าเสร็จและตรวจรับผ่าน ให้เปลี่ยน `ENGINE_STATUS` ใน `v34_spec.py`
> เป็น `"imported"` ใน commit แยกต่างหาก พร้อมผลตรวจรับ

## แหล่งที่มา (Source)

- สกิล `liplnwza-motion` **v3.4 Lean & Punchy** ที่ติดตั้งบน Gemini Task Web
- หน้า Notion อ้างอิง: "LiplnwZa Motion Kit v3.4 — Production Spec, Installed Skill & GitHub Sync Plan"
- ผู้ส่งออก: ฟิลิปหรือ Gemini (Task Web) — บีนตรวจรับไฟล์จริงก่อน merge เท่านั้น

## รายการไฟล์ที่ต้องนำเข้า

| # | ไฟล์ (ชื่อที่ล็อก) | พาธเป้าหมายที่เสนอ* | สิ่งที่ต้องมีข้างใน |
|---|---|---|---|
| 1 | `render_liplnwza_v3.py` | `renderer/render_liplnwza_v3.py` | เอนจินเรนเดอร์ CDP หลัก: 720×1280 @ 24fps, JPEG q=92, `--chunk-frames 120`, faststart, กล้อง 4 แบบ, ทรานซิชั่น 4 แบบ, Lip-Sync 2 โหมด |
| 2 | `stage_template.html` | `renderer/stage_template.html` | เทมเพลต Full-Canvas Paper Stage: ริบบิ้น y=144, เวที y=214..659, ซับกลางจอ y=672 + Auto-Fit, มาสคอต 500px ล่างซ้าย |
| 3 | `widgets.js` | `renderer/widgets.js` | 12 Animated Micro-Widgets + ช่องทีวี `media_clip_frame` |
| 4 | `audio_mixer.py` | `renderer/audio_mixer.py` | มิกซ์เสียง: BGM 3 แนว (funk_brass 118 / warm_groove 108 / mystery_pulse 104 BPM), Mid-Band Ducking 300Hz–4kHz, Foley, 2-pass −14.5 LUFS, BGM สร้างใน `/tmp/liplnwza_v3_bgm/` |
| 5 | `mouth_anchors.json` | `renderer/mouth_anchors.json` | จุดยึดปาก SVG 6 ทรงบน clean plate 16 ท่า |
| 6 | แผ่นคลีน 16 ท่า (WebP) | `assets/mascot/v34/clean_plates/` | Mouthless Clean Plate 16 ท่าตามรายชื่อใน `v34_spec.py` รวม 220.8 KB |
| 7 | พร็อพ/บอท 12 ชิ้น (WebP) | `assets/mascot/v34/props/` | WebP โปร่งใส 12 ชิ้นตามรายชื่อใน `v34_spec.py` รวม 88.4 KB |
| 8 | ปาก SVG 6 ทรง | `assets/mascot/v34/mouths/` | เวกเตอร์ SVG: CLOSED / AA / EE / OH / OO / FV |

\* พาธเป้าหมายเป็นข้อเสนอ — ให้ยืนยันกับโครงสร้าง export จริงตอนนำเข้า
ส่วนที่ล็อกคือ**ชื่อไฟล์และเนื้อหาตามสเปก** ไม่ใช่พาธ

## ขั้นตอนตรวจรับ (Acceptance — ต้องผ่านทุกข้อก่อน merge)

1. ไฟล์ครบทั้ง 8 รายการ ชื่อไฟล์ตรงรายการข้างต้น ไม่ขาดไม่เกิน
2. นับแอสเสตจริง: clean plates 16 ไฟล์ / props 12 ไฟล์ / ปาก SVG 6 ทรง ชื่อตรง `v34_spec.py`
3. ขนาดรวมตรงสเปก: clean plates รวม 220.8 KB / props รวม 88.4 KB (คลาดได้เฉพาะการปัดเศษทศนิยม)
4. `mouth_anchors.json` อ่านได้เป็น JSON ครบ 16 ท่า × 6 ทรงปาก
5. รันเอนจินกับงานทดสอบแล้วได้ MP4 720×1280 @ 24fps, faststart, ความดัง 2-pass −14.5 LUFS
6. ตรวจเฟรมจริง: ซับอยู่กลางจอ y=672 ไม่ล้นขอบ, มาสคอตนิ่ง (หายใจ ±2.2px เท่านั้น), กล้อง/ทรานซิชั่นขยับเฉพาะเวที+พื้นหลัง
7. รัน `python3 renderer/verify_manifest.py` และ `python3 -m unittest discover -s tests` ผ่านทั้งหมด (รวมเทสต์ v3.4 ใหม่)
8. อัปเดต `manifest-sha256.json` ให้ครอบคลุมไฟล์ที่นำเข้าทั้งหมด
9. ห้ามมีรายละเอียดการโคลนเสียง (voice ID, ชื่อโมเดล, ค่า stability/similarity, ไฟล์เสียงอ้างอิง) หลุดมาในไฟล์ที่นำเข้า — ตรวจด้วย grep ก่อน merge ทุกครั้ง

## สิ่งที่ห้ามทำตอนนำเข้า

- ห้ามเขียนทับไฟล์เครื่องยนต์เก่า (`renderer/kit.py`, `layouts/aot/compose.py`) — เครื่องยนต์เก่าแช่แข็งไว้เพื่องานเดิมและเทสต์
- ห้ามเปลี่ยนค่าคงที่ใน `renderer/v34_spec.py` เพื่อให้ตรงไฟล์ที่นำเข้า — ถ้าไฟล์นำเข้าขัดกับสเปกที่ล็อกไว้ ให้หยุดและถามฟิลิปก่อน
- ห้าม merge จนกว่าฟิลิปจะอนุมัติแยกต่างหาก
