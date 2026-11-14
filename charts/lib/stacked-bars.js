(function (LC) {
  'use strict';

  var h = LC._.h;
  var tipRow = LC._.tipRow;
  var attachTip = LC._.attachTip;
  var legend = LC._.legend;

  /* ---------- stacked bars ----------
     One whole per row, split into the same parts.
     opts: { segments: [{ key, label, color, ink? }],
             summary?: function (values, total) -> string } */

  function stackedBars(root, opts) {
    var segs = opts.segments;
    var rows = [];
    root.classList.add('lc-stacked');
    root.appendChild(legend(segs, 'box'));
    var list = h('div', 'lc-rows');
    list.setAttribute('role', 'list');
    root.appendChild(list);

    function create(item) {
      var row = h('div', 'lc-row');
      row.setAttribute('role', 'listitem');
      var r = { row: row, item: item, parts: {} };
      row.appendChild(h('span', 'lc-row-label', item.label));
      var stack = h('div', 'lc-stack');
      segs.forEach(function (sg) {
        var part = h('div', 'lc-seg');
        part.style.background = sg.color;
        part.style.color = sg.ink || 'var(--lc-on-series)';
        part.appendChild(h('span'));
        stack.appendChild(part);
        r.parts[sg.key] = part;
      });
      row.appendChild(stack);
      r.summary = h('span', 'lc-row-value');
      row.appendChild(r.summary);
      attachTip(row, function (t) {
        t.appendChild(h('div', 'lc-tip-head', r.item.label));
        segs.forEach(function (sg) {
          tipRow(t, sg.color, 'box', String(r.item.values[sg.key]), sg.label);
        });
      });
      list.appendChild(row);
      row.offsetWidth;
      return r;
    }

    function update(items) {
      items.forEach(function (item, i) {
        var r = rows[i] || (rows[i] = create(item));
        r.item = item;
        var total = segs.reduce(function (sum, sg) { return sum + item.values[sg.key]; }, 0);
        var spoken = [];
        segs.forEach(function (sg) {
          var v = item.values[sg.key];
          var part = r.parts[sg.key];
          part.style.flexGrow = v;
          part.firstChild.textContent = v;
          // A part too narrow for its number prints none; the tooltip has it.
          part.classList.toggle('is-tight', !total || v / total < 0.13);
          spoken.push(v + ' ' + sg.label.toLowerCase());
        });
        r.summary.textContent = opts.summary ? opts.summary(item.values, total) : String(total);
        r.row.setAttribute('aria-label', item.label + ': ' + spoken.join(', '));
      });
    }

    return { update: update };
  }

  LC.stackedBars = stackedBars;
})(window.LiveCharts);
