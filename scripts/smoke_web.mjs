#!/usr/bin/env node
/**
 * Browser-level smoke test for the citizen UI (optional dev tool, not part of pytest).
 *
 *   npm install --no-save jsdom
 *   node scripts/smoke_web.mjs http://127.0.0.1:8000
 *
 * It loads the real page in jsdom, walks every hash route, asks the assistant a question
 * through the real API and fails if a route renders nothing or the answer carries no
 * source. jsdom is not a browser: layout, CSS and speech APIs are not tested here —
 * see docs/TESTING_REPORT.md for what still needs a human with a phone.
 */
import { JSDOM, VirtualConsole } from "jsdom";

const base = process.argv[2] || process.env.NYAYMITRA_URL || "http://127.0.0.1:8000";
const problems = [];
const console_errors = [];

const virtualConsole = new VirtualConsole();
virtualConsole.on("jsdomError", (error) => console_errors.push(`jsdom: ${error.message}`));

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const text = (node) => (node?.textContent || "").replace(/\s+/g, " ").trim();

const dom = await JSDOM.fromURL(`${base}/`, {
  runScripts: "dangerously",
  resources: "usable",
  pretendToBeVisual: true,
  virtualConsole,
  beforeParse(window) {
    // jsdom has no network layer for relative URLs and no layout engine.
    window.fetch = (input, init) => fetch(new URL(input, window.location.href), init);
    window.scrollTo = () => {};
    window.Element.prototype.scrollIntoView = () => {};
  },
});

const { window } = dom;
const go = async (hash) => {
  window.location.hash = hash;
  window.dispatchEvent(new window.Event("hashchange"));
  await wait(800);
  return text(window.document.querySelector("main"));
};

for (const route of ["#/home", "#/assistant", "#/complaint", "#/library", "#/departments", "#/glossary"]) {
  const body = await go(route);
  if (body.length < 40) problems.push(`${route} rendered ${body.length} characters — expected content`);
  if (/network_error|internal_error/.test(body)) problems.push(`${route} surfaced an error state: ${body.slice(0, 120)}`);
  console.log(`${route.padEnd(14)} ${String(body.length).padStart(5)} chars  ${body.slice(0, 70)}`);
}

await go("#/assistant");
const question = window.document.querySelector("#question");
if (!question) {
  problems.push("#question textarea missing on #/assistant");
} else {
  question.value = "What does equality before law mean?";
  question.closest("form").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
  await wait(2500);
  const body = text(window.document.querySelector("main"));
  if (!/Article \d+/.test(body)) problems.push("assistant answer shows no article citation");
  if (!/(not legal advice|કાનૂની સલાહ નથી)/i.test(body)) problems.push("assistant answer shows no disclaimer");
  if (/network_error/.test(body)) problems.push("assistant call failed with network_error");
  console.log(`assistant      ${String(body.length).padStart(5)} chars  citations+disclaimer checked`);
}

if (console_errors.length) problems.push(...console_errors);

if (problems.length) {
  console.error("\nFAILED");
  for (const problem of problems) console.error(" -", problem);
  process.exit(1);
}
console.log(`\nOK — every route and the assistant answered from ${base}`);
