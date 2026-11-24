# V34 Import Checklist — เอนจินและแอสเสต v3.4 ที่นำเข้า repo นี้

> **สถานะ: นำเข้าแล้ว (IMPORTED 2026-11-24)** — ไฟล์นำเข้ามาจาก export
> ของสกิล `liplnwza-motion` v3.4 บน Gemini Task Web
> (`liplnwza-motion-v3.4-export.zip`, sha256
> `289b3e0b328b0ffef13f07154a24b0f753fbf2a8035725ed9d39846863ed4ea9`)
> คัดลอกแบบ byte-for-byte ตรวจรับตามรายการด้านล่าง ผลตรวจรับเต็มอยู่ท้ายไฟล์
>
> หมายเหตุโครงสร้างจริง (ต่างจากพาธที่เสนอไว้เดิม): `mouth_anchors.json`
> อยู่กับ clean plates ใน `assets_v3/mascot/` เพราะเอนจินอ่านจากที่นั่น
> และปาก 6 ทรงเป็น SVG แบบ procedural ที่ `widgets.js` สร้างขึ้น
> (ไม่มีไฟล์ SVG แยก) — ดูผลตรวจรับท้ายไฟล์

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

## ผลตรวจรับ — นำเข้าเสร็จ 2026-11-24 (บีนตรวจไฟล์จริงก่อน merge)

แหล่งไฟล์: `liplnwza-motion-v3.4-export.zip` (sha256 `289b3e0b328b0ffef13f07154a24b0f753fbf2a8035725ed9d39846863ed4ea9`)
คัดลอกแบบ byte-for-byte ตรวจด้วย `cmp`/`diff -r` ตรงทุกไฟล์ที่นำเข้า
ไฟล์ `SKILL.md` ที่มากับ ZIP **ไม่ได้**นำเข้า — ตรวจเนื้อหาแล้วตรงกับสเปกที่ล็อกไว้
สเปกหลักฉบับเดียวคือ `SKILL.md` ที่ราก repo อยู่แล้ว นำเข้าซ้ำจะกลายเป็นแหล่งความจริงที่ 3

ผลตามข้อตรวจรับ (1–9):

1. ✅ ไฟล์ครบ — สคริปต์ 4 ไฟล์ + แอสเสต WebP 28 ไฟล์ + `mouth_anchors.json` + `references/scene_spec_schema.md` = 34 ไฟล์ (ไฟล์ที่ 35 ใน ZIP คือ SKILL.md ที่ไม่ได้นำเข้าตามเหตุผลข้างบน)
2. ✅ นับแอสเสตจริง: clean plates 16 ไฟล์ / props 12 ไฟล์ ชื่อตรง `v34_spec.py` ทุกชื่อ — ปาก 6 ทรง**ไม่มีไฟล์แยก**: ปากเป็น SVG แบบ procedural ที่ `widgets.js` สร้าง (`renderProceduralMouth`) ตรวจโค้ดแล้วมีครบ 6 ทรง
3. ✅ ขนาดรวมตรงสเปกเป๊ะ: clean plates 226,124 ไบต์ = 220.8 KB / props 90,566 ไบต์ = 88.4 KB
4. ⚠️ ปรับถ้อยคำ: `mouth_anchors.json` อ่านได้เป็น JSON ครบ 16 ท่า (ต่อท่ามี `mx`/`my`/`scale`) — ไม่ใช่ "16 ท่า × 6 ทรงปาก" เพราะรูปปากไม่ได้ผูกกับท่า แต่สกัดจากเสียง/visemes แบบ procedural — พาธจริงคือ `assets_v3/mascot/mouth_anchors.json` (เอนจินอ่านจากโฟลเดอร์มาสคอต) ไม่ใช่ `renderer/` ตามที่เสนอไว้เดิม
5. ⚠️ เกือบผ่าน: เรนเดอร์ทดสอบ 6 วิได้ MP4 720×1280 @ 24fps, faststart (moov อยู่ก่อน mdat), 144 เฟรม 2 chunks — ความดังวัดจาก MP4 จริงได้ **−14.83 LUFS** (เป้า −14.5 คลาด 0.33 LU) แต่ **True Peak −0.48 dBTP เกินเกณฑ์ ≤ −1.0** — วินิจฉัยแล้ว: WAV ก่อนบีบอัด AAC ได้ TP −1.05 (ผ่านเกณฑ์) แต่ AAC 192k ดันพีคขึ้นอีก +0.57 dB — เป็นพฤติกรรมของมิกเซอร์ตัวนี้ (loudnorm linear ไม่จำกัดพีคจริง กับดักเดียวกับที่บันทึกไว้ใน SKILL.md แล้ว) **ต้องแก้ฝั่งเอนจินก่อนส่งคลิปจริงคลิปแรก** บีนไม่ได้แก้โค้ดที่นำเข้าเอง
6. ✅ ตรวจเฟรมจริงจาก MP4: ซับสีรายคำอยู่กลางจอโซน y=672 ไม่ล้นขอบ ตัวอักษรไทยสะอาด มาสคอตยืนนิ่งนอก Camera Rig (ตรวจโครงสร้างเทมเพลตแล้ว: `#mascot-layer` อยู่นอก `#camera-rig`) ปากขยับตามไทม์ไลน์จริง (เฟรม 1.3 วิปากเปิด) กล้อง/ทรานซิชั่นขยับเฉพาะเวที+พื้นหลัง — เฟรมตรวจ: `/tmp/v34-mp4-frame.png` (สเปกทดสอบ `/tmp/v34-smoke-spec.json`)
7. ✅ `verify_manifest.py` ผ่าน (199 ไฟล์) + `unittest discover` ผ่าน 100 ข้อ (เดิม 87 + v34 13 ข้อ รวมเทสต์ตรวจไฟล์เอนจินจริง) + smoke test `--qa-only` ผ่าน 2 รอบ (แผ่น QA 3 ช็อต + ช่องทีวี Lemo)
8. ✅ `manifest-sha256.json` รีเจนใหม่ครอบคลุมไฟล์นำเข้าทั้งหมดแล้ว
9. ✅ grep ไฟล์ที่นำเข้าทั้งหมด: ไม่มี voice ID / ชื่อโมเดลเสียง / stability / similarity / API key หลุดมา

ยังไม่ได้ตรวจ (อยู่นอกขอบเขต smoke test): Lip-Sync โหมด Studio (visemes.json จาก MFA) และ Express (สกัดจากเสียงจริง) กับเสียงพากย์จริง — smoke test ใช้เสียง BGM อย่างเดียว ไทม์ไลน์ปากจึงเป็นโหมด demo — ต้องตรวจอีกครั้งกับงานจริงงานแรก
