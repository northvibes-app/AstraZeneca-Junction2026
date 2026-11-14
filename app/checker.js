/* Number checker: every number in an AI answer must exist in the pipeline tables.
   Works in the browser (window.Checker) and in Node (module.exports) so it can be tested. */
(function (root) {
  const TARGET = 80;

  function numbersIn(text) {
    const re = /\d{1,3}(?:[ ,\u00a0]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?/g;
    const out = [];
    for (const m of String(text).replace(/\(S\d+\)|\bS\d+\b/g, " ").matchAll(re)) {
      const raw = m[0], v = parseFloat(raw.replace(/[ ,\u00a0]/g, ""));
      const isInt = !raw.includes(".");
      if (isInt && (v <= 10 || (v >= 1990 && v <= 2100))) continue;   // list numbers and years
      out.push({ raw, v });
    }
    return out;
  }

  function knownNumbers(P) {
    const set = [];
    const add = v => { if (v === "" || v == null) return; v = Number(v); if (isFinite(v)) set.push(v); };
    for (const g of P.equity_gaps) ["worse_value", "better_value", "gap", "gap_ci_low", "gap_ci_high",
      "people_in_worse_group", "potential_additional"].forEach(k => add(g[k]));
    for (const r of P.region_facts) ["value", "ci_low", "ci_high"].forEach(k => add(r[k]));
    for (const r of P.recommendations) ["cost_eur", "people_in_worse_group", "potential_additional"].forEach(k => add(r[k]));
    for (const g of (P.goal3_targets || [])) { add(g.target_value); add(g.baseline_value); }
    for (const t of (P.national_trends || [])) add(t.deaths);
    add(TARGET);
    // differences between regions of the same indicator and year (statements like "9.5 points")
    const groups = {};
    for (const r of P.region_facts)
      if (r.sex === "total" && r.value !== "" && r.region_code !== "FI")
        (groups[r.indicator_key + r.year] ||= []).push(Number(r.value));
    for (const vals of Object.values(groups))
      for (let i = 0; i < vals.length; i++) for (let j = i + 1; j < vals.length; j++) add(Math.abs(vals[i] - vals[j]));
    return set;
  }

  function checkNumbers(text, known) {
    const found = [], missing = [];
    for (const n of numbersIn(text)) {
      const d = n.raw.includes(".") ? n.raw.split(".")[1].length : 0;   // precision as typed
      const tol = 0.5 * Math.pow(10, -d) + 1e-9;                         // 9.5 matches 9.45-9.55, 97.77 only 97.765-97.775
      const ok = known.some(k => Math.abs(k - n.v) < tol);
      (ok ? found : missing).push(n.raw);
    }
    return { found, missing };
  }

  const api = { numbersIn, knownNumbers, checkNumbers, TARGET };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Checker = api;
})(typeof window !== "undefined" ? window : globalThis);
