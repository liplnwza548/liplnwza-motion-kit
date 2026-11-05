# Changes

## aot-widgets-phase4 — 2026-11-05 (merged to main, Philip approved)
แก้ปัญหาวิดเจ็ตของคลิปผลัดวันประกันพรุ่ง 2026-11-05: ป้ายของ container ย้ายขึ้นไปอยู่เหนือกล่อง 12px แทนการวางกึ่งกลางขอบกล่องที่ทำให้ตัวอักษรล่างครึ่งตัวถูกขอบกล่องตัด (B05); กล่อง typewriter เปลี่ยนจากสี่เหลี่ยมสูง 260px กลางภาพที่บังจุดเด่นของภาพ เป็นกล่องสูงตามเนื้อหา (1 บรรทัด = 126px) ยึดขอบล่างของพาเนล (B07) และเครื่องหมายถูกย้ายไปเป็นป้ายที่มุมขวาล่างของกล่องแทนการวางทับข้อความ; กฎวิดเจ็ตใหม่ใน `load_job` (`validate_widgets`): หนึ่งบีตมีวิดเจ็ตพาเนลได้สูงสุด 1 ตัว (highlight ที่อยู่แค่แถบ header ยกเว้น), แถวไอเทมของ container ต้องพอดีความกว้างพาเนล, ข้อความ typewriter ต้องพอดีไม่เกิน 3 บรรทัดและเหลือที่ให้ป้ายถูก — ไม่เช่นนั้นงานล้มดังๆ แทนการตัดข้อความเงียบๆ; เทสต์ใหม่ 7 ข้อใน `tests/test_aot_layout.py` (รวม 23 ข้อ) ตรวจจากพิกเซลจริงของเฟรมที่วาดด้วย `widget_frame` ว่าป้ายไม่แตะขอบกล่องและกล่อง typewriter อยู่ขอบล่างพาเนล; ตรวจด้วยวลี 37 ชิ้นเดิมของคลิปผลัดวันฯ แล้วว่าเกทเฟส 1–3 ปฏิเสธงานเก่า และข้อมูลวิดเจ็ต B05/B07 เดิมผ่านเกทเฟส 4 — งานรันใหม่ของ AGY จึงแก้แค่ words.json ทาง MFA ไม่ต้องแก้ข้อมูลวิดเจ็ต

## aot-words-thai-gates — 2026-11-05 (merged to main, Philip approved)
แก้ต้นตอของคลิปผลัดวันประกันพรุ่ง 2026-11-05 ที่ชิปขึ้นเป็นวลีทั้งก้อนเพราะ words.json เขียนมือพร้อมเวลาที่กะจากความยาวตัวอักษร: `layouts/aot/compose.py` ตรวจ words.json ตอนโหลด (ชิปไม่เกิน 12 กลุ่มตัวอักษร / 16 ตัวอักษร / 600px ที่ 80px / 1.2 วิ, เวลาต้องเรียงกัน, งานจริงต้องมีไฟล์ provenance จาก `renderer/mfa_to_cues.py` ข้าง words.json — ตัวอย่างใน repo เท่านั้นที่ยกเว้นด้วย `"fixture": true`); ยก `mfa_to_cues.py` ขึ้นเป็นทางเดินคำมาตรฐานของ AoT ใน SPEC.md และ PROMPT-FOR-CHATGPT.md ห้ามเขียนสคริปต์ประกอบงานเฉพาะคลิปอีก; แก้ตัวอักษรไทยซ้อนกัน: typewriter/CTA พิมพ์ทีละกลุ่มตัวอักษรแทนทีละรหัส, ชิปและป้ายยึดเส้นฐานแทนกึ่งกลาง bbox (เดิมชิปในแถวเดียวกันสูงต่ำต่างกันถึง 19px), `font()` ล้มดังๆ ถ้า Pillow ไม่มี RAQM; เทสต์ใหม่ 10 ข้อใน `tests/test_aot_layout.py` (รวม 16 ข้อ) และซ่อมเทสต์เก่า 2 ข้อที่อ้างชื่อฟังก์ชัน/ค่าคงที่เดิมที่ไม่มีแล้ว

## 0.2.0 — 2026-10-20
เพิ่ม mouth rig แบบ clean plate แยกทั้งหกท่าของ LiplnwZa ใช้พารามิเตอร์ปากต่อเนื่องจาก cue เสียงและปิดปากช่วงเงียบ ป้องกันบริเวณมือ/แว่นด้วย mask เฉพาะท่า เพิ่มการตรวจ registration และเปลี่ยน approval digest ให้ครอบคลุม source/profile/code ของ rig เก็บ sprite รุ่นเก่าไว้เพื่อเทียบเท่านั้น เพิ่มการทดสอบ rig หกท่าและการเปลี่ยนท่า

## 0.1.0 — 2026-10-20
First portable single-style kit extracted from accepted Pilot002 v3: parameterized scenes, captions, registered mascot mouths, original SFX, local media composition, preflight/validation/QC, owner approval record, fresh-folder benchmark and cross-agent protocol. Cross-product compatibility is pending owner tests; no model weights/API keys bundled.

## aot-v001 — 2026-11-03
เพิ่มเลย์เอาต์ AoT เป็นสไตล์หลักของงานใหม่ (บนกรอบภาพ / กลางซับชิป / ล่างมาสคอต, 1080x1920, 30fps) พร้อมตัวประกอบ generic ใน layouts/aot/compose.py, สเปกใน layouts/aot/SPEC.md, ตัวอย่าง placeholder ใน layouts/aot/example/ และเทสต์เลย์เอาต์ใน tests/test_aot_layout.py; เลย์เอาต์กระดาษ paper-v021 และ benchmark15 เหลือเป็นเทสต์เทคนิค legacy เท่านั้น ไม่ใช่ต้นแบบสไตล์งานใหม่; ไม่แตะโค้ด renderer/kit.py เดิม
