(function (LC) {
  'use strict';

  var h = LC._.h;
  var formatter = LC._.formatter;
  var tweenNumber = LC._.tweenNumber;
  var tipRow = LC._.tipRow;
  var attachTip = LC._.attachTip;

  /* ---------- ranked bars ----------
     Rows re-sort themselves as values change.
     opts: { max, unit?, decimals?, order?: 'desc' | 'asc', valueLabel?,
             target?: { value, label }, flagNote? }
     update(items, changes?) — items: [{ id, label, value, flagged?, details? }]
     `changes` replaces any of the options above (for example a new scale).
     A row is flagged when item.flagged is true or, if that is not given,
     when its value is above the target. */

  function rankedBars(root, opts) {
    var cfg = {};
    var fmt, unit;
    var rows = {};
    var order = [];

    root.classList.add('lc-ranked');
    var head = h('div', 'lc-row lc-target-head');
    head.appendChild(h('span'));
    var headTrack = h('div', 'lc-track');
    var headLabel = h('span', 'lc-target-label');
    headTrack.appendChild(headLabel);
    head.appendChild(headTrack);
    head.appendChild(h('span'));
    root.appendChild(head);
    var list = h('div', 'lc-rows');
    list.setAttribute('role', 'list');
    root.appendChild(list);
    var note = h('div', 'lc-footnote');
    note.appendChild(h('span', 'lc-flag', '!'));
    var noteText = document.createTextNode('');
    note.appendChild(noteText);
    root.appendChild(note);

    function configure(changes) {
      for (var k in changes) cfg[k] = changes[k];
      fmt = formatter(cfg.decimals);
      unit = cfg.unit ? ' ' + cfg.unit : '';
      head.style.display = cfg.target ? '' : 'none';
      if (cfg.target) {
        headLabel.textContent = cfg.target.label;
        headLabel.style.left = targetLeft();
      }
      noteText.nodeValue = flagNote();
    }

    function targetLeft() {
      return Math.min(100, cfg.target.value / cfg.max * 100) + '%';
    }

    function flagNote() {
      return cfg.flagNote || 'Above the target';
    }

    function create(item) {
      var row = h('div', 'lc-row');
      row.setAttribute('role', 'listitem');
      var r = { row: row, item: item };
      row.appendChild(h('span', 'lc-row-label', item.label));
      var track = h('div', 'lc-track');
      r.bar = h('div', 'lc-bar');
      track.appendChild(r.bar);
      r.line = h('div', 'lc-target-line');
      track.appendChild(r.line);
      row.appendChild(track);
      var value = h('span', 'lc-row-value');
      r.num = h('span');
      value.appendChild(r.num);
      r.flag = h('span', 'lc-flag', '!');
      r.flag.hidden = true;
      value.appendChild(r.flag);
      row.appendChild(value);
      attachTip(row, function (t) {
        t.appendChild(h('div', 'lc-tip-head', r.item.label));
        tipRow(t, null, null, fmt(r.item.value) + unit, cfg.valueLabel || '');
        if (cfg.target) {
          var diff = r.item.value - cfg.target.value;
          tipRow(t, null, null, (diff > 0 ? '+' : '−') + fmt(Math.abs(diff)) + unit,
            'vs ' + (cfg.target.name || 'target'));
        }
        (r.item.details || []).forEach(function (d) { tipRow(t, null, null, d[0], d[1]); });
      });
      list.appendChild(row);
      row.offsetWidth; // commit the zero-width state so the bar grows in
      return r;
    }

    // Row height comes from the stylesheet (it grows on narrow screens).
    function place() {
      if (!order.length) return;
      var rowH = rows[order[0]].row.offsetHeight;
      list.style.height = order.length * rowH + 'px';
      order.forEach(function (id, rank) {
        rows[id].row.style.transform = 'translateY(' + rank * rowH + 'px)';
      });
    }
    new ResizeObserver(place).observe(root);

    function update(items, changes) {
      if (changes) configure(changes);
      var dir = cfg.order === 'asc' ? -1 : 1;
      var sorted = items.slice().sort(function (a, b) { return dir * (b.value - a.value); });
      var seen = {};
      var anyFlag = false;
      sorted.forEach(function (item) {
        seen[item.id] = true;
        var r = rows[item.id] || (rows[item.id] = create(item));
        r.item = item;
        r.row.firstChild.textContent = item.label;
        r.bar.style.width = Math.min(100, item.value / cfg.max * 100) + '%';
        r.line.style.display = cfg.target ? '' : 'none';
        if (cfg.target) r.line.style.left = targetLeft();
        tweenNumber(r.num, item.value, function (v) { return fmt(v) + unit; });
        var flagged = item.flagged != null
          ? !!item.flagged
          : !!cfg.target && item.value > cfg.target.value;
        anyFlag = anyFlag || flagged;
        r.flag.hidden = !flagged;
        r.row.setAttribute('aria-label',
          item.label + ': ' + fmt(item.value) + unit + (flagged ? ', ' + flagNote().toLowerCase() : ''));
      });
      Object.keys(rows).forEach(function (id) {
        if (!seen[id]) { rows[id].row.remove(); delete rows[id]; }
      });
      note.style.display = anyFlag || cfg.target ? '' : 'none';
      order = sorted.map(function (item) { return item.id; });
      place();
    }

    configure(opts);
    return { update: update };
  }

  LC.rankedBars = rankedBars;
})(window.LiveCharts);
