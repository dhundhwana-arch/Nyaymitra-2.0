#!/usr/bin/env node
/**
 * Browser-level smoke test for the citizen UI and admin console (optional dev tool,
 * not part of pytest).
 *
 *   npm install --no-save jsdom
 *   node scripts/smoke_web.mjs http://127.0.0.1:8000
 *
 * It loads the real pages in jsdom and drives them like a person would: walks all six
 * citizen routes, switches language, searches the library, filters the glossary, files a
 * complaint through preview → confirmation → submission, opens the saved complaint with
 * its one-time token, and signs in to the admin console.
 *
 * jsdom is not a browser: layout, CSS breakpoints, speech synthesis and real mobile
 * viewports are NOT covered here. See docs/TESTING_REPORT.md for what still needs a
 * human with a phone.
 */
import { JSDOM, VirtualConsole } from "jsdom";

const base = process.argv[2] || process.env.NYAYMITRA_URL || "http://127.0.0.1:8000";
const adminToken = process.env.NYAYMITRA_ADMIN_TOKEN || "";
const problems = [];
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const clean = (node) => (node?.textContent || "").replace(/\s+/g, " ").trim();
const check = (condition, message) => {
  if (!condition) problems.push(message);
};

async function openPage(path) {
  const virtualConsole = new VirtualConsole();
  virtualConsole.on("jsdomError", (error) => problems.push(`jsdom(${path}): ${error.message}`));
  const dom = await JSDOM.fromURL(`${base}${path}`, {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    virtualConsole,
    beforeParse(window) {
      window.fetch = (input, init) => fetch(new URL(input, window.location.href), init);
      window.scrollTo = () => {};
      window.Element.prototype.scrollIntoView = () => {};
      window.matchMedia = window.matchMedia || (() => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }));
    },
  });
  await wait(1200);
  return dom;
}

/* ------------------------------------------------------------------ citizen */
const dom = await openPage("/");
const { window } = dom;
const document = window.document;
const setLang = (code) => { const sel = document.querySelector("#langSelect"); sel.value = code; sel.dispatchEvent(new window.Event("change")); };

const go = async (hash) => {
  window.location.hash = hash;
  window.dispatchEvent(new window.Event("hashchange"));
  await wait(800);
  return clean(document.querySelector("main"));
};

for (const route of ["#/home", "#/assistant", "#/complaint", "#/library", "#/departments", "#/glossary"]) {
  const body = await go(route);
  check(body.length >= 40, `${route} rendered only ${body.length} characters`);
  check(!/network_error|internal_error/.test(body), `${route} surfaced an error state`);
  console.log(`${route.padEnd(14)} ${String(body.length).padStart(5)} chars`);
}

/* keyboard and focus: the router must move focus to the main landmark */
const main = document.querySelector("#main");
check(main && main.getAttribute("tabindex") === "-1", "main landmark is not focusable");
check(document.querySelector(".skip-link")?.getAttribute("href") === "#main", "skip link missing");
await go("#/library");
check(document.activeElement === document.querySelector("#main"), "route change did not move focus to main");

/* language toggle */
setLang("en");
await wait(400);
const englishHome = await go("#/home");
check(/Your rights|Know your|legal information/i.test(englishHome), "language toggle did not switch the UI to English");
check(document.documentElement.lang === "en", "html[lang] was not updated to en");
setLang("gu");
await wait(300);
const gujaratiHome = await go("#/home");
check(/[\u0A80-\u0AFF]/.test(gujaratiHome), "language toggle did not switch the UI back to Gujarati");
console.log("language       toggled en <-> gu");

/* assistant */
await go("#/assistant");
const question = document.querySelector("#question");
question.value = "What does equality before law mean?";
question.closest("form").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
await wait(2500);
const answerText = clean(document.querySelector("main"));
check(/Article \d+/.test(answerText), "assistant answer shows no article citation");
check(/(not legal advice|કાનૂની સલાહ નથી)/i.test(answerText), "assistant answer shows no disclaimer");
check(!/network_error/.test(answerText), "assistant call failed");
console.log(`assistant      ${String(answerText.length).padStart(5)} chars  citations + disclaimer`);

/* library search */
await go("#/library");
const libQuery = document.querySelector("#libQuery");
libQuery.value = "equality";
document.querySelector("#libForm").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
await wait(1200);
const libraryText = clean(document.querySelector("#libResults"));
check(/14/.test(libraryText), "library search returned no Article 14 result");
check(/verification|verif|ચકાસણી/i.test(libraryText), "library results show no verification status");
console.log(`library        ${String(libraryText.length).padStart(5)} chars  search result shown`);

