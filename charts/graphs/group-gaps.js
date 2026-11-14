/* Graph: gaps measured directly between groups (evidence A).
 * For the chosen factor, the latest national comparison per indicator:
 * the group with the worse result against the group with the better one.
 * Needs ../lib/core.js, ../lib/paired-bars.js and shared.js.
 */
(function (G) {
  'use strict';

  G.groupGaps = function (root) {
    var area = G.chartWithEmpty(root, 'The open sources publish no per-group figures for this factor.');
    var chart = LiveCharts.pairedBars(area.chart, {
      max: 100, unit: '%', decimals: 1,
      series: [
        { key: 'worse', label: 'Group with the worse result', color: 'var(--lc-s1)' },
        { key: 'better', label: 'Group with the better result', color: 'var(--lc-s2)' }
      ]
    });

    return {
      draw: function (P, factor) {
        // "low" / "high" on their own say nothing: name what they are levels of.
        function group(name) {
          return /^(low|medium|high)$/.test(name) ? G.cap(name) + ' ' + G.words(factor) : G.cap(name);
        }

        var latest = {};
        P.equity_gaps.forEach(function (g) {
          if (g.evidence_type !== 'A' || g.region !== 'Finland' || g.factor !== factor) return;
          if (!latest[g.indicator_key] || g.year > latest[g.indicator_key].year) latest[g.indicator_key] = g;
        });
        var gaps = Object.keys(latest).map(function (k) { return latest[k]; })
          .sort(function (a, b) { return b.gap - a.gap; });

        area.show(gaps.length > 0);
        chart.update(gaps.map(function (g) {
          return {
            title: g.indicator_name + ' ' + g.year,
            tag: g.status !== 'observed' ? g.status : '',
            href: g.source_url,
            note: 'Gap ' + G.num(g.gap, 1) + ' points' + (g.potential_additional !== ''
              ? ' · ' + G.num(g.people_in_worse_group) + ' people in the worse-off group; ' +
                G.num(g.potential_additional) + ' more would take part at the level of the best group'
              : ''),
            rows: {
              worse: { label: group(g.worse_group), value: Number(g.worse_value) },
              better: { label: group(g.better_group), value: Number(g.better_value) }
            }
          };
        }));
      }
    };
  };
})(window.Graphs);
