---
name: liplnwza-motion
description: สร้างวิดีโอโมชั่นแนวตั้ง LiplnwZa จากบทความ ข้อความ หรือ YouTube โดยตรวจต้นฉบับ เสนอข้อเสนอให้ Philip อนุมัติ ใช้ mascot และ renderer ใน Motion Kit แล้วเรนเดอร์ ตรวจคุณภาพ และส่งไฟล์ ใช้เมื่อขอสร้างหรือปรับคลิปโมชั่น ซับสีรายคำ หรือมาสคอตพิธีกรของ Philip
---

# LiplnwZa Motion

ใช้ Motion Kit 0.2.0 ที่ Philip จัดไว้เป็น runtime/assets กลาง สกิลนี้เป็น controller ไม่ได้รวม runtime หนักใน native skill installation; mouth rig v0.2 รองรับปากต่อเนื่องบน clean plate ทั้งหกท่า แต่คลิป Pilot002 v4 ยังรอ Philip ตรวจภาพฉบับเต็ม

1. หา kit root แบบจำกัด: ใช้ LIP_MOTION_ROOT หากกำหนด หรือ kit ใน workspace ที่ผู้ใช้แนบ ให้มี START_HERE.md และ renderer/kit.py ถ้าไม่พบ ใช้โฟลเดอร์ที่เจ้าของระบุ https://drive.google.com/drive/folders/1sbnVgJ-w9AfzKlm35wJQXO-vhJPSCRK5 เพื่อดาวน์โหลดชุด หรือขอให้แนบ ZIP อย่าค้น private filesystem ทั้งเครื่อง
2. อ่าน START_HERE.md และ AGENTS.md ของ kit แล้ว references/WORKFLOW.md, STYLE.md; โหลด JOB_FORMAT.md เมื่อวางฉาก, AUDIO_AND_TIMING.md เมื่อเตรียมเสียง/คำ, ASSET_SOURCES.md เมื่อหาสื่อ, QUALITY.md ก่อนส่งออก
3. ตรวจความสามารถที่มีจริง: เปิดต้นฉบับ/Drive, ดาวน์โหลด, filesystem, Python/RAQM/FFmpeg, render และส่งไฟล์ได้หรือไม่ เรียก `python renderer/kit.py doctor` ใน kit root หากไม่มี shell ให้รายงาน planning-only อย่าอ้าง render pass
4. รับเนื้อหา เก็บต้นทางและตรวจข้อกล่าวสำคัญ ห้ามใช้ชื่อ/thumbnail แทนเนื้อหาทั้ง YouTube ถ้าเข้าถึงไม่ได้บอกข้อจำกัดและขอ transcript/ไฟล์ที่จำเป็น
5. สร้าง jobs/<id> ด้วย renderer/new_job.py เสนอประเด็น บท เสียง ความยาว แนวภาพและสื่อ ต้นทุน/ข้อจำกัด ให้ Philip อนุมัติก่อนผลิตเต็ม ตัวอย่าง benchmark อนุมัติเฉพาะ technical test ตามคำสั่งสร้างชุดเดิม
6. หลังอนุมัติ ทำงานย่อยที่ย้อนกลับได้เองให้จบ ใช้ assets ของ Philip ก่อน แล้วค่อยหาสื่อที่มีสิทธิ์ตรงงาน จดที่มา และ label evidence/illustration/screen_recording ชัด ไม่ใส่ Warodom likeness/voice/footage/course assets
7. เตรียมเสียง words.json และ visemes.json จากเสียงจริง ไม่ใช้เวลาหารเท่าอ้าง sync ปากเป็น raster pronunciation approximation ไม่ใช่ rig 3D หรือ acoustic phoneme-perfect หากขาด alignment tools ให้บอกและเลือกทางที่มีจริง
8. เติม job.json ตรวจ validate และ preview บันทึก approval.json จากหลักฐาน owner จริง พร้อม digest ของ job/inputs รุ่นนั้น ห้ามอนุมัติตัวเอง ถ้าสาระ/เสียงหลักเปลี่ยนให้กลับตรวจใหม่ แต่ไม่ขออนุมัติซ้ำเพียงเพราะรายละเอียดประกอบงานเดิมเสร็จแล้ว
9. Render ด้วย renderer/kit.py แล้วดู/ฟังและตรวจ QC ตาม QUALITY.md ส่ง MP4, SRT, ซอร์สที่ส่งต่อได้, sources และรายงานสิ่งที่ตรวจจริง เก็บ SESSION.md ให้ AI ตัวถัดไปทำต่อได้
10. ห้ามเผยแพร่ ซื้อบริการ ส่งหาคนอื่น โคลนเสียงใหม่ หรือเขียนทับต้นฉบับโดยไม่มีคำสั่งครอบคลุม ห้ามเรียกพร้อมโพสต์หากสิทธิ์/เนื้อหาค้างหรือฉบับเต็มยังไม่ผ่าน Philip

สำหรับ installed skill ให้เปิด references/runtime.md เมื่อไม่แน่ใจการหา runtime และใช้ scripts/locate_kit.py ตรวจเฉพาะตำแหน่งที่ระบุ
