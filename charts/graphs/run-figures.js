/* Graph: the pipeline run in five figures.
 * Needs ../lib/core.js, ../lib/stat-tile.js and shared.js.
 * Graphs.runFigures(element, { tileClass }) — one tile per figure is added
 * to the element; tileClass is the class each tile gets (for example "card").
 */
(function (G) {
  'use strict';

  var FIGURES = [
    ['Rows read', 'rows_read'],
    ['Observations published', 'published'],
    ['Out of scope', 'filtered_out_of_scope'],
    ['Duplicates removed', 'duplicates_removed'],
    ['Fallback values added', 'of_which_imputed']
  ];

  G.runFigures = function (root, opts) {
    var tiles = FIGURES.map(function (figure, i) {
      var box = G.el('div', (opts && opts.tileClass) || '');
      box.style.setProperty('--i', i);
      root.appendChild(box);
      return LiveCharts.statTile(box, { label: figure[0] });
    });

    return {
      draw: function (P) {
        var rec = P.lineage.reconciliation;
        tiles.forEach(function (tile, i) { tile.update(rec[FIGURES[i][1]]); });
      }
    };
  };
})(window.Graphs);
