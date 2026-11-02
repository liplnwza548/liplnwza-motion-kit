# เปิดใช้กับ AI ต่างตัว

ใช้ core เดียวกัน อย่าสร้าง workflow คนละฉบับและปล่อยให้กติกาขัดกัน ตารางนี้เป็นวิธีเริ่มทดสอบ ไม่ใช่การรับรองว่าทุกผลิตภัณฑ์มีเครื่องมือเหมือนกัน

- ChatGPT Cloud/Work: แนบ ZIP หรือให้เข้าถึง Drive แล้วสั่งอ่าน START_HERE ตรวจว่ามี filesystem/Python/FFmpeg และส่งไฟล์ได้จริง หากช่องทางนั้นอ่านได้อย่างเดียว ให้ทำ proposal/job pack ไม่อ้างเรนเดอร์
- Gemini Spark: แนบ/เปิดชุดแล้วทดสอบ preflight ของ environment นั้นโดยตรง อย่าเอาความสามารถ Gemini CLI มาอ้างแทน Spark
- BeAN: ดาวน์โหลดชุดบน VM เปิด START_HERE รัน doctor แก้ dependency ที่จำเป็นตามสิทธิ์เดิม ไม่ต้องซื้อ API ใหม่
- Codex Local: เปิดโฟลเดอร์ kit เป็น workspace อ่าน AGENTS.md + skill โดย explicit prompt ก่อน ถ้าจะติดตั้ง skill ให้ติดตั้ง skills/liplnwza-motion ตามกลไกจริงของรุ่นที่ใช้ และตั้ง LIP_MOTION_ROOT ให้ชี้ kit เมื่อ skill แยกจาก runtime
- AGY Local: เปิดโฟลเดอร์เดียวกันและสั่งอ่าน START_HERE/AGENTS/skill ชัด ๆ ตรวจเครื่องมือจริง หาก auto-load ใช้ชื่อไฟล์อื่น ให้สร้างไฟล์ชี้ไป AGENTS.md สั้น ๆ ไม่คัดลอกกติกาซ้ำ

AGENTS.md / SKILL.md ไม่ได้ถูกค้นอัตโนมัติเหมือนกันทุกแอป การอ่านเป็นคู่มือกับการติดตั้ง native skill ต่างกัน ทาง explicit read เป็น fallback ที่ต้องตรวจว่ามันอ่านครบจริง

ทดสอบแต่ละตัวในโฟลเดอร์/แชทใหม่ จดรุ่นโมเดลและ environment ที่เห็นจริง ไม่บอกว่ารุ่นใดชนะล่วงหน้า อย่าส่งต่อบัญชี token หรือ API key ในแพ็ก

Native installed skill เป็น controller ขนาดเล็ก Runtime/assets อยู่ใน kit ตั้ง LIP_MOTION_ROOT หรือวาง kit ใน workspace; หากไม่พบให้กลับไป START_HERE ที่ Drive ไม่ค้นหา private files ทั้งเครื่อง
