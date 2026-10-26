# Job format v1

อ่าน examples/benchmark15/job.json เป็นตัวอย่างเต็ม; JSON คือข้อมูล ห้ามใส่ Python/JavaScript หรือ shell commands

Root: schema_version=1, title, topic_label, duration (0–120s), voice, words, visemes, footer, sources[], scenes[]; sfx_gain optional (default 1). `renderer/new_job.py` sets `render_policy_version=1` on new jobs. `show_brand=false` hides the kit's fixed brand label when all visible copy must come from an approved script.

Review-only jobs may set `draft_review: {"allow_draft": true, "decoration_motion": "drift"}`. This explicit opt-in resolves draft theme/assets for an owner-review render and applies deterministic drift to theme decorations without changing library status. Such a job must keep `approval.json.status="pending"`, set `review_only=true`, and pin `review_digest` to the current job digest; it cannot add BGM or claim full-job approval. Normal jobs still reject drafts and require owner approval before render.

New jobs with `render_policy_version=1` show each word chip only from its cue start until `min(cue.end, cue.start+1.2s)`; cues are never extended to fill gaps. Their average visible duration must be 0.4–0.7s per clip or validation asks for word-cue re-alignment. Jobs without the version field retain the legacy caption behavior.

Paths อ้างจากโฟลเดอร์ job, อยู่ภายใน job หรือ kit root เท่านั้น ตัวอย่าง assets ใช้ ../../assets/... เมื่อ job อยู่ใน jobs/ID หรือ examples/ID เสียงยาวกว่าวิดีโอไม่ผ่าน ห้ามซ่อนการตัดคำใน renderer

words.json: [{"word":"สวัสดี","start":0,"end":0.5}, ...] เป็นวินาทีบวก เรียงและไม่ทับกัน ครอบคลุมคำที่พูดจริง ขอบคำจากเสียงต้องมี provenance
visemes.json: [{"start":0,"shape":"AA"}, ...] shape ∈ CLOSED, AA, EE, OH, OO, FV; เรียงเวลา ใช้ pronunciation approximation และ gate ปิดปากช่วงเงียบ ไม่รับรอง phoneme-perfect

Scene: start,end ต่อเนื่องครอบคลุม duration; layout ∈ title,compare,list,media,summary; title; pose ∈ explain,point_right,thinking,magnify,point_left,thumbs_up; right boolean; body ใช้กับ title/summary; items[] ใช้ compare (2) หรือ list (สูงสุด4); aside และ cta เป็นข้อความสั้น; pose_changes:[{"at":1.5,"pose":"thinking"}] เวลา relative; optional `background_variant` selects a pinned variant ID from the selected theme for that scene. `show_title=false` and `show_topic_label=false` suppress those labels in an individual scene; all supplied copy otherwise follows the job's approved-script rules. A theme mascot concept with an approved `runtime_rig` resolves that versioned rig, validates its manifest and file hashes, and adds its files to the render digest. Mouth rig v0.2 swaps the clean plate and profile for each pose.

Media optional: {"path":"inputs/example.mp4","kind":"video","in":0,"role":"illustration","label":"ภาพประกอบ","source_id":"asset01","green_screen":true}
kind=image|video; role=illustration|evidence|screen_recording; green_screen ใช้กับ video และ key สีเขียว #00FF00 แบบพื้นฐาน ต้องตรวจขอบจริง; ไม่รองรับ key สีอื่นใน v0.2 วิดีโอสั้นกว่าฉากจะค้างเฟรมท้าย ไม่วนอัตโนมัติ หากไม่เหมาะให้เลือกไฟล์ใหม่หรือจัดฉากให้พอดี

Sources แต่ละรายการ: id,origin (URL หรือ path),creator,license,usage,checked_date; ใส่ข้อจำกัด/เครดิตใน usage ตัว validator ตรวจว่ามี field ไม่สามารถรับรองสิทธิ์จริงแทนการอ่าน license

approval.json: status=pending จนมีหลักฐาน owner; เมื่ออนุมัติแล้ว status=approved, evidence=ข้อความ/วัน/ขอบเขตจริง, job_digest=ค่าจากคำสั่ง digest checksum ป้องกันใช้แผนคนละรุ่น ไม่ใช่ระบบ authentication ของผู้อนุมัติ ใน v0.2 digest รวม SHA-256 ของ assets และโค้ด mouth rig ใน kit ด้วย

Optional `bgm`: `{ "source_id", "path", "in_s", "gain_db", "loop", "fade_in_s", "fade_out_s", "ducking" }`; `path` must stay inside the job. Looping is unsupported and the source must cover the complete job duration. Fades are fixed at 0.5s/1.5s and ducking cannot be disabled. The matching source entry must record `license`, `usage`, `checked_date`, `rights: {"status":"cleared","evidence","checked_date"}`, and `approval: {"status":"approved","approved_by":"Philip","evidence"}`. Missing file, rights evidence, source approval, or duration fails validation. No BGM field means voice/SFX render without a music input.

Cue templates และ benchmark เป็นตัวอย่างเท่านั้น งานใหม่ห้าม reuse เสียง/คำ/ข้อเท็จจริงรถบินโดยอัตโนมัติ
