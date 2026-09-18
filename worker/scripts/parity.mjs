// Parity check: run the same corpus & questions through the TypeScript engine and
// the Python engine, and compare cited_doc_ids + confidence for every case.
// Requires `npm run build:data` to have run first (cases file is re-read live).
// Python engine path is auto-detected relative to the repo root.

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { answerQuestion } from "../src/agent.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..", ".."); // cloudtechner-coding-exercise
const CASES = JSON.parse(readFileSync(join(REPO, "examples.json"), "utf8"));

function pyAnswer(question) {
  const code = `import sys;\nfrom cloudtech_rag import answer_question;\nimport json; print(json.dumps(answer_question(sys.argv[1])))`;
  const out = execFileSync("python3", ["-c", code, question], { cwd: REPO, encoding: "utf8" });
  return JSON.parse(out.trim());
}

let pass = 0;
let fail = 0;
for (const c of CASES) {
  const py = pyAnswer(c.question);
  const ts = answerQuestion(c.question);
  const same =
    JSON.stringify(py.cited_doc_ids) === JSON.stringify(ts.cited_doc_ids) &&
    py.confidence === ts.confidence;
  if (same) {
    pass++;
    console.log(`OK   ${c.question.slice(0, 58).padEnd(60)} py=${py.cited_doc_ids[0] ?? "no-match"} (${py.confidence}) == ts=${ts.cited_doc_ids[0] ?? "no-match"} (${ts.confidence})`);
  } else {
    fail++;
    console.log(`DIFF ${c.question.slice(0, 58)}`);
    console.log(`     py: ${JSON.stringify(py)}`);
    console.log(`     ts: ${JSON.stringify(ts)}`);
  }
}
console.log(`\nparity: ${pass}/${CASES.length} cases match between Python and TypeScript engines`);
process.exit(fail === 0 ? 0 : 1);