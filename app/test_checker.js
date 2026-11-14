// Run: node app/test_checker.js   (needs pipeline/output/pipeline-data.js and rag_response.json)
const fs = require("fs"), path = require("path"), assert = require("assert");
const C = require("./checker.js");
const js = fs.readFileSync(path.join(__dirname, "../pipeline/output/pipeline-data.js"), "utf8");
const P = JSON.parse(js.slice(js.indexOf("{"), js.lastIndexOf("}") + 1));
const known = C.knownNumbers(P);
const rag = JSON.parse(fs.readFileSync(path.join(__dirname, "../rag_response.json"), "utf8"));
let r = C.checkNumbers(rag.answer, known);
console.log("saved AI answer ->", r);
assert.equal(r.missing.length, 0, "the saved AI answer should pass");
r = C.checkNumbers("Breast screening participation in Lapland is 97.77 % and 4 321 people are missing.", known);
console.log("fake text      ->", r);
assert(r.missing.includes("97.77") && r.missing.includes("4 321"), "fake numbers must be caught");
assert.equal(C.checkNumbers("The target is 80 % and 13 300 deaths a year.", known).missing.length, 0);
console.log("ALL CHECKER TESTS PASS");
