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
    const tvSrc = (window.__LEMO_TV_FRAME__) || '';
    if (w.fit === 'full_bleed') {
      const innerFb = tvSrc
        ? `<img src="${tvSrc}" style="width:100%;height:100%;object-fit:cover;display:block;"/>`
        : `<div style="width:100%;height:100%;background:#0F172A;color:#FFD648;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:800;">LEMO FULL-BLEED SLOT</div>`;
      const badge = w.channel_label
        ? `<div style="position:absolute;top:18px;left:22px;background:rgba(15,23,42,0.78);color:#F8FAFC;border:1.5px solid rgba(255,255,255,0.2);border-radius:999px;padding:6px 16px;font-size:16px;font-weight:700;backdrop-filter:blur(6px);">${w.channel_label}</div>`
        : '';
      const credit = w.credit
        ? `<div style="position:absolute;top:18px;right:22px;background:rgba(15,23,42,0.78);color:#CBD5E1;border-radius:999px;padding:6px 14px;font-size:15px;font-weight:700;">${w.credit}</div>`
        : '';
      return `<div style="position:relative;width:100%;height:100%;overflow:hidden;">${innerFb}${badge}${credit}</div>`;
    }
    const sc = springScale(age, 0.18);
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

  function w_custom_html(w, age, beatDur) {
    const p = clamp(age / Math.max(0.25, beatDur || 1.0), 0, 1);
    const sc = w.no_pop ? 1.0 : springScale(age, 0.18);
    const cssTag = w.css ? `<style>${w.css}</style>` : '';
    let html = String(w.html || '');
    // Dynamic value substitution for smooth 24/30fps data-driven animation
    html = html
      .replaceAll('{{AGE}}', age.toFixed(3))
      .replaceAll('{{PROGRESS}}', p.toFixed(4))
      .replaceAll('{{PCT}}', (p * 100).toFixed(1));
    return `${cssTag}<div class="v35-custom-wrap" style="--age:${age.toFixed(3)};--progress:${p.toFixed(4)};width:100%;height:100%;transform:scale(${sc.toFixed(3)});transform-origin:center center;">${html}</div>`;
  }

  // === v3.6 Built-in Living Comic Widgets ===
  function w_evidence_card(w, age) {
    const sc = springScale(age, 0.16);
    const items = w.items || [];
    const badgeColor = w.badge_color || '#2264D8';
    const rowsHtml = items.map((it, i) => {
      const at = (typeof it === 'object' && it.at != null) ? it.at : (0.18 + i * 0.45);
      const txt = (typeof it === 'object') ? it.text : String(it);
      const val = (typeof it === 'object' && it.value) ? it.value : '';
      const hl = (typeof it === 'object' && it.highlight) ? it.highlight : '';
      return `<div data-at="${at}" data-anim="slide-left" style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-radius:12px;border:2.5px solid #181B26;background:${hl || '#FFFDF6'};box-shadow:3px 4px 0 #181B26;font-size:23px;font-weight:800;">
        <span>${txt}</span>${val ? `<span style="color:#E5483B;font-weight:900;">${val}</span>` : ''}
      </div>`;
    }).join('');
    const stampHtml = w.stamp ? `<div data-at="${w.stamp_at != null ? w.stamp_at : 1.2}" data-anim="slam" data-rot="-6" class="comic-stamp" style="right:18px;bottom:14px;background:${w.stamp_bg || '#E5483B'};color:#FFFDF6;font-size:28px;">${w.stamp}</div>` : '';
    return `<div class="paper-card" style="width:100%;height:100%;padding:22px 24px;display:flex;flex-direction:column;gap:12px;transform:scale(${sc.toFixed(3)});">
      <div class="tape-strip" style="top:-12px;left:50%;transform:translateX(-50%) rotate(-2deg);"></div>
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:3px dashed #181B26;padding-bottom:10px;">
        <span style="background:${badgeColor};color:#FFFDF6;border:2.5px solid #181B26;border-radius:10px;padding:4px 14px;font-size:20px;font-weight:900;">${w.badge || 'หลักฐานตัวเลข'}</span>
        ${w.kicker ? `<span style="font-size:17px;font-weight:800;color:#475569;">${w.kicker}</span>` : ''}
      </div>
      <div style="display:flex;flex-direction:column;gap:11px;flex:1;justify-content:center;">${rowsHtml}</div>
      ${stampHtml}
    </div>`;
  }

  function w_live_calc_receipt(w, age) {
    const sc = springScale(age, 0.16);
    const lines = w.lines || [];
    const rows = lines.map((ln, i) => {
      const at = ln.at != null ? ln.at : (0.15 + i * 0.45);
      return `<div data-at="${at}" data-anim="slide-up" style="display:flex;justify-content:space-between;align-items:center;padding:9px 14px;border-bottom:2px dashed rgba(24,27,38,0.22);font-size:23px;font-weight:800;">
        <span style="color:#334155;">${ln.label}</span>
        <span style="color:${ln.color || '#181B26'};font-weight:900;font-size:25px;">${ln.value}</span>
      </div>`;
    }).join('');
    const tot = w.total || {};
    const totAt = tot.at != null ? tot.at : 1.4;
    return `<div class="comic-receipt" style="width:100%;height:100%;padding:20px 24px;display:flex;flex-direction:column;justify-content:space-between;transform:scale(${sc.toFixed(3)});">
      <div style="display:flex;justify-content:space-between;align-items:center;background:#181B26;color:#FFD648;padding:9px 16px;border-radius:10px;font-size:21px;font-weight:900;">
        <span>🧾 ${w.title || 'บิลจ่ายจริง'}</span>
        <span style="font-size:16px;color:#FFFDF6;">${w.subtitle || 'ตัวอย่างสมมติ'}</span>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:4px;margin:8px 0;">${rows}</div>
      ${tot.label ? `<div data-at="${totAt}" data-anim="slam" data-rot="-1.5" style="background:${tot.bg || '#E5483B'};color:${tot.fg || '#FFFDF6'};border:3.5px solid #181B26;border-radius:14px;padding:12px 18px;box-shadow:5px 6px 0 #181B26;display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:23px;font-weight:800;">${tot.label}</span>
        <span data-at="${totAt}" data-anim="count" data-from="${tot.from || 0}" data-to="${tot.to || 0}" data-dur="0.55" data-suffix="${tot.suffix || ' บ.'}" style="font-size:38px;font-weight:900;">${tot.value || ''}</span>
      </div>` : ''}
    </div>`;
  }

  function w_bar_compare(w, age) {
    const sc = springScale(age, 0.16);
    const bars = w.bars || [];
    const rows = bars.map((b, i) => {
      const at = b.at != null ? b.at : (0.18 + i * 0.42);
      return `<div data-at="${at}" data-anim="slide-up" style="display:flex;flex-direction:column;gap:6px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:22px;font-weight:900;">
          <span>${b.label}</span>
          <span style="color:${b.color || '#E5483B'};">${b.value} ${b.tag ? `<span style="background:${b.color || '#E5483B'};color:#FFFDF6;font-size:15px;padding:2px 9px;border-radius:999px;border:2px solid #181B26;margin-left:6px;">${b.tag}</span>` : ''}</span>
        </div>
        <div style="width:100%;height:34px;background:#E2E8F0;border:3px solid #181B26;border-radius:10px;overflow:hidden;box-shadow:3px 4px 0 #181B26;">
          <div data-at="${at + 0.08}" data-anim="bar" data-pct="${b.pct || 50}" data-dur="0.48" style="height:100%;width:0%;background:${b.color || '#2264D8'};border-right:3px solid #181B26;"></div>
        </div>
      </div>`;
    }).join('');
    return `<div class="paper-card" style="width:100%;height:100%;padding:22px 26px;display:flex;flex-direction:column;justify-content:space-between;transform:scale(${sc.toFixed(3)});">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:24px;font-weight:900;">${w.title || 'เทียบสัดส่วนภาระ'}</span>
        ${w.kicker ? `<span style="background:#FFD648;border:2.5px solid #181B26;border-radius:999px;padding:3px 12px;font-size:16px;font-weight:900;">${w.kicker}</span>` : ''}
      </div>
      <div style="display:flex;flex-direction:column;gap:18px;flex:1;justify-content:center;">${rows}</div>
      ${w.footer ? `<div style="font-size:18px;font-weight:800;color:#475569;text-align:center;">${w.footer}</div>` : ''}
    </div>`;
  }

  const WIDGET_MAP = {
    custom_html: w_custom_html,
    evidence_card: w_evidence_card,
    live_calc_receipt: w_live_calc_receipt,
    bar_compare: w_bar_compare,
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

  // === v3.6 Deterministic Sub-Beat Choreography Engine (30fps-ready) ===
  function formatGroupedInt(val) {
    return Math.round(val).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function applySubBeatAnimations(root, age) {
    if (!root) return;
    const nodes = root.querySelectorAll('[data-at], [data-anim]');
    nodes.forEach(el => {
      const at = parseFloat(el.getAttribute('data-at') || '0');
      const untilAttr = el.getAttribute('data-until');
      const until = untilAttr !== null ? parseFloat(untilAttr) : Infinity;
      const anim = el.getAttribute('data-anim') || 'pop';
      const dur = parseFloat(el.getAttribute('data-dur') || '0.20');
      const baseRot = parseFloat(el.getAttribute('data-rot') || '0');

      if (age < at || age >= until) {
        if (anim === 'bar') {
          el.style.width = '0%';
        } else if (anim === 'strike') {
          el.style.width = '0%';
          el.style.opacity = '0';
        } else if (anim === 'count') {
          const fr = parseFloat(el.getAttribute('data-from') || '0');
          const pre = el.getAttribute('data-prefix') || '';
          const suf = el.getAttribute('data-suffix') || '';
          if (age < at) {
            el.style.opacity = '0';
            el.textContent = pre + formatGroupedInt(fr) + suf;
          } else {
            el.style.opacity = '0';
          }
        } else {
          el.style.opacity = '0';
          el.style.visibility = 'hidden';
        }
        return;
      }

      const local = Math.max(0, age - at);
      el.style.visibility = 'visible';

      if (anim === 'pop') {
        const sc = springScale(local, dur || 0.18);
        el.style.opacity = clamp(local / 0.08, 0, 1).toFixed(3);
        el.style.transform = `scale(${sc.toFixed(3)}) rotate(${baseRot}deg)`;
      } else if (anim === 'slam') {
        const p = clamp(local / (dur || 0.15), 0, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        const sc = 2.35 - 1.35 * ease;
        const rot = baseRot + (1 - ease) * -14;
        el.style.opacity = clamp(p * 2.5, 0, 1).toFixed(3);
        el.style.transform = `scale(${sc.toFixed(3)}) rotate(${rot.toFixed(2)}deg)`;
      } else if (anim === 'slide-up') {
        const p = clamp(local / (dur || 0.22), 0, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        el.style.opacity = ease.toFixed(3);
        el.style.transform = `translateY(${((1 - ease) * 34).toFixed(1)}px) rotate(${baseRot}deg)`;
      } else if (anim === 'slide-left') {
        const p = clamp(local / (dur || 0.22), 0, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        el.style.opacity = ease.toFixed(3);
        el.style.transform = `translateX(${((1 - ease) * 48).toFixed(1)}px) rotate(${baseRot}deg)`;
      } else if (anim === 'slide-right') {
        const p = clamp(local / (dur || 0.22), 0, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        el.style.opacity = ease.toFixed(3);
        el.style.transform = `translateX(${(-(1 - ease) * 48).toFixed(1)}px) rotate(${baseRot}deg)`;
      } else if (anim === 'count') {
        const fr = parseFloat(el.getAttribute('data-from') || '0');
        const to = parseFloat(el.getAttribute('data-to') || '0');
        const cDur = parseFloat(el.getAttribute('data-dur') || '0.55');
        const pre = el.getAttribute('data-prefix') || '';
        const suf = el.getAttribute('data-suffix') || '';
        const p = clamp(local / Math.max(0.08, cDur), 0, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        const val = fr + (to - fr) * ease;
        el.style.opacity = '1';
        el.textContent = pre + formatGroupedInt(val) + suf;
      } else if (anim === 'bar') {
        const pct = parseFloat(el.getAttribute('data-pct') || '100');
        const bDur = parseFloat(el.getAttribute('data-dur') || '0.45');
        const p = clamp(local / Math.max(0.08, bDur), 0, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        el.style.opacity = '1';
        el.style.width = (pct * ease).toFixed(2) + '%';
      } else if (anim === 'strike') {
        const sDur = parseFloat(el.getAttribute('data-dur') || '0.22');
        const p = clamp(local / Math.max(0.06, sDur), 0, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        el.style.opacity = '1';
        el.style.width = (100 * ease).toFixed(1) + '%';
      } else if (anim === 'type') {
        const full = el.getAttribute('data-text') || '';
        const cps = parseFloat(el.getAttribute('data-cps') || '18');
        const nChars = Math.min(full.length, Math.floor(local * cps));
        const caret = (nChars < full.length || Math.floor(local * 4) % 2 === 0) ? '|' : '';
        el.style.opacity = '1';
        el.textContent = full.slice(0, nChars) + caret;
      } else if (anim === 'fade') {
        const p = clamp(local / (dur || 0.2), 0, 1);
        el.style.opacity = p.toFixed(3);
      }
    });
  }

  // === v3.6 Built-in Comic FX Overlay Renderer ===
  // Oversized centered square SVG (r=1600, 3200x3200) so rotating 0..360deg around (cx,cy)
  // NEVER exposes clipped SVG box edges or leaves bottom corners uncovered (max corner dist ~923px).
  function sunburstSVG(color, rays = 16, r = 1600) {
    let paths = '';
    const size = r * 2;
    for (let i = 0; i < rays; i++) {
      const a1 = (i * 2 * Math.PI) / rays;
      const a2 = ((i + 0.48) * 2 * Math.PI) / rays;
      const x1 = (Math.cos(a1) * r).toFixed(1);
      const y1 = (Math.sin(a1) * r).toFixed(1);
      const x2 = (Math.cos(a2) * r).toFixed(1);
      const y2 = (Math.sin(a2) * r).toFixed(1);
      paths += `<polygon points="0,0 ${x1},${y1} ${x2},${y2}" fill="${color}"/>`;
    }
    return `<svg width="${size}" height="${size}" viewBox="${-r} ${-r} ${size} ${size}" style="display:block;overflow:visible;">${paths}</svg>`;
  }

  function speedLinesSVG(color = 'rgba(24,27,38,0.16)') {
    let lines = '';
    const cx = 360, cy = 435;
    for (let i = 0; i < 36; i++) {
      const ang = (i * 2 * Math.PI) / 36;
      const rIn = 235 + (i % 3) * 28;
      const rOut = 1400;
      const w = (i % 2 === 0) ? 4.5 : 2.5;
      const x1 = (cx + Math.cos(ang) * rIn).toFixed(1);
      const y1 = (cy + Math.sin(ang) * rIn).toFixed(1);
      const x2 = (cx + Math.cos(ang) * rOut).toFixed(1);
      const y2 = (cy + Math.sin(ang) * rOut).toFixed(1);
      lines += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="${w}" stroke-linecap="round"/>`;
    }
    return `<svg width="720" height="1280" viewBox="0 0 720 1280">${lines}</svg>`;
  }

  function comicBurstSVG(bg, size = 148, points = 12) {
    let d = '';
    const cx = size / 2, cy = size / 2;
    const rOut = size * 0.47, rIn = size * 0.31;
    for (let i = 0; i < points * 2; i++) {
      const ang = (i * Math.PI) / points - Math.PI / 2;
      const r = i % 2 === 0 ? rOut : rIn;
      d += (i === 0 ? 'M' : 'L') + (cx + Math.cos(ang) * r).toFixed(1) + ',' + (cy + Math.sin(ang) * r).toFixed(1);
    }
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="filter:drop-shadow(4px 5px 0 #181B26);"><path d="${d}Z" fill="${bg}" stroke="#181B26" stroke-width="3.5" stroke-linejoin="round"/></svg>`;
  }

  function renderComicFX(beat, age, t, mascotShot) {
    const bgFx = document.getElementById('bg-fx-layer');
    const stFx = document.getElementById('stage-fx-layer');
    const acFx = document.getElementById('actor-fx-layer');
    if (!bgFx || !stFx || !acFx) return;

    let bgHtml = '';
    let stHtml = '';
    let acHtml = '';

    const fxList = Array.isArray(beat.comic_fx) ? beat.comic_fx.slice() : [];
    // Shorthand mascot_bubble / sidekick_bubble
    if (beat.mascot_bubble) {
      const mb = typeof beat.mascot_bubble === 'string' ? { text: beat.mascot_bubble } : beat.mascot_bubble;
      fxList.push(Object.assign({ type: 'speech_bubble', target: 'mascot', at: 0.25 }, mb));
    }
    if (beat.sidekick_bubble) {
      const sb = typeof beat.sidekick_bubble === 'string' ? { text: beat.sidekick_bubble } : beat.sidekick_bubble;
      fxList.push(Object.assign({ type: 'speech_bubble', target: 'sidekick', at: 0.45 }, sb));
    }

    fxList.forEach(fx => {
      const at = fx.at != null ? fx.at : 0;
      const until = fx.until != null ? fx.until : Infinity;
      if (age < at || age >= until) return;
      const local = age - at;

      if (fx.type === 'sunburst') {
        const cx = fx.cx != null ? fx.cx : 360;
        const cy = fx.cy != null ? fx.cy : 430;
        const r = 1600;
        const size = r * 2;
        const sc = 0.94 + 0.06 * springScale(local, 0.22);
        const rot = (t * (fx.speed || 16)) % 360;
        const op = fx.opacity != null ? fx.opacity : 0.24;
        const col = fx.color || '#FFD648';
        bgHtml += `<div style="position:absolute;left:${cx - r}px;top:${cy - r}px;width:${size}px;height:${size}px;opacity:${(op * Math.min(1, local / 0.16)).toFixed(3)};transform-origin:50% 50%;transform:scale(${sc.toFixed(3)}) rotate(${rot.toFixed(1)}deg);">${sunburstSVG(col, fx.rays || 16, r)}</div>`;
      } else if (fx.type === 'speed_lines') {
        const pulse = 0.85 + 0.15 * Math.sin(t * 18);
        const col = fx.color || 'rgba(24,27,38,0.16)';
        bgHtml += `<div style="position:absolute;inset:0;opacity:${(pulse * Math.min(1, local / 0.1)).toFixed(3)};">${speedLinesSVG(col)}</div>`;
      } else if (fx.type === 'stamp_slam') {
        const p = clamp(local / 0.14, 0, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        const sc = 2.4 - 1.4 * ease;
        const rot = (fx.rot != null ? fx.rot : -8) + (1 - ease) * -12;
        const x = fx.x != null ? fx.x : 445;
        const y = fx.y != null ? fx.y : 550;
        const bg = fx.bg || '#E5483B';
        const fg = fx.fg || '#FFFDF6';
        const fz = fx.font_size || 30;
        stHtml += `<div class="comic-stamp" style="left:${x}px;top:${y}px;background:${bg};color:${fg};font-size:${fz}px;opacity:${clamp(p*2.5,0,1).toFixed(3)};transform:translate(-50%,-50%) scale(${sc.toFixed(3)}) rotate(${rot.toFixed(1)}deg);">${fx.text || 'ปัง!'}</div>`;
      } else if (fx.type === 'comic_burst') {
        const sc = springScale(local, 0.18);
        const x = fx.x != null ? fx.x : 590;
        const y = fx.y != null ? fx.y : 240;
        const sz = fx.size || 142;
        const rot = (fx.rot != null ? fx.rot : 8) + Math.sin(t * 4.5) * 3.5;
        const bg = fx.bg || '#FFD648';
        const fg = fx.fg || '#181B26';
        stHtml += `<div style="position:absolute;left:${x}px;top:${y}px;width:${sz}px;height:${sz}px;transform:translate(-50%,-50%) scale(${sc.toFixed(3)}) rotate(${rot.toFixed(1)}deg);display:flex;align-items:center;justify-content:center;">
          <div style="position:absolute;inset:0;">${comicBurstSVG(bg, sz, fx.points || 12)}</div>
          <div style="position:relative;z-index:2;text-align:center;color:${fg};font-size:${fx.font_size || 24}px;font-weight:900;line-height:1.1;padding:0 12px;">${fx.text || '!'}</div>
        </div>`;
      } else if (fx.type === 'magnifying_lens') {
        const dur = fx.dur || 1.6;
        const p = clamp(local / dur, 0, 1);
        const ease = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
        const x = (fx.x1 != null ? fx.x1 : 170) + ((fx.x2 != null ? fx.x2 : 520) - (fx.x1 != null ? fx.x1 : 170)) * ease;
        const y = (fx.y1 != null ? fx.y1 : 340) + ((fx.y2 != null ? fx.y2 : 460) - (fx.y1 != null ? fx.y1 : 340)) * ease + Math.sin(p * Math.PI * 2) * 14;
        const sc = springScale(local, 0.2);
        stHtml += `<div style="position:absolute;left:${x.toFixed(1)}px;top:${y.toFixed(1)}px;transform:translate(-50%,-50%) scale(${sc.toFixed(3)});filter:drop-shadow(4px 6px 0 rgba(24,27,38,0.35));">
          <svg width="116" height="116" viewBox="0 0 116 116">
            <circle cx="48" cy="48" r="34" fill="rgba(255,214,72,0.22)" stroke="#181B26" stroke-width="7"/>
            <path d="M 32,34 Q 44,24 58,32" fill="none" stroke="#FFFFFF" stroke-width="5" stroke-linecap="round" opacity="0.85"/>
            <line x1="74" y1="74" x2="104" y2="104" stroke="#181B26" stroke-width="12" stroke-linecap="round"/>
            <line x1="74" y1="74" x2="104" y2="104" stroke="#E5483B" stroke-width="6" stroke-linecap="round"/>
          </svg>
        </div>`;
      } else if (fx.type === 'arrow_callout') {
        const sc = springScale(local, 0.18);
        const x = fx.x != null ? fx.x : 500;
        const y = fx.y != null ? fx.y : 290;
        const bg = fx.bg || '#FFD648';
        stHtml += `<div style="position:absolute;left:${x}px;top:${y}px;transform:translate(-50%,-50%) scale(${sc.toFixed(3)}) rotate(${fx.rot || -4}deg);background:${bg};color:#181B26;border:3.5px solid #181B26;border-radius:14px;padding:7px 16px;font-size:21px;font-weight:900;box-shadow:4px 5px 0 #181B26;white-space:nowrap;">${fx.text || 'ดูตรงนี้!'}</div>`;
      } else if (fx.type === 'speech_bubble') {
        const sc = springScale(local, 0.18);
        const bob = Math.sin(t * 3.2) * 3;
        const isRightMascot = (mascotShot === 'right_standard' || mascotShot === 'closeup_right' || mascotShot === 'peek_right');
        const isCenterMascot = (mascotShot === 'center_stage' || mascotShot === 'closeup_center');
        const styleCls = fx.style === 'shout' ? 'bubble-shout' : (fx.style === 'alert' ? 'bubble-alert' : '');
        let x, y, tailCls;
        if (fx.x != null && fx.y != null) {
          x = fx.x; y = fx.y;
          tailCls = fx.tail === 'right' ? 'comic-bubble-tail-right' : (fx.tail === 'none' ? '' : 'comic-bubble-tail-left');
        } else if (fx.target === 'sidekick') {
          if (isRightMascot) {
            x = 185; y = 850; tailCls = 'comic-bubble-tail-left';
          } else {
            x = 290; y = 850; tailCls = 'comic-bubble-tail-right';
          }
        } else {
          // Mascot bubble — strictly BELOW y=768 so it never touches y=672..758 subtitle!
          if (isRightMascot) {
            x = 40; y = 805; tailCls = 'comic-bubble-tail-right';
          } else if (isCenterMascot) {
            x = 435; y = 785; tailCls = 'comic-bubble-tail-left';
          } else {
            x = 395; y = 805; tailCls = 'comic-bubble-tail-left';
          }
        }
        acHtml += `<div class="comic-bubble ${styleCls} ${tailCls}" style="left:${x}px;top:${y}px;transform:translateY(${bob.toFixed(1)}px) scale(${sc.toFixed(3)}) rotate(${fx.rot || (isRightMascot ? -1.5 : 1.5)}deg);">${fx.text || ''}</div>`;
      }
    });

    bgFx.innerHTML = bgHtml;
    stFx.innerHTML = stHtml;
    acFx.innerHTML = acHtml;
  }

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

    const theme = Object.assign({}, spec.theme || {}, beat.theme || {});
    const layout = beat.layout || theme.layout || 'standard';
    const mascotShot = beat.mascot_shot || theme.mascot_shot || '';
    const mascotMode = beat.mascot_mode || theme.mascot_mode || (layout === 'full_stage' ? 'mini_left' : 'standard');

    const stage = document.getElementById('stage');
    const bgName = beat.bg || theme.bg || 'cream_graph';
    const cls = ['bg-' + bgName, 'layout-' + layout];
    if (mascotShot) cls.push('shot-' + mascotShot);
    else if (mascotMode && mascotMode !== 'standard') cls.push('mascot-' + mascotMode);
    stage.className = cls.join(' ');

    if (theme.bg_css) {
      stage.style.background = theme.bg_css;
    } else if (theme.bg_color) {
      stage.style.backgroundImage = 'none';
      stage.style.backgroundColor = theme.bg_color;
    } else {
      stage.style.background = '';
      stage.style.backgroundImage = '';
      stage.style.backgroundColor = '';
    }

    const customStyleEl = document.getElementById('custom-theme-style');
    if (customStyleEl) customStyleEl.textContent = theme.css || '';

    const chipsOuter = document.getElementById('chips-outer');
    if (chipsOuter) {
      if (theme.chips_y != null) chipsOuter.style.top = theme.chips_y + 'px';
      else chipsOuter.style.top = '';
    }

    if (theme.show_stars === false) {
      document.getElementById('deco-layer').innerHTML = '';
    } else {
      renderDecorations(t, bgName);
    }

    const rLayer = document.getElementById('ribbon-layer');
    if (beat.ribbon && theme.show_ribbon !== false) {
      const rCol = RIBBON_COLORS[beat.ribbon_color || 'red'] || RIBBON_COLORS.red;
      const rStyle = theme.ribbon_style || 'glass_tag';
      const rScale = springScale(age, 0.16).toFixed(3);
      if (theme.ribbon_style === 'pill') {
        rLayer.innerHTML = `<div class="pill-ribbon" style="background:${rCol.bg};color:${rCol.fg};transform:scale(${rScale});">${beat.ribbon}</div>`;
      } else if (rStyle === 'torn') {
        rLayer.innerHTML = `<div class="torn-ribbon" style="background:${rCol.bg};color:${rCol.fg};transform:scale(${rScale}) rotate(-1.2deg);">${beat.ribbon}</div>`;
      } else {
        const raw = String(beat.ribbon);
        const sepIdx = raw.indexOf('·') !== -1 ? raw.indexOf('·') : raw.indexOf(':');
        let innerHtml = '';
        if (sepIdx > 0 && sepIdx < raw.length - 1) {
          const leftPart = raw.slice(0, sepIdx).trim();
          const rightPart = raw.slice(sepIdx + 1).trim();
          innerHtml = `<span class="glass-tag-pill" style="background:${rCol.bg};color:${rCol.fg};">${leftPart}</span><span class="glass-tag-text">${rightPart}</span>`;
        } else {
          innerHtml = `<span class="glass-tag-dot" style="background:${rCol.bg};"></span><span class="glass-tag-text">${raw}</span>`;
        }
        rLayer.innerHTML = `<div class="glass-tag-ribbon" style="transform:scale(${rScale});">${innerHtml}</div>`;
      }
    } else {
      rLayer.innerHTML = '';
    }

    const wStage = document.getElementById('widget-stage');
    const wObj = beat.widget;
    const beatDur = Math.max(0.2, beat.end - beat.start);
    wStage.innerHTML = (wObj && WIDGET_MAP[wObj.type]) ? WIDGET_MAP[wObj.type](wObj, age, beatDur) : '';
    applySubBeatAnimations(wStage, age);

    // Preloaded Mascot + SVG Mouth + v3.6 Stage Blocking & Flip
    const mLayer = document.getElementById('mascot-layer');
    const mFlip = document.getElementById('mascot-flip');
    const mImg = document.getElementById('mascot-img');
    const pKey = poseName || 'wave';
    if (pKey !== lastPose && assets.mascots[pKey]) {
      mImg.src = assets.mascots[pKey];
      lastPose = pKey;
    }
    const isCenteredShot = (mascotShot === 'center_stage' || mascotShot === 'closeup_center');
    const bobY = Math.sin(t * 2.8) * 2.2;
    const sway = Math.sin(t * 1.6) * 0.6;
    let enterX = 0, enterY = 0, enterSc = 1.0;
    const mEnter = beat.mascot_enter || '';
    if (mEnter && age < 0.24) {
      const ep = clamp(age / 0.24, 0, 1);
      const ease = 1 - Math.pow(1 - ep, 3);
      if (mEnter === 'slide_left') enterX = -(1 - ease) * 140;
      else if (mEnter === 'slide_right') enterX = (1 - ease) * 140;
      else if (mEnter === 'rise') enterY = (1 - ease) * 120;
      else if (mEnter === 'pop') enterSc = springScale(age, 0.22);
    }
    const baseTx = isCenteredShot ? `translateX(calc(-50% + ${enterX.toFixed(1)}px))` : `translateX(${enterX.toFixed(1)}px)`;
    mLayer.style.transform = `${baseTx} translateY(${(bobY + enterY).toFixed(1)}px) scale(${enterSc.toFixed(3)}) rotate(${sway.toFixed(2)}deg)`;

    if (mFlip) {
      mFlip.style.transform = beat.mascot_flip ? 'scaleX(-1)' : '';
    }
    renderProceduralMouth(mouthShape || 'CLOSED', assets.anchors[pKey] || assets.anchors.wave);

    // Preloaded Sidekick Prop + v3.6 Auto-Opposite Blocking
    const skLayer = document.getElementById('sidekick-layer');
    const skImg = document.getElementById('sidekick-img');
    const isRightMascot = (mascotShot === 'right_standard' || mascotShot === 'closeup_right' || mascotShot === 'peek_right');
    const skPos = beat.sidekick_pos || (isRightMascot ? 'left' : '');
    if (skLayer) {
      skLayer.className = skPos ? ('sk-' + skPos) : '';
    }
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

    renderComicFX(beat, age, t, mascotShot);
    applyCameraAndTransition(beat, age, beatDur);
    renderWords(t);
  };
})();
