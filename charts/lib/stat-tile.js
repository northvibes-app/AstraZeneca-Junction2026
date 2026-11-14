(function (LC) {
  'use strict';

  var h = LC._.h;
  var formatter = LC._.formatter;
  var tweenNumber = LC._.tweenNumber;

  /* ---------- stat tile ----------
     opts: { label, unit?, decimals?, note? } */

  function statTile(root, opts) {
    var fmt = formatter(opts.decimals);
    root.classList.add('lc-tile');
    root.appendChild(h('div', 'lc-tile-label', opts.label));
    var line = h('div', 'lc-tile-value');
    var num = h('span', null, '–');
    line.appendChild(num);
    if (opts.unit) line.appendChild(h('span', 'lc-tile-unit', opts.unit));
    root.appendChild(line);
    if (opts.note) root.appendChild(h('div', 'lc-tile-note', opts.note));
    return {
      update: function (value) { tweenNumber(num, value, fmt); }
    };
  }

  LC.statTile = statTile;
})(window.LiveCharts);
