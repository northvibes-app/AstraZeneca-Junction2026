// Smoke test: runs the page script against real pipeline output with a stub DOM.
// Run: node app/test_page.js     (does not test layout; open app/index.html in a browser for that)
const fs = require("fs"), path = require("path"), assert = require("assert"), vm = require("vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const main = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const els = {};
const el = id => els[id] ||= { id, innerHTML: "", textContent: "", value: id === "region" ? "FI" : id === "gapSel" ? "0" : id === "share" ? "50" : "", hidden: true, disabled: false };
const window = {}; const sandbox = { window, document: { getElementById: el }, fetch: async () => { throw new Error("offline"); }, console };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, "../pipeline/output/pipeline-data.js"), "utf8"), sandbox);
sandbox.window = sandbox.window || window;
vm.runInContext(fs.readFileSync(path.join(__dirname, "checker.js"), "utf8"), sandbox);
sandbox.Checker = sandbox.Checker || sandbox.window.Checker;
vm.runInContext(main, sandbox);
const must = (id, text) => assert(els[id].innerHTML.includes(text) || els[id].textContent.includes(text), `${id} should contain "${text}"`);
must("status", "all accounted for");
must("cards", "Goal 3: cancer deaths");
must("strip", "Treatment start");
must("strip", "No open data");
must("regionTable", "Breast screening participation");
must("recs", "National");
must("deathChart", "<svg");
must("goal3gap", "THL guidance 21/2016");
must("goal3table", "five year survival lung increase");
assert(els.scenOut.textContent.startsWith("+"), "scenario output");
// switch region and re-render
els.region.value = "14"; els.region.onchange(); must("regionTable", "84.2");
// number checker via the page button
el("paste").value = "Participation is 97.77 % in Lapland."; els.pasteBtn.onclick(); must("check", "97.77");
console.log("cards:", els.cards.innerHTML.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim());
console.log("scenario:", els.scenOut.textContent, "|", els.scenFormula.textContent.slice(0, 120));
console.log("PAGE SMOKE TEST PASS");