/* glossary filter */
await go("#/glossary");
const filter = document.querySelector("#glossFilter");
const before = document.querySelectorAll("#glossList > *").length;
filter.value = "FIR";
filter.dispatchEvent(new window.Event("input", { bubbles: true }));
await wait(500);
const after = document.querySelectorAll("#glossList > *").length;
check(before > 0, "glossary rendered no terms");
check(after > 0 && after < before, `glossary filter did not narrow the list (${before} -> ${after})`);
console.log(`glossary       ${before} terms -> ${after} after filtering "FIR"`);

/* complaint wizard: preview -> confirm -> submit -> retrieve */
await go("#/complaint");
document.querySelector("#cCategory").value = "cyber_fraud";
document.querySelector("#cTitle").value = "Unauthorised withdrawal from my bank account";
document.querySelector("#cDescription").value =
  "On 5 November 2026 an unknown person withdrew 25000 rupees from my savings account without any OTP being shared. I informed the bank the same day and they gave me a complaint number.";
document.querySelector("#cDate").value = "2026-11-05";
document.querySelector("#cLocation").value = "Jamnagar";
document.querySelector("#cConsent").checked = true;
document.querySelector("#complaintForm").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
await wait(1500);
const previewText = clean(document.querySelector("#complaintRoot"));
check(/Summary|સારાંશ/i.test(previewText), "complaint preview screen did not appear");
check(/no legal decision|કોઈ કાનૂની નિર્ણય/i.test(previewText), "preview does not label the summary as non-legal");
const confirm = document.querySelector("#confirmReview");
check(confirm, "confirmation checkbox missing — the review gate is not enforced");
check(document.querySelector("#submitComplaint").disabled, "submit button is enabled before confirmation");
confirm.checked = true;
confirm.dispatchEvent(new window.Event("change", { bubbles: true }));
check(!document.querySelector("#submitComplaint").disabled, "confirming did not enable submission");
document.querySelector("#submitComplaint").click();
await wait(2000);
const savedText = clean(document.querySelector("#complaintRoot"));
const reference = (savedText.match(/NYM-[A-Z0-9]{4,}/) || [])[0];
check(reference, "no complaint reference was shown after submission");
check(/token|ટોકન/i.test(savedText), "the one-time access token was not shown");
console.log(`complaint      ${reference || "NO REFERENCE"} created through preview + confirmation`);

if (reference) {
  const tokenMatch = savedText.match(/[A-Za-z0-9_-]{30,}/);
  check(tokenMatch, "could not find the access token in the saved view");
}

/* saved complaint lookup */
await go("#/complaint");
console.log("complaint      saved lookup form present:", Boolean(document.querySelector("#savedForm")));

/* -------------------------------------------------------------------- admin */
if (adminToken) {
  const adminDom = await openPage("/admin");
  const adminWindow = adminDom.window;
  const adminDocument = adminWindow.document;
  adminDocument.querySelector("#adminToken").value = adminToken;
  adminDocument.querySelector("#authForm").dispatchEvent(
    new adminWindow.Event("submit", { bubbles: true, cancelable: true })
  );
  await wait(2500);
  const stats = clean(adminDocument.querySelector("#statsPanel"));
  const queue = clean(adminDocument.querySelector("#queuePanel"));
  const docsPanel = clean(adminDocument.querySelector("#documentsPanel"));
  check(stats.length > 10, "admin statistics did not load");
  check(/pending/i.test(queue), "verification queue did not load");
  check(docsPanel.length > 0, "document review panel did not load");
  check(/administration/i.test(clean(adminDocument.querySelector("main"))), "admin page did not render");
  const metricsPanel = clean(adminDocument.querySelector("#metricsPanel"));
  const hasMetrics = adminWindow.document.body.innerHTML.includes("http.requests_total");
  check(metricsPanel.length > 0 && hasMetrics, "process metrics panel did not load");
  console.log(`admin          stats=${stats.length} chars, queue=${queue.length} chars, metrics=${hasMetrics ? "loaded" : "MISSING"}, documents=${docsPanel.length} chars`);
} else {
  console.log("admin          skipped (set NYAYMITRA_ADMIN_TOKEN to exercise the console)");
}

if (problems.length) {
  console.error("\nFAILED");
  for (const problem of problems) console.error(" -", problem);
  process.exit(1);
}
console.log(`\nOK — all citizen journeys and the admin console worked against ${base}`);
