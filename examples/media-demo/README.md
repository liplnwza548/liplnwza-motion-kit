# Media demo

ตัวอย่างนี้แสดงการลงทะเบียนภาพ AI และฟุตเทจจากแหล่ง stock ใน `job.json` โดยจงใจไม่เก็บไฟล์สื่อจริงไว้ใน repo

วางไฟล์เมื่อมีงานที่อนุมัติให้ใช้สื่อนั้นแล้ว:

- `media/ai-city-illustration.png` — สร้างภาพประกอบด้วย AI ตามหัวข้องาน แล้วแทนที่ข้อมูล `creator`, `origin`, `license`, `checked_date` และ `media.label` ด้วยรายละเอียดจริงของเครื่องมือและ output ก่อนใช้
- `media/pexels-city-timelapse.mp4` — Pexels clip [Traveling Through the City](https://www.pexels.com/video/traveling-through-the-city-5129233/) โดย Joseph Eulo; ดาวน์โหลดเมื่อเลือกใช้กับ job นี้เท่านั้น และตรวจหน้าคลิปกับ license ซ้ำก่อนใช้
- `media/_ที่มา.txt` — บันทึกชื่อไฟล์ ลิงก์ตรง ผู้สร้าง เงื่อนไข license/การใช้ และวันที่ตรวจของทุกไฟล์ที่ดาวน์โหลด รวมรายละเอียดเครื่องมือ, รุ่น, วันที่ และ prompt ของภาพ AI
- `inputs/voice.wav`, `inputs/words.json`, `inputs/visemes.json` — ใส่เสียงที่อนุมัติแล้วและ cue ที่สัมพันธ์กับเสียงตามขั้นตอนของ kit

ไฟล์สื่อและเสียงข้างต้นไม่มีอยู่ในตัวอย่างนี้ `kit.py validate` ตรวจว่าทุก path มีไฟล์อยู่ จึงต้องเตรียม input จริงก่อน validate job สำหรับการใช้งานจริง ตัวอย่างนี้ยังไม่มี `approval.json` และยังไม่ approved
