/* Shared by the graph files in this folder. Load after ../lib/core.js and
 * before any graph file. Every graph is created with
 *   const graph = Graphs.<name>(element)
 * and drawn with
 *   graph.draw(window.PIPELINE, factorKey)
 * Calling draw() again animates the graph to the new data.
 */
(function (global) {
  'use strict';

  var FACTORS = [
    ['education', 'Lower education'], ['language', 'Language barrier'], ['income', 'Lower income'],
    ['employment', 'Unemployment'], ['smoking', 'Smoking'],
    ['primary_care_access', 'Slow primary care access'], ['sex', 'Sex']
  ];

  function words(s) { return String(s).replace(/_/g, ' '); }

  function cap(s) {
    s = words(s);
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function num(v, decimals) {
    return Number(v).toLocaleString('en', {
      minimumFractionDigits: decimals || 0,
      maximumFractionDigits: decimals || 0
    });
  }

  function factorLabel(key) {
    var found = FACTORS.filter(function (f) { return f[0] === key; })[0];
    return found ? found[1] : cap(key);
  }

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  // A chart area plus the message shown instead when there is nothing to draw.
  function chartWithEmpty(root, emptyText) {
    var chart = el('div');
    var empty = el('p', 'lc-empty', emptyText);
    empty.hidden = true;
    root.appendChild(chart);
    root.appendChild(empty);
    return {
      chart: chart,
      show: function (hasData) {
        chart.hidden = !hasData;
        empty.hidden = hasData;
      }
    };
  }

  global.Graphs = {
    FACTORS: FACTORS,
    words: words,
    cap: cap,
    num: num,
    factorLabel: factorLabel,
    el: el,
    chartWithEmpty: chartWithEmpty
  };
})(window);
