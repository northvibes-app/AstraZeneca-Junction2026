/* Graph: the regions ranked on the chosen factor's own measure, most
 * disadvantaged first, with the Finland value as a marker and the
 * disadvantaged third flagged.
 * Needs ../lib/core.js, ../lib/ranked-bars.js and shared.js.
 */
(function (G) {
  'use strict';

  // [description, unit] per measure; units are from pipeline/reference/indicators.csv.
  var MEASURE = {
    low_income_rate: ['Share of residents below the low-income threshold', '%'],
    unemployment_rate: ['Unemployed share of the labour force', '%'],
    education_level_index: ['Education level index (average length of education)', ''],
    other_language_per_1000: ['Residents per 1,000 whose native language is not Finnish, Swedish or Sami', ''],
    daily_smokers: ['Daily smokers', '%'],
    primary_care_wait_over_7_days: ['Non-urgent primary care doctor visits with a wait over 7 days', '%']
  };

  G.regionRanking = function (root) {
    var note = G.el('p', 'lc-note');
    root.appendChild(note);
    var area = G.chartWithEmpty(root, 'There is no regional measure for this factor.');
    area.chart.style.setProperty('--lc-value-col', '78px');
    var chart = LiveCharts.rankedBars(area.chart, {
      max: 100, decimals: 1, flagNote: 'In the disadvantaged third of regions on this factor'
    });

    return {
      draw: function (P, factor) {
        var levels = P.region_factor_levels.filter(function (r) { return r.factor === factor; });
        area.show(levels.length > 0);
        note.textContent = '';
        note.hidden = !levels.length;
        if (!levels.length) return;

        function mean(level) {
          var values = levels.filter(function (r) { return r.factor_level === level; })
            .map(function (r) { return Number(r.context_value); });
          return values.reduce(function (a, b) { return a + b; }, 0) / (values.length || 1);
        }

        var key = levels[0].context_indicator;
        var measure = MEASURE[key] || [G.cap(key), ''];
        var highIsWorse = mean('disadvantaged') >= mean('advantaged');
        var national = Number(levels[0].national_value);
        var peak = Math.max.apply(null, levels.map(function (r) { return Number(r.context_value); }).concat(national));

        note.appendChild(document.createTextNode(measure[0] + ', ' + levels[0].context_year + '. ' +
          (highIsWorse ? 'Higher' : 'Lower') +
          ' counts as more disadvantaged; regions are split into thirds relative to each other. '));
        var source = P.indicator_sources && P.indicator_sources[key];
        if (source) {
          var link = G.el('a', null, 'Source');
          link.href = source;
          link.target = '_blank';
          link.rel = 'noopener';
          note.appendChild(link);
        }

        chart.update(levels.map(function (r) {
          return {
            id: r.region_code,
            label: r.region_name,
            value: Number(r.context_value),
            flagged: r.factor_level === 'disadvantaged',
            details: [[G.cap(r.factor_level) + ' third', 'of regions']]
          };
        }), {
          max: peak * 1.06,
          unit: measure[1],
          order: highIsWorse ? 'desc' : 'asc',
          valueLabel: String(levels[0].context_year),
          target: { value: national, label: 'Finland ' + G.num(national, 1), name: 'Finland' }
        });
      }
    };
  };
})(window.Graphs);
