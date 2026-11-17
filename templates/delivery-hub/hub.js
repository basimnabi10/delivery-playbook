/* Delivery Hub client script. Reads the data block embedded in the page (#hub-data) to draw the timeline,
   and runs the page router, the release filters, the changelog toggles and the copy buttons.
   No network requests. Everything it shows comes from the page itself. */
(function () {
  'use strict';
  var dataEl = document.getElementById('hub-data');
  var data = null;
  try { data = dataEl ? JSON.parse(dataEl.textContent) : null; } catch (e) { data = null; }

  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var DAY = 864e5, WEEK = 7 * DAY;
  function d(s) { var p = s.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]); }
  function fmtT(t) { var x = new Date(t); return x.getUTCDate() + ' ' + MON[x.getUTCMonth()]; }
  function wk(n) { return n + (n === 1 ? ' week' : ' weeks'); }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  /* ---------- page router: #hours, #sprints, otherwise the release notes ---------- */
  var pages = [].slice.call(document.querySelectorAll('.hub-page'));
  var navLinks = [].slice.call(document.querySelectorAll('.pagenav a'));
  var redraw = function () {};
  function route() {
    var h = '';
    try { h = decodeURIComponent(location.hash.replace('#', '')); } catch (e) { h = ''; }
    var ids = pages.map(function (p) { return p.getAttribute('data-page'); });
    var page = ids.indexOf(h) !== -1 ? h : 'release-notes';
    pages.forEach(function (p) { p.hidden = p.getAttribute('data-page') !== page; });
    navLinks.forEach(function (a) {
      if (a.getAttribute('href') === '#' + page) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
    if (ids.indexOf(h) === -1 && h) { var t = document.getElementById(h); if (t) t.scrollIntoView(); }
    redraw();
  }

  /* ---------- changelog toggle and filters ---------- */
  var btn = document.getElementById('toggle-all');
  var all = [].slice.call(document.querySelectorAll('details.changelog'));
  function syncToggle() {
    if (!btn) return;
    var allOpen = all.every(function (x) { return x.open; });
    btn.textContent = allOpen ? 'Collapse all changelogs' : 'Expand all changelogs';
    btn.setAttribute('aria-pressed', allOpen ? 'true' : 'false');
  }
  if (btn) {
    btn.addEventListener('click', function () {
      var allOpen = all.every(function (x) { return x.open; });
      all.forEach(function (x) { x.open = !allOpen; });
      syncToggle();
    });
    all.forEach(function (x) { x.addEventListener('toggle', syncToggle); });
  }
  var fs = document.getElementById('f-search'), fa = document.getElementById('f-area'), ft = document.getElementById('f-type');
  var line = document.getElementById('result-line');
  var total = document.querySelectorAll('.changes li').length;
  function applyFilters() {
    if (!fs || !fa || !ft) return;
    var q = fs.value.trim().toLowerCase(), ar = fa.value, ty = ft.value, active = !!(q || ar || ty), shown = 0;
    [].forEach.call(document.querySelectorAll('section.release'), function (sec) {
      var secShown = 0, secTotal = 0;
      [].forEach.call(sec.querySelectorAll('.group'), function (g) {
        var gShown = 0;
        [].forEach.call(g.querySelectorAll('.changes li'), function (li) {
          secTotal++;
          var ok = (!ar || g.getAttribute('data-area') === ar) &&
                   (!ty || li.querySelector('.tag').classList.contains(ty)) &&
                   (!q || li.textContent.toLowerCase().indexOf(q) !== -1);
          li.hidden = !ok;
          if (ok) { gShown++; secShown++; }
        });
        g.hidden = gShown === 0;
      });
      shown += secShown;
      sec.classList.toggle('filtering', active);
      sec.classList.toggle('no-match', active && secShown === 0);
      var c = sec.querySelector('summary .count');
      if (c) c.textContent = active ? (secShown + ' of ' + secTotal + ' changes') : (secTotal + (secTotal === 1 ? ' change' : ' changes'));
      var det = sec.querySelector('details.changelog');
      if (det && active) det.open = secShown > 0;
    });
    if (line) line.textContent = active ? ('Showing ' + shown + ' of ' + total + ' changes' + (shown === 0 ? '. Try a different search or filter.' : '')) : '';
    syncToggle();
  }
  [fs, fa, ft].forEach(function (x) { if (x) { x.addEventListener('input', applyFilters); x.addEventListener('change', applyFilters); } });

  /* ---------- copy buttons ---------- */
  [].forEach.call(document.querySelectorAll('.prompts .copy'), function (b) {
    b.addEventListener('click', function () {
      var q = b.parentNode.querySelector('q'), text = q.textContent;
      function done(ok) { b.textContent = ok ? 'Copied' : 'Selected'; setTimeout(function () { b.textContent = 'Copy'; }, 1600); }
      function fallback() { var r = document.createRange(); r.selectNodeContents(q); var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r); done(false); }
      try { navigator.clipboard.writeText(text).then(function () { done(true); }, fallback); } catch (e) { fallback(); }
    });
  });

  /* ---------- timeline chart, drawn from the embedded data ---------- */
  function mix(i, n) {
    if (!(window.CSS && CSS.supports && CSS.supports('color', 'color-mix(in oklab, red 50%, blue)')) || n < 2) return '';
    var p = Math.round(i / (n - 1) * 100);
    return 'color-mix(in oklab, var(--primary) ' + (100 - p) + '%, var(--green))';
  }
  function niceStep(max) {
    var steps = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000];
    for (var i = 0; i < steps.length; i++) if (max / steps[i] <= 4) return steps[i];
    return 1000;
  }
  function buildChart() {
    var host = document.getElementById('pr-chart');
    if (!host || !data) return;
    var wc = data.weekly_counts || { weeks: [] };
    var weeks = wc.weeks || [];
    var phases = (data.phases || []).map(function (p) { return { name: p.name, short: p.short_label || '', gapShort: p.gap_short_label || '', a: d(p.start), b: d(p.end) + DAY }; }).sort(function (x, y) { return x.a - y.a; });
    var miles = (data.milestones || []).slice().sort(function (x, y) { return d(x.date) - d(y.date); });
    if (!weeks.length && !phases.length && !miles.length) { host.innerHTML = '<p class="empty-note">The timeline will appear when phases, milestones or weekly counts are added.</p>'; return; }

    var anchor = weeks.length ? d(weeks[0].week_ending) - 6 * DAY : (phases.length ? phases[0].a : d(miles[0].date));
    var lo = anchor;
    if (phases.length) lo = Math.min(lo, phases[0].a);
    if (miles.length) lo = Math.min(lo, d(miles[0].date));
    var t0 = anchor - Math.ceil((anchor - lo) / WEEK) * WEEK;
    var hi = 0;
    if (weeks.length) hi = Math.max(hi, d(weeks[weeks.length - 1].week_ending) + DAY);
    if (phases.length) hi = Math.max(hi, phases[phases.length - 1].b);
    if (miles.length) hi = Math.max(hi, d(miles[miles.length - 1].date) + DAY);
    var NW = Math.max(1, Math.ceil((hi - t0) / WEEK));
    var counts = {};
    weeks.forEach(function (w) { counts[d(w.week_ending) - 6 * DAY] = w.merged; });
    var lastCounted = weeks.length ? d(weeks[weeks.length - 1].week_ending) - 6 * DAY : null;
    var allWeeks = [];
    for (var i = 0; i < NW; i++) {
      var tw = t0 + i * WEEK;
      allWeeks.push({ t: tw, v: Object.prototype.hasOwnProperty.call(counts, tw) ? counts[tw] : null, partial: !!wc.partial_week && tw === lastCounted });
    }

    var now = new Date(), TODAY = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    var cur = null, curI = -1;
    phases.forEach(function (p, k) { if (p.a <= TODAY && TODAY < p.b) { cur = p; curI = k; } });
    var tToday = cur ? Math.min(Math.max(TODAY, cur.a), cur.b) : null;
    function phaseOf(t) {
      for (var k = 0; k < phases.length; k++) {
        var p = phases[k];
        if (t >= p.a && t < p.b) return (k === curI) ? (t < tToday ? p.name + ': elapsed' : p.name + ': time remaining') : p.name;
        if (k + 1 < phases.length && t >= p.b && t < phases[k + 1].a) return 'Gap';
      }
      return '\u2013';
    }

    /* the "time left" figure */
    var kpi = document.getElementById('phase-left');
    if (kpi) kpi.textContent = cur ? wk(Math.max(0, Math.ceil((cur.b - TODAY) / WEEK))) : '\u2013';

    /* legend */
    var lg = document.getElementById('phase-legend');
    if (lg) {
      var rows = [], EN = ' \u2013 ', DOT = ' \u00b7 ';
      phases.forEach(function (p, k) {
        var cls = 'sw-' + (k % 2);
        if (k === curI) {
          rows.push([cls, p.name + ': elapsed', fmtT(p.a) + EN + fmtT(tToday) + DOT + wk(Math.round((tToday - p.a) / WEEK))]);
          rows.push(['sw-left', p.name + ': time remaining', fmtT(tToday) + EN + fmtT(p.b - DAY) + DOT + wk(Math.max(0, Math.ceil((p.b - tToday) / WEEK)))]);
        } else {
          rows.push([cls, p.name, fmtT(p.a) + EN + fmtT(p.b - DAY) + DOT + wk(Math.round((p.b - p.a) / WEEK))]);
        }
        if (k + 1 < phases.length && phases[k + 1].a > p.b) rows.push(['sw-gap', 'Gap before ' + phases[k + 1].name, fmtT(p.b) + EN + fmtT(phases[k + 1].a - DAY) + DOT + wk(Math.round((phases[k + 1].a - p.b) / WEEK))]);
      });
      if (TODAY >= t0 && TODAY <= hi) rows.push(['sw-today', 'Today', fmtT(TODAY)]);
      lg.innerHTML = rows.map(function (r) {
        return '<li><span class="sw ' + r[0] + '" aria-hidden="true"></span><span class="lg-name">' + esc(r[1]) + '</span><span class="lg-meta">' + esc(r[2]) + '</span></li>';
      }).join('');
    }

    /* table view */
    var tb = document.querySelector('#pr-table tbody');
    if (tb) {
      tb.innerHTML = '';
      allWeeks.forEach(function (w) {
        var tr = document.createElement('tr');
        tr.innerHTML = '<td>' + fmtT(w.t + 6 * DAY) + (w.partial ? ' (partial)' : '') + '</td><td>' + esc(phaseOf(w.t)) + '</td><td class="num">' + (w.v === null ? 'not yet counted' : w.v) + '</td>';
        tb.appendChild(tr);
      });
    }

    /* milestone list */
    var ol = document.getElementById('milestones');
    if (ol) {
      ol.innerHTML = '';
      miles.forEach(function (ms, k) {
        var li = document.createElement('li'), future = d(ms.date) > TODAY;
        li.innerHTML = '<span class="n' + (future ? ' future' : '') + '">' + (k + 1) + '</span><span class="when">' + fmtT(d(ms.date)) + '</span><span>' + esc(ms.title) + '</span>';
        var mc = mix(k, miles.length); if (mc && !future) li.querySelector('.n').style.background = mc;
        ol.appendChild(li);
      });
    }

    host.setAttribute('aria-label', 'Timeline from the week ending ' + fmtT(t0 + 6 * DAY) + ' to the week ending ' + fmtT(t0 + (NW - 1) * WEEK + 6 * DAY) + ', shaded by phase. ' +
      phases.map(function (p) { return p.name + ' runs from ' + fmtT(p.a) + ' to ' + fmtT(p.b - DAY); }).join('. ') + (phases.length ? '. ' : '') +
      'Bars show pull requests merged per week, ' + (wc.total || 0) + ' in total. ' + miles.length + ' milestones are marked.');

    var tip = document.createElement('div'); tip.className = 'tip'; tip.hidden = true;
    var NS = 'http://www.w3.org/2000/svg';
    function el(n, a) { var e = document.createElementNS(NS, n); for (var k in a) e.setAttribute(k, a[k]); return e; }
    var maxV = 0; allWeeks.forEach(function (w) { if (w.v > maxV) maxV = w.v; });
    var step = niceStep(Math.max(maxV, 4)), max = Math.ceil(Math.max(maxV, 4) / step) * step;

    function draw() {
      var W = host.clientWidth || 700, H = host.clientHeight || 290;
      var m = { l: 30, r: 8, t: 32, b: 66 };
      var pw = W - m.l - m.r, ph = H - m.t - m.b, band = pw / NW;
      var y = function (v) { return m.t + ph - (v / max) * ph; };
      var x = function (t) { return m.l + (t - t0) / WEEK * band; };
      var bw = Math.max(4, Math.min(24, band - 2));
      var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H });
      var defs = el('defs', {});
      var pat = el('pattern', { id: 'left-hatch', patternUnits: 'userSpaceOnUse', width: 6, height: 6, patternTransform: 'rotate(45)' });
      pat.appendChild(el('rect', { width: 6, height: 6, class: 'ph-left-bg' }));
      pat.appendChild(el('line', { x1: 1, y1: 0, x2: 1, y2: 6, class: 'hatch-l' }));
      defs.appendChild(pat); svg.appendChild(defs);

      var SY = 6, SH = 18, CH = 6.6, bands = [];
      phases.forEach(function (p, k) {
        var c = 'c' + (k % 2);
        if (k === curI) {
          bands.push({ a: p.a, b: tToday, cls: 'ph-' + (k % 2), tc: c, labels: [p.name.toUpperCase() + ': ELAPSED', 'ELAPSED'] });
          bands.push({ a: tToday, b: p.b, cls: 'ph-left', tc: 'left', labels: [p.name.toUpperCase() + ': TIME LEFT', 'TIME LEFT'] });
        } else {
          bands.push({ a: p.a, b: p.b, cls: 'ph-' + (k % 2), tc: c, labels: [p.name.toUpperCase()].concat(p.short ? [p.short.toUpperCase()] : [], [p.name.split(':')[0].toUpperCase()]) });
        }
        var nx = phases[k + 1];
        if (nx && nx.a > p.b) bands.push({ a: p.b, b: nx.a, cls: 'ph-gap', tc: 'gap', labels: ['GAP BEFORE ' + nx.name.toUpperCase()].concat(nx.gapShort ? [nx.gapShort.toUpperCase()] : []), last: 'GAP' });
      });
      bands.forEach(function (bd) {
        var xa = x(bd.a), xb = Math.min(x(bd.b), W - m.r), w = xb - xa;
        if (w <= 0.5) return;
        svg.appendChild(bd.cls === 'ph-left'
          ? el('rect', { x: xa, y: m.t, width: w, height: ph, fill: 'url(#left-hatch)' })
          : el('rect', { x: xa, y: m.t, width: w, height: ph, class: bd.cls }));
        svg.appendChild(el('rect', { x: xa, y: SY, width: Math.max(0, w - 1), height: SH, rx: 3, class: bd.cls === 'ph-left' ? 'ph-left-bg' : bd.cls }));
        /* the first label that fits; otherwise the first one cut from its start, never a made-up abbreviation */
        var lab = '';
        for (var k = 0; k < bd.labels.length && !lab; k++) if (bd.labels[k].length * CH + 10 <= w) lab = bd.labels[k];
        if (!lab) { var fit = Math.floor((w - 10) / CH) - 1; if (fit >= 3) lab = bd.labels[0].slice(0, fit).replace(/\s+$/, '') + '\u2026'; }
        if (!lab && bd.last && bd.last.length * CH + 10 <= w) lab = bd.last;
        if (lab) { var st = el('text', { x: xa + 5, y: SY + 12.5, class: 'st-t ' + bd.tc }); st.textContent = lab; svg.appendChild(st); }
      });
      for (var v = 0; v <= max; v += step) {
        svg.appendChild(el('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: 'grid' }));
        var t = el('text', { x: m.l - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'axis-t' }); t.textContent = v; svg.appendChild(t);
      }
      var cd = new Date(t0); cd = Date.UTC(cd.getUTCFullYear(), cd.getUTCMonth(), 1);
      while (cd < t0 + NW * WEEK) {
        if (cd >= t0) { var mt = el('text', { x: x(cd), y: m.t + ph + 16, class: 'axis-t' }); mt.textContent = MON[new Date(cd).getUTCMonth()]; svg.appendChild(mt); }
        var nd = new Date(cd); cd = Date.UTC(nd.getUTCFullYear(), nd.getUTCMonth() + 1, 1);
      }
      allWeeks.forEach(function (w) {
        if (!w.v) return;
        var cx = x(w.t) + band / 2, x0 = cx - bw / 2, top = y(w.v), base = y(0), r = Math.min(4, (base - top) / 2, bw / 2);
        var path = 'M' + x0 + ',' + base + 'V' + (top + r) + 'Q' + x0 + ',' + top + ' ' + (x0 + r) + ',' + top +
                   'H' + (x0 + bw - r) + 'Q' + (x0 + bw) + ',' + top + ' ' + (x0 + bw) + ',' + (top + r) + 'V' + base + 'Z';
        svg.appendChild(el('path', { d: path, class: 'bar' + (w.partial ? ' partial' : '') }));
        if (w.v === maxV) {
          var vt = bw >= 16
            ? el('text', { x: cx, y: top + 14, 'text-anchor': 'middle', class: 'val-in' })
            : el('text', { x: cx + bw / 2 + 3, y: top + 10, 'text-anchor': 'start', class: 'val-t' });
          vt.textContent = String(w.v); svg.appendChild(vt);
        }
      });
      var mx = miles.map(function (ms) { return x(d(ms.date)); });
      miles.forEach(function (ms, i) {
        svg.appendChild(el('line', { x1: mx[i], x2: mx[i], y1: m.t, y2: m.t + ph, class: 'ms-line' + (d(ms.date) > TODAY ? ' future' : '') }));
      });
      if (TODAY >= t0 && TODAY <= hi) {
        var tx = x(TODAY);
        svg.appendChild(el('line', { x1: tx, x2: tx, y1: SY, y2: m.t + ph, class: 'today-line' }));
        var right = tx + 6 + 40 < W - m.r;
        var tt = el('text', { x: right ? tx + 5 : tx - 5, y: m.t + 12, 'text-anchor': right ? 'start' : 'end', class: 'today-t' }); tt.textContent = 'TODAY'; svg.appendChild(tt);
      }
      var rad = band < 20 ? 7 : 8, gap = 2 * rad + 2;
      var rowY = [m.t + ph + 34, m.t + ph + 34 + 2 * rad + 3], last = [-1e9, -1e9];
      miles.forEach(function (ms, i) {
        var dx = mx[i], best = 0, bx = Infinity;
        for (var r = 0; r < 2; r++) { var px = Math.max(dx, last[r] + gap); if (px - dx < bx - dx - 0.01) { bx = px; best = r; } }
        bx = Math.min(bx, W - rad - 1); last[best] = bx;
        var cy = rowY[best], future = d(ms.date) > TODAY;
        if (Math.abs(bx - dx) > 0.5 || best === 1) svg.appendChild(el('line', { x1: dx, y1: m.t + ph + 21, x2: bx, y2: cy - rad, class: 'ms-link' }));
        var dot = el('circle', { cx: bx, cy: cy, r: rad, class: 'ms-dot' + (future ? ' future' : '') });
        var mc = mix(i, miles.length); if (mc && !future) dot.style.fill = mc; svg.appendChild(dot);
        var tn = el('text', { x: bx, y: cy + 3.5, 'text-anchor': 'middle', class: 'ms-num' + (future ? ' future' : '') }); tn.textContent = i + 1; svg.appendChild(tn);
      });
      allWeeks.forEach(function (w) {
        var xa = x(w.t), cx = xa + band / 2, ph2 = phaseOf(w.t);
        var what = w.v === null ? 'not yet counted' : w.v + ' pull request' + (w.v === 1 ? '' : 's');
        var hit = el('rect', { x: xa, y: m.t, width: band, height: ph, class: 'hit', tabindex: '0', 'aria-label': 'Week ending ' + fmtT(w.t + 6 * DAY) + ': ' + what + ', ' + ph2 });
        function show() {
          tip.textContent = 'Week ending ' + fmtT(w.t + 6 * DAY) + ' \u00b7 ' + what + '\n' + ph2;
          tip.style.left = Math.max(118, Math.min(W - 118, cx)) + 'px'; tip.style.top = (y(w.v || 0) - 10) + 'px'; tip.hidden = false;
        }
        hit.addEventListener('mouseenter', show); hit.addEventListener('focus', show);
        hit.addEventListener('mouseleave', function () { tip.hidden = true; }); hit.addEventListener('blur', function () { tip.hidden = true; });
        svg.appendChild(hit);
      });
      host.innerHTML = ''; host.appendChild(svg); host.appendChild(tip);
    }
    redraw = function () { if (host.clientWidth) draw(); };
    draw();
    if (window.ResizeObserver) new ResizeObserver(function () { if (host.clientWidth) draw(); }).observe(host);
    else window.addEventListener('resize', redraw);
  }

  buildChart();
  window.addEventListener('hashchange', route);
  route();
  applyFilters();
})();
