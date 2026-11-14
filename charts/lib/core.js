/* Live charts — shared helpers.
 * Load this file first, then one file per chart type you use
 * (stat-tile.js, stream-chart.js, ranked-bars.js, funnel.js,
 * stacked-bars.js, paired-bars.js, diverging-bars.js).
 * Each of those adds one function to window.LiveCharts.
 * Needs ../live-charts.css, and a wrapper with class "lc" for the colour tokens.
 */
(function (global) {
  'use strict';

  var SVG_NS = 'http://www.w3.org/2000/svg';
  var reduceMotion = global.matchMedia
    ? global.matchMedia('(prefers-reduced-motion: reduce)')
    : { matches: false };

  /* ---------- helpers ---------- */

  function h(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function s(tag, attrs) {
    var node = document.createElementNS(SVG_NS, tag);
    for (var k in attrs) node.setAttribute(k, attrs[k]);
    return node;
  }

  function formatter(decimals) {
    var f = new Intl.NumberFormat('en', {
      minimumFractionDigits: decimals || 0,
      maximumFractionDigits: decimals || 0
    });
    return function (v) { return f.format(v); };
  }

  // Clean axis maximum and tick step for a value (steps of 1, 2 or 5 × 10^k).
  function niceScale(v) {
    var raw = Math.max(v, 1e-9) / 4;
    var p = Math.pow(10, Math.floor(Math.log10(raw)));
    var f = raw / p;
    var step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p;
    return { max: Math.ceil(v / step) * step, step: step };
  }

  // Animate the number shown in a node from its current value to `to`.
  function tweenNumber(node, to, format) {
    var from = node._lcCur == null ? 0 : node._lcCur;
    cancelAnimationFrame(node._lcRaf);
    if (reduceMotion.matches || from === to) {
      node._lcCur = to;
      node.textContent = format(to);
      return;
    }
    var start = performance.now();
    (function step(now) {
      var k = Math.max(0, Math.min(1, (now - start) / 700));
      var eased = 1 - Math.pow(1 - k, 3);
      node._lcCur = from + (to - from) * eased;
      node.textContent = format(node._lcCur);
      if (k < 1) node._lcRaf = requestAnimationFrame(step);
    })(start);
  }

  /* ---------- tooltip (one shared element) ---------- */

  var tip;

  function tipShow(x, y, build) {
    if (!tip) {
      tip = h('div', 'lc lc-tip');
      document.body.appendChild(tip);
    }
    if (build) {
      tip.textContent = '';
      build(tip);
    }
    tip.style.display = 'block';
    var w = tip.offsetWidth, ht = tip.offsetHeight;
    var left = x + 14, top = y - ht - 10;
    if (left + w > global.innerWidth - 8) left = x - w - 14;
    if (left < 8) left = 8;
    if (top < 8) top = y + 16;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }

  function tipHide() {
    if (tip) tip.style.display = 'none';
  }

  function tipRow(parent, color, shape, value, name) {
    var row = h('div', 'lc-tip-row');
    if (color) {
      var key = h('span', shape === 'box' ? 'lc-key-box' : 'lc-key-line');
      key.style.background = color;
      row.appendChild(key);
    }
    row.appendChild(h('strong', null, value));
    row.appendChild(h('span', null, name));
    parent.appendChild(row);
  }

  // Same details on hover and on keyboard focus.
  function attachTip(node, build) {
    node.tabIndex = 0;
    node.addEventListener('pointermove', function (e) { tipShow(e.clientX, e.clientY, build); });
    node.addEventListener('pointerleave', tipHide);
    node.addEventListener('focus', function () {
      var r = node.getBoundingClientRect();
      tipShow(r.left + r.width / 2, r.top, build);
    });
    node.addEventListener('blur', tipHide);
  }

  function legend(items, shape) {
    var box = h('div', 'lc-legend');
    items.forEach(function (it) {
      var item = h('span', 'lc-legend-item');
      var key = h('span', shape === 'box' ? 'lc-key-box' : 'lc-key-line');
      key.style.background = it.color;
      item.appendChild(key);
      item.appendChild(h('span', null, it.label));
      it.valueNode = h('strong');
      item.appendChild(it.valueNode);
      box.appendChild(item);
    });
    return box;
  }

  // `_` holds the helpers the chart files share; it is not a public API.
  global.LiveCharts = {
    _: {
      reduceMotion: reduceMotion,
      h: h,
      s: s,
      formatter: formatter,
      niceScale: niceScale,
      tweenNumber: tweenNumber,
      tipShow: tipShow,
      tipHide: tipHide,
      tipRow: tipRow,
      attachTip: attachTip,
      legend: legend
    }
  };
})(window);
