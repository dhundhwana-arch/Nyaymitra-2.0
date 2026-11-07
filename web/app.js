/* NYAYMITRA 2.0 — citizen UI.
 * Vanilla JS, no framework, no CDN. All user data is inserted with textContent or escaped,
 * never as raw HTML. Routes are hash based so the app works behind any static path. */
(function () {
  'use strict';

  var API = '/api/v1';
  var LS_LANG = 'nyaymitra.lang';

  var state = {
    lang: 'gu',
    meta: null,
    complaint: null,
    toastTimer: null
  };

  /* ------------------------------------------------------------------ i18n */
  var T = {
    gu: {
      brandTag: 'ન્યાય સુલભતા અને માર્ગદર્શન',
      navHome: 'મુખ્ય પૃષ્ઠ', navAssistant: 'સહાયક', navComplaint: 'ફરિયાદ',
      navLibrary: 'બંધારણ', navDepartments: 'કચેરીઓ', navGlossary: 'શબ્દકોશ',
      heroEyebrow: 'તમારો હક, તમારો અવાજ',
      heroTitle: 'કાનૂની માહિતી, સરળ ભાષામાં',
      heroBody: 'તમારી સમસ્યા લખો કે બોલો. અમે સંબંધિત કાનૂની માહિતી, યોગ્ય સરકારી કચેરી અને આગળના પગલાં દર્શાવીશું — સ્રોત સાથે. અમે ન્યાય આપતા નથી.',
      cardAssistantTitle: 'સહાયકને પૂછો', cardAssistantBody: 'સાયબર ફ્રોડ, જમીન, મફત કાનૂની સહાય કે સરકારી અરજી — સ્રોત આધારિત માહિતી.',
      cardComplaintTitle: 'ફરિયાદ તૈયાર કરો', cardComplaintBody: 'માહિતી ભરો, સારાંશ ચકાસો, પછી સાચવો અને સત્તાવાર માધ્યમથી જાતે સબમિટ કરો.',
      cardLibraryTitle: 'બંધારણ જુઓ', cardLibraryBody: 'કલમ શોધો, મૂળ સ્રોત અને ચકાસણી સ્થિતિ સાથે.',
      cardDepartmentsTitle: 'કચેરીઓ અને હેલ્પલાઇન', cardDepartmentsBody: 'સત્તાવાર પોર્ટલ, હેલ્પલાઇન અને ચકાસણી તારીખ સાથે.',
      openCta: 'ખોલો',
      askLabel: 'તમારી મુશ્કેલી લખો',
      askHint: 'ગુજરાતી કે અંગ્રેજીમાં. ઓછામાં ઓછા ૫ અક્ષર.',
      askPlaceholder: 'દા.ત. મારા બેંક ખાતામાંથી અજાણ્યા વ્યક્તિએ ૨૫,૦૦૦ રૂપિયા ઉપાડી લીધા, હવે શું કરવું?',
      categoryLabel: 'શ્રેણી (વૈકલ્પિક)',
      askSubmit: 'માહિતી મેળવો',
      askLoading: 'સ્રોત તપાસી રહ્યું છે…',
      micStart: 'બોલીને લખો', micStop: 'સાંભળી રહ્યું છે… બંધ કરવા દબાવો',
      micUnsupported: 'આ બ્રાઉઝરમાં અવાજ ઓળખ ઉપલબ્ધ નથી — કૃપા કરીને લખો.',
      answerHeading: 'માહિતી',
      citationsHeading: 'સ્રોત (સંબંધિત કલમો)',
      stepsHeading: 'આગળના સંભવિત પગલાં',
      docsHeading: 'તૈયાર રાખવાના દસ્તાવેજો',
      officesHeading: 'સંપર્ક કરવા યોગ્ય કચેરીઓ',
      speak: 'સાંભળો', stopSpeak: 'બંધ કરો',
      reportUnsafe: 'ખોટી કે અસુરક્ષિત માહિતી જણાવો',
      reportThanks: 'આભાર — તમારો રિપોર્ટ માનવ તપાસ માટે નોંધાયો છે.',
      providerOffline: 'ઑફલાઇન (નિયમ-આધારિત)',
      providerLive: 'AI મોડેલ',
      groundedYes: 'સ્રોત આધારિત',
      groundedNo: 'પૂરતો સ્રોત નથી',
      degradedNote: 'AI સેવા ઉપલબ્ધ ન હોવાથી નિયમ-આધારિત, સ્રોત-આધારિત જવાબ આપ્યો છે.',
      complaintTitle: 'ફરિયાદ / અરજી તૈયાર કરો',
      complaintIntro: 'નીચેની માહિતી ભરો. અમે તમારા જ શબ્દોમાંથી સારાંશ બનાવીશું — તમે ચકાસ્યા પછી જ સાચવાશે.',
      step1: '૧. વિગત', step2: '૨. ચકાસણી', step3: '૩. સંદર્ભ',
      fCategory: 'શ્રેણી', fTitle: 'ટૂંકમાં વિષય', fDescription: 'શું થયું તે વિગતે લખો',
      fDate: 'બનાવની તારીખ (વૈકલ્પિક)', fLocation: 'ગામ / શહેર (વૈકલ્પિક)', fDistrict: 'જિલ્લો (વૈકલ્પિક)',
      fState: 'રાજ્ય (વૈકલ્પિક)', fRespondent: 'સામેની વ્યક્તિ/કચેરી (વૈકલ્પિક)',
      fPhone: 'મોબાઇલ નંબર (વૈકલ્પિક)', fEmail: 'ઈમેલ (વૈકલ્પિક)', fDocs: 'દસ્તાવેજ જોડો (PDF/ફોટો, વૈકલ્પિક)',
      consent: 'હું સંમત છું કે આ માહિતી આ સર્વર પર સાચવવામાં આવશે.',
      next: 'આગળ: સારાંશ ચકાસો', back: 'પાછળ', submit: 'ફરિયાદ સાચવો',
      previewLoading: 'સારાંશ બનાવી રહ્યું છે…',
      summaryHeading: 'તમારો ફરિયાદ સારાંશ',
      confirmLabel: 'મેં ઉપરનો સારાંશ અને વિગતો ચકાસી લીધી છે અને તે સાચી છે.',
      savedHeading: 'ફરિયાદ સાચવાઈ ગઈ',
      refLabel: 'સંદર્ભ નંબર', tokenLabel: 'એક્સેસ ટોકન',
      tokenWarning: 'આ ટોકન ફક્ત એક જ વાર દેખાય છે. તેને સાચવો — તેના વિના ફરિયાદ ફરી જોઈ શકાશે નહીં.',
      copy: 'કોપી કરો', copied: 'કોપી થયું', download: 'ટેક્સ્ટ ડાઉનલોડ કરો',
      viewSaved: 'સાચવેલી ફરિયાદ જુઓ', savedRefLabel: 'સંદર્ભ નંબર', savedTokenLabel: 'એક્સેસ ટોકન', open: 'ખોલો',
      libraryTitle: 'ભારતનું બંધારણ', librarySearch: 'કલમ નંબર કે શબ્દ શોધો',
      search: 'શોધો', allParts: 'બધા ભાગ', results: 'પરિણામ', noResults: 'કોઈ પરિણામ મળ્યું નથી.',
      articleText: 'મૂળ કલમનું લખાણ', explanation: 'નાગરિક માટે સરળ સમજૂતી', sourceHeading: 'સ્રોત',
      textNotLoaded: 'આ કલમનું સત્તાવાર લખાણ હજુ લોડ થયેલું નથી — ફક્ત માનવ-લિખિત સમજૂતી ઉપલબ્ધ છે.',
      lastChecked: 'છેલ્લે ચકાસ્યું', neverChecked: 'ક્યારેય ચકાસાયું નથી',
      departmentsTitle: 'સરકારી કચેરીઓ અને સત્તાવાર માધ્યમ', helpline: 'હેલ્પલાઇન', portal: 'પોર્ટલ',
      glossaryTitle: 'કાનૂની શબ્દકોશ', glossarySub: 'સામાન્ય શબ્દોની સરળ સમજૂતી (કાયદાની અધિકૃત વ્યાખ્યા નથી).',
      loading: 'લોડ થઈ રહ્યું છે…', errorGeneric: 'કંઈક ખોટું થયું. ફરી પ્રયાસ કરો.',
      retry: 'ફરી પ્રયાસ કરો', backHome: 'મુખ્ય પૃષ્ઠ પર જાઓ',
      required: 'આ માહિતી જરૂરી છે', tooShort: 'ઓછામાં ઓછા ૨૦ અક્ષર લખો',
      corpusWarning: 'ચેતવણી: સત્તાવાર કલમ લખાણ હજુ લોડ થયેલું નથી (૦ કલમ). હાલ ફક્ત માનવ-લિખિત સમજૂતી દેખાય છે.',
      footerLine: 'AI-આધારિત સમાવેશી ન્યાય સુલભતા અને માર્ગદર્શન.',
      offlineBanner: 'AI સેવા કન્ફિગર નથી — જવાબો નિયમ-આધારિત અને સ્રોત-આધારિત છે.'
    },
    en: {
      brandTag: 'Justice access & navigation',
      navHome: 'Home', navAssistant: 'Assistant', navComplaint: 'Complaint',
      navLibrary: 'Constitution', navDepartments: 'Departments', navGlossary: 'Glossary',
      heroEyebrow: 'Your rights, your voice',
      heroTitle: 'Legal information, in plain language',
      heroBody: 'Describe your problem. We show relevant legal information, the right government office and the next steps — with sources. We do not decide cases.',
      cardAssistantTitle: 'Ask the assistant', cardAssistantBody: 'Cyber fraud, land, free legal aid or a pending government application — sourced information.',
      cardComplaintTitle: 'Prepare a complaint', cardComplaintBody: 'Fill in the details, review the summary, save it and submit it yourself through the official channel.',
      cardLibraryTitle: 'Browse the Constitution', cardLibraryBody: 'Search articles with their original source and verification status.',
      cardDepartmentsTitle: 'Offices and helplines', cardDepartmentsBody: 'Official portals, helplines and the date each contact was checked.',
      openCta: 'Open',
      askLabel: 'Describe your problem',
      askHint: 'Gujarati or English. At least 5 characters.',
      askPlaceholder: 'e.g. Someone withdrew 25,000 rupees from my bank account. What should I do?',
      categoryLabel: 'Category (optional)',
      askSubmit: 'Get information',
      askLoading: 'Checking the sources…',
      micStart: 'Speak instead of typing', micStop: 'Listening… press to stop',
      micUnsupported: 'Speech recognition is not available in this browser — please type.',
      answerHeading: 'Information',
      citationsHeading: 'Sources (related articles)',
      stepsHeading: 'Possible next steps',
      docsHeading: 'Documents to keep ready',
      officesHeading: 'Offices you can contact',
      speak: 'Listen', stopSpeak: 'Stop',
      reportUnsafe: 'Report wrong or unsafe information',
      reportThanks: 'Thank you — your report is queued for human review.',
      providerOffline: 'Offline (rule-based)',
      providerLive: 'AI model',
      groundedYes: 'Grounded in sources',
      groundedNo: 'Not enough sources',
      degradedNote: 'The AI service was unavailable, so a rule-based, source-grounded answer was produced instead.',
      complaintTitle: 'Prepare a complaint or application',
      complaintIntro: 'Fill in the details below. The summary is built only from your own words, and nothing is saved until you review and confirm it.',
      step1: '1. Details', step2: '2. Review', step3: '3. Reference',
      fCategory: 'Category', fTitle: 'Short subject', fDescription: 'What happened (in detail)',
      fDate: 'Date of incident (optional)', fLocation: 'Village / city (optional)', fDistrict: 'District (optional)',
      fState: 'State (optional)', fRespondent: 'Person / office complained against (optional)',
      fPhone: 'Mobile number (optional)', fEmail: 'E-mail (optional)', fDocs: 'Attach documents (PDF/photo, optional)',
      consent: 'I agree that this information may be stored on this server.',
      next: 'Next: review the summary', back: 'Back', submit: 'Save complaint',
      previewLoading: 'Building your summary…',
      summaryHeading: 'Your complaint summary',
      confirmLabel: 'I have reviewed the summary and details above and confirm they are correct.',
      savedHeading: 'Complaint saved',
      refLabel: 'Reference number', tokenLabel: 'Access token',
      tokenWarning: 'This token is shown once. Save it — without it the complaint cannot be opened again.',
      copy: 'Copy', copied: 'Copied', download: 'Download as text',
      viewSaved: 'Open a saved complaint', savedRefLabel: 'Reference number', savedTokenLabel: 'Access token', open: 'Open',
      libraryTitle: 'The Constitution of India', librarySearch: 'Search an article number or a word',
      search: 'Search', allParts: 'All parts', results: 'Results', noResults: 'No results found.',
      articleText: 'Text of the article', explanation: 'Plain-language explanation for citizens', sourceHeading: 'Source',
      textNotLoaded: 'The authoritative text of this article is not loaded yet — only a human-written explanation is available.',
      lastChecked: 'Last checked', neverChecked: 'Never checked',
      departmentsTitle: 'Government offices and official channels', helpline: 'Helpline', portal: 'Portal',
      glossaryTitle: 'Legal glossary', glossarySub: 'Plain-language explanations (not statutory definitions).',
      loading: 'Loading…', errorGeneric: 'Something went wrong. Please try again.',
      retry: 'Retry', backHome: 'Go to home',
      required: 'This field is required', tooShort: 'Please write at least 20 characters',
      corpusWarning: 'Note: the authoritative article text is not loaded yet (0 articles). Only human-written explanations are shown.',
      footerLine: 'AI-powered inclusive justice access and navigation.',
      offlineBanner: 'No AI provider is configured — answers are rule-based and source-grounded.'
    }
  };

  function t(key) {
    var dict = T[state.lang] || T.en;
    return dict[key] || T.en[key] || key;
  }

  /* --------------------------------------------------------------- helpers */
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function $(sel, root) { return (root || document).querySelector(sel); }

  function toast(message) {
    var region = $('#toastRegion');
    var node = document.createElement('div');
    node.className = 'toast';
    node.textContent = message;
    region.appendChild(node);
    window.setTimeout(function () { node.remove(); }, 4200);
  }

  function badge(status) {
    var map = {
      verified: ['badge-verified', state.lang === 'gu' ? 'ચકાસાયેલ' : 'verified'],
      requires_human_verification: ['badge-review', state.lang === 'gu' ? 'માનવ ચકાસણી બાકી' : 'needs human review'],
      unverified: ['badge-unverified', state.lang === 'gu' ? 'અચકાસાયેલ' : 'unverified'],
      outdated: ['badge-unverified', state.lang === 'gu' ? 'જૂનું' : 'outdated'],
      verified_source_text: ['badge-verified', state.lang === 'gu' ? 'સત્તાવાર લખાણ' : 'source text'],
      owner_authored_summary: ['badge-review', state.lang === 'gu' ? 'સમજૂતી (કાયદો નહીં)' : 'summary, not statute'],
      not_available: ['badge-unverified', state.lang === 'gu' ? 'લખાણ ઉપલબ્ધ નથી' : 'text unavailable']
    };
    var item = map[status] || ['badge-neutral', status || '—'];
    return '<span class="badge ' + item[0] + '">' + esc(item[1]) + '</span>';
  }

  async function api(path, options) {
    options = options || {};
    var init = { method: options.method || 'GET', headers: {} };
    if (options.body !== undefined) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(options.body);
    }
    if (options.form) init.body = options.form;
    if (options.headers) Object.keys(options.headers).forEach(function (k) { init.headers[k] = options.headers[k]; });

    var response;
    try {
      response = await fetch(API + path, init);
    } catch (networkError) {
      var offline = new Error(t('errorGeneric'));
      offline.code = 'network_error';
      throw offline;
    }
    var text = await response.text();
    var data = null;
    if (text) { try { data = JSON.parse(text); } catch (e) { data = null; } }
    if (!response.ok) {
      var err = (data && data.error) || {};
      var error = new Error(err.message || t('errorGeneric'));
      error.code = err.code || 'http_' + response.status;
      error.details = err.details;
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function loadingBlock(message) {
    return '<div class="card loading" role="status"><span class="spinner" aria-hidden="true"></span>' +
      '<span>' + esc(message || t('loading')) + '</span></div>';
  }

  function errorBlock(error) {
    var detail = '';
    if (error && error.details && error.details.fields && error.details.fields.length) {
      detail = '<ul class="tiny">' + error.details.fields.map(function (f) {
        return '<li>' + esc(f.field) + ': ' + esc(f.message) + '</li>';
      }).join('') + '</ul>';
    }
    return '<div class="card"><div class="notice danger"><strong>' + esc((error && error.message) || t('errorGeneric')) +
      '</strong>' + detail + '</div><p class="small muted">' + esc(error && error.code ? 'Error code: ' + error.code : '') + '</p></div>';
  }

  /* ------------------------------------------------------------- meta/status */
  async function loadMeta() {
    try {
      state.meta = await api('/meta');
    } catch (error) {
      state.meta = null;
      return;
    }
    var region = $('#statusRegion');
    var html = '';
    var caps = state.meta.capabilities;
    var corpus = state.meta.corpus;
    if (!caps.ai_live) {
      html += '<div class="notice warn small"><strong>' + esc(t('offlineBanner')) + '</strong></div>';
    }
    if (corpus && corpus.verified_text === 0) {
      html += '<div class="notice danger small"><strong>' + esc(t('corpusWarning')) + '</strong><br>' +
        esc(state.lang === 'gu'
          ? 'સ્રોત: ' + corpus.articles + ' કલમ લોડ થયેલ, તેમાંથી ' + corpus.verified_text + ' સત્તાવાર લખાણ.'
          : corpus.articles + ' articles loaded, of which ' + corpus.verified_text + ' have authoritative text.') + '</div>';
    }
    region.innerHTML = html;
    $('#footerVersion').textContent = state.meta.app_name + ' v' + state.meta.version + ' · ' +
      (caps.ai_live ? t('providerLive') : t('providerOffline'));
    $('#brandTag').textContent = t('brandTag');
    $('#footerLine').textContent = t('footerLine');
  }

  /* ------------------------------------------------------------------ views */
  function viewHome() {
    var cards = [
      ['#/assistant', t('cardAssistantTitle'), t('cardAssistantBody')],
      ['#/complaint', t('cardComplaintTitle'), t('cardComplaintBody')],
      ['#/library', t('cardLibraryTitle'), t('cardLibraryBody')],
      ['#/departments', t('cardDepartmentsTitle'), t('cardDepartmentsBody')]
    ];
    return '<section class="hero stack">' +
      '<p class="eyebrow">' + esc(t('heroEyebrow')) + '</p>' +
      '<h1>' + esc(t('heroTitle')) + '</h1>' +
      '<p class="muted">' + esc(t('heroBody')) + '</p>' +
      '</section>' +
      '<section class="grid cols-2" aria-label="' + esc(t('heroTitle')) + '">' +
      cards.map(function (card) {
        return '<a class="card" href="' + card[0] + '"><h2>' + esc(card[1]) + '</h2>' +
          '<p class="small muted">' + esc(card[2]) + '</p>' +
          '<span class="btn btn-sm btn-ghost">' + esc(t('openCta')) + ' →</span></a>';
      }).join('') +
      '</section>' +
      '<section class="card"><h2>' + esc(t('glossaryTitle')) + '</h2>' +
      '<p class="small muted">' + esc(t('glossarySub')) + '</p>' +
      '<a class="btn btn-sm btn-ghost" href="#/glossary">' + esc(t('openCta')) + ' →</a></section>';
  }

  /* ---- assistant ---- */
  var categories = [
    ['', '—'],
    ['cyber_fraud', 'cyber_fraud'], ['land_revenue', 'land_revenue'], ['legal_aid', 'legal_aid'],
    ['consumer', 'consumer'], ['government_grievance', 'government_grievance'],
    ['women_safety', 'women_safety'], ['labour', 'labour'], ['other', 'other']
  ];
  var categoryLabels = {
    cyber_fraud: { gu: 'સાયબર ફસાડ / છેતરપિંડી', en: 'Cyber fraud / financial fraud' },
    land_revenue: { gu: 'જમીન / મહેસૂલ', en: 'Land / revenue' },
    legal_aid: { gu: 'મફત કાનૂની સહાય', en: 'Free legal aid' },
    consumer: { gu: 'ગ્રાહક ફરિયાદ', en: 'Consumer' },
    government_grievance: { gu: 'સરકારી અરજી', en: 'Government application' },
    women_safety: { gu: 'મહિલા સુરક્ષા', en: 'Women safety' },
    labour: { gu: 'શ્રમ / વેતન', en: 'Labour / wages' },
    other: { gu: 'અન્ય', en: 'Other' }
  };

  function categoryLabel(key) {
    var item = categoryLabels[key];
    return item ? item[state.lang] : key;
  }

  function viewAssistant() {
    var options = categories.map(function (pair) {
      return '<option value="' + esc(pair[0]) + '">' +
        esc(pair[0] ? categoryLabel(pair[0]) : '—') + '</option>';
    }).join('');
    return '<section class="card stack">' +
      '<h1>' + esc(t('navAssistant')) + '</h1>' +
      '<form id="askForm" novalidate>' +
      '<div class="field"><label for="question">' + esc(t('askLabel')) + '</label>' +
      '<textarea id="question" name="question" maxlength="1500" required aria-describedby="questionHint" ' +
      'placeholder="' + esc(t('askPlaceholder')) + '"></textarea>' +
      '<p class="hint" id="questionHint">' + esc(t('askHint')) + '</p></div>' +
      '<div class="field"><label for="category">' + esc(t('categoryLabel')) + '</label>' +
      '<select id="category" name="category">' + options + '</select></div>' +
      '<div class="row">' +
      '<button class="btn btn-primary" type="submit" id="askSubmit">' + esc(t('askSubmit')) + '</button>' +
      '<button class="btn btn-ghost" type="button" id="micBtn" aria-pressed="false">🎙 ' + esc(t('micStart')) + '</button>' +
      '</div></form></section>' +
      '<section id="answerArea" aria-live="polite"></section>';
  }

  var warningText = {
    insufficient_sources: {
      gu: 'આ પ્રશ્ન માટે ચકાસાયેલ સ્રોત ઉપલબ્ધ નથી, તેથી અનુમાન કરવામાં આવ્યું નથી.',
      en: 'No verified source covers this question, so no answer was guessed.'
    },
    answer_degraded_offline_grounded: {
      gu: 'જવાબ નિયમ-આધારિત, સ્રોત-આધારિત છે (AI મોડેલ વપરાયું નથી).',
      en: 'The answer is rule-based and source-grounded (no AI model was used).'
    },
    provider_unavailable_fallback: {
      gu: 'AI સેવા ઉપલબ્ધ ન હતી; નિયમ-આધારિત જવાબ આપ્યો.',
      en: 'The AI service was unavailable; a rule-based answer was returned.'
    },
    provider_not_configured: {
      gu: 'સર્વર પર AI પ્રોવાઇડર કન્ફિગર નથી.',
      en: 'No AI provider is configured on this server.'
    },
    fell_back_to_offline_grounded: {
      gu: 'મોડેલના જવાબમાં સ્રોત વગરનો ઉલ્લેખ હતો, તેથી તે રદ કરી સ્રોત-આધારિત જવાબ આપ્યો.',
      en: 'The model answer cited an article outside the retrieved sources, so it was discarded.'
    }
  };

  function warningLabel(code) {
    if (warningText[code]) return warningText[code][state.lang];
    if (code.indexOf('input:') === 0) {
      return state.lang === 'gu'
        ? 'તમારા લખાણમાં સૂચના જેવો ભાગ મળ્યો; તેને ડેટા ગણીને જ જવાબ આપ્યો છે.'
        : 'Instruction-like text was detected in your input and treated as data only.';
    }
    if (code.indexOf('model_rejected:') === 0) {
      return state.lang === 'gu' ? 'મોડેલનો જવાબ સુરક્ષા ચકાસણીમાં પસાર ન થયો.' : 'A model answer failed the safety check.';
    }
    return code;
  }

  function renderAnswer(payload) {
    var area = $('#answerArea');
    var badges = '';
    badges += '<span class="badge badge-neutral">' + esc(payload.provider === 'offline' ? t('providerOffline') : t('providerLive')) + '</span> ';
    badges += '<span class="badge ' + (payload.grounded ? 'badge-verified' : 'badge-unverified') + '">' +
      esc(payload.grounded ? t('groundedYes') : t('groundedNo')) + '</span>';

    var citations = '';
    if (payload.citations && payload.citations.length) {
      citations = '<h3>' + esc(t('citationsHeading')) + '</h3><ul class="cite-list">' +
        payload.citations.map(function (cite) {
          return '<li><a href="#/library/' + esc(cite.article_label.replace(/[^0-9A-Za-z]/g, '')) + '">' +
            esc(cite.article_label) + '</a> ' + badge(cite.verification_status) +
            (cite.title ? ' <span class="small muted">' + esc(cite.title) + '</span>' : '') + '</li>';
        }).join('') + '</ul>';
    }

    var guide = '';
    if (payload.guide) {
      guide = '<h3>' + esc(payload.guide[state.lang === 'gu' ? 'category_gu' : 'category_en']) + '</h3>';
      if (payload.guide.steps && payload.guide.steps.length) {
        guide += '<h4>' + esc(t('stepsHeading')) + '</h4><ol class="step-list">' +
          payload.guide.steps.map(function (step) { return '<li>' + esc(step) + '</li>'; }).join('') + '</ol>';
      }
      if (payload.guide.documents && payload.guide.documents.length) {
        guide += '<h4>' + esc(t('docsHeading')) + '</h4><ul class="doc-list">' +
          payload.guide.documents.map(function (doc) { return '<li>' + esc(doc) + '</li>'; }).join('') + '</ul>';
      }
    }

    var offices = '';
    if (payload.departments && payload.departments.length) {
      offices = '<h3>' + esc(t('officesHeading')) + '</h3><ul class="cite-list">' +
        payload.departments.map(function (dep) {
          var name = state.lang === 'gu' ? dep.name_gu : dep.name_en;
          var helpline = dep.helpline ? ' · <a href="tel:' + esc(dep.helpline) + '">' + esc(dep.helpline) + '</a>' : '';
          var portal = dep.portal_url ? ' · <a href="' + esc(dep.portal_url) + '" rel="noopener noreferrer" target="_blank">' + esc(dep.portal_label || dep.portal_url) + '</a>' : '';
          return '<li>' + esc(name) + ' ' + badge(dep.verification_status) + helpline + portal + '</li>';
        }).join('') + '</ul>';
    }

    var warnings = '';
    if (payload.warnings && payload.warnings.length) {
      warnings = '<div class="notice warn small"><ul class="tiny">' + payload.warnings.map(function (code) {
        return '<li>' + esc(warningLabel(code)) + '</li>';
      }).join('') + '</ul></div>';
    }

    area.innerHTML = '<article class="card stack">' +
      '<div class="panel-head"><h2>' + esc(t('answerHeading')) + '</h2><div>' + badges + '</div></div>' +
      '<p class="answer">' + esc(payload.answer) + '</p>' +
      warnings + guide + citations + offices +
      '<div class="notice small">' + payload.disclaimers.map(function (line) { return esc(line); }).join('<br>') + '</div>' +
      '<div class="row">' +
      '<button class="btn btn-sm btn-ghost" type="button" id="speakBtn">🔊 ' + esc(t('speak')) + '</button>' +
      '<button class="btn btn-sm btn-ghost" type="button" id="reportBtn">⚠ ' + esc(t('reportUnsafe')) + '</button>' +
      '</div></article>';

    var speakBtn = $('#speakBtn');
    if (speakBtn) {
      speakBtn.addEventListener('click', function () {
        if (!('speechSynthesis' in window)) { toast(t('micUnsupported')); return; }
        if (window.speechSynthesis.speaking) {
          window.speechSynthesis.cancel();
          speakBtn.textContent = '🔊 ' + t('speak');
          return;
        }
        var utterance = new SpeechSynthesisUtterance(payload.answer);
        utterance.lang = state.lang === 'gu' ? 'gu-IN' : 'en-IN';
        utterance.rate = 0.95;
        utterance.onend = function () { speakBtn.textContent = '🔊 ' + t('speak'); };
        speakBtn.textContent = '⏹ ' + t('stopSpeak');
        window.speechSynthesis.speak(utterance);
      });
    }

    var reportBtn = $('#reportBtn');
    if (reportBtn) {
      reportBtn.addEventListener('click', async function () {
        try {
          await api('/feedback', {
            method: 'POST',
            body: {
              target_type: 'ai_answer',
              target_ref: payload.request_id || 'unknown',
              reason: payload.grounded ? 'incorrect_law' : 'other',
              message: 'Reported from the citizen UI'
            }
          });
          toast(t('reportThanks'));
          reportBtn.disabled = true;
        } catch (error) {
          toast(error.message);
        }
      });
    }
    area.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function setupAssistant() {
    var form = $('#askForm');
    if (!form) return;
    form.addEventListener('submit', async function (event) {
      event.preventDefault();
      var question = $('#question').value.trim();
      if (question.length < 5) {
        $('#question').setAttribute('aria-invalid', 'true');
        toast(t('required'));
        $('#question').focus();
        return;
      }
      $('#question').removeAttribute('aria-invalid');
      var area = $('#answerArea');
      area.innerHTML = loadingBlock(t('askLoading'));
      var submit = $('#askSubmit');
      submit.disabled = true;
      try {
        var payload = await api('/ai/explain', {
          method: 'POST',
          body: {
            question: question,
            language: state.lang,
            category: $('#category').value || null
          }
        });
        renderAnswer(payload);
      } catch (error) {
        area.innerHTML = errorBlock(error);
      } finally {
        submit.disabled = false;
      }
    });

    var micBtn = $('#micBtn');
    var recognition = null;
    var listening = false;
    micBtn.addEventListener('click', function () {
      var Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!Recognition) { toast(t('micUnsupported')); return; }
      if (listening && recognition) { recognition.stop(); return; }
      recognition = new Recognition();
      recognition.lang = state.lang === 'gu' ? 'gu-IN' : 'en-IN';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onstart = function () {
        listening = true;
        micBtn.setAttribute('aria-pressed', 'true');
        micBtn.textContent = '⏹ ' + t('micStop');
      };
      recognition.onresult = function (event) {
        var transcript = event.results[0][0].transcript;
        $('#question').value = transcript;
        // The user must review and press submit: nothing is sent automatically.
        $('#question').focus();
      };
      recognition.onerror = function () { toast(t('micUnsupported')); };
      recognition.onend = function () {
        listening = false;
        micBtn.setAttribute('aria-pressed', 'false');
        micBtn.textContent = '🎙 ' + t('micStart');
      };
      try { recognition.start(); } catch (e) { toast(t('micUnsupported')); }
    });
  }

  /* ---- complaint ---- */
  function newComplaintState() {
    return { step: 1, form: { documents: [] }, preview: null, saved: null };
  }

  function viewComplaint() {
    if (!state.complaint) state.complaint = newComplaintState();
    return '<section id="complaintRoot"><h1>' + esc(t('complaintTitle')) + '</h1>' +
      '<p class="muted small">' + esc(t('complaintIntro')) + '</p>' +
      renderComplaintStep() + '</section>';
  }

  function progressBar(step) {
    var labels = [t('step1'), t('step2'), t('step3')];
    return '<div class="progress" role="list">' + labels.map(function (label, index) {
      return '<span role="listitem" ' + (index + 1 === step ? 'aria-current="step"' : '') + '>' + esc(label) + '</span>';
    }).join('') + '</div>';
  }

  function renderComplaintStep() {
    var complaint = state.complaint;
    if (complaint.step === 3 && complaint.saved) return renderComplaintSaved();
    if (complaint.step === 2) return progressBar(2) + renderComplaintReview();
    return progressBar(1) + renderComplaintForm();
  }

  function renderComplaintForm() {
    var form = state.complaint.form;
    var options = categories.filter(function (pair) { return pair[0]; }).map(function (pair) {
      return '<option value="' + esc(pair[0]) + '"' + (form.category === pair[0] ? ' selected' : '') + '>' +
        esc(categoryLabel(pair[0])) + '</option>';
    }).join('');
    return '<form class="card stack" id="complaintForm" novalidate>' +
      '<div class="field"><label for="cCategory">' + esc(t('fCategory')) + ' *</label>' +
      '<select id="cCategory" required>' + options + '</select></div>' +
      '<div class="field"><label for="cTitle">' + esc(t('fTitle')) + ' *</label>' +
      '<input type="text" id="cTitle" maxlength="150" required value="' + esc(form.title || '') + '"></div>' +
      '<div class="field"><label for="cDescription">' + esc(t('fDescription')) + ' *</label>' +
      '<textarea id="cDescription" maxlength="5000" required aria-describedby="cDescHint">' + esc(form.description || '') + '</textarea>' +
      '<p class="hint" id="cDescHint">' + esc(t('tooShort')) + '</p></div>' +
      '<div class="grid cols-2">' +
      '<div class="field"><label for="cDate">' + esc(t('fDate')) + '</label><input type="date" id="cDate" value="' + esc(form.incident_date || '') + '"></div>' +
      '<div class="field"><label for="cLocation">' + esc(t('fLocation')) + '</label><input type="text" id="cLocation" maxlength="200" value="' + esc(form.location || '') + '"></div>' +
      '<div class="field"><label for="cDistrict">' + esc(t('fDistrict')) + '</label><input type="text" id="cDistrict" maxlength="200" value="' + esc(form.district || '') + '"></div>' +
      '<div class="field"><label for="cState">' + esc(t('fState')) + '</label><input type="text" id="cState" maxlength="200" value="' + esc(form.state || '') + '"></div>' +
      '<div class="field"><label for="cRespondent">' + esc(t('fRespondent')) + '</label><input type="text" id="cRespondent" maxlength="200" value="' + esc(form.respondent || '') + '"></div>' +
      '<div class="field"><label for="cPhone">' + esc(t('fPhone')) + '</label><input type="tel" id="cPhone" maxlength="15" value="' + esc(form.contact_phone || '') + '"></div>' +
      '</div>' +
      '<div class="field"><label for="cEmail">' + esc(t('fEmail')) + '</label><input type="email" id="cEmail" maxlength="120" value="' + esc(form.contact_email || '') + '"></div>' +
      '<div class="field"><label for="cDocs">' + esc(t('fDocs')) + '</label>' +
      '<input type="file" id="cDocs" accept="application/pdf,image/jpeg,image/png,image/webp" multiple>' +
      '<p class="hint">' + esc((state.meta ? Math.round(state.meta.capabilities.max_upload_bytes / (1024 * 1024)) : 10) + ' MB max per file. PDF, JPEG, PNG, WEBP.') + '</p>' +
      '<ul class="tiny" id="docList">' + (form.documents || []).map(function (doc) {
        return '<li>' + esc(doc.name) + ' — ' + esc(doc.extraction_status || '') + '</li>';
      }).join('') + '</ul></div>' +
      '<div class="field check"><input type="checkbox" id="cConsent" ' + (form.consent ? 'checked' : '') + '>' +
      '<label for="cConsent">' + esc(t('consent')) + ' *</label></div>' +
      '<div aria-live="polite" id="complaintError"></div>' +
      '<button class="btn btn-primary" type="submit">' + esc(t('next')) + '</button>' +
      '</form>';
  }

  function collectComplaintForm() {
    var form = state.complaint.form;
    form.category = $('#cCategory').value;
    form.title = $('#cTitle').value.trim();
    form.description = $('#cDescription').value.trim();
    form.incident_date = $('#cDate').value || null;
    form.location = $('#cLocation').value.trim() || null;
    form.district = $('#cDistrict').value.trim() || null;
    form.state = $('#cState').value.trim() || null;
    form.respondent = $('#cRespondent').value.trim() || null;
    form.contact_phone = $('#cPhone').value.trim() || null;
    form.contact_email = $('#cEmail').value.trim() || null;
    form.consent = $('#cConsent').checked;
  }

  function complaintPayload(includeConfirm) {
    var form = state.complaint.form;
    var payload = {
      language: state.lang,
      category: form.category,
      title: form.title,
      description: form.description,
      incident_date: form.incident_date || null,
      location: form.location,
      district: form.district,
      state: form.state,
      respondent: form.respondent,
      contact_phone: form.contact_phone || null,
      contact_email: form.contact_email || null,
      consent: !!form.consent
    };
    if (includeConfirm) {
      payload.confirmed = true;
      payload.documents = (form.documents || []).map(function (doc) {
        return { id: doc.id, token: doc.token };
      });
    }
    return payload;
  }

  function setupComplaint() {
    var form = $('#complaintForm');
    if (form) {
      var fileInput = $('#cDocs');
      if (fileInput) {
        fileInput.addEventListener('change', async function () {
          var files = Array.prototype.slice.call(fileInput.files || []);
          for (var i = 0; i < files.length; i += 1) {
            var body = new FormData();
            body.append('file', files[i]);
            body.append('document_kind', 'evidence');
            try {
              toast(state.lang === 'gu' ? 'અપલોડ થઈ રહ્યું છે…' : 'Uploading…');
              var record = await api('/documents', { method: 'POST', form: body });
              state.complaint.form.documents.push({
                id: record.id, token: record.access_token, name: record.original_name,
                extraction_status: record.extraction_status
              });
              var list = $('#docList');
              if (list) {
                var li = document.createElement('li');
                li.textContent = record.original_name + ' — ' + record.extraction_status;
                list.appendChild(li);
              }
            } catch (error) {
              toast(error.message);
            }
          }
          fileInput.value = '';
        });
      }
      form.addEventListener('submit', async function (event) {
        event.preventDefault();
        collectComplaintForm();
        var errorBox = $('#complaintError');
        var form2 = state.complaint.form;
        if (form2.title.length < 5 || form2.description.length < 20) {
          errorBox.innerHTML = '<p class="field-error">' + esc(t('required')) + ' — ' + esc(t('tooShort')) + '</p>';
          return;
        }
        if (!form2.consent) {
          errorBox.innerHTML = '<p class="field-error">' + esc(t('consent')) + '</p>';
          return;
        }
        errorBox.innerHTML = loadingBlock(t('previewLoading'));
        try {
          var preview = await api('/complaints/preview', { method: 'POST', body: complaintPayload(false) });
          state.complaint.preview = preview;
          state.complaint.step = 2;
          $('#complaintRoot').outerHTML = '<section id="complaintRoot"><h1>' + esc(t('complaintTitle')) + '</h1>' +
            renderComplaintStep() + '</section>';
          setupComplaint();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (error) {
          errorBox.innerHTML = '<p class="field-error">' + esc(error.message) + '</p>';
        }
      });
      return;
    }

    var confirmBox = $('#confirmReview');
    if (confirmBox) {
      confirmBox.addEventListener('change', function () {
        var submit = $('#submitComplaint');
        if (submit) submit.disabled = !confirmBox.checked;
      });
    }
    var backBtn = $('#backToForm');
    if (backBtn) {
      backBtn.addEventListener('click', function () {
        state.complaint.step = 1;
        $('#complaintRoot').outerHTML = '<section id="complaintRoot"><h1>' + esc(t('complaintTitle')) + '</h1>' +
          renderComplaintStep() + '</section>';
        setupComplaint();
      });
    }
    var submitBtn = $('#submitComplaint');
    if (submitBtn) {
      submitBtn.addEventListener('click', async function () {
        if (!confirmBox.checked) return;
        submitBtn.disabled = true;
        try {
          var saved = await api('/complaints', { method: 'POST', body: complaintPayload(true) });
          state.complaint.saved = saved;
          state.complaint.step = 3;
          $('#complaintRoot').outerHTML = '<section id="complaintRoot"><h1>' + esc(t('complaintTitle')) + '</h1>' +
            renderComplaintStep() + '</section>';
          setupComplaint();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (error) {
          toast(error.message);
          submitBtn.disabled = false;
        }
      });
    }
    var copyButtons = document.querySelectorAll('[data-copy]');
    Array.prototype.forEach.call(copyButtons, function (button) {
      button.addEventListener('click', function () {
        var value = button.getAttribute('data-copy');
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(value).then(function () { toast(t('copied')); });
        } else {
          toast(value);
        }
      });
    });
    var downloadBtn = $('#downloadComplaint');
    if (downloadBtn) {
      downloadBtn.addEventListener('click', function () {
        var saved = state.complaint.saved;
        var text = [
          'NYAYMITRA 2.0 — complaint draft',
          'Reference: ' + saved.reference,
          'Category: ' + categoryLabel(saved.category),
          'Summary: ' + saved.summary,
          'Description: ' + state.complaint.form.description,
          '',
          'Next steps:',
          (saved.next_steps || []).map(function (step, index) { return (index + 1) + '. ' + step; }).join('\n'),
          '',
          'This draft is information only. Submit it yourself through the official channel.'
        ].join('\n');
        var blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        var link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = saved.reference + '.txt';
        link.click();
        URL.revokeObjectURL(link.href);
      });
    }
    var savedForm = $('#savedForm');
    if (savedForm) {
      savedForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        var reference = $('#savedRef').value.trim();
        var token = $('#savedToken').value.trim();
        var output = $('#savedOutput');
        output.innerHTML = loadingBlock();
        try {
          var record = await api('/complaints/' + encodeURIComponent(reference) + '?token=' + encodeURIComponent(token));
          output.innerHTML = '<div class="card"><h3>' + esc(record.reference) + '</h3>' +
            '<p class="small muted">' + esc(record.created_at) + ' · ' + esc(record.status) + '</p>' +
            '<p>' + esc(record.summary) + '</p></div>';
        } catch (error) {
          output.innerHTML = errorBlock(error);
        }
      });
    }
  }

  function renderComplaintReview() {
    var preview = state.complaint.preview || {};
    var form = state.complaint.form;
    return '<div class="card stack">' +
      '<h2>' + esc(t('summaryHeading')) + '</h2>' +
      '<div class="draft">' + esc(preview.summary || '') + '</div>' +
      '<div class="table-wrap"><table><tbody>' +
      '<tr><th>' + esc(t('fCategory')) + '</th><td>' + esc(categoryLabel(form.category)) + '</td></tr>' +
      '<tr><th>' + esc(t('fTitle')) + '</th><td>' + esc(form.title) + '</td></tr>' +
      '<tr><th>' + esc(t('fDate')) + '</th><td>' + esc(form.incident_date || '—') + '</td></tr>' +
      '<tr><th>' + esc(t('fLocation')) + '</th><td>' + esc([form.location, form.district, form.state].filter(Boolean).join(', ') || '—') + '</td></tr>' +
      '<tr><th>' + esc(t('fPhone')) + '</th><td>' + esc(form.contact_phone || '—') + '</td></tr>' +
      '</tbody></table></div>' +
      '<div class="field check"><input type="checkbox" id="confirmReview">' +
      '<label for="confirmReview">' + esc(t('confirmLabel')) + '</label></div>' +
      '<div class="row"><button class="btn btn-ghost" type="button" id="backToForm">' + esc(t('back')) + '</button>' +
      '<button class="btn btn-primary" type="button" id="submitComplaint" disabled>' + esc(t('submit')) + '</button></div>' +
      '</div>';
  }

  function renderComplaintSaved() {
    var saved = state.complaint.saved || {};
    var offices = (saved.departments || []).map(function (dep) {
      return '<li>' + esc(state.lang === 'gu' ? dep.name_gu : dep.name_en) +
        (dep.helpline ? ' · <a href="tel:' + esc(dep.helpline) + '">' + esc(dep.helpline) + '</a>' : '') + '</li>';
    }).join('');
    return '<div class="card stack">' +
      '<div class="notice ok"><strong>' + esc(t('savedHeading')) + '</strong></div>' +
      '<div><span class="tiny muted">' + esc(t('refLabel')) + '</span>' +
      '<div class="token-box">' + esc(saved.reference) + '</div>' +
      '<button class="btn btn-sm btn-ghost" type="button" data-copy="' + esc(saved.reference) + '">' + esc(t('copy')) + '</button></div>' +
      '<div><span class="tiny muted">' + esc(t('tokenLabel')) + '</span>' +
      '<div class="token-box">' + esc(saved.access_token) + '</div>' +
      '<button class="btn btn-sm btn-ghost" type="button" data-copy="' + esc(saved.access_token) + '">' + esc(t('copy')) + '</button></div>' +
      '<div class="notice warn small">' + esc(t('tokenWarning')) + '</div>' +
      '<h3>' + esc(t('stepsHeading')) + '</h3><ol class="step-list">' +
      (saved.next_steps || []).map(function (step) { return '<li>' + esc(step) + '</li>'; }).join('') + '</ol>' +
      (offices ? '<h3>' + esc(t('officesHeading')) + '</h3><ul class="cite-list">' + offices + '</ul>' : '') +
      '<div class="notice small">' + esc(saved.notice || '') + '</div>' +
      '<div class="row"><button class="btn btn-sm btn-ghost" type="button" id="downloadComplaint">' + esc(t('download')) + '</button>' +
      '<a class="btn btn-sm btn-ghost" href="#/home">' + esc(t('backHome')) + '</a></div>' +
      '</div>' + savedLookupBlock();
  }

  function savedLookupBlock() {
    return '<div class="card stack"><h3>' + esc(t('viewSaved')) + '</h3><form id="savedForm">' +
      '<div class="field"><label for="savedRef">' + esc(t('savedRefLabel')) + '</label>' +
      '<input type="text" id="savedRef" required maxlength="20" placeholder="NYM-XXXXXX"></div>' +
      '<div class="field"><label for="savedToken">' + esc(t('savedTokenLabel')) + '</label>' +
      '<input type="password" id="savedToken" required maxlength="200"></div>' +
      '<button class="btn btn-ghost" type="submit">' + esc(t('open')) + '</button></form>' +
      '<div id="savedOutput" aria-live="polite"></div></div>';
  }

  /* ---- library ---- */
  async function viewLibrary(identifier) {
    var container = $('#view');
    container.innerHTML = loadingBlock();
    try {
      if (identifier) {
        var article = await api('/constitution/articles/' + encodeURIComponent(identifier));
        container.innerHTML = renderArticle(article);
        var report = $('#reportArticle');
        if (report) {
          report.addEventListener('click', async function () {
            try {
              await api('/feedback', {
                method: 'POST',
                body: { target_type: 'article', target_ref: article.article_label, reason: 'incorrect_law', message: 'Reported from article view' }
              });
              toast(t('reportThanks'));
              report.disabled = true;
            } catch (error) { toast(error.message); }
          });
        }
        return;
      }
      var parts = await api('/constitution/parts');
      var options = '<option value="">' + esc(t('allParts')) + '</option>' + parts.map(function (part) {
        return '<option value="' + esc(part.part_no || '') + '">' +
          esc((part.part_no ? 'Part ' + part.part_no + ' — ' : '') + (part.part_title || '')) + '</option>';
      }).join('');
      container.innerHTML = '<section class="card stack"><h1>' + esc(t('libraryTitle')) + '</h1>' +
        '<form id="libForm" class="row"><div class="field field-grow">' +
        '<label class="sr-only" for="libQuery">' + esc(t('librarySearch')) + '</label>' +
        '<input type="search" id="libQuery" placeholder="' + esc(t('librarySearch')) + '"></div>' +
        '<div class="field field-flush"><label class="sr-only" for="libPart">' + esc(t('allParts')) + '</label>' +
        '<select id="libPart">' + options + '</select></div>' +
        '<button class="btn btn-primary" type="submit">' + esc(t('search')) + '</button></form>' +
        '<div id="libResults" aria-live="polite"></div></section>';
      var form = $('#libForm');
      form.addEventListener('submit', function (event) { event.preventDefault(); runLibrarySearch(); });
      $('#libPart').addEventListener('change', runLibrarySearch);
      runLibrarySearch();
    } catch (error) {
      container.innerHTML = errorBlock(error);
    }
  }

  async function runLibrarySearch() {
    var results = $('#libResults');
    if (!results) return;
    results.innerHTML = loadingBlock();
    var query = $('#libQuery').value.trim();
    var part = $('#libPart').value;
    var params = ['page_size=20', 'language=' + state.lang];
    if (query) params.push('q=' + encodeURIComponent(query));
    if (part) params.push('part=' + encodeURIComponent(part));
    try {
      var data = await api('/constitution/articles?' + params.join('&'));
      if (!data.items.length) {
        results.innerHTML = '<p class="muted">' + esc(t('noResults')) + '</p>' +
          (data.notice ? '<div class="notice small">' + esc(data.notice) + '</div>' : '');
        return;
      }
      results.innerHTML = '<p class="small muted">' + esc(t('results') + ': ' + data.total + ' · ' + data.took_ms + ' ms') + '</p>' +
        data.items.map(function (item) {
          var title = state.lang === 'gu' ? (item.title_gu || item.title_en) : (item.title_en || item.title_gu);
          return '<a class="article-item" href="#/library/' + esc(item.article_no) + '">' +
            '<div class="spread"><strong>' + esc(item.article_label) + '</strong>' +
            '<span>' + badge(item.verification_status) + ' ' + badge(item.text_status) + '</span></div>' +
            '<h3>' + esc(title || '') + '</h3>' +
            (item.snippet ? '<p class="snippet">' + esc(item.snippet) + '</p>' : '') + '</a>';
        }).join('');
    } catch (error) {
      results.innerHTML = errorBlock(error);
    }
  }

  function renderArticle(article) {
    var title = state.lang === 'gu' ? (article.title_gu || article.title_en) : (article.title_en || article.title_gu);
    var text = state.lang === 'gu' ? article.text_gu : article.text_en;
    var explanation = state.lang === 'gu' ? article.citizen_explanation_gu : article.citizen_explanation_en;
    var sources = (article.sources || []).map(function (source) {
      return '<li><strong>' + esc(source.title) + '</strong><br>' + esc(source.publisher) +
        (source.url ? '<br><a href="' + esc(source.url) + '" rel="noopener noreferrer" target="_blank">' + esc(source.url) + '</a>' : '') +
        '<br><span class="tiny muted">' + esc(source.source_type) +
        (source.retrieved_on ? ' · retrieved ' + esc(source.retrieved_on) : ' · not retrieved in this environment') + '</span></li>';
    }).join('');
    return '<article class="card stack">' +
      '<a class="btn btn-sm btn-ghost" href="#/library">← ' + esc(t('navLibrary')) + '</a>' +
      '<div class="spread"><h1>' + esc(article.article_label) + ': ' + esc(title || '') + '</h1>' +
      '<div>' + badge(article.verification_status) + ' ' + badge(article.text_status) + '</div></div>' +
      '<p class="small muted">' + esc((article.part_no ? 'Part ' + article.part_no + ' — ' : '') + (article.part_title || '') +
        (article.chapter_title ? ' · ' + article.chapter_title : '')) + '</p>' +
      '<div><h3>' + esc(t('articleText')) + '</h3>' +
      (text ? '<p>' + esc(text) + '</p>'
        : '<div class="notice warn small">' + esc(t('textNotLoaded')) + '</div>') + '</div>' +
      '<div><h3>' + esc(t('explanation')) + '</h3><p>' + esc(explanation || '—') + '</p></div>' +
      (article.notes ? '<details><summary class="small muted">' + esc(state.lang === 'gu' ? 'નોંધ' : 'Notes') + '</summary><p class="small">' + esc(article.notes) + '</p></details>' : '') +
      '<p class="small muted">' + esc(t('lastChecked') + ': ' + (article.last_checked_at || t('neverChecked'))) + '</p>' +
      (sources ? '<div><h3>' + esc(t('sourceHeading')) + '</h3><ul class="cite-list">' + sources + '</ul></div>' : '') +
      '<div class="notice small">' + (article.disclaimers || []).map(esc).join('<br>') + '</div>' +
      '<div class="row"><button class="btn btn-sm btn-ghost" type="button" id="reportArticle">⚠ ' + esc(t('reportUnsafe')) + '</button></div>' +
      '</article>';
  }

  /* ---- departments ---- */
  async function viewDepartments() {
    var container = $('#view');
    container.innerHTML = loadingBlock();
    try {
      var data = await api('/departments');
      container.innerHTML = '<section class="stack"><h1>' + esc(t('departmentsTitle')) + '</h1>' +
        '<div class="notice small">' + esc(data.notice) + '</div>' +
        '<div class="grid cols-2">' + data.items.map(function (dep) {
          var name = state.lang === 'gu' ? dep.name_gu : dep.name_en;
          var purpose = state.lang === 'gu' ? dep.purpose_gu : dep.purpose_en;
          return '<article class="card stack">' +
            '<div class="spread"><h2>' + esc(name) + '</h2>' + badge(dep.verification_status) + '</div>' +
            '<p class="small muted">' + esc(purpose || '') + '</p>' +
            '<div class="row">' +
            (dep.helpline ? '<a class="btn btn-sm btn-primary" href="tel:' + esc(dep.helpline) + '">📞 ' + esc(dep.helpline) + '</a>' : '') +
            (dep.portal_url ? '<a class="btn btn-sm btn-ghost" href="' + esc(dep.portal_url) + '" target="_blank" rel="noopener noreferrer">' + esc(dep.portal_label || t('portal')) + '</a>' : '') +
            '</div>' +
            '<p class="tiny muted">' + esc(dep.verified_on ? t('lastChecked') + ': ' + dep.verified_on : t('neverChecked')) + '</p>' +
            (dep.source ? '<p class="tiny"><a href="' + esc(dep.source.url || '#') + '" target="_blank" rel="noopener noreferrer">' + esc(dep.source.publisher) + '</a></p>' : '') +
            '</article>';
        }).join('') + '</div></section>';
    } catch (error) {
      container.innerHTML = errorBlock(error);
    }
  }

  /* ---- glossary ---- */
  async function viewGlossary() {
    var container = $('#view');
    container.innerHTML = loadingBlock();
    try {
      var items = await api('/ai/glossary?language=' + state.lang);
      container.innerHTML = '<section class="card stack"><h1>' + esc(t('glossaryTitle')) + '</h1>' +
        '<p class="small muted">' + esc(t('glossarySub')) + '</p>' +
        '<div class="field"><label class="sr-only" for="glossFilter">' + esc(t('search')) + '</label>' +
        '<input type="search" id="glossFilter" placeholder="' + esc(t('search')) + '"></div>' +
        '<div id="glossList" class="stack"></div></section>';
      var render = function (filter) {
        var list = items.filter(function (item) {
          if (!filter) return true;
          var haystack = (item.term + ' ' + item.explanation).toLowerCase();
          return haystack.indexOf(filter.toLowerCase()) !== -1;
        });
        $('#glossList').innerHTML = list.length ? list.map(function (item) {
          return '<details class="article-item"><summary><strong>' + esc(item.term) + '</strong></summary>' +
            '<p class="small">' + esc(item.explanation) + '</p></details>';
        }).join('') : '<p class="muted">' + esc(t('noResults')) + '</p>';
      };
      render('');
      $('#glossFilter').addEventListener('input', function (event) { render(event.target.value); });
    } catch (error) {
      container.innerHTML = errorBlock(error);
    }
  }

  /* ---------------------------------------------------------------- routing */
  function parseRoute() {
    var hash = window.location.hash.replace(/^#\/?/, '');
    var parts = hash.split('/').filter(Boolean);
    return { name: parts[0] || 'home', param: parts[1] || null };
  }

  async function route() {
    var current = parseRoute();
    var view = $('#view');
    var navLinks = document.querySelectorAll('[data-nav]');
    Array.prototype.forEach.call(navLinks, function (link) {
      var name = link.getAttribute('data-nav');
      var isActive = name === current.name || (current.name === 'home' && name === 'home');
      if (isActive) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });

    if (current.name === 'assistant') {
      view.innerHTML = viewAssistant();
      setupAssistant();
    } else if (current.name === 'complaint') {
      view.innerHTML = viewComplaint();
      setupComplaint();
    } else if (current.name === 'library') {
      await viewLibrary(current.param);
    } else if (current.name === 'departments') {
      await viewDepartments();
    } else if (current.name === 'glossary') {
      await viewGlossary();
    } else {
      view.innerHTML = viewHome();
    }
    var main = $('#main');
    if (main) main.focus({ preventScroll: true });
  }

  /* -------------------------------------------------------------- language */
  function applyLanguage(lang, persist) {
    state.lang = lang === 'en' ? 'en' : 'gu';
    document.documentElement.lang = state.lang;
    var gu = $('#langGu');
    var en = $('#langEn');
    gu.setAttribute('aria-pressed', String(state.lang === 'gu'));
    en.setAttribute('aria-pressed', String(state.lang === 'en'));
    var navMap = {
      home: t('navHome'), assistant: t('navAssistant'), complaint: t('navComplaint'),
      library: t('navLibrary'), departments: t('navDepartments'), glossary: t('navGlossary')
    };
    Object.keys(navMap).forEach(function (key) {
      var link = document.querySelector('[data-nav="' + key + '"]');
      if (link) link.textContent = navMap[key];
    });
    $('#brandTag').textContent = t('brandTag');
    $('#footerLine').textContent = t('footerLine');
    if (persist) {
      try { localStorage.setItem(LS_LANG, state.lang); } catch (e) { /* storage may be blocked */ }
    }
    loadMeta().then(route);
  }

  function init() {
    var stored = null;
    try { stored = localStorage.getItem(LS_LANG); } catch (e) { stored = null; }
    state.lang = stored === 'en' ? 'en' : 'gu';
    $('#langGu').addEventListener('click', function () { applyLanguage('gu', true); });
    $('#langEn').addEventListener('click', function () { applyLanguage('en', true); });
    window.addEventListener('hashchange', route);
    applyLanguage(state.lang, false);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
