(function (LC) {
  'use strict';

  var h = LC._.h;
  var formatter = LC._.formatter;
  var tweenNumber = LC._.tweenNumber;
  var tipRow = LC._.tipRow;
  var attachTip = LC._.attachTip;

  /* ---------- diverging bars ----------
     Values on both sides of zero (for example a correlation, −1 to +1).
     opts: { extent?, decimals?, negColor?, posColor?, footnote? }
     update([{ label, value, mark?, details?: [[value, name], …] }]) */

  function divergingBars(root, opts) {
    opts = opts || {};
    var extent = opts.extent || 1;
    var fmt = formatter(opts.decimals == null ? 2 : opts.decimals);
    var neg = opts.negColor || 'var(--lc-s1)';
    var pos = opts.posColor || 'var(--lc-s2)';
    var rows = [];
    function show(v) { return (v < 0 ? '−' : v > 0 ? '+' : '') + fmt(Math.abs(v)); }

    root.classList.add('lc-diverging');
    var head = h('div', 'lc-row lc-target-head');
    head.appendChild(h('span'));
    var scale = h('div', 'lc-track lc-div-scale');
    [['−' + extent, '0%', 'start'], ['0', '50%', 'mid'], ['+' + extent, '100%', 'end']].forEach(function (t) {
      var tick = h('span', 'lc-div-tick is-' + t[2], t[0]);
      tick.style.left = t[1];
      scale.appendChild(tick);
    });
    head.appendChild(scale);
    head.appendChild(h('span'));
    root.appendChild(head);
    var list = h('div', 'lc-rows');
    list.setAttribute('role', 'list');
    root.appendChild(list);
    if (opts.footnote) root.appendChild(h('div', 'lc-footnote', opts.footnote));

    function create(item) {
      var row = h('div', 'lc-row');
      row.setAttribute('role', 'listitem');
      var r = { row: row, item: item };
      r.label = h('span', 'lc-row-label');
      row.appendChild(r.label);
      var track = h('div', 'lc-track');
      r.bar = h('div', 'lc-bar lc-div-bar');
      r.bar.style.left = '50%';
      track.appendChild(r.bar);
      var zero = h('div', 'lc-target-line');
      zero.style.left = '50%';
      track.appendChild(zero);
      row.appendChild(track);
      var value = h('span', 'lc-row-value');
      r.num = h('span');
      r.mark = h('small');
      value.appendChild(r.num);
      value.appendChild(r.mark);
      row.appendChild(value);
      attachTip(row, function (t) {
        t.appendChild(h('div', 'lc-tip-head', r.item.fullLabel || r.item.label));
        tipRow(t, r.item.value < 0 ? neg : pos, 'box', show(r.item.value), opts.valueLabel || '');
        (r.item.details || []).forEach(function (d) { tipRow(t, null, null, d[0], d[1]); });
      });
      list.appendChild(row);
      row.offsetWidth;
      return r;
    }

    function update(items) {
      items.forEach(function (item, i) {
        var r = rows[i] || (rows[i] = create(item));
        r.item = item;
        r.row.hidden = false;
        r.label.textContent = item.label;
        var half = Math.min(1, Math.abs(item.value) / extent) * 50;
        r.bar.style.left = (item.value < 0 ? 50 - half : 50) + '%';
        r.bar.style.width = half + '%';
        r.bar.style.background = item.value < 0 ? neg : pos;
        r.bar.classList.toggle('is-neg', item.value < 0);
        tweenNumber(r.num, item.value, show);
        r.mark.textContent = item.mark || '';
        r.row.setAttribute('aria-label',
          (item.fullLabel || item.label) + ': ' + show(item.value) + (item.mark ? ' ' + item.mark : ''));
      });
      for (var i = items.length; i < rows.length; i++) rows[i].row.hidden = true;
    }

    return { update: update };
  }

  LC.divergingBars = divergingBars;
})(window.LiveCharts);
