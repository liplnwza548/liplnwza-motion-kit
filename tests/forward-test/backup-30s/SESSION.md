# Session

สถานะ: proposal_ready / awaiting_owner_approval_and_voice
ชุด: Motion Kit 0.1.0
ต้นฉบับ: inputs/article.txt (ข้อความจากแชท ไม่มี URL)
สิ่งที่อนุมัติ: ยังไม่มีสำหรับงานนี้ approval.json เป็น pending, evidence และ digest เป็น null

ทำแล้ว: อ่าน START_HERE, AGENTS, SKILL และ WORKFLOW/STYLE/JOB_FORMAT/AUDIO_AND_TIMING; doctor ผ่านจริง (ดู PREFLIGHT.json); ใช้สำเนา renderer/new_job.py สร้าง scaffold ในพื้นที่งานนี้ เติม brief/proposal/source ledger/job draft และตรวจ JSON/ความต่อเนื่องเวลาฉาก

ข้อจำกัด: job.json เป็นแผนร่าง 30 วินาที ไม่พร้อม render ไม่มี inputs/voice.wav, words.json, visemes.json หรือ timing_provenance.json ไม่สร้างเวลา word sync จำลอง ไม่เรียก validate/preview/render และไม่อ้าง QC pass ไม่มี MP4/SRT

ขั้นถัดไป: รอ Philip ตรวจ PROPOSAL.md และให้เสียงหรือสิทธิ์วิธีจัดหาเสียง หลังได้อนุมัติและเสียงให้ฟัง/ตรวจบท เตรียม alignment จากเสียงจริงและ provenance ปรับแผนเวลาโดยไม่เปลี่ยนสาระ ตรวจสิทธิ์ assets แล้วบันทึก approval จากหลักฐานจริงพร้อม digest ของ inputs/job รุ่นครบ อ่าน QUALITY.md ก่อน preview/render/QC ไม่ถือ benchmark เป็นสิทธิ์อนุมัติงานนี้

ขอบเขตไฟล์: เขียนเฉพาะ agent_forward_test; ไม่แก้ kit; ไม่ซื้อ/เผยแพร่/ส่งหาผู้อื่น
