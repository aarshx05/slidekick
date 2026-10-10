// Runs inside the page. Reads every <section class="slide"> and returns the Low-IR:
// exact geometry + computed style for each [data-pptx] element, with text split into paragraphs/runs.
async () => {
  const W = 1280, H = 720;
  const warnings = [];
  let nextId = 1, nextTid = 1, slideNo = 0;

  const describe = (el) => {
    if (!el || !el.tagName) return '';
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    if (el.classList && el.classList.length) s += '.' + Array.from(el.classList).slice(0, 3).join('.');
    if (el.dataset && el.dataset.name) s += `[data-name="${el.dataset.name}"]`;
    const t = (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    return t ? `${s} "${t}"` : s;
  };
  const warn = (code, msg, el) => warnings.push({ slide: slideNo, code, msg, el: describe(el) });

  // ---------- colors ----------
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  const colorCache = new Map();
  const hex2 = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0').toUpperCase();
  function parseColor(str) {
    if (!str) return null;
    str = str.trim();
    if (str === 'transparent' || str === 'none' || str === 'currentcolor') return null;
    if (colorCache.has(str)) return colorCache.get(str);
    let res = null;
    const m = str.match(/^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)$/);
    if (m) {
      const a = m[4] === undefined ? 1 : (m[4].endsWith('%') ? parseFloat(m[4]) / 100 : parseFloat(m[4]));
      res = { hex: hex2(+m[1]) + hex2(+m[2]) + hex2(+m[3]), alpha: a };
    } else if (CSS.supports('color', str)) {
      cx.globalCompositeOperation = 'copy';
      cx.fillStyle = '#000';
      cx.fillStyle = str;
      cx.fillRect(0, 0, 1, 1);
      const d = cx.getImageData(0, 0, 1, 1).data;
      res = { hex: hex2(d[0]) + hex2(d[1]) + hex2(d[2]), alpha: d[3] / 255 };
    }
    if (res && res.alpha <= 0.004) res = null;
    colorCache.set(str, res);
    return res;
  }

  function splitTop(str, sep = ',') {
    const out = []; let depth = 0, cur = '', q = null;
    for (const ch of str) {
      if (q) { cur += ch; if (ch === q) q = null; continue; }
      if (ch === '"' || ch === "'") { q = ch; cur += ch; continue; }
      if (ch === '(') depth++;
      if (ch === ')') depth--;
      if (depth === 0 && (sep === ' ' ? /\s/.test(ch) : ch === sep)) { if (cur.trim()) out.push(cur.trim()); cur = ''; }
      else cur += ch;
    }
    if (cur.trim()) out.push(cur.trim());
    return out;
  }

  const toDeg = (v) => {
    const n = parseFloat(v);
    if (v.endsWith('turn')) return n * 360;
    if (v.endsWith('grad')) return n * 0.9;
    if (v.endsWith('rad')) return n * 180 / Math.PI;
    return n;
  };
  function sideAngle(txt, w, h) {
    const t = txt.replace(/^to\s+/, '').split(/\s+/).sort().join(' ');
    const a = Math.atan2(h, w) * 180 / Math.PI;
    return ({ 'top': 0, 'right': 90, 'bottom': 180, 'left': 270, 'right top': a, 'bottom right': 180 - a,
      'bottom left': 180 + a, 'left top': 360 - a })[t] ?? 180;
  }
  function parsePos(txt, w = 100, h = 100) {
    const kw = { left: 0, center: 50, right: 100, top: 0, bottom: 100 };
    const toks = txt.trim().split(/\s+/);
    let x = 50, y = 50;
    // px offsets are relative to the slack (box - image); with no slack any offset means centred, not NaN
    const val = (t, size) => t in kw ? kw[t] : t.endsWith('%') ? parseFloat(t) : size ? (parseFloat(t) / size) * 100 : 50;
    if (toks.length === 1) {
      if (toks[0] === 'top' || toks[0] === 'bottom') y = kw[toks[0]]; else x = val(toks[0], w);
    } else {
      let [a, b] = toks;
      if (a === 'top' || a === 'bottom' || b === 'left' || b === 'right') [a, b] = [b, a];
      x = val(a, w); y = val(b, h);
    }
    return [x, y];
  }
  function parseGradient(str, w, h) {
    const m = str.match(/^(repeating-)?(linear|radial)-gradient\(([\s\S]*)\)$/);
    if (!m) return null;
    if (m[1]) return { unsupported: 'repeating gradient' };
    const kind = m[2], parts = splitTop(m[3]);
    let angle = 180, cxp = 50, cyp = 50;
    if (parts.length && !CSS.supports('color', splitTop(parts[0], ' ')[0])) {
      const first = parts.shift();
      if (kind === 'linear') angle = /^to\s/.test(first) ? sideAngle(first, w, h) : toDeg(first);
      else { const at = first.match(/at\s+(.+)$/); if (at) [cxp, cyp] = parsePos(at[1], w, h); }
    }
    const len = kind === 'linear'
      ? Math.abs(w * Math.sin(angle * Math.PI / 180)) + Math.abs(h * Math.cos(angle * Math.PI / 180))
      : Math.hypot(w, h) / 2;
    const stops = [];
    for (const p of parts) {
      const toks = splitTop(p, ' ');
      const col = parseColor(toks[0]) || (CSS.supports('color', toks[0]) ? { hex: '000000', alpha: 0 } : null);
      if (!col) continue;  // color hint
      const positions = toks.slice(1).map(t => t.endsWith('%') ? parseFloat(t) / 100 : parseFloat(t) / (len || 1));
      if (!positions.length) stops.push({ pos: null, hex: col.hex, alpha: col.alpha });
      for (const pos of positions) stops.push({ pos, hex: col.hex, alpha: col.alpha });
    }
    if (!stops.length) return null;
    if (stops[0].pos === null) stops[0].pos = 0;
    if (stops[stops.length - 1].pos === null) stops[stops.length - 1].pos = 1;
    for (let i = 1; i < stops.length - 1; i++) {
      if (stops[i].pos === null) {
        let j = i; while (stops[j].pos === null) j++;
        const a = stops[i - 1].pos, b = stops[j].pos;
        for (let k = i; k < j; k++) stops[k].pos = a + (b - a) * (k - i + 1) / (j - i + 1);
      }
    }
    stops.forEach(s => { s.pos = Math.max(0, Math.min(1, s.pos)); });
    return { type: 'gradient', kind, angle, cx: cxp, cy: cyp, stops };
  }
  function parseShadow(str) {
    if (!str || str === 'none') return null;
    for (const s of splitTop(str)) {
      if (/\binset\b/.test(s)) continue;
      const toks = splitTop(s, ' ');
      let col = null; const nums = [];
      for (const t of toks) { if (/^-?[\d.]+(px)?$/.test(t)) nums.push(parseFloat(t)); else col = parseColor(t) || col; }
      if (!col || nums.length < 2) continue;
      return { hex: col.hex, alpha: col.alpha, x: nums[0], y: nums[1], blur: nums[2] || 0, spread: nums[3] || 0 };
    }
    return null;
  }

  // ---------- geometry ----------
  const BLOCKS = new Set(['block', 'list-item', 'flex', 'grid', 'table', 'table-row', 'table-cell', 'flow-root',
    'table-caption', 'table-row-group', 'table-header-group', 'table-footer-group']);
  const isBlock = (cs) => BLOCKS.has(cs.display) || cs.display.startsWith('block') || cs.display.startsWith('flow-root');
  const r2 = (n) => Math.round(n * 100) / 100;

  function opacityOf(el, stop) {
    let o = 1;
    for (let e = el; e && e !== stop.parentElement; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity);
    return o;
  }
  function rotationOf(cs) {
    if (!cs.transform || cs.transform === 'none') return { rot: 0, sx: 1, sy: 1, other: false };
    const m = new DOMMatrixReadOnly(cs.transform);
    const rot = Math.atan2(m.b, m.a) * 180 / Math.PI;
    const sx = Math.hypot(m.a, m.b), sy = Math.hypot(m.c, m.d);
    return { rot: Math.abs(rot) < 0.01 ? 0 : rot, sx, sy, other: Math.abs(sx - 1) > 0.01 || Math.abs(sy - 1) > 0.01 };
  }
  // Measure `el` with its own rotation removed; returns {box (slide coords, unrotated), origin (viewport rect while unrotated), restore()}
  function frameOf(el, slideRect) {
    const cs = getComputedStyle(el);
    const t = rotationOf(cs);
    const vis = el.getBoundingClientRect();
    if (!t.rot) {
      return { rot: 0, scale: t, box: { x: vis.left - slideRect.left, y: vis.top - slideRect.top, w: vis.width, h: vis.height }, origin: vis, restore() {} };
    }
    const cxv = vis.left + vis.width / 2, cyv = vis.top + vis.height / 2;
    const prev = el.style.getPropertyValue('transform'), prio = el.style.getPropertyPriority('transform');
    el.style.setProperty('transform', 'none', 'important');
    const flat = el.getBoundingClientRect();
    const w = flat.width * t.sx, h = flat.height * t.sy;
    return {
      rot: t.rot, scale: t,
      box: { x: cxv - w / 2 - slideRect.left, y: cyv - h / 2 - slideRect.top, w, h },
      origin: flat,
      restore() { if (prev) el.style.setProperty('transform', prev, prio); else el.style.removeProperty('transform'); },
    };
  }

  function borderInfo(cs) {
    const sides = ['Top', 'Right', 'Bottom', 'Left'].map(s => {
      const w = parseFloat(cs[`border${s}Width`]) || 0, st = cs[`border${s}Style`], c = parseColor(cs[`border${s}Color`]);
      return { side: s.toLowerCase(), w: (w > 0 && st !== 'none' && st !== 'hidden' && c) ? w : 0, style: st, c };
    });
    return sides;
  }
  function radiusInfo(cs, w, h) {
    const rs = [cs.borderTopLeftRadius, cs.borderTopRightRadius, cs.borderBottomRightRadius, cs.borderBottomLeftRadius];
    const vals = rs.map(r => {
      const p = r.split(/\s+/)[0];
      return p.endsWith('%') ? { pct: parseFloat(p) } : { px: parseFloat(p) || 0 };
    });
    if (vals.some(v => v.pct >= 50) && vals.every(v => v.pct >= 50 || v.px >= Math.max(w, h) / 2)) return { geom: 'ellipse', radius: 0, uneven: false };
    const px = vals.map(v => v.pct !== undefined ? v.pct / 100 * Math.min(w, h) : v.px);
    const max = Math.max(...px);
    if (max <= 0.5) return { geom: 'rect', radius: 0, uneven: false };
    if (max >= Math.min(w, h) / 2 - 0.5 && Math.abs(w - h) < 1) return { geom: 'ellipse', radius: 0, uneven: false };
    return { geom: 'roundRect', radius: Math.min(max, Math.min(w, h) / 2), uneven: px.some(v => Math.abs(v - max) > 0.5) };
  }

  function boxVisual(el, cs, w, h, opts = {}) {
    const bg = parseColor(cs.backgroundColor);
    const layers = cs.backgroundImage && cs.backgroundImage !== 'none' ? splitTop(cs.backgroundImage) : [];
    const textClip = cs.webkitBackgroundClip === 'text' || cs.backgroundClip === 'text';
    let grad = null, image = null;
    for (const L of layers) {
      if (/gradient\(/.test(L) && !grad && !image) grad = parseGradient(L, w, h);
      else if (/^url\(/.test(L) && !image) image = L.replace(/^url\(\s*["']?/, '').replace(/["']?\s*\)$/, '');
      else if (/gradient\(/.test(L) && grad) warn('multi-gradient', 'only the top background gradient layer is kept', el);
    }
    if (grad && grad.unsupported) { warn('gradient', grad.unsupported + ' not supported; using first stop color', el); grad = null; }
    let fill = null;
    if (!textClip) {
      if (grad) {
        if (bg) grad.stops.forEach(s => {   // composite translucent stops over the background color
          if (s.alpha < 1) {
            const [r1, g1, b1] = [0, 2, 4].map(i => parseInt(s.hex.slice(i, i + 2), 16));
            const [r2_, g2, b2] = [0, 2, 4].map(i => parseInt(bg.hex.slice(i, i + 2), 16));
            const a = s.alpha, ba = bg.alpha, oa = a + ba * (1 - a);
            s.hex = hex2((r1 * a + r2_ * ba * (1 - a)) / oa) + hex2((g1 * a + g2 * ba * (1 - a)) / oa) + hex2((b1 * a + b2 * ba * (1 - a)) / oa);
            s.alpha = oa;
          }
        });
        fill = grad;
      } else if (bg) fill = { type: 'solid', hex: bg.hex, alpha: bg.alpha };
    }
    const sides = borderInfo(cs);
    const vis = sides.filter(s => s.w > 0);
    let line = null, bars = [];
    if (vis.length === 4 && vis.every(s => Math.abs(s.w - vis[0].w) < 0.01 && s.c.hex === vis[0].c.hex && s.style === vis[0].style)) {
      line = { hex: vis[0].c.hex, alpha: vis[0].c.alpha, width: vis[0].w, dash: vis[0].style };
    } else bars = vis;
    const rad = radiusInfo(cs, w, h);
    if (rad.uneven) warn('radius', 'different corner radii are approximated with one radius', el);
    return { fill, line, bars, geom: rad.geom, radius: rad.radius, shadow: parseShadow(cs.boxShadow), image,
      bgSize: cs.backgroundSize, bgPos: cs.backgroundPosition, textClip: textClip ? grad : null };
  }

  // ---------- text ----------
  function decorations(el, root) {
    const d = { underline: false, strike: false };
    for (let e = el; e; e = e.parentElement) {
      const t = getComputedStyle(e).textDecorationLine || '';
      if (t.includes('underline')) d.underline = true;
      if (t.includes('line-through')) d.strike = true;
      if (e === root) break;
    }
    return d;
  }
  function gradientTextOf(el, root) {
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if ((cs.webkitBackgroundClip === 'text' || cs.backgroundClip === 'text') && /gradient\(/.test(cs.backgroundImage)) {
        const r = e.getBoundingClientRect();
        return parseGradient(splitTop(cs.backgroundImage).find(L => /gradient\(/.test(L)), r.width, r.height);
      }
      if (e === root) break;
    }
    return null;
  }
  function transformText(t, tt) {
    if (tt === 'lowercase') return t.toLowerCase();
    if (tt === 'capitalize') return t.replace(/(^|\s)(\S)/g, (m, a, b) => a + b.toUpperCase());
    return t;
  }
  function tagTid(el) {
    if (!el.dataset.deckTid) el.dataset.deckTid = String(nextTid++);
    return +el.dataset.deckTid;
  }
  function runStyle(el, root) {
    const cs = getComputedStyle(el);
    const col = parseColor(cs.color);
    const d = decorations(el, root);
    const a = el.closest('a[href]');
    const ts = parseShadow(cs.textShadow);
    return {
      size: r2(parseFloat(cs.fontSize)), weight: parseInt(cs.fontWeight, 10) || 400,
      italic: cs.fontStyle !== 'normal', family: cs.fontFamily,
      hex: col ? col.hex : '000000', alpha: col ? col.alpha : 0,
      spacing: cs.letterSpacing === 'normal' ? 0 : r2(parseFloat(cs.letterSpacing) || 0),
      caps: cs.textTransform === 'uppercase' ? 'all' : (cs.fontVariantCaps === 'small-caps' || cs.fontVariantCaps === 'all-small-caps') ? 'small' : 'none',
      underline: d.underline, strike: d.strike,
      link: a && root.contains(a) ? a.href : null,
      baseline: cs.verticalAlign === 'super' ? 30 : cs.verticalAlign === 'sub' ? -25 : 0,
      gradient: gradientTextOf(el, root), shadow: ts,
      tid: tagTid(el),
    };
  }
  const BULLETS = { disc: '•', circle: '◦', square: '▪', 'disclosure-closed': '▸', 'disclosure-open': '▾' };
  const AUTONUM = { decimal: 'arabicPeriod', 'decimal-leading-zero': 'arabicPeriod', 'lower-alpha': 'alphaLcPeriod',
    'lower-latin': 'alphaLcPeriod', 'upper-alpha': 'alphaUcPeriod', 'upper-latin': 'alphaUcPeriod',
    'lower-roman': 'romanLcPeriod', 'upper-roman': 'romanUcPeriod' };

  function lineBoxes(nodes) {
    const rects = [];
    for (const n of nodes) {
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) if (r.width > 0.1 && r.height > 0.1) rects.push(r);
    }
    rects.sort((a, b) => a.top - b.top || a.left - b.left);
    const lines = [];
    for (const r of rects) {
      const mid = (r.top + r.bottom) / 2;
      const L = lines.find(l => mid >= l.top - 0.5 && mid <= l.bottom + 0.5);
      if (L) { L.top = Math.min(L.top, r.top); L.bottom = Math.max(L.bottom, r.bottom); L.left = Math.min(L.left, r.left); L.right = Math.max(L.right, r.right); }
      else lines.push({ top: r.top, bottom: r.bottom, left: r.left, right: r.right });
    }
    return lines;
  }

  // Baseline y of the line holding `node`'s start (or end), via a zero-size inline-block probe.
  function baselineAt(node, atEnd) {
    const probe = document.createElement('span');
    probe.style.cssText = 'display:inline-block;width:0;height:0;padding:0;margin:0;border:0;vertical-align:baseline';
    node.parentNode.insertBefore(probe, atEnd ? node.nextSibling : node);
    const y = probe.getBoundingClientRect().bottom;
    probe.remove();
    return y;
  }
  const lineSig = (nodes) => lineBoxes(nodes).map(l => Math.round(l.right - l.left)).join(',');
  // Range of border-box width deltas that keep exactly the same line breaks (PowerPoint gets the middle).
  function wrapRange(el, nodes) {
    const props = ['width', 'min-width', 'max-width'];
    const saved = props.map(p => [p, el.style.getPropertyValue(p), el.style.getPropertyPriority(p)]);
    const w0 = el.getBoundingClientRect().width;
    const sig0 = lineSig(nodes);
    const at = (w) => { el.style.setProperty('min-width', '0px', 'important'); el.style.setProperty('max-width', 'none', 'important');
      el.style.setProperty('width', w + 'px', 'important'); return lineSig(nodes) === sig0; };
    let lo = w0, hi = w0 + Math.max(60, w0 * 0.5), up, down;
    if (at(hi)) up = hi - w0;
    else { for (let k = 0; k < 11; k++) { const m = (lo + hi) / 2; if (at(m)) lo = m; else hi = m; } up = lo - w0; }
    lo = Math.max(1, w0 * 0.5); hi = w0;
    if (at(lo)) down = lo - w0;
    else { for (let k = 0; k < 11; k++) { const m = (lo + hi) / 2; if (at(m)) hi = m; else lo = m; } down = hi - w0; }
    for (const [p, v, prio] of saved) { if (v) el.style.setProperty(p, v, prio); else el.style.removeProperty(p); }
    return { min: r2(down), max: r2(up) };
  }

  // Split `root` into paragraphs/runs; geometry relative to `origin` (root's unrotated viewport rect).
  function extractText(root, origin, opts = {}) {
    const rootCS = getComputedStyle(root);
    const paras = []; let cur = null;
    const startPara = (block) => { cur = { block, runs: [], nodes: [], li: null }; paras.push(cur); };
    const walk = (node, block) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const parent = node.parentElement, cs = getComputedStyle(parent);
        if (cs.visibility !== 'visible') return;
        let t = node.data;
        const pre = /^(pre|pre-wrap|break-spaces)$/.test(cs.whiteSpace);
        if (!pre) t = t.replace(/[\t\n\r\f ]+/g, ' ');
        if (!t) return;
        if (!cur) startPara(block);
        if (pre && t.includes('\n')) {
          t.split('\n').forEach((piece, i) => {
            if (i) cur.runs.push({ br: true, el: parent });
            if (piece) cur.runs.push({ text: transformText(piece, cs.textTransform), el: parent, pre: true });
          });
        } else cur.runs.push({ text: transformText(t, cs.textTransform), el: parent, pre });
        cur.nodes.push(node);
        return;
      }
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      const el = node;
      if (el !== root && el.hasAttribute('data-pptx')) return;
      if (el.matches('aside.notes, script, style, template, noscript')) return;
      const cs = getComputedStyle(el);
      if (cs.display === 'none') return;
      if (el.tagName === 'BR') { if (!cur) startPara(block); cur.runs.push({ br: true, el: el.parentElement }); return; }
      if (el.tagName === 'IMG' || el.tagName.toLowerCase() === 'svg') { warn('inline-image', 'images inside a text element are dropped; tag them data-pptx="image"', el); return; }
      if (el !== root && cs.display.startsWith('inline') && parseColor(cs.backgroundColor)) warn('inline-bg', 'inline background (badge/highlight) inside text is lost; make it its own data-pptx element', el);
      if ((cs.display === 'flex' || cs.display === 'grid' || cs.display === 'inline-flex') && !cs.flexDirection.startsWith('column')) {
        const textKids = Array.from(el.children).filter(c => !c.hasAttribute('data-pptx') && (c.innerText || '').trim());
        if (textKids.length > 1 && cs.display !== 'grid') warn('row-layout-text', 'side-by-side text inside one text element will stack; split into separate data-pptx elements', el);
        if (cs.display === 'grid' && textKids.length > 1 && cs.gridTemplateColumns.split(' ').length > 1) warn('row-layout-text', 'grid columns inside one text element will stack; split into separate data-pptx elements', el);
      }
      for (const pseudo of ['::before', '::after']) {
        const pc = getComputedStyle(el, pseudo).content;
        if (pc && pc !== 'none' && pc !== 'normal' && pc !== '""' && pc !== "''") warn('pseudo-content', `${pseudo} content ${pc.slice(0, 20)} is not exported; use a real element`, el);
      }
      if (el !== root && isBlock(cs)) {
        cur = null;
        const before = paras.length;
        for (const ch of el.childNodes) walk(ch, el);
        if (cs.display === 'list-item' && paras.length > before) paras[before].li = el;
        cur = null;
      } else {
        for (const ch of el.childNodes) walk(ch, block);
      }
    };
    for (const ch of root.childNodes) walk(ch, root);

    // whitespace collapsing across runs
    for (const p of paras) {
      let prevSpace = true;
      for (const r of p.runs) {
        if (r.br) { prevSpace = true; continue; }
        if (r.pre) { prevSpace = false; continue; }
        if (prevSpace) r.text = r.text.replace(/^ +/, '');
        if (r.text) prevSpace = r.text.endsWith(' ');
      }
      for (let i = 0; i < p.runs.length; i++) {
        const r = p.runs[i];
        if (r.br || r.pre) continue;
        const next = p.runs.slice(i + 1).find(x => x.br || (x.text && x.text.length));
        if (!next || next.br) r.text = r.text.replace(/ +$/, '');
      }
      p.runs = p.runs.filter(r => r.br || r.text.length);
      while (p.runs.length && p.runs[p.runs.length - 1].br) p.runs.pop();
    }
    const kept = paras.filter(p => p.runs.some(r => !r.br));
    if (!kept.length) return null;

    // Lists: the root's left padding is where CSS hangs the markers, so it belongs in each paragraph's marL
    // (PowerPoint cannot draw a bullet left of the inset), not in the text-box inset.
    const listy = kept.some(p => p.li);
    const pad = {
      l: (listy ? 0 : (parseFloat(rootCS.paddingLeft) || 0)) + (parseFloat(rootCS.borderLeftWidth) || 0),
      r: (parseFloat(rootCS.paddingRight) || 0) + (parseFloat(rootCS.borderRightWidth) || 0),
      t: (parseFloat(rootCS.paddingTop) || 0) + (parseFloat(rootCS.borderTopWidth) || 0),
      b: (parseFloat(rootCS.paddingBottom) || 0) + (parseFloat(rootCS.borderBottomWidth) || 0),
    };
    const out = [];
    let prevBottom = null, maxLines = 0, overflowX = false;
    const contentRight = origin.width - pad.r;
    for (const p of kept) {
      const bcs = getComputedStyle(p.block);
      const lines = lineBoxes(p.nodes);
      maxLines = Math.max(maxLines, lines.length);
      const firstRun = p.runs.find(r => !r.br);
      const fsize = parseFloat(getComputedStyle(firstRun.el).fontSize);
      let lh = bcs.lineHeight === 'normal' ? null : parseFloat(bcs.lineHeight);
      if (!lh) lh = lines.length > 1 ? (lines[lines.length - 1].top - lines[0].top) / (lines.length - 1) : (lines[0] ? lines[0].bottom - lines[0].top : fsize * 1.2);
      const top = lines.length ? lines[0].top - (lh - (lines[0].bottom - lines[0].top)) / 2 - origin.top : 0;
      const bottom = lines.length ? lines[lines.length - 1].bottom + (lh - (lines[lines.length - 1].bottom - lines[lines.length - 1].top)) / 2 - origin.top : 0;
      for (const L of lines) if (L.right - origin.left > contentRight + 1.5 || L.left - origin.left < pad.l - 1.5) overflowX = true;
      const align = { left: 'l', start: 'l', center: 'ctr', right: 'r', end: 'r', justify: 'just', '-webkit-center': 'ctr' }[bcs.textAlign] || 'l';
      const blockRect = (p.li || p.block).getBoundingClientRect();
      const bl = p.li ? getComputedStyle(p.li) : bcs;
      const contentLeft = blockRect.left + (parseFloat(bl.paddingLeft) || 0) + (parseFloat(bl.borderLeftWidth) || 0) - origin.left;
      const contentRightBlock = blockRect.right - (parseFloat(bl.paddingRight) || 0) - (parseFloat(bl.borderRightWidth) || 0) - origin.left;
      const para = {
        align, line_height: r2(lh), top: r2(top), bottom: r2(bottom), lines: lines.length,
        // width of the last line relative to the widest one (taste lint: runts / widows)
        last_line_ratio: lines.length > 1 ? r2((lines[lines.length - 1].right - lines[lines.length - 1].left) / Math.max(1, ...lines.map(l => l.right - l.left))) : 1,
        baseline_first: r2(baselineAt(p.nodes[0], false) - origin.top),
        baseline_last: r2(baselineAt(p.nodes[p.nodes.length - 1], true) - origin.top),
        space_before: prevBottom === null ? 0 : r2(Math.max(0, top - prevBottom)),
        mar_l: r2(Math.max(0, (p.block === root && !p.li ? pad.l + (listy ? (parseFloat(rootCS.paddingLeft) || 0) : 0) : contentLeft) - pad.l)),
        mar_r: r2(Math.max(0, (contentRight) - (p.block === root && !p.li ? contentRight : contentRightBlock))),
        indent: r2(parseFloat(bcs.textIndent) || 0),
        bullet: null,
        runs: p.runs.map(r => r.br ? { br: true, ...runStyle(r.el, root) } : { text: r.text, ...runStyle(r.el, root) }),
      };
      if (p.li) {
        const lcs = getComputedStyle(p.li);
        const type = lcs.listStyleType;
        let level = 0;
        for (let e = p.li.parentElement; e && e !== root; e = e.parentElement) if (/^(UL|OL)$/.test(e.tagName)) level++;
        level = Math.max(0, level - 1);
        const mk = parseColor(getComputedStyle(p.li, '::marker').color) || parseColor(lcs.color);
        const indent = -Math.min(para.mar_l, fsize);
        if (type !== 'none') {
          let b;
          if (/^["']/.test(type)) b = { type: 'char', char: type.slice(1, -1).trim() || '•' };
          else if (AUTONUM[type]) {
            const ol = p.li.closest('ol');
            const items = ol ? Array.from(ol.children).filter(c => c.tagName === 'LI') : [];
            b = { type: 'auto', scheme: AUTONUM[type], start: (ol && ol.start ? ol.start : 1) + Math.max(0, items.indexOf(p.li)) };
          } else b = { type: 'char', char: BULLETS[type] || '•' };
          para.bullet = { ...b, hex: mk ? mk.hex : '000000', alpha: mk ? mk.alpha : 1, level, size: r2(parseFloat(getComputedStyle(p.li, '::marker').fontSize) || fsize) };
        }
        para.indent = r2(indent);
        para.level = level;
      }
      prevBottom = bottom;
      out.push(para);
    }
    const textTop = out[0].top, textBottom = out[out.length - 1].bottom;
    const ch = origin.height - pad.t - pad.b;
    const gapT = textTop - pad.t, gapB = (origin.height - pad.b) - textBottom;
    let anchor = 't';
    if (gapT > 2 && gapB > 2 && Math.abs(gapT - gapB) <= Math.max(2, 0.08 * (gapT + gapB))) anchor = 'ctr';
    else if (gapT > gapB + 2 && gapT > 2) anchor = 'b';
    const overflowY = textBottom > origin.height - pad.b + 1.5 && (textBottom - textTop) > ch + 1.5;
    const wraps = maxLines > 1 && !out.some(p => p.align === 'just');
    return {
      wrap_range: wraps && opts.wrap !== false ? wrapRange(root, kept.flatMap(p => p.nodes)) : null,
      paragraphs: out, anchor, pad,
      text_top: r2(textTop), text_bottom: r2(textBottom),
      single_line: maxLines <= 1 && !out.some(p => p.runs.some(r => r.br)) && out.length >= 1,
      overflow: overflowY || overflowX, overflow_x: overflowX, overflow_y: overflowY,
      direction: rootCS.direction,
    };
  }

  // ---------- images ----------
  function loadImage(src) {
    return new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = src; });
  }
  function serializeSvg(svg) {
    const clone = svg.cloneNode(true);
    const srcEls = [svg, ...svg.querySelectorAll('*')], dstEls = [clone, ...clone.querySelectorAll('*')];
    const props = ['fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'opacity', 'fill-opacity', 'stroke-opacity', 'fill-rule', 'stroke-dasharray'];
    srcEls.forEach((s, i) => {
      const cs = getComputedStyle(s), d = dstEls[i];
      for (const p of props) {
        let v = cs.getPropertyValue(p);
        if (!v) continue;
        if ((p === 'fill' || p === 'stroke') && v !== 'none' && !v.startsWith('url(')) { const c = parseColor(v); v = c ? '#' + c.hex : 'none'; if (c && c.alpha < 1) d.setAttribute(p + '-opacity', String(c.alpha)); }
        d.setAttribute(p, v);
      }
      d.removeAttribute('class'); d.removeAttribute('style');
    });
    const r = svg.getBoundingClientRect();
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    if (!clone.getAttribute('viewBox')) clone.setAttribute('viewBox', `0 0 ${r.width} ${r.height}`);
    clone.setAttribute('width', String(r.width)); clone.setAttribute('height', String(r.height));
    return new XMLSerializer().serializeToString(clone);
  }
  // Placement rect P of the full natural image, in viewport coords.
  function placeObject(D, nw, nh, fit, posTxt) {
    if (!nw || !nh || fit === 'fill') return { x: D.left, y: D.top, w: D.width, h: D.height };
    let s;
    if (fit === 'cover') s = Math.max(D.width / nw, D.height / nh);
    else if (fit === 'contain') s = Math.min(D.width / nw, D.height / nh);
    else if (fit === 'scale-down') s = Math.min(1, D.width / nw, D.height / nh);
    else s = 1;
    const w = nw * s, h = nh * s;
    const [px, py] = parsePos(posTxt || '50% 50%', D.width - w, D.height - h);
    return { x: D.left + (D.width - w) * px / 100, y: D.top + (D.height - h) * py / 100, w, h };
  }
  function placeBackground(D, nw, nh, size, pos) {
    let w, h;
    if (size === 'cover' || size === 'contain') {
      const s = size === 'cover' ? Math.max(D.width / nw, D.height / nh) : Math.min(D.width / nw, D.height / nh);
      w = nw * s; h = nh * s;
    } else {
      const [a, b = 'auto'] = size.split(/\s+/);
      const dim = (v, total) => v === 'auto' ? null : v.endsWith('%') ? total * parseFloat(v) / 100 : parseFloat(v);
      w = dim(a, D.width); h = dim(b, D.height);
      if (w === null && h === null) { w = nw; h = nh; } else if (w === null) w = h * nw / nh; else if (h === null) h = w * nh / nw;
    }
    const [px, py] = parsePos(pos || '0% 0%', D.width - w, D.height - h);
    return { x: D.left + (D.width - w) * px / 100, y: D.top + (D.height - h) * py / 100, w, h };
  }

  async function imageInfo(el, cs, frame, slideRect) {
    let target = el, src = null, kind = 'raster', svg = null, nw = 0, nh = 0, P = null, clip = null;
    const tag = el.tagName.toLowerCase();
    if (tag !== 'img' && tag !== 'svg' && tag !== 'picture') {
      const inner = el.querySelector('img, svg');
      const own = cs.backgroundImage && cs.backgroundImage.includes('url(');
      if (inner && !own) { target = inner; clip = (cs.overflow !== 'visible' || cs.overflowX !== 'visible') ? frame.origin : null; }
    } else if (tag === 'picture') target = el.querySelector('img');
    const tcs = getComputedStyle(target);
    const ttag = target.tagName.toLowerCase();
    const D = target === el ? frame.origin : target.getBoundingClientRect();
    if (ttag === 'img') {
      src = target.currentSrc || target.src; nw = target.naturalWidth; nh = target.naturalHeight;
      if (/\.svg([?#]|$)/i.test(src) || src.startsWith('data:image/svg')) kind = 'svg';
      P = placeObject(D, nw, nh, tcs.objectFit, tcs.objectPosition);
      if (!target.complete || !nw) warn('image-load', 'image did not load: ' + src, target);
    } else if (ttag === 'svg') {
      kind = 'svg-inline'; svg = serializeSvg(target); P = { x: D.left, y: D.top, w: D.width, h: D.height };
    } else {
      const url = splitTop(cs.backgroundImage).find(L => /^url\(/.test(L));
      if (!url) { warn('image-src', 'data-pptx="image" has no <img>, <svg> or background-image url()', el); return null; }
      src = new URL(url.replace(/^url\(\s*["']?/, '').replace(/["']?\s*\)$/, ''), document.baseURI).href;
      const im = await loadImage(src);
      nw = im ? im.naturalWidth : 0; nh = im ? im.naturalHeight : 0;
      if (/\.svg([?#]|$)/i.test(src)) kind = 'svg';
      P = nw ? placeBackground(D, nw, nh, cs.backgroundSize, cs.backgroundPosition) : { x: D.left, y: D.top, w: D.width, h: D.height };
      if (cs.backgroundRepeat && !cs.backgroundRepeat.includes('no-repeat') && (P.w < D.width - 1 || P.h < D.height - 1)) warn('bg-repeat', 'repeating background images are placed once', el);
    }
    // visible region V = D ∩ P ∩ clip
    let V = { l: Math.max(D.left, P.x), t: Math.max(D.top, P.y), r: Math.min(D.left + D.width, P.x + P.w), b: Math.min(D.top + D.height, P.y + P.h) };
    if (clip) V = { l: Math.max(V.l, clip.left), t: Math.max(V.t, clip.top), r: Math.min(V.r, clip.right), b: Math.min(V.b, clip.bottom) };
    if (V.r - V.l < 0.5 || V.b - V.t < 0.5) return null;
    const crop = { l: (V.l - P.x) / P.w, t: (V.t - P.y) / P.h, r: (P.x + P.w - V.r) / P.w, b: (P.y + P.h - V.b) / P.h };
    const maskSrc = clip ? cs : tcs;
    const rad = radiusInfo(maskSrc, V.r - V.l, V.b - V.t);
    // V is in viewport coords of the unrotated frame; convert to slide coords
    const dx = frame.box.x - (frame.origin.left - slideRect.left), dy = frame.box.y - (frame.origin.top - slideRect.top);
    return {
      box: { x: r2(V.l - slideRect.left + dx), y: r2(V.t - slideRect.top + dy), w: r2(V.r - V.l), h: r2(V.b - V.t) },
      image: { src, kind, svg, natural: [nw, nh], crop: { l: r2(crop.l * 1e4) / 1e4, t: r2(crop.t * 1e4) / 1e4, r: r2(crop.r * 1e4) / 1e4, b: r2(crop.b * 1e4) / 1e4 },
        mask: rad.geom, radius: rad.radius, alt: target.getAttribute('alt') || el.getAttribute('aria-label') || '' },
      vis: boxVisual(clip ? el : target, clip ? cs : tcs, V.r - V.l, V.b - V.t),
    };
  }

  // ---------- tables / charts ----------
  function tableInfo(tbl, frame) {
    const o = frame.origin;
    const xs = [], ys = [];
    const rows = Array.from(tbl.rows);
    const snap = (arr, v) => { const f = arr.find(a => Math.abs(a - v) < 1.5); if (f === undefined) arr.push(v); };
    rows.forEach(tr => {
      const rr = tr.getBoundingClientRect(); snap(ys, rr.top - o.top); snap(ys, rr.bottom - o.top);
      Array.from(tr.cells).forEach(td => { const c = td.getBoundingClientRect(); snap(xs, c.left - o.left); snap(xs, c.right - o.left); });
    });
    xs.sort((a, b) => a - b); ys.sort((a, b) => a - b);
    const idx = (arr, v) => { let best = 0; arr.forEach((a, i) => { if (Math.abs(a - v) < Math.abs(arr[best] - v)) best = i; }); return best; };
    const cells = [];
    rows.forEach(tr => Array.from(tr.cells).forEach(td => {
      const c = td.getBoundingClientRect(), ccs = getComputedStyle(td);
      const r0 = idx(ys, c.top - o.top), r1 = idx(ys, c.bottom - o.top), c0 = idx(xs, c.left - o.left), c1 = idx(xs, c.right - o.left);
      let bgc = parseColor(ccs.backgroundColor) || parseColor(getComputedStyle(tr).backgroundColor);
      const sec = tr.parentElement; if (!bgc && sec) bgc = parseColor(getComputedStyle(sec).backgroundColor);
      const text = extractText(td, c, { wrap: false });
      cells.push({
        r: r0, c: c0, rs: Math.max(1, r1 - r0), cs: Math.max(1, c1 - c0),
        fill: bgc ? { type: 'solid', hex: bgc.hex, alpha: bgc.alpha } : null,
        borders: Object.fromEntries(borderInfo(ccs).map(s => [s.side, s.w ? { hex: s.c.hex, alpha: s.c.alpha, width: s.w, dash: s.style } : null])),
        pad: { l: parseFloat(ccs.paddingLeft) || 0, r: parseFloat(ccs.paddingRight) || 0, t: parseFloat(ccs.paddingTop) || 0, b: parseFloat(ccs.paddingBottom) || 0 },
        anchor: ccs.verticalAlign === 'middle' ? 'ctr' : ccs.verticalAlign === 'bottom' ? 'b' : (text ? text.anchor : 't'),
        text,
      });
    }));
    const cols = xs.slice(1).map((x, i) => r2(x - xs[i])), rws = ys.slice(1).map((y, i) => r2(y - ys[i]));
    return { cols, rows: rws, cells };
  }
  function chartInfo(el) {
    let spec = null;
    const raw = el.getAttribute('data-chart') || (el.querySelector('script[type="application/json"]') || {}).textContent;
    try { spec = JSON.parse(raw); } catch (e) { warn('chart-json', 'data-chart is not valid JSON: ' + e.message, el); return null; }
    const cs = getComputedStyle(el), col = parseColor(cs.color);
    return { spec, font: { family: cs.fontFamily, size: parseFloat(cs.fontSize), hex: col ? col.hex : '333333', tid: tagTid(el) } };
  }

  // ---------- element dispatch ----------
  function animOf(el) {
    const a = el.dataset.anim;
    if (!a || a === 'none') return null;
    return { effect: a, trigger: el.dataset.animTrigger || 'click', delay: +(el.dataset.animDelay || 0),
      duration: el.dataset.animDuration ? +el.dataset.animDuration : null, order: el.dataset.animOrder !== undefined ? +el.dataset.animOrder : null };
  }

  async function extractElement(el, kind, slideRect) {
    const cs = getComputedStyle(el);
    const frame = frameOf(el, slideRect);
    try {
      const base = { id: 'e' + (nextId++), kind, name: el.dataset.name || null, rotation: r2(frame.rot),
        opacity: r2(opacityOf(el, el.closest('section.slide'))), z: parseInt(cs.zIndex, 10) || 0, anim: animOf(el), src: describe(el) };
      if (frame.scale.other && kind !== 'image') warn('scale', 'scale() transforms are not exported for text/shapes; set real sizes', el);
      const box = { x: r2(frame.box.x), y: r2(frame.box.y), w: r2(frame.box.w), h: r2(frame.box.h) };
      if (box.w < 0.5 || box.h < 0.5) return [];
      if (kind === 'group') {
        const vis = boxVisual(el, cs, box.w, box.h);
        const kids = await collect(el, slideRect);
        if ((el.innerText || '').trim() && !kids.length) warn('group-text', 'group has text but no data-pptx children', el);
        const deco = (vis.fill || vis.line || vis.shadow) ? [{ ...base, id: 'e' + (nextId++), kind: 'shape', name: (base.name || 'group') + ' background', anim: null, box, shape: vis, text: null }] : [];
        return [{ ...base, box, children: [...deco, ...kids] }];
      }
      if (kind === 'image') {
        const info = await imageInfo(el, cs, frame, slideRect);
        if (!info) return [];
        return [{ ...base, box: info.box, image: info.image, shape: info.vis }];
      }
      if (kind === 'table') {
        if (el.tagName !== 'TABLE') { warn('table-tag', 'data-pptx="table" must be on a <table>', el); return []; }
        return [{ ...base, box, table: tableInfo(el, frame), shape: boxVisual(el, cs, box.w, box.h) }];
      }
      if (kind === 'chart') {
        const ch = chartInfo(el);
        return ch ? [{ ...base, box, chart: ch, shape: boxVisual(el, cs, box.w, box.h) }] : [];
      }
      if (kind !== 'text' && kind !== 'shape') { warn('kind', `unknown data-pptx="${kind}"`, el); return []; }
      const vis = boxVisual(el, cs, box.w, box.h);
      const out = [];
      // pieces split off one element (background image, border bars) animate together with it
      const follow = base.anim ? { ...base.anim, trigger: 'with', delay: base.anim.delay } : null;
      let mainAnim = base.anim;
      if (vis.image) {
        const info = await imageInfo(el, cs, frame, slideRect);
        if (info) {
          out.push({ ...base, id: 'e' + (nextId++), kind: 'image', name: (base.name || 'shape') + ' image', anim: base.anim, box: info.box,
            image: { ...info.image, mask: vis.geom, radius: vis.radius }, shape: { fill: null, line: null, bars: [], shadow: vis.shadow } });
          mainAnim = follow;
        }
        vis.shadow = info ? null : vis.shadow;
      }
      const text = extractText(el, frame.origin);
      if (text && text.overflow) warn('overflow', `text overflows its box (${text.overflow_x ? 'horizontally' : 'vertically'}) — the PPTX will overflow too`, el);
      out.push({ ...base, anim: mainAnim, kind: text ? 'text' : 'shape', box, shape: vis, text });
      vis.bars.forEach(s => {
        const bw = s.w;
        const bb = s.side === 'top' ? { x: box.x, y: box.y, w: box.w, h: bw } : s.side === 'bottom' ? { x: box.x, y: box.y + box.h - bw, w: box.w, h: bw }
          : s.side === 'left' ? { x: box.x, y: box.y, w: bw, h: box.h } : { x: box.x + box.w - bw, y: box.y, w: bw, h: box.h };
        out.push({ id: 'e' + (nextId++), kind: 'shape', name: `${base.name || 'border'} ${s.side}`, rotation: base.rotation, opacity: base.opacity, z: base.z, anim: follow,
          box: bb, shape: { fill: { type: 'solid', hex: s.c.hex, alpha: s.c.alpha }, line: null, bars: [], geom: 'rect', radius: 0, shadow: null }, text: null });
      });
      return out;
    } finally { frame.restore(); }
  }

  async function collect(container, slideRect) {
    const out = [];
    const walk = async (node) => {
      for (const ch of node.children) {
        if (ch.matches('aside.notes, script, style, template, noscript')) continue;
        const kind = ch.getAttribute('data-pptx');
        const cs = getComputedStyle(ch);
        if (cs.display === 'none') continue;
        if (kind && kind !== 'ignore') {
          if (cs.visibility === 'hidden') continue;
          out.push(...await extractElement(ch, kind, slideRect));
          if (kind === 'group' || kind === 'table' || kind === 'chart' || kind === 'image') continue;
          await walk(ch);
        } else if (kind !== 'ignore') await walk(ch);
      }
    };
    await walk(container);
    return out.map((e, i) => [e, i]).sort((a, b) => (a[0].z - b[0].z) || (a[1] - b[1])).map(a => a[0]);
  }

  function auditUntagged(slide) {
    const tw = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT);
    const seen = new Set();
    while (tw.nextNode()) {
      const t = tw.currentNode; if (!t.data.trim()) continue;
      const p = t.parentElement;
      if (p.closest('aside.notes, script, style, template, [data-pptx="ignore"], svg')) continue;
      const owner = p.closest('[data-pptx]');
      const ok = owner && slide.contains(owner) && ['text', 'shape', 'table', 'chart'].includes(owner.getAttribute('data-pptx'));
      if (!ok && p.getClientRects().length && getComputedStyle(p).visibility === 'visible' && !seen.has(p)) {
        seen.add(p); warn('untagged-text', 'visible text is not inside a data-pptx text element and will be missing', p);
      }
    }
    slide.querySelectorAll('img, svg, video, canvas, iframe').forEach(el => {
      if (el.closest('[data-pptx="ignore"]') || el.parentElement.closest('svg')) return;
      const owner = el.closest('[data-pptx]');
      if ((!owner || !['image', 'chart'].includes(owner.getAttribute('data-pptx'))) && el.getClientRects().length) warn('untagged-media', 'visible media is not tagged data-pptx="image" and will be missing', el);
    });
    let n = 0;
    slide.querySelectorAll('*').forEach(el => {
      if (n > 5 || el.closest('[data-pptx]') || el.closest('aside.notes, [data-pptx="ignore"]') || el.closest('svg')) return;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility !== 'visible') return;
      if (parseColor(cs.backgroundColor) || (cs.backgroundImage && cs.backgroundImage !== 'none') || parseShadow(cs.boxShadow) || borderInfo(cs).some(s => s.w > 0)) {
        n++; warn('untagged-box', 'visible background/border/shadow outside any data-pptx element will be missing', el);
      }
    });
  }

  // ---------- slides ----------
  const slides = Array.from(document.querySelectorAll('section.slide'));
  if (!slides.length) return { error: 'no <section class="slide"> elements found' };
  const outSlides = [];
  for (const slide of slides) {
    slideNo++;
    slide.scrollIntoView();
    const sr = slide.getBoundingClientRect();
    if (Math.abs(sr.width - W) > 0.5 || Math.abs(sr.height - H) > 0.5) warn('slide-size', `slide is ${sr.width}x${sr.height}, expected ${W}x${H}`, slide);
    const cs = getComputedStyle(slide);
    const bgVis = boxVisual(slide, cs, W, H);
    let bgImage = null;
    if (bgVis.image) {
      const frame = { rot: 0, scale: {}, box: { x: 0, y: 0, w: W, h: H }, origin: sr, restore() {} };
      const info = await imageInfo(slide, cs, frame, sr);
      if (info) bgImage = { box: info.box, image: info.image };
    }
    const notesEl = slide.querySelector('aside.notes');
    auditUntagged(slide);
    outSlides.push({
      index: slideNo, id: slide.id || null,
      background: { fill: bgVis.fill, image: bgImage },
      transition: slide.dataset.transition ? { type: slide.dataset.transition, dir: slide.dataset.transitionDir || null,
        duration: slide.dataset.transitionDuration ? +slide.dataset.transitionDuration : null,
        advance: slide.dataset.advance ? +slide.dataset.advance : null } : null,
      notes: notesEl ? notesEl.textContent.trim().replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n') : '',
      elements: await collect(slide, sr),
    });
  }
  return { canvas: { width: W, height: H }, slides: outSlides, warnings };
}
