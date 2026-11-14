/* Graph: patterns between regions (evidence B).
 * Rank correlation across the regions between disadvantage on the chosen
 * factor and each result, plus one sentence on what survives correction
 * for the number of comparisons.
 * Needs ../lib/core.js, ../lib/diverging-bars.js and shared.js.
 */
(function (G) {
  'use strict';

  var OUTCOME = {
    cancer_index_age_standardised: 'Cancer index (lower is better)',
    screening_participation_breast: 'Breast screening participation',
    screening_participation_cervical: 'Cervical screening participation',
    screening_participation_colorectal: 'Colorectal screening participation',
    survival_5y_breast: 'Breast cancer 5-year survival',
    survival_5y_cervical: 'Cervical cancer 5-year survival',
    survival_5y_colon: 'Colon cancer 5-year survival'
  };

  G.regionPatterns = function (root) {
    var area = G.chartWithEmpty(root, 'No regional comparison was run for this factor.');
    var chart = LiveCharts.divergingBars(area.chart, {
      extent: 1, decimals: 2, valueLabel: 'rank correlation',
      footnote: '✓ The pattern survives correction for the number of comparisons.'
    });
    var finding = G.el('p', 'lc-finding');
    root.appendChild(finding);

    return {
      draw: function (P, factor) {
        var all = P.equity_gaps.filter(function (g) { return g.evidence_type === 'B'; });
        var mine = all.filter(function (g) { return g.factor === factor; });

        area.show(mine.length > 0);
        chart.update(mine.map(function (g) {
          return {
            label: OUTCOME[g.indicator_key] || g.indicator_name,
            fullLabel: g.indicator_name + ' ' + g.year,
            value: Number(g.spearman_rho),
            mark: g.robust === 'yes' ? '✓' : '',
            details: [
              [String(g.worse_value), 'disadvantaged third of regions'],
              [String(g.better_value), 'advantaged third of regions'],
              [String(g.p_adjusted), 'adjusted p-value, ' + g.n_regions + ' regions']
            ]
          };
        }));

        var sizeable = all.filter(function (g) { return Math.abs(g.spearman_rho) >= 0.4; });
        var robust = all.filter(function (g) { return g.robust === 'yes'; });
        finding.textContent = 'Across all factors, ' + sizeable.length + ' of ' + all.length +
          ' combinations reach 0.4 in size, but with ' + all.length +
          ' comparisons some of that is chance. After correction ' + robust.length + ' remain: ' +
          (robust.map(function (g) {
            return G.factorLabel(g.factor).toLowerCase() + ' and ' + g.indicator_name.toLowerCase() +
              ' (' + String(g.spearman_rho).replace('-', '−') + ')';
          }).join('; ') || 'none') + '.';
      }
    };
  };
})(window.Graphs);
