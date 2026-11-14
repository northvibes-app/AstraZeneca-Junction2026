(function (LC) {
  'use strict';

  var h = LC._.h;
  var formatter = LC._.formatter;
  var tweenNumber = LC._.tweenNumber;
  var tipRow = LC._.tipRow;
  var attachTip = LC._.attachTip;

  /* ---------- funnel ----------
     Fixed stage order; each bar is relative to the first stage and shows
     its share of the previous stage.
     opts: { decimals? } */

  function funnel(root, opts) {
    opts = opts || {};
    var fmt = formatter(opts.decimals);
    var rows = [];
    root.classList.add('lc-funnel');
    root.style.setProperty('--lc-value-col', '92px');
    var list = h('div', 'lc-rows');
    list.setAttribute('role', 'list');
    root.appendChild(list);
    root.appendChild(h('div', 'lc-footnote', 'Percentages are the share of the step before.'));

    function create(stage) {
      var row = h('div', 'lc-row');
      row.setAttribute('role', 'listitem');
      var r = { stage: stage, share: null };
      row.appendChild(h('span', 'lc-row-label', stage.label));
      var track = h('div', 'lc-track');
      r.bar = h('div', 'lc-bar');
      track.appendChild(r.bar);
      row.appendChild(track);
      var value = h('span', 'lc-row-value');
      r.num = h('span');
      r.pct = h('small');
      value.appendChild(r.num);
      value.appendChild(r.pct);
      row.appendChild(value);
      attachTip(row, function (t) {
        t.appendChild(h('div', 'lc-tip-head', r.stage.label));
        tipRow(t, null, null, fmt(r.stage.value), opts.valueLabel || '');
        if (r.share != null) tipRow(t, null, null, Math.round(r.share) + '%', 'of the step before');
      });
      list.appendChild(row);
      row.offsetWidth;
      return r;
    }

    function update(stages) {
      var first = stages.length ? stages[0].value : 0;
      stages.forEach(function (stage, i) {
        var r = rows[i] || (rows[i] = create(stage));
        r.stage = stage;
        r.bar.style.width = (first ? stage.value / first * 100 : 0) + '%';
        tweenNumber(r.num, stage.value, fmt);
        var prev = i ? stages[i - 1].value : 0;
        r.share = i && prev ? stage.value / prev * 100 : null;
        r.pct.textContent = r.share == null ? '' : Math.round(r.share) + '%';
      });
    }

    return { update: update };
  }

  LC.funnel = funnel;
})(window.LiveCharts);
