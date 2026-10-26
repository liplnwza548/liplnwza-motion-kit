# Style v0.1 — locked reference, flexible content

ฐานหน้าตาคือ Pilot002_Final_v3 ที่ Philip ยืนยันในแชท 20 ต.ค. 2026 ไม่ใช่การอนุญาตนำไฟล์/หน้า/เสียงของ Warodom มาใช้

- 1080×1920 / 30fps; pastel grid + rough paper cards, ink #181b26, yellow #ffd648, blue #2264d8, red #f44336, green #38b577
- LiplnwZa เสื้อฮู้ดดำ ขอบสติกเกอร์ขาว มี 6 ท่า; mouth rig v0.2 ลบรอยยิ้มเดิมด้วย clean plate เฉพาะพื้นที่ แล้วประกอบรูปปาก 2D ต่อเนื่องตาม timeline; ห้ามเรียกว่า rig 3D หรือระบบจับหน่วยเสียงจริง
- พิธีกรเกือบตลอด แต่ให้หัวข้อ/หลักฐานเด่นตามเรื่อง เปลี่ยนท่าเมื่อมีเหตุผล ไม่สลับสุ่มถี่จนรบกวน
- ซับเป็น lexical chips ไม่บังคับแยกทุกพยางค์ คำประสม/ชื่อให้อ่านรู้เรื่อง เด้งตามขอบคำ แสดงบริบทได้สูงสุด 3 ชิป แถวยาวให้ลดจำนวนคำก่อนลดตัวเล็กมาก
- พื้นที่: brand y92, title y255, subject y400–880, mascot/aside y930–1530, captions y1635, source footer y1765; ไม่รับรอง safe area ของทุกแอป ต้องตรวจบนปลายทาง
- คำสั้นบนการ์ดไม่ซ้ำซับยาวทั้งประโยค ภาพใหม่ต้องช่วยเล่าเรื่อง การตกแต่งไม่ควรบังหลักฐาน/หน้า/ซับ
- เสียงพากย์ต่อเนื่อง ตัดเฉพาะพักที่ยืนยันว่าเงียบ ไม่ลบจนกินพยัญชนะ/หายใจ ไม่เร่งเสียงอัตโนมัติ เป้าหมายมิกซ์ -16 LUFS, true peak <=-1 dBTP
- SFX original swish/pop/tap/ding; ไม่มีเพลงเป็นค่าเริ่มต้น ถ้าต้องเพิ่มเพลงตรวจสิทธิ์และอนุมัติแนวเสียง
- ตัวเรนเดอร์ v0.1 มี title, compare, list, media, summary ใช้ pose_changes และการ์ดสั้นทำจังหวะเพิ่มได้ จังหวะฉากต้องตามเสียง/ความหมาย ไม่บังคับเปลี่ยนของทุก 1.3 วินาที
- สไตล์นี้เป็นฐาน ไม่ใช่ข้ออ้างใช้รถแดงหรือเรื่อง Tesla ในหัวข้อใหม่

## Motion for new jobs

Jobs created with `render_policy_version=1` apply repeatable still-image motion from the theme seed, item identity, and absolute render time. Scene media moves within its paper panel and stays contained so the full source image remains visible; evidence and screen captures are not cropped for drift. Theme decorations may opt into `motion: "drift"`; their motion uses fixed small bounds and skips placements that intersect protected text, evidence/media, mascot, caption, footer, or progress regions. `motion: "static"` remains stationary. Jobs without a render policy version keep their previous frame behavior.
