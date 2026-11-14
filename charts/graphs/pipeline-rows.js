/* Graph: how many input rows were left after each kind of check.
 * Needs ../lib/core.js, ../lib/funnel.js and shared.js.
 */
(function (G) {
  'use strict';

  G.pipelineRows = function (root) {
    var chart = LiveCharts.funnel(root, { valueLabel: 'rows' });

    return {
      draw: function (P) {
        var rec = P.lineage.reconciliation;
        var readable = rec.rows_read - rec.quarantined;
        var inScope = readable - rec.filtered_out_of_scope;
        chart.update([
          { label: 'Rows read', value: rec.rows_read },
          { label: 'Readable (' + G.num(rec.quarantined) + ' quarantined)', value: readable },
          { label: 'In scope', value: inScope },
          { label: 'After removing duplicates', value: inScope - rec.duplicates_removed },
          { label: 'Published (+' + G.num(rec.of_which_imputed) + ' fallback values)', value: rec.published }
        ]);
      }
    };
  };
})(window.Graphs);
