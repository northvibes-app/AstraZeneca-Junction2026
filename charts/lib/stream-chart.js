(function (LC) {
  'use strict';

  var h = LC._.h;
  var s = LC._.s;
  var formatter = LC._.formatter;
  var niceScale = LC._.niceScale;
  var tweenNumber = LC._.tweenNumber;
  var tipShow = LC._.tipShow;
  var tipHide = LC._.tipHide;
  var tipRow = LC._.tipRow;
  var legend = LC._.legend;
  var reduceMotion = LC._.reduceMotion;
  var uid = 0;

  /* ---------- streaming line chart ----------
     opts: { series: [{ key, label, color }], window?, interval?, height?,
             decimals?, unit? }
     `interval` is the expected time between push() calls in ms; the line
     slides one step to the left over that time. */

  function streamChart(root, opts) {
    var series = opts.series;
    var win = opts.window || 40;
    var interval = opts.interval || 1500;
    var H = opts.height || 220;
    var m = { t: 10, r: 10, b: 24, l: 34 };
    var fmt = formatter(opts.decimals);
    var unit = opts.unit ? ' ' + opts.unit : '';

    root.classList.add('lc-stream');
    root.appendChild(legend(series, 'line'));

    var plot = h('div', 'lc-plot');
    var svg = s('svg', { height: H, role: 'img', tabindex: 0,
      'aria-label': (opts.label || 'Live chart') + '. Use left and right arrow keys to read values.' });
    var clipId = 'lc-clip-' + (++uid);
    var defs = s('defs', {});
    var clip = s('clipPath', { id: clipId });
    var clipRect = s('rect', { x: m.l, y: 0, height: H });
    clip.appendChild(clipRect);
    defs.appendChild(clip);
    svg.appendChild(defs);

    var gGrid = s('g', {});
    var gX = s('g', {});
    var baseline = s('line', { 'class': 'lc-baseline' });
    var cross = s('line', { 'class': 'lc-cross', visibility: 'hidden' });
    var gLines = s('g', { 'clip-path': 'url(#' + clipId + ')' });
    var gDots = s('g', {});
    [gGrid, gX, baseline, cross, gLines, gDots].forEach(function (g) { svg.appendChild(g); });

    series.forEach(function (sr) {
      sr.path = s('path', { 'class': 'lc-line' });
      sr.path.style.stroke = sr.color;
      gLines.appendChild(sr.path);
      sr.dot = s('circle', { 'class': 'lc-dot', r: 5, visibility: 'hidden' });
      sr.dot.style.fill = sr.color;
      gDots.appendChild(sr.dot);
      sr.hoverDot = s('circle', { 'class': 'lc-dot', r: 5, visibility: 'hidden' });
      sr.hoverDot.style.fill = sr.color;
      gDots.appendChild(sr.hoverDot);
    });
    plot.appendChild(svg);
    root.appendChild(plot);

    // Table view: every value is reachable without hovering.
    var details = h('details', 'lc-table');
    details.appendChild(h('summary', null, 'Show latest values as a table'));
    var table = h('table');
    details.appendChild(table);
    root.appendChild(details);
    details.addEventListener('toggle', renderTable);

    var W = 0;
    var pts = [];
    var lastPush = 0;
    var yMax = 0, yTarget = niceScale(opts.minMax || 10);
    var ticks = [];
    var hover = null;       // { x } from pointer, or { back } from keyboard
    var shownPoint = null;
    var raf = 0;

    function layout() {
      W = plot.clientWidth;
      if (!W) return;
      svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
      clipRect.setAttribute('width', W - m.l - m.r);
      baseline.setAttribute('x1', m.l);
      baseline.setAttribute('x2', W - m.r);
      baseline.setAttribute('y1', H - m.b + 0.5);
      baseline.setAttribute('y2', H - m.b + 0.5);
      // Time axis is relative ("now" at the right edge), so it never scrolls.
      gX.textContent = '';
      var span = (win - 1) * interval / 1000;
      var parts = W < 420 ? 2 : 4;
      for (var i = 0; i <= parts; i++) {
        var secs = Math.round(span * (1 - i / parts));
        var label = s('text', {
          'class': 'lc-tick',
          x: m.l + (W - m.l - m.r) * i / parts,
          y: H - 6,
          'text-anchor': i === 0 ? 'start' : i === parts ? 'end' : 'middle'
        });
        label.textContent = secs === 0 ? 'now' : '−' + secs + ' s';
        gX.appendChild(label);
      }
    }

    function buildTicks() {
      gGrid.textContent = '';
      ticks = [];
      for (var v = yTarget.step; v <= yTarget.max + 1e-9; v += yTarget.step) {
        var line = s('line', { 'class': 'lc-gridline' });
        var text = s('text', { 'class': 'lc-tick', 'text-anchor': 'end' });
        text.textContent = fmt(v);
        gGrid.appendChild(line);
        gGrid.appendChild(text);
        ticks.push({ v: v, line: line, text: text });
      }
    }

    function renderTable() {
      if (!details.open) return;
      table.textContent = '';
      var head = h('tr');
      head.appendChild(h('th', null, 'Time'));
      series.forEach(function (sr) { head.appendChild(h('th', null, sr.label)); });
      table.appendChild(head);
      pts.slice(-8).reverse().forEach(function (p) {
        var tr = h('tr');
        tr.appendChild(h('td', null, p.t.toLocaleTimeString()));
        series.forEach(function (sr) { tr.appendChild(h('td', null, fmt(p.v[sr.key]) + unit)); });
        table.appendChild(tr);
      });
    }

    function push(point) {
      pts.push({ t: point.t || new Date(), v: point.values });
      if (pts.length > win + 2) pts.shift();
      lastPush = performance.now();

      var peak = opts.minMax || 10;
      pts.forEach(function (p) {
        series.forEach(function (sr) { peak = Math.max(peak, p.v[sr.key]); });
      });
      var next = niceScale(peak * 1.1);
      if (next.max !== yTarget.max || !ticks.length) {
        yTarget = next;
        buildTicks();
      }
      if (!yMax) yMax = yTarget.max;

      series.forEach(function (sr) {
        tweenNumber(sr.valueNode, point.values[sr.key], function (v) { return fmt(v) + unit; });
      });
      renderTable();
    }

    function frame(now) {
      raf = requestAnimationFrame(frame);
      var n = pts.length;
      if (!W || !n) return;

      var still = reduceMotion.matches;
      var p = still ? 1 : Math.min(1, (now - lastPush) / interval);
      yMax += (yTarget.max - yMax) * (still ? 1 : 0.12);

      var pw = W - m.l - m.r, ph = H - m.t - m.b;
      var step = pw / (win - 1);
      var right = m.l + pw;
      function X(i) { return right - (n - 1 - i) * step + step * (1 - p); }
      function Y(v) { return m.t + ph - (v / yMax) * ph; }

      ticks.forEach(function (tk) {
        var y = Math.round(Y(tk.v)) + 0.5;
        var visible = y >= m.t - 1;
        tk.line.setAttribute('visibility', visible ? 'visible' : 'hidden');
        tk.text.setAttribute('visibility', visible ? 'visible' : 'hidden');
        tk.line.setAttribute('x1', m.l);
        tk.line.setAttribute('x2', right);
        tk.line.setAttribute('y1', y);
        tk.line.setAttribute('y2', y);
        tk.text.setAttribute('x', m.l - 8);
        tk.text.setAttribute('y', y + 4);
      });

      series.forEach(function (sr) {
        var d = '';
        for (var i = 0; i < n; i++) {
          d += (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(pts[i].v[sr.key]).toFixed(1);
        }
        sr.path.setAttribute('d', d);
        // The end dot sits on the right edge, where the line is right now.
        var cur = pts[n - 1].v[sr.key];
        var prev = (pts[n - 2] || pts[n - 1]).v[sr.key];
        sr.dot.setAttribute('cx', right);
        sr.dot.setAttribute('cy', Y(prev + (cur - prev) * p));
        sr.dot.setAttribute('visibility', 'visible');
      });

      // Crosshair snaps to the nearest point that is on screen.
      var idx = -1;
      if (hover) {
        var last = X(n - 1) > right + 0.5 ? n - 2 : n - 1;
        var first = 0;
        while (first < last && X(first) < m.l - 0.5) first++;
        if (last >= first) {
          idx = hover.back != null
            ? last - hover.back
            : Math.round((hover.x - X(0)) / step);
          idx = Math.max(first, Math.min(last, idx));
        }
      }
      if (idx < 0) {
        cross.setAttribute('visibility', 'hidden');
        series.forEach(function (sr) { sr.hoverDot.setAttribute('visibility', 'hidden'); });
        if (shownPoint) { shownPoint = null; tipHide(); }
        return;
      }
      var pt = pts[idx], cx = X(idx);
      cross.setAttribute('visibility', 'visible');
      cross.setAttribute('x1', cx);
      cross.setAttribute('x2', cx);
      cross.setAttribute('y1', m.t);
      cross.setAttribute('y2', m.t + ph);
      series.forEach(function (sr) {
        sr.hoverDot.setAttribute('visibility', 'visible');
        sr.hoverDot.setAttribute('cx', cx);
        sr.hoverDot.setAttribute('cy', Y(pt.v[sr.key]));
      });
      var box = svg.getBoundingClientRect();
      var changed = pt !== shownPoint;
      shownPoint = pt;
      tipShow(box.left + cx, box.top + m.t + 24, changed ? function (t) {
        t.appendChild(h('div', 'lc-tip-head', pt.t.toLocaleTimeString()));
        series.forEach(function (sr) {
          tipRow(t, sr.color, 'line', fmt(pt.v[sr.key]) + unit, sr.label);
        });
      } : null);
    }

    svg.addEventListener('pointermove', function (e) {
      hover = { x: e.clientX - svg.getBoundingClientRect().left };
    });
    svg.addEventListener('pointerleave', function () { hover = null; });
    svg.addEventListener('focus', function () { if (!hover) hover = { back: 0 }; });
    svg.addEventListener('blur', function () { hover = null; });
    svg.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      e.preventDefault();
      var back = hover && hover.back != null ? hover.back : 0;
      back += e.key === 'ArrowLeft' ? 1 : -1;
      hover = { back: Math.max(0, Math.min(win - 1, back)) };
    });

    var ro = new ResizeObserver(layout);
    ro.observe(plot);
    layout();
    raf = requestAnimationFrame(frame);

    return {
      push: push,
      destroy: function () {
        cancelAnimationFrame(raf);
        ro.disconnect();
      }
    };
  }

  LC.streamChart = streamChart;
})(window.LiveCharts);
