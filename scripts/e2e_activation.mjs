#!/usr/bin/env node
/**
 * End-to-end check of the data-activation journeys, driving the real pages in jsdom.
 *
 *   npm install --no-save jsdom
 *   node scripts/e2e_activation.mjs <frontend-url> [<expected-api-origin>]
 *
 * Works for both layouts:
 *   same origin      node scripts/e2e_activation.mjs http://127.0.0.1:8000
 *   separate sites   node scripts/e2e_activation.mjs http://127.0.0.1:3000 http://127.0.0.1:8000
 *
 * Every network call the page makes is recorded. For cross-origin calls the script applies
 * the browser's CORS rule itself (jsdom's fetch shim would not): a response without a matching
 * Access-Control-Allow-Origin header is treated as blocked, exactly as a browser would.
 * jsdom is not a real browser: layout, CSS and service workers are not exercised.
 */
import { JSDOM, VirtualConsole } from "jsdom";

const frontend = (process.argv[2] || "http://127.0.0.1:8000").replace(/\/+$/, "");
const expectedApi = (process.argv[3] || frontend).replace(/\/+$/, "");
const ATTRIBUTION = "Created & Developed by Bambhaniya Divyesh Nonghanbhai";
const results = [];
const network = [];
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const text = (node) => (node?.textContent || "").replace(/\s+/g, " ").trim();
const step = (name, ok, detail = "") => {
  results.push({ name, ok: Boolean(ok), detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
};

const virtualConsole = new VirtualConsole();
virtualConsole.on("jsdomError", (e) => step("no script errors", false, e.message));
const dom = await JSDOM.fromURL(frontend + "/", {
  runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole,
  beforeParse(window) {
    window.fetch = async (input, init = {}) => {
      const url = new URL(input, window.location.href);
      const crossOrigin = url.origin !== window.location.origin;
      const headers = { ...(init.headers || {}) };
      if (crossOrigin) headers.Origin = window.location.origin;
      const response = await fetch(url, { ...init, headers });
      const allow = response.headers.get("access-control-allow-origin");
      const blocked = crossOrigin && allow !== window.location.origin && allow !== "*";
      network.push({ method: init.method || "GET", url: url.href, status: response.status, crossOrigin, blocked });
      if (blocked) throw new TypeError("blocked by CORS policy");
      return response;
    };
    window.scrollTo = () => {};
    window.Element.prototype.scrollIntoView = () => {};
  },
});
const { window } = dom;
const doc = window.document;
const $ = (sel) => doc.querySelector(sel);
const go = async (hash, ms = 700) => { window.location.hash = hash; await wait(ms); };
const view = () => text($("#view"));
await wait(1500);

// 1. frontend opens
step("1. frontend opens and reaches the API", network.some((n) => n.url.endsWith("/api/v1/meta") && n.status === 200),
  `API origin ${new URL(network[0]?.url || frontend).origin}`);
step("   API calls go to the expected backend", network.length > 0 && network.every((n) => n.url.startsWith(expectedApi + "/api/")));
step("   footer attribution (exact text)", text($("footer")).includes(ATTRIBUTION));
step("   home attribution (exact text)", view().includes(ATTRIBUTION));

// 2-3. constitution: parts and articles
$("#langEn").click(); await wait(900);
await go("#/library");
const partButtons = [...doc.querySelectorAll("#libParts [data-part]")];
const articles = () => [...doc.querySelectorAll("#libResults a.article-item")];
step("2. Constitution page opens", Boolean($("#libForm")));
step("3. Parts are displayed", partButtons.length >= 4, partButtons.map(text).join(" | "));
step("   Articles are displayed", articles().length === 9, `${articles().length} articles`);
partButtons.find((b) => b.getAttribute("data-part") === "III").click(); await wait(700);
step("   Part III filter", articles().length === 6, `${articles().length} articles in Part III`);
$("#libQuery").value = "equality"; $("#libForm").dispatchEvent(new window.Event("submit", { cancelable: true })); await wait(700);
step("   Constitution search", articles().some((a) => text(a).includes("Article 14")));

// 4-5. article detail, language switch
await go("#/library/14");
step("4. Article detail shows stored content", view().includes("Article 14") && view().includes("Equality before law") && view().includes("equal protection"));
step("   official text is NOT faked (explicit notice)", /authoritative text|not been loaded|not loaded/i.test(view()));
step("   source reference shown", view().includes("indiacode.nic.in") || view().toLowerCase().includes("owner"));
step("   verification label shown", Boolean($("#view .badge")));
$("#langGu").click(); await wait(1000);
step("5. Switch to Gujarati", view().includes("કાયદા સમક્ષ સમાનતા"));
$("#langEn").click(); await wait(1000);
step("   Switch back to English", view().includes("Equality before law"));

// 6-8. legal library
await go("#/legal", 900);
const libItems = () => [...doc.querySelectorAll("#legalResults a.article-item")];
step("6. Library lists all stored items", libItems().length === 43, `${libItems().length} items`);
$("#legalQuery").value = "refund"; $("#legalForm").dispatchEvent(new window.Event("submit", { cancelable: true })); await wait(700);
step("7. Library keyword search", libItems().length >= 1 && text(libItems()[0]).toLowerCase().includes("consumer"), `${libItems().length} hit(s)`);
$("#legalQuery").value = ""; $("#legalCategory").value = "department"; $("#legalCategory").dispatchEvent(new window.Event("change")); await wait(700);
step("8. Category filter", libItems().length === 11, `${libItems().length} offices`);
$("#legalCategory").value = ""; $("#legalLang").value = "gu"; $("#legalLang").dispatchEvent(new window.Event("change")); await wait(700);
step("   Language filter (Gujarati content)", libItems().length === 43, `${libItems().length} items with Gujarati content`);
await go("#/legal/guide/consumer-complaint", 800);
step("   Library item detail with source section", view().includes("Source") && doc.querySelectorAll("#view .step-list li").length > 0);

// 9-11. assistant
const ask = async (question) => {
  await go("#/assistant", 500);
  $("#question").value = question;
  $("#askForm").dispatchEvent(new window.Event("submit", { cancelable: true, bubbles: true }));
  await wait(1500);
  return text($("#answerArea"));
};
$("#langGu").click(); await wait(900);
const gu = await ask("મફત કાનૂની સહાય કેવી રીતે મળે?");
step("9. Assistant answers a Gujarati question", gu.includes("15100") || gu.includes("૧૫૧૦૦"), gu.slice(0, 70));
const guArticle = await ask("કાયદા સમક્ષ સમાનતા એટલે શું?");
step("   Gujarati question returns an article + reference", guArticle.includes("Article 14") && Boolean($("#answerArea .cite-list a")));
$("#langEn").click(); await wait(900);
const en = await ask("What is equality before law?");
const cite = $("#answerArea .cite-list a");
step("10. Assistant answers an English question", en.includes("Article 14"), en.slice(0, 70));
step("11. Source reference is displayed", cite && cite.getAttribute("href") === "#/library/14", cite?.getAttribute("href"));
const notOfficial = en.includes("not the official text");
await go(cite.getAttribute("href"), 900);
step("    reference opens the cited article", view().includes("Article 14") && view().includes("Equality before law"));
step("    explanation is labelled as not official text", notOfficial);

// 12. unavailable data
const missing = await ask("What does Article 300A say about property?");
step("12. Assistant says a missing article is unavailable", missing.includes("Article 300A is not available"));
await go("#/library/300A", 800);
step("    Missing article page shows a clear message, not a blank page", view().length > 10 && /not found|મળ્યું નથી|મળી નથી/i.test(view()), view().slice(0, 60));
await go("#/legal", 800);
$("#legalQuery").value = "zzzzqqqq"; $("#legalForm").dispatchEvent(new window.Event("submit", { cancelable: true })); await wait(700);
step("    Library with no hits says so", /No results/i.test(text($("#legalResults"))));

// about
await go("#/about", 900);
step("About page: attribution + data counts", view().includes(ATTRIBUTION) && view().includes("Constitution: 9"));

// 13. network
const bad = network.filter((n) => n.blocked || (n.status >= 400 && !n.url.endsWith("/300A")));
step("13. Network: no blocked or failed API calls", bad.length === 0,
  `${network.length} calls, ${network.filter((n) => n.status === 200).length}×200, ` +
  `${network.filter((n) => n.status === 404).length}×404 (expected: Article 300A), ${network.filter((n) => n.blocked).length} blocked`);

window.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
