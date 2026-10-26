# Quality and delivery gate

## อัตโนมัติ
- doctor: Python 3.11+, Pillow RAQM, FFmpeg/FFprobe, font, profile และ original/clean plate ครบทั้งหกท่า
- validate: ไฟล์ครบ, interval ฉากครอบคลุมเวลา, คำเป็นบวกไม่ทับ, รูปปาก/ท่าถูกชื่อ, source_id อ้างถึงได้, เสียงไม่ยาวกว่าภาพ
- new jobs with `render_policy_version=1`: validates the 1.2s per-chip cap and 0.4–0.7s clip average; visual context expires per cue. Static media drift is deterministic and contained inside its paper panel; decorations marked `drift` are checked against protected layout regions.
- optional BGM: validation requires job-local audio, a matching source entry, recorded rights evidence, Philip approval, and enough source duration. Voice and BGM normalize as separate stems; the renderer records gain/duck analysis and fade/target settings in `mix_report.json`.
- render ต้องมี approval รุ่นตรง; preview ตรวจ fit ของข้อความทุกขอบคำ ถ้าข้อความใส่ไม่ได้ให้ fail แทนตัดทิ้ง
- qc: ffprobe นับเฟรม; FFmpeg decode ทั้งไฟล์; H264 1080×1920 30fps / AAC stereo48k; measured loudness -18 ถึง -14 LUFS, TP <=-1 dBTP (target -16)
- BGM mix targets -16 LUFS and TP <=-1 dBTP; separate-stem duck analysis checks active 0.4s voice windows for at least 12dB voice-over-BGM margin before the final mix.
- จด hash ของ MP4 และเวอร์ชัน kit; เก็บ file paths จริง ไม่สร้างลิงก์ที่ยังไม่มีไฟล์

## ดูและฟังจริง
- ดูภาพ export จริงทุกฉากและรอยต่อ ตรวจหน้า ปาก มือ ซับ และข้อความสำคัญไม่ทับกัน
- ตรวจปากครบหกท่าและจุดเปลี่ยนท่า: ไม่มีปากเดิมโผล่/รอยปะ/ภาพสั่น, alignment ผ่านทุก profile, มือและกรอบแว่นอยู่ด้านหน้า; ดูทั้งขนาดปกติและภาพขยาย
- ฟังเสียงต่อเนื่อง ตรวจคำครบ ไม่ตัดพยัญชนะ เสียงเอฟเฟกต์ไม่กลบ ไม่มีจังหวะพักที่ไม่ตั้งใจ; final reading hold มีได้
- ซับตรงเสียงและอ่านได้ ชื่อ/ตัวเลขตรงบท; ปากเปลี่ยนรูปสมเหตุสมผล ไม่อ้างว่าตรงทุกหน่วยเสียงจาก waveform อย่างเดียว
- ภาพหลักฐานมาจากเหตุการณ์จริงที่อ้าง ภาพประกอบมี label; screenshot ไม่มีข้อมูลส่วนตัว สิทธิ์และเครดิตครบ
- footer ไม่รับรองพื้นที่ปลอดภัยทุกแพลตฟอร์ม ต้องดูบนมือถือ/ปลายทางหากจะโพสต์

## ส่งมอบ
MP4, SRT (plain timing ไม่เก็บสี/โมชั่น), ซอร์สที่แจกต่อได้, SOURCES.md, QC.md, SESSION.md และข้อความโพสต์/เครดิตถ้ามอบหมาย

เรียกว่าพร้อมให้ Philip ตรวจเมื่อ technical pass แล้ว บอกว่าดู/ฟังอะไรได้จริง หากมีประเด็นเนื้อหา/สิทธิ์ค้างอย่าเรียกพร้อมโพสต์ การตรวจเดโมเดิมไม่ใช่การอนุมัติ export ใหม่ และการอนุมัติคลิปไม่ใช่การสั่งเผยแพร่
