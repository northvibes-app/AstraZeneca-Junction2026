(function (LC) {
  'use strict';

  var h = LC._.h;
  var formatter = LC._.formatter;
  var tweenNumber = LC._.tweenNumber;
  var tipRow = LC._.tipRow;
  var attachTip = LC._.attachTip;
  var legend = LC._.legend;

  /* ---------- paired bars ----------
     Two groups compared on the same measure, one block per measure.
     opts: { max, unit?, decimals?, series: [{ key, label, color }] }
     update([{ title, tag?, note?, href?, rows: { <key>: { label, value } } }]) */

  function pairedBars(root, opts) {
    var fmt = formatter(opts.decimals);
    var unit = opts.unit ? ' ' + opts.unit : '';
    var blocks = [];
    root.classList.add('lc-paired');
    root.appendChild(legend(opts.series, 'box'));
    var list = h('div', 'lc-pairs');
    root.appendChild(list);

    function create() {
      var b = { el: h('div', 'lc-pair'), rows: {}, item: null };
      var title = h('div', 'lc-pair-title');
      b.title = h('span');
      b.tag = h('span', 'lc-tag');
      b.link = h('a', 'lc-source', 'Source');
      b.link.target = '_blank';
      b.link.rel = 'noopener';
      title.appendChild(b.title);
      title.appendChild(b.tag);
      title.appendChild(b.link);
      b.el.appendChild(title);
      b.note = h('div', 'lc-pair-note');
      b.el.appendChild(b.note);
      opts.series.forEach(function (sr) {
        var row = h('div', 'lc-row');
        var r = { row: row };
        r.label = h('span', 'lc-row-label');
        row.appendChild(r.label);
        var track = h('div', 'lc-track');
        r.bar = h('div', 'lc-bar');
        r.bar.style.background = sr.color;
        track.appendChild(r.bar);
        row.appendChild(track);
        r.num = h('span', 'lc-row-value');
        row.appendChild(r.num);
        attachTip(row, function (t) {
          var d = b.item.rows[sr.key];
          t.appendChild(h('div', 'lc-tip-head', b.item.title));
          tipRow(t, sr.color, 'box', fmt(d.value) + unit, d.label);
          tipRow(t, null, null, sr.label, '');
        });
        b.el.appendChild(row);
        b.rows[sr.key] = r;
      });
      list.appendChild(b.el);
      b.el.offsetWidth;
      return b;
    }

    function update(items) {
      items.forEach(function (item, i) {
        var b = blocks[i] || (blocks[i] = create());
        b.item = item;
        b.el.hidden = false;
        b.title.textContent = item.title;
        b.tag.textContent = item.tag || '';
        b.tag.hidden = !item.tag;
        b.link.hidden = !item.href;
        if (item.href) b.link.href = item.href;
        b.note.textContent = item.note || '';
        opts.series.forEach(function (sr) {
          var d = item.rows[sr.key], r = b.rows[sr.key];
          r.label.textContent = d.label;
          r.bar.style.width = Math.min(100, d.value / opts.max * 100) + '%';
          tweenNumber(r.num, d.value, function (v) { return fmt(v) + unit; });
          r.row.setAttribute('aria-label', d.label + ': ' + fmt(d.value) + unit + ' (' + sr.label + ')');
        });
      });
      for (var i = items.length; i < blocks.length; i++) blocks[i].el.hidden = true;
    }

    return { update: update };
  }

  LC.pairedBars = pairedBars;
})(window.LiveCharts);
