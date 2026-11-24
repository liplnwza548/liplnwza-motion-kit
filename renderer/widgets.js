// liplnwza-motion-v3.2: Preloaded Assets (zero IPC bloat) + Auto-Fit Chips + 12 Widgets + SVG Procedural Mouth
(function() {
  const PALETTE = [
    { bg: '#FFD648', fg: '#181B26' },
    { bg: '#2264D8', fg: '#FFFDF6' },
    { bg: '#F44336', fg: '#FFFDF6' },
    { bg: '#38B577', fg: '#181B26' },
  ];
  const ROLE_COLORS = {
    emphasis:  { bg: '#FFD648', fg: '#181B26' },
    tool:      { bg: '#2264D8', fg: '#FFFDF6' },
    result:    { bg: '#38B577', fg: '#181B26' },
    verb:      { bg: '#F44336', fg: '#FFFDF6' },
    connector: { bg: '#FFFDF6', fg: '#181B26' },
  };
  const RIBBON_COLORS = {
    red:    { bg: '#E5483B', fg: '#FFFDF6' },
    blue:   { bg: '#2264D8', fg: '#FFFDF6' },
    yellow: { bg: '#FFD648', fg: '#181B26' },
    green:  { bg: '#2EAE6D', fg: '#FFFDF6' },
  };

  let lastPose = '';
  let lastSidekick = '';

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  function springScale(age, dur = 0.16) {
    if (age <= 0) return 0;
    if (age >= dur) return 1.0;
    const p = age / dur;
    if (p < 0.65) {
      const k = p / 0.65;
      return 0.6 + (1.08 - 0.6) * (1 - Math.pow(1 - k, 3));
    }
    const k = (p - 0.65) / 0.35;
    return 1.08 - 0.08 * k;
  }

  function renderProceduralMouth(shape, anchor) {
    const svg = document.getElementById('mascot-mouth-svg');
    if (!anchor) { svg.innerHTML = ''; return; }
    svg.style.left = (anchor.mx * 100).toFixed(2) + '%';
    svg.style.top  = (anchor.my * 100).toFixed(2) + '%';
    const s = (anchor.scale || 1.0) * 0.92;
    svg.style.transform = `translate(-50%, -50%) scale(${s.toFixed(3)})`;

    const ink = '#5A251E', cavity = '#6E2226', tongue = '#F07A7A';
    const shapes = {
      CLOSED: `<path d="M -11,-1 Q 0,6 11,-1" fill="none" stroke="${ink}" stroke-width="3.2" stroke-linecap="round"/>`,
      AA: `<path d="M -14,-5 Q 0,-8 14,-5 Q 13,12 0,13 Q -13,12 -14,-5 Z" fill="${cavity}" stroke="${ink}" stroke-width="2.6" stroke-linejoin="round"/>
           <path d="M -11,-4 Q 0,-6 11,-4 L 10,-1 Q 0,-2 -10,-1 Z" fill="#FFFFFF"/>
           <ellipse cx="0" cy="7.5" rx="7.5" ry="4" fill="${tongue}"/>`,
      EE: `<path d="M -15,-3 Q 0,-5 15,-3 Q 13,7 0,8 Q -13,7 -15,-3 Z" fill="${cavity}" stroke="${ink}" stroke-width="2.5" stroke-linejoin="round"/>
           <path d="M -13,-2 Q 0,-3.5 13,-2 L 11,2.5 Q 0,3.5 -11,2.5 Z" fill="#FFFFFF"/>`,
      OH: `<ellipse cx="0" cy="2" rx="9" ry="10.5" fill="${cavity}" stroke="${ink}" stroke-width="2.6"/>
           <ellipse cx="0" cy="7" rx="5.5" ry="3.5" fill="${tongue}"/>`,
      OO: `<ellipse cx="0" cy="2" rx="6.2" ry="7.2" fill="${cavity}" stroke="${ink}" stroke-width="2.6"/>
           <ellipse cx="0" cy="5.2" rx="3.4" ry="2.2" fill="${tongue}"/>`,
      FV: `<path d="M -12,-2 Q 0,-4 12,-2 Q 11,4 0,4.5 Q -11,4 -12,-2 Z" fill="#FFFFFF" stroke="${ink}" stroke-width="2.4" stroke-linejoin="round"/>
           <path d="M -9,4.5 Q 0,7 9,4.5" fill="none" stroke="${ink}" stroke-width="2.2" stroke-linecap="round"/>`,
    };
    svg.innerHTML = shapes[shape] || shapes.CLOSED;
  }

  function starSVG(color, size, points = 8) {
    let d = '';
    const cx = size / 2, cy = size / 2;
    const rOut = size * 0.46, rIn = size * 0.22;
    for (let i = 0; i < points * 2; i++) {
      const ang = (i * Math.PI) / points - Math.PI / 2;
      const r = i % 2 === 0 ? rOut : rIn;
      d += (i === 0 ? 'M' : 'L') + (cx + Math.cos(ang) * r).toFixed(1) + ',' + (cy + Math.sin(ang) * r).toFixed(1);
    }
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><path d="${d}Z" fill="${color}" stroke="#181B26" stroke-width="2.5" stroke-linejoin="round"/></svg>`;
  }

  function renderDecorations(t, bgName) {
    const deco = document.getElementById('deco-layer');
    const isDark = bgName === 'dark_navy_grid';
    const stars = [
      { x: 632, y: 215, c: '#F44336', s: 48, spd: 14, p: 8 },
      { x: 636, y: 555, c: '#FFD648', s: 52, spd: -18, p: 7 },
      { x: 626, y: 785, c: isDark ? '#38B577' : '#2264D8', s: 44, spd: 20, p: 8 },
      { x: 26,  y: 310, c: isDark ? '#FFD648' : '#38B577', s: 36, spd: -12, p: 6 },
    ];
    let html = '';
    stars.forEach((st, idx) => {
      const rot = (t * st.spd + idx * 25) % 360;
      const bob = Math.sin(t * 2.4 + idx) * 6;
      html += `<div class="star-deco" style="left:${st.x}px;top:${(st.y + bob).toFixed(1)}px;transform:rotate(${rot.toFixed(1)}deg)">${starSVG(st.c, st.s, st.p)}</div>`;
    });
    deco.innerHTML = html;
  }

  function w_rating_stars(w, age) {
    const sc = springScale(age, 0.18);
    const starsTotal = w.stars || 5, filled = w.filled != null ? w.filled : 5;
    let starsHtml = '';
    for (let i = 0; i < starsTotal; i++) {
      const sAge = age - (0.15 + i * 0.12);
      const isLit = i < filled && sAge > 0;
      starsHtml += `<span style="display:inline-block;font-size:42px;color:${isLit ? '#FFD648' : '#E2DED3'};-webkit-text-stroke:2px #181B26;transform:scale(${Math.max(0.85, springScale(sAge, 0.16)).toFixed(3)});margin:0 4px;">★</span>`;
    }
    const badgeAge = age - 0.6;
    return `
      <div style="display:flex;flex-direction:column;align-items:center;padding-top:14px;transform:scale(${sc.toFixed(3)})">
        <div class="paper-card" style="width:450px;padding:20px 22px 22px;text-align:center;">
          <div style="background:#181B26;color:#FFFDF6;border-radius:12px;padding:28px 16px;font-size:32px;font-weight:800;margin-bottom:14px;">${w.card_title || 'LIPLNWZA v3.2'}</div>
          <div>${starsHtml}</div>
        </div>
        ${badgeAge > 0 ? `<div style="margin-top:14px;background:#FFFDF6;border:3px solid #181B26;border-radius:999px;padding:7px 22px;font-size:23px;font-weight:800;box-shadow:4px 5px 0 #181B26;transform:scale(${springScale(badgeAge, 0.18).toFixed(3)});"><span style="color:#38B577;margin-right:8px;">●</span>${w.badge || 'ภาพสวย ขยับลื่นทุกบีต'}</div>` : ''}
      </div>`;
  }

  function w_chat_bubbles(w, age) {
    const sc = springScale(age, 0.18);
    const msgs = w.messages || ['คำสั่งซ้ำๆ', 'ไม่สุภาพ'];
    let rows = '';
    msgs.forEach((m, i) => {
      const mAge = age - (0.12 + i * 0.20);
      if (mAge <= 0) return;
      const col = m.color || '#E5483B';
      const txt = typeof m === 'string' ? m : m.text;
      rows += `<div style="background:${col};color:#FFFDF6;border:3px solid #181B26;border-radius:14px;padding:10px 16px;margin-bottom:10px;font-size:22px;font-weight:800;box-shadow:3px 4px 0 #181B26;transform:scale(${springScale(mAge, 0.16).toFixed(3)});transform-origin:left center;">${txt}</div>`;
    });
    const stampAge = age - (0.22 + msgs.length * 0.20);
    return `
      <div style="display:flex;justify-content:center;padding-top:10px;transform:scale(${sc.toFixed(3)})">
        <div class="paper-card" style="width:490px;overflow:hidden;">
          <div style="background:#E5483B;color:#FFFDF6;padding:10px 18px;border-bottom:3.5px solid #181B26;display:flex;align-items:center;justify-content:space-between;font-size:21px;font-weight:800;">
            <span>● ● ●</span><span>${w.header || 'Chat Window'}</span><span>×</span>
          </div>
          <div style="padding:16px 18px 64px;min-height:260px;background:#FFFDF6;position:relative;">
            ${rows}
            ${w.stamp && stampAge > 0 ? `<div style="position:absolute;right:16px;bottom:14px;background:#181B26;color:#FFD648;border:3px solid #FFD648;border-radius:12px;padding:6px 16px;font-size:21px;font-weight:900;transform:scale(${springScale(stampAge, 0.16).toFixed(3)}) rotate(-3deg);">${w.stamp}</div>` : ''}
          </div>
        </div>
      </div>`;
  }

  function w_calendar_flip(w, age) {
    const sc = springScale(age, 0.18);
    const flipAt = w.flip_at || 0.65;
    const flipped = age >= flipAt;
    const cardTilt = flipped ? Math.max(0, 1 - (age - flipAt) / 0.22) * -14 : 0;
    const month = flipped ? (w.after_month || 'อายุ 40') : (w.before_month || 'อายุ 30');
    const num = flipped ? (w.after_num || '40') : (w.before_num || '30');
    const pillAge = age - (flipAt + 0.14);
    return `
      <div style="display:flex;flex-direction:column;align-items:center;padding-top:10px;transform:scale(${sc.toFixed(3)})">
        <div class="paper-card" style="width:300px;overflow:hidden;transform:rotate(${(cardTilt - 2).toFixed(1)}deg);">
          <div style="background:${flipped ? '#E5483B' : '#2264D8'};color:#FFFDF6;padding:14px;text-align:center;font-size:30px;font-weight:900;border-bottom:3.5px solid #181B26;">${month}</div>
          <div style="padding:28px 18px;text-align:center;font-size:96px;font-weight:900;line-height:1;background:#FFFDF6;">${num}</div>
        </div>
        ${w.caption && pillAge > 0 ? `<div style="margin-top:16px;background:#FFD648;border:3px solid #181B26;border-radius:14px;padding:8px 22px;font-size:24px;font-weight:900;box-shadow:4px 5px 0 #181B26;transform:scale(${springScale(pillAge, 0.16).toFixed(3)});">${w.caption}</div>` : ''}
      </div>`;
  }

  function w_checklist_ticks(w, age) {
    const items = w.items || ['ข้อที่ 1', 'ข้อที่ 2', 'ข้อที่ 3'];
    let html = '<div style="display:flex;flex-direction:column;align-items:center;gap:16px;padding:16px 36px 0;">';
    items.forEach((it, i) => {
      const iAge = age - (0.10 + i * 0.22);
      if (iAge <= 0) return;
      const tickAge = iAge - 0.16;
      html += `
        <div class="paper-card" style="width:100%;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;transform:scale(${springScale(iAge, 0.16).toFixed(3)});">
          <div style="display:flex;align-items:center;gap:14px;">
            <span style="background:${PALETTE[i % 4].bg};color:${PALETTE[i % 4].fg};border:2.5px solid #181B26;border-radius:10px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-size:21px;font-weight:900;">${i + 1}</span>
            <span style="font-size:25px;font-weight:800;">${it}</span>
          </div>
          <div style="width:40px;height:40px;border-radius:50%;background:${tickAge > 0 ? '#38B577' : '#EEE'};color:#FFFDF6;border:3px solid #181B26;display:flex;align-items:center;justify-content:center;font-size:23px;font-weight:900;transform:scale(${Math.max(0.8, springScale(tickAge, 0.14)).toFixed(3)});">✓</div>
        </div>`;
    });
    return html + '</div>';
  }

  function w_cycle_diagram(w, age) {
    const nodes = w.nodes || ['1. รับเสียง', '2. จัดบีต', '3. ตรวจ QA', '4. เรนเดอร์'];
    const pos = [{ x: 265, y: 34 }, { x: 440, y: 168 }, { x: 265, y: 300 }, { x: 90, y: 168 }];
    const rot = (age * 35) % 360;
    let nodesHtml = '';
    nodes.slice(0, 4).forEach((lbl, i) => {
      const nAge = age - (0.10 + i * 0.22);
      if (nAge <= 0) return;
      const col = PALETTE[i % 4];
      nodesHtml += `<div style="position:absolute;left:${pos[i].x}px;top:${pos[i].y}px;transform:translate(-50%,-50%) scale(${springScale(nAge, 0.16).toFixed(3)});background:${col.bg};color:${col.fg};border:3px solid #181B26;border-radius:999px;padding:10px 20px;font-size:21px;font-weight:900;white-space:nowrap;box-shadow:4px 5px 0 #181B26;">${lbl}</div>`;
    });
    return `<div style="position:relative;width:540px;height:350px;margin:10px auto 0;">
      <svg width="540" height="350" viewBox="0 0 540 350" style="position:absolute;left:0;top:0;">
        <circle cx="265" cy="168" r="132" fill="none" stroke="#181B26" stroke-width="5" stroke-dasharray="16 12" transform="rotate(${rot.toFixed(1)} 265 168)"/>
      </svg>${nodesHtml}</div>`;
  }

  function w_score_grid(w, age) {
    const sc = springScale(age, 0.18);
    const cols = w.cols || 5, rows = w.rows || 3, hitCount = w.hits || 12;
    let cells = '';
    for (let i = 0; i < cols * rows; i++) {
      const isHit = i < hitCount;
      const cAge = age - (0.12 + i * 0.05);
      cells += `<div style="width:62px;height:62px;border-radius:12px;background:${isHit ? '#2264D8' : '#CBD5E1'};border:3px solid #181B26;display:flex;align-items:center;justify-content:center;font-size:30px;font-weight:900;color:#FFD648;">
        ${(isHit && cAge > 0.10) ? `<span style="transform:scale(${springScale(cAge - 0.10, 0.14).toFixed(3)});display:inline-block;">✓</span>` : ''}
      </div>`;
    }
    return `<div style="display:flex;flex-direction:column;align-items:center;padding-top:10px;transform:scale(${sc.toFixed(3)})">
      <div class="paper-card" style="padding:18px 24px;">
        <div style="font-size:23px;font-weight:900;text-align:center;margin-bottom:12px;">${w.title || 'ผลทดสอบ'}</div>
        <div style="display:grid;grid-template-columns:repeat(${cols},62px);gap:10px;">${cells}</div>
      </div></div>`;
  }

  function w_waveform_notes(w, age) {
    const sc = springScale(age, 0.18);
    let bars = '';
    for (let i = 0; i < 24; i++) {
      const h = 16 + Math.abs(Math.sin(age * 7.5 + i * 0.55)) * 86;
      bars += `<div style="width:12px;height:${h.toFixed(1)}px;background:${i % 5 === 0 ? '#E5483B' : '#2264D8'};border-radius:6px;"></div>`;
    }
    return `<div style="display:flex;flex-direction:column;align-items:center;padding-top:18px;transform:scale(${sc.toFixed(3)})">
      <div class="paper-card" style="width:520px;padding:20px 26px;text-align:center;">
        <div style="font-size:32px;margin-bottom:6px;transform:translateY(${(Math.sin(age * 6) * 9).toFixed(1)}px);">♪ &nbsp; ♫ &nbsp; ♪</div>
        <div style="height:108px;display:flex;align-items:center;justify-content:center;gap:6px;">${bars}</div>
        <div style="margin-top:12px;background:#181B26;color:#FFFDF6;display:inline-block;padding:6px 18px;border-radius:999px;font-size:20px;font-weight:800;">${w.label || 'VO + BGM Ducking'}</div>
      </div></div>`;
  }

  function w_terminal_code(w, age) {
    const sc = springScale(age, 0.18);
    const lines = w.lines || ['$ render_v3', '> ready ✓'];
    let totalChars = Math.floor(Math.max(0, age - 0.1) * 44);
    let out = '';
    lines.forEach((ln) => {
      const take = clamp(totalChars, 0, ln.length);
      totalChars -= ln.length;
      if (take > 0) out += `<div style="margin-bottom:8px;">${ln.slice(0, take)}</div>`;
    });
    return `<div style="display:flex;justify-content:center;padding-top:18px;transform:scale(${sc.toFixed(3)})">
      <div style="width:540px;background:#151822;color:#B7F34A;border:3.5px solid #181B26;border-radius:16px;box-shadow:7px 8px 0 #181B26;overflow:hidden;font-family:monospace;">
        <div style="background:#2A3142;padding:10px 16px;color:#FFFDF6;font-size:18px;display:flex;gap:8px;align-items:center;">
          <span style="color:#F44336;">●</span><span style="color:#FFD648;">●</span><span style="color:#38B577;">●</span>
          <span style="margin-left:8px;font-family:'NotoThai',sans-serif;">${w.title || 'Terminal'}</span>
        </div>
        <div style="padding:18px 20px;min-height:175px;font-size:21px;line-height:1.45;">${out}<span style="color:#FFD648;">${Math.floor(age*4)%2===0?'█':''}</span></div>
      </div></div>`;
  }

  function w_screenshot_frame(w, age) {
    const sc = springScale(age, 0.18);
    const quoteAge = age - 0.30;
    return `<div style="display:flex;flex-direction:column;align-items:center;padding-top:10px;transform:scale(${sc.toFixed(3)})">
      <div class="paper-card" style="width:540px;padding:20px 24px;transform:rotate(-1deg);">
        <div style="font-size:17px;color:#64748B;margin-bottom:5px;">${w.kicker || 'Announcement'}</div>
        <div style="font-size:28px;font-weight:900;line-height:1.25;margin-bottom:10px;">${w.headline || 'หัวข้อข่าว'}</div>
        <div style="background:#181B26;color:#FFFDF6;display:inline-block;padding:4px 14px;border-radius:8px;font-size:17px;">${w.source || 'Source'}</div>
      </div>
      ${w.quote && quoteAge > 0 ? `<div class="paper-card" style="width:500px;margin-top:14px;padding:14px 20px;background:#FFF8D6;transform:scale(${springScale(quoteAge, 0.18).toFixed(3)}) rotate(1deg);font-size:23px;font-weight:800;line-height:1.35;">“${w.quote}”</div>` : ''}
    </div>`;
  }

  function w_media_clip_frame(w, age) {
    const sc = springScale(age, 0.18);
    const tvSrc = (window.__LEMO_TV_FRAME__) || '';
    const inner = tvSrc
      ? `<img src="${tvSrc}" style="width:100%;height:100%;object-fit:cover;display:block;"/>`
      : `<div style="width:100%;height:100%;background:#0F172A;color:#FFD648;display:flex;align-items:center;justify-content:center;font-size:24px;">LEMO TV SLOT</div>`;
    return `<div style="display:flex;flex-direction:column;align-items:center;padding-top:4px;transform:scale(${sc.toFixed(3)})">
      <div class="paper-card" style="width:550px;padding:12px;background:#FFFDF6;transform:rotate(-0.6deg);">
        <div style="display:flex;align-items:center;justify-content:space-between;background:#FFE9A8;border:2.5px solid #181B26;border-radius:10px 10px 0 0;padding:7px 14px;margin-bottom:8px;">
          <div style="display:flex;gap:7px;">
            <span style="width:13px;height:13px;border-radius:50%;background:#F44336;border:2px solid #181B26;display:inline-block;"></span>
            <span style="width:13px;height:13px;border-radius:50%;background:#FFD648;border:2px solid #181B26;display:inline-block;"></span>
            <span style="width:13px;height:13px;border-radius:50%;background:#38B577;border:2px solid #181B26;display:inline-block;"></span>
          </div>
          <div style="font-size:19px;font-weight:900;">${w.channel_label || 'LEMO-OPUSCAR CLIP'}</div>
          <div style="background:#E5483B;color:#FFFDF6;padding:2px 9px;border-radius:999px;font-size:14px;font-weight:800;">● LIVE</div>
        </div>
        <div style="width:518px;height:310px;border:3px solid #181B26;border-radius:10px;overflow:hidden;background:#0F172A;">${inner}</div>
      </div>
      ${w.credit ? `<div style="margin-top:10px;background:#181B26;color:#FFFDF6;padding:6px 18px;border-radius:999px;font-size:19px;font-weight:800;">${w.credit}</div>` : ''}
    </div>`;
  }

  function w_cta_comment_box(w, age) {
    const sc = springScale(age, 0.18);
    const kw = w.keyword || 'คอมเมนต์';
    const typed = kw.slice(0, Math.min(kw.length, Math.floor(Math.max(0, age - 0.18) * 10)));
    const sent = age > 0.72;
    const raySc = sent ? springScale(age - 0.72, 0.2) : 0;
    return `<div style="display:flex;flex-direction:column;align-items:center;padding-top:26px;position:relative;transform:scale(${sc.toFixed(3)})">
      ${sent ? `<div style="position:absolute;top:-6px;font-size:58px;font-weight:900;background:#E5483B;color:#FFFDF6;padding:8px 32px;border:4px solid #181B26;border-radius:18px;box-shadow:6px 7px 0 #181B26;transform:scale(${raySc.toFixed(3)}) rotate(-4deg);z-index:2;">${kw}</div>` : ''}
      <div class="paper-card" style="width:500px;margin-top:100px;padding:14px 22px;display:flex;align-items:center;justify-content:space-between;border-radius:999px;">
        <span style="font-size:26px;font-weight:800;color:${typed ? '#181B26' : '#94A3B8'};">${typed || 'พิมพ์คอมเมนต์...'}<span style="opacity:${Math.floor(age*4)%2};">|</span></span>
        <span style="width:44px;height:44px;border-radius:50%;background:#2264D8;color:#FFFDF6;border:3px solid #181B26;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:900;">↑</span>
      </div>
      ${sent ? `<div style="margin-top:16px;background:#38B577;color:#181B26;border:3px solid #181B26;border-radius:14px;padding:8px 24px;font-size:23px;font-weight:900;box-shadow:4px 5px 0 #181B26;transform:scale(${raySc.toFixed(3)});">${w.sublabel || 'คอมเมนต์บอกกันหน่อย!'}</div>` : ''}
    </div>`;
  }

  function w_vote_buttons(w, age) {
    const sc = springScale(age, 0.18);
    const popR = springScale(age - 0.22, 0.18);
    return `<div style="display:flex;flex-direction:column;align-items:center;padding-top:40px;">
      <div style="display:flex;gap:24px;margin-bottom:26px;">
        <div style="background:#38B577;color:#FFFDF6;border:3.5px solid #181B26;border-radius:18px;padding:18px 42px;font-size:34px;font-weight:900;box-shadow:6px 7px 0 #181B26;transform:scale(${sc.toFixed(3)}) rotate(-2deg);">${w.left || 'ใช่เลย'}</div>
        <div style="background:#E5483B;color:#FFFDF6;border:3.5px solid #181B26;border-radius:18px;padding:18px 42px;font-size:34px;font-weight:900;box-shadow:6px 7px 0 #181B26;transform:scale(${popR.toFixed(3)}) rotate(2deg);">${w.right || 'ไม่ใช่'}</div>
      </div>
      ${w.prompt ? `<div class="paper-card" style="padding:12px 26px;font-size:23px;font-weight:800;">💬 ${w.prompt}</div>` : ''}
    </div>`;
  }

  const WIDGET_MAP = {
    rating_stars: w_rating_stars,
    chat_bubbles: w_chat_bubbles,
    calendar_flip: w_calendar_flip,
    checklist_ticks: w_checklist_ticks,
    cycle_diagram: w_cycle_diagram,
    score_grid: w_score_grid,
    waveform_notes: w_waveform_notes,
    terminal_code: w_terminal_code,
    screenshot_frame: w_screenshot_frame,
    media_clip_frame: w_media_clip_frame,
    cta_comment_box: w_cta_comment_box,
    vote_buttons: w_vote_buttons,
  };

  function renderWords(t) {
    const layer = document.getElementById('chips-layer');
    const chunks = window.__SPEC__.word_rows || [];
    const active = chunks.find(r => t >= r.start && t <= r.end);
    if (!active) { layer.innerHTML = ''; layer.style.transform = 'scale(1)'; return; }
    let html = '';
    active.words.forEach((w, idx) => {
      if (t < w.start) return;
      const age = t - w.start;
      const sc = springScale(age, 0.13);
      const col = (w.role && ROLE_COLORS[w.role]) ? ROLE_COLORS[w.role] : PALETTE[idx % PALETTE.length];
      const rot = idx % 2 === 0 ? -1.6 : 1.6;
      html += `<div class="word-chip" style="background:${col.bg};color:${col.fg};transform:scale(${sc.toFixed(3)}) rotate(${rot}deg);">${w.text}</div>`;
    });
    layer.innerHTML = html;
    // Overflow auto-fit guard: guarantee chips NEVER exceed 634px safe width!
    layer.style.transform = 'scale(1)';
    const wActual = layer.scrollWidth;
    if (wActual > 634) {
      const ratio = 634 / wActual;
      layer.style.transform = `scale(${ratio.toFixed(3)})`;
    }
  }


  function applyCameraAndTransition(beat, age, beatDur) {
    const rig = document.getElementById('camera-rig');
    const curt = document.getElementById('trans-curtain');
    if (!rig) return;
    const p = clamp(age / Math.max(0.2, beatDur), 0, 1);
    const cam = beat.camera || 'push_in';
    let sc = 1.0, tx = 0, ty = 0;

    if (cam === 'push_in') {
      sc = 1.00 + 0.045 * p;
      ty = -6 * p;
    } else if (cam === 'pull_out') {
      sc = 1.05 - 0.05 * p;
      ty = -6 * (1 - p);
    } else if (cam === 'focus_tv') {
      const ease = 1 - Math.pow(1 - Math.min(1, age / 0.55), 3);
      sc = 1.00 + 0.065 * ease;
      ty = 18 * ease;
    } else if (cam === 'punch_in') {
      const k = Math.min(1, age / 0.24);
      sc = 1.08 - 0.05 * (1 - Math.pow(1 - k, 3)) + 0.015 * p;
    }

    // 4 Premium Paper-Cut Transitions over first 0.26s of each beat
    const tr = beat.transition || 'paper_slide';
    curt.style.display = 'none';
    if (age < 0.26 && beat.start > 0.01) {
      const tp = age / 0.26;
      const easeOut = 1 - Math.pow(1 - tp, 3);
      if (tr === 'paper_slide') {
        const shift = (1 - easeOut) * 180;
        tx += shift;
        curt.style.display = 'block';
        curt.style.background = 'linear-gradient(90deg, rgba(24,27,38,0.22), transparent)';
        curt.style.transform = `translateX(${(easeOut * 720).toFixed(1)}px)`;
        curt.style.opacity = (1 - easeOut).toFixed(2);
      } else if (tr === 'whip_zoom') {
        sc *= (1.16 - 0.16 * easeOut);
      } else if (tr === 'page_peel') {
        curt.style.display = 'block';
        curt.style.background = '#FFF6E8';
        curt.style.borderRight = '6px solid #181B26';
        curt.style.boxShadow = '10px 0 24px rgba(24,27,38,0.32)';
        curt.style.transform = `translateX(${(-easeOut * 780).toFixed(1)}px) skewX(-6deg)`;
        curt.style.opacity = '1';
      } else if (tr === 'ink_flash') {
        if (age < 0.09) {
          curt.style.display = 'block';
          curt.style.background = '#FFD648';
          curt.style.transform = 'none';
          curt.style.opacity = (0.45 * (1 - age / 0.09)).toFixed(2);
        }
      }
    }
    rig.style.transform = `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px) scale(${sc.toFixed(4)})`;
  }

  // Fast IPC signature: pass ONLY tiny strings (poseName, mouthShape, sidekickName) — zero Base64 IPC bloat!
  window.renderAtTime = function(t, poseName, mouthShape, sidekickName, lemoTvDataUri) {
    window.__LEMO_TV_FRAME__ = lemoTvDataUri || '';
    const assets = window.__ASSETS__ || { mascots: {}, anchors: {}, props: {} };
    const spec = window.__SPEC__;
    const beats = spec.beats || [];
    const beat = beats.find(b => t >= b.start && t < b.end) || beats[beats.length - 1];
    const age = Math.max(0, t - beat.start);

    const stage = document.getElementById('stage');
    const bgName = beat.bg || 'cream_graph';
    stage.className = 'bg-' + bgName;

    renderDecorations(t, bgName);

    const rLayer = document.getElementById('ribbon-layer');
    if (beat.ribbon) {
      const rCol = RIBBON_COLORS[beat.ribbon_color || 'red'] || RIBBON_COLORS.red;
      rLayer.innerHTML = `<div class="torn-ribbon" style="background:${rCol.bg};color:${rCol.fg};transform:scale(${springScale(age, 0.16).toFixed(3)}) rotate(-1.2deg);">${beat.ribbon}</div>`;
    } else {
      rLayer.innerHTML = '';
    }

    const wStage = document.getElementById('widget-stage');
    const wObj = beat.widget;
    wStage.innerHTML = (wObj && WIDGET_MAP[wObj.type]) ? WIDGET_MAP[wObj.type](wObj, age) : '';

    // Preloaded Mascot + SVG Mouth
    const mLayer = document.getElementById('mascot-layer');
    const mImg = document.getElementById('mascot-img');
    const pKey = poseName || 'wave';
    if (pKey !== lastPose && assets.mascots[pKey]) {
      mImg.src = assets.mascots[pKey];
      lastPose = pKey;
    }
    const bobY = Math.sin(t * 2.8) * 2.2;
    const sway = Math.sin(t * 1.6) * 0.6;
    mLayer.style.transform = `translateY(${bobY.toFixed(1)}px) rotate(${sway.toFixed(2)}deg)`;
    renderProceduralMouth(mouthShape || 'CLOSED', assets.anchors[pKey] || assets.anchors.wave);

    // Preloaded Sidekick Prop
    const skImg = document.getElementById('sidekick-img');
    if (sidekickName && assets.props[sidekickName]) {
      if (sidekickName !== lastSidekick) {
        skImg.src = assets.props[sidekickName];
        lastSidekick = sidekickName;
      }
      skImg.style.display = 'block';
      const skSc = springScale(age - 0.08, 0.20);
      const skBob = Math.sin(t * 3.8 + 1.2) * 6;
      skImg.style.transform = `translateY(${skBob.toFixed(1)}px) scale(${skSc.toFixed(3)}) rotate(${(Math.sin(t * 2.5) * 4).toFixed(1)}deg)`;
    } else {
      skImg.style.display = 'none';
      lastSidekick = '';
    }

    applyCameraAndTransition(beat, age, (beat.end - beat.start));
    renderWords(t);
  };
})();
