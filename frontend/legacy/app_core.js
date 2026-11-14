// --- COMPLETE MULTILINGUAL DATA & SYSTEM ENGINE ---
let currentLang = 'en';

const legalArticlesData = [
  {
    no: "Article 14",
    title_en: "Equality Before Law",
    title_gu: "કાયદા સમક્ષ સમાનતા",
    title_hi: "विधि के समक्ष समानता",
    tag_en: "Right to Equality",
    tag_gu: "સમાનતાનો અધિકાર",
    tag_hi: "समानता का अधिकार",
    desc_en: "The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India. Rich or poor, all are equal in the eyes of law.",
    desc_gu: "રાજ્ય ભારતના પ્રદેશમાં કોઈપણ વ્યક્તિને કાયદા સમક્ષ સમાનતા અથવા કાયદાઓના સમાન રક્ષણથી વંચિત રાખશે નહીં. અમીર હોય કે ગરીબ, કાયદો બધા માટે સમાન છે.",
    desc_hi: "राज्य भारत के राज्यक्षेत्र में किसी व्यक्ति को विधि के समक्ष समानता से या विधियों के समान संरक्षण से वंचित नहीं करेगा। कानून की नजर में सब एकसमान हैं।"
  },
  {
    no: "Article 19",
    title_en: "Protection of Six Freedoms (Speech & Expression)",
    title_gu: "વાણી અને અભિવ્યક્તિની સ્વતંત્રતા",
    title_hi: "वाक्-स्वातंत्र्य और अभिव्यक्ति की स्वतंत्रता",
    tag_en: "Right to Freedom",
    tag_gu: "સ્વતંત્રતાનો અધિકાર",
    tag_hi: "स्वतंत्रता का अधिकार",
    desc_en: "Guarantees all citizens the right to freedom of speech, peaceful assembly, forming associations, free movement, and trade or profession across India.",
    desc_gu: "તમામ નાગરિકોને શાંતિપૂર્ણ સભા ભરવાની, સંગઠનો બનાવવાની, દેશભરમાં મુક્તપણે ફરવાની અને વાણી સ્વાતંત્ર્યનો અધિકાર છે.",
    desc_hi: "सभी नागरिकों को विचार और अभिव्यक्ति की, शांतिपूर्वक सम्मेलन करने की, संस्था या संघ बनाने की और संचरण करने की स्वतंत्रता है।"
  },
  {
    no: "Article 21",
    title_en: "Protection of Life & Personal Liberty",
    title_gu: "જીવન અને વ્યક્તિગત સ્વતંત્રતાનું રક્ષણ",
    title_hi: "प्राण और दैहिक स्वतंत्रता का संरक्षण",
    tag_en: "Right to Life",
    tag_gu: "જીવનનો હક્ક",
    tag_hi: "जीवन का अधिकार",
    desc_en: "No person shall be deprived of his life or personal liberty except according to procedure established by law. Includes right to clean environment, speedy trial, and privacy.",
    desc_gu: "કાયદા દ્વારા સ્થાપિત પ્રક્રિયા સિવાય કોઈપણ વ્યક્તિને તેના જીવન અથવા વ્યક્તિગત સ્વતંત્રતાથી વંચિત કરી શકાશે નહીં. આમાં ઝડપી ન્યાય અને ગૌરવપૂર્ણ જીવન સામેલ છે.",
    desc_hi: "विधि द्वारा स्थापित प्रक्रिया के अतिरिक्त किसी व्यक्ति को उसके प्राण या दैहिक स्वतंत्रता से वंचित नहीं किया जाएगा। इसमें त्वरित न्याय और निजता शामिल है।"
  },
  {
    no: "Article 22",
    title_en: "Protection Against Arrest & Detention",
    title_gu: "ધરપકડ સામે રક્ષણના કાનૂની હક્કો",
    title_hi: "गिरफ्तारी और निरोध से संरक्षण",
    tag_en: "Legal Defense",
    tag_gu: "કાનૂની બચાવ",
    tag_hi: "विधिक बचाव",
    desc_en: "Right to be informed of grounds of arrest, right to consult and be defended by a legal practitioner, and mandatory presentation before a magistrate within 24 hours.",
    desc_gu: "ધરપકડનું કારણ જાણવાનો હક, વકીલ સાથે સલાહ કરવાનો હક અને ૨૪ કલાકમાં મેજિસ્ટ્રેટ સમક્ષ રજૂ થવાનો અબાધિત હક છે.",
    desc_hi: "गिरफ्तारी के कारण जानने का अधिकार, अपनी पसंद के वकील से परामर्श करने का अधिकार तथा २४ घंटे के भीतर मजिस्ट्रेट के समक्ष पेश किए जाने का अधिकार।"
  },
  {
    no: "Article 32 & 226",
    title_en: "Constitutional Remedies & Writs (Supreme Court / High Court)",
    title_gu: "બંધારણીય ઉપચારો અને રીટ અરજીઓ",
    title_hi: "संवैधानिक उपचार और रिट याचिका",
    tag_en: "Remedies",
    tag_gu: "બંધારણીય ઉપાયો",
    tag_hi: "संवैधानिक उपचार",
    desc_en: "Right to move Supreme Court (Art 32) and High Court (Art 226) through Writs (Habeas Corpus, Mandamus, Quo Warranto, etc.) for direct enforcement of fundamental rights.",
    desc_gu: "જો સરકાર કે કોઈ અધિકારી તમારા મૂળભૂત અધિકારનું ઉલ્લંઘન કરે, તો સીધા હાઇકોર્ટ કે સુપ્રીમ કોર્ટમાં હેબિયસ કોર્પસ કે મેન્ડેમસ રીટ દાખલ કરી શકાય છે.",
    desc_hi: "मौलिक अधिकारों के उल्लंघन पर सीधे उच्च न्यायालय या सर्वोच्च न्यायालय में बंदी प्रत्यक्षीकरण और परमादेश जैसी रिट याचिका दायर करने का अधिकार।"
  },
  {
    no: "Article 39A",
    title_en: "Equal Justice & Free Legal Aid for Citizens",
    title_gu: "સમાન ન્યાય અને મફત કાનૂની સહાય",
    title_hi: "समान न्याय और निःशुल्क विधिक सहायता",
    tag_en: "Free Legal Aid",
    tag_gu: "મફત કાનૂની સહાય",
    tag_hi: "निःशुल्क कानूनी सहायता",
    desc_en: "The State shall provide free legal aid by suitable legislation or schemes to ensure opportunities for securing justice are not denied to any citizen by reason of economic disability.",
    desc_gu: "કોઈપણ નાગરિક આર્થિક કે અન્ય અસમર્થતાના કારણે ન્યાય મેળવવાથી વંચિત ન રહે તે સુનિશ્ચિત કરવા રાજ્ય મફત કાનૂની સહાય પૂરી પાડશે. (NALSA & DLSA).",
    desc_hi: "राज्य यह सुनिश्चित करेगा कि आर्थिक या किसी अन्य अक्षमता के कारण कोई नागरिक न्याय प्राप्त करने के अवसर से वंचित न रहे। निःशुल्क विधिक सहायता उपलब्ध कराई जाएगी।"
  }
];

// UI Text Translation Dictionaries
const uiTranslations = {
  en: {
    heroTitle: "We are here to help.",
    heroSub: "Explore information, find services, and understand possible next steps.",
    tagline: "Your Rights, Your Voice | Equitable, Accessible, and Timely Justice for Every Citizen of India",
    secTitle: "Constitution of India & Citizen Rights (Constitution Library)",
    secSub: "Most useful constitutional articles and fundamental rights for every citizen.",
    btnAssistant: "🎙️ Voice & Text Assistant",
    btnDrafter: "📝 Application Drafter",
    btnLibrary: "📖 Constitution Library",
    btnHelpline: "🏛️ Official Portals & Helplines"
  },
  gu: {
    heroTitle: "અમે અહીં તમારી સહાય માટે છીએ.",
    heroSub: "માહિતી મેળવો, કાનૂની સેવાઓ શોધો અને આગામી યોગ્ય પગલાં સમજો.",
    tagline: "તમારો હક, તમારો અવાજ | ભારતભરમાં દરેક નાગરિક માટે સમાન, સત્વરે અને પારદર્શક ન્યાય",
    secTitle: "ભારતીય સંવિધાન અને નાગરિક અધિકારો (Constitution Library)",
    secSub: "સામાન્ય નાગરિક માટે સૌથી વધુ ઉપયોગી બંધારણીય કલમો અને મૂળભૂત અધિકારો.",
    btnAssistant: "🎙️ અવાજ અને ટેક્સ્ટ સહાયક",
    btnDrafter: "📝 કાનૂની અરજી ડ્રાફ્ટર",
    btnLibrary: "📖 બંધારણીય લાઇબ્રેરી",
    btnHelpline: "🏛️ સત્તાવાર પોર્ટલ અને હેલ્પલાઇન"
  },
  hi: {
    heroTitle: "हम आपकी सहायता के लिए यहाँ हैं।",
    heroSub: "जानकारी प्राप्त करें, कानूनी सेवाएं खोजें और उचित कदम समझें।",
    tagline: "आपका अधिकार, आपकी आवाज़ | भारत के प्रत्येक नागरिक के लिए सुलभ और त्वरित न्याय",
    secTitle: "भारतीय संविधान एवं नागरिक अधिकार (Constitution Library)",
    secSub: "आम नागरिकों के लिए सबसे उपयोगी संवैधानिक अनुच्छेद और मौलिक अधिकार।",
    btnAssistant: "🎙️ वॉइस एवं टेक्स्ट सहायक",
    btnDrafter: "📝 कानूनी आवेदन ड्राफ्टर",
    btnLibrary: "📖 संविधान लाइब्रेरी",
    btnHelpline: "🏛️ आधिकारिक पोर्टल एवं हेल्पलाइन"
  }
};

// Render Articles based on Language
function renderArticles() {
  const container = document.getElementById('articlesListContainer');
  if (!container) return;
  
  let html = '';
  legalArticlesData.forEach(item => {
    const title = item['title_' + currentLang] || item.title_en;
    const tag = item['tag_' + currentLang] || item.tag_en;
    const desc = item['desc_' + currentLang] || item.desc_en;
    
    html += `
      <div class="card" style="margin-bottom: 18px; border: 1px solid var(--line); border-radius: 14px; padding: 18px; background: #0c1729;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
          <strong style="color:var(--gold); font-size:16px;">${item.no}</strong>
          <span style="background: rgba(229,189,104,0.15); color: var(--gold2); padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">${tag}</span>
        </div>
        <h3 style="color: #fff; margin: 6px 0 10px; font-size: 18px;">${title}</h3>
        <p style="color: var(--muted); font-size: 14px; line-height: 1.7; margin: 0;">${desc}</p>
      </div>
    `;
  });
  container.innerHTML = html;
}

// Update UI Text on Language Change
function setLanguage(lang) {
  currentLang = lang;
  const t = uiTranslations[lang] || uiTranslations.en;
  
  // Update Buttons & Headings
  const heroH = document.querySelector('.hero h1, .welcome-title, h1');
  if (heroH) heroH.innerText = t.heroTitle;
  
  const heroP = document.querySelector('.hero p, .subbrand');
  if (heroP) heroP.innerText = t.heroSub;
  
  const secH = document.getElementById('secTitleHeader');
  if (secH) secH.innerText = t.secTitle;
  
  const secP = document.getElementById('secSubHeader');
  if (secP) secP.innerText = t.secSub;
  
  // Re-render articles
  renderArticles();
}

// Dynamic Interactive Navigation for 4 Main Feature Buttons
function showFeature(featureKey) {
  const displayArea = document.getElementById('dynamicFeatureArea');
  if (!displayArea) return;
  
  displayArea.style.display = 'block';
  
  if (featureKey === 'assistant') {
    displayArea.innerHTML = `
      <div class="card" style="background:#111f38; border:1px solid var(--gold); border-radius:16px; padding:20px; margin-bottom:25px;">
        <h3 style="color:var(--gold2); margin-top:0;">🎙️ Legal Voice & Text AI Assistant</h3>
        <p style="color:var(--muted); font-size:14px;">Ask any legal query in plain English, Gujarati, or Hindi:</p>
        <div style="display:flex; gap:10px; margin-top:12px;">
          <input type="text" id="userQueryInput" class="field" placeholder="e.g. Someone stole my vehicle / સાયબર ફ્રોડ થયો..." style="flex:1;">
          <button class="gold-btn" onclick="executeSearch()">Ask JARVIS</button>
        </div>
        <div id="aiQueryResult" style="margin-top:15px; display:none; padding:14px; background:#071224; border-radius:10px;"></div>
      </div>
    `;
  } else if (featureKey === 'drafter') {
    displayArea.innerHTML = `
      <div class="card" style="background:#111f38; border:1px solid var(--gold); border-radius:16px; padding:20px; margin-bottom:25px;">
        <h3 style="color:var(--gold2); margin-top:0;">📝 Automated Legal Application Drafter</h3>
        <p style="color:var(--muted); font-size:14px;">Generate RTI, Police Complaint, or Consumer Grievance Application:</p>
        <select id="draftType" class="field" style="margin-bottom:10px;">
          <option value="police">Police Complaint / FIR Notice</option>
          <option value="rti">Right to Information (RTI) Application</option>
          <option value="consumer">Consumer Court Notice</option>
        </select>
        <textarea id="draftDetails" class="field" placeholder="Enter incident details, dates, and parties involved..."></textarea>
        <button class="gold-btn" style="margin-top:10px;" onclick="generateDraftPreview()">Generate Legal Draft</button>
        <div id="draftOutput" style="margin-top:15px; display:none; padding:14px; background:#071224; border-radius:10px; white-space:pre-wrap;"></div>
      </div>
    `;
  } else if (featureKey === 'library') {
    displayArea.style.display = 'none';
    const libSec = document.getElementById('constitutionSection');
    if (libSec) libSec.scrollIntoView({ behavior: 'smooth' });
  } else if (featureKey === 'helplines') {
    displayArea.innerHTML = `
      <div class="card" style="background:#111f38; border:1px solid var(--gold); border-radius:16px; padding:20px; margin-bottom:25px;">
        <h3 style="color:var(--gold2); margin-top:0;">🏛️ Official Citizen Legal Portals & Emergency Helplines</h3>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:12px; margin-top:15px;">
          <div style="background:#081224; padding:12px; border-radius:10px; border:1px solid var(--line);">
            <strong style="color:var(--gold2);">Cyber Crime Helpline</strong><br>
            <span style="font-size:18px; color:#fff;">📞 1930</span><br>
            <small style="color:var(--muted);">cybercrime.gov.in</small>
          </div>
          <div style="background:#081224; padding:12px; border-radius:10px; border:1px solid var(--line);">
            <strong style="color:var(--gold2);">National Legal Aid (NALSA)</strong><br>
            <span style="font-size:18px; color:#fff;">📞 15100</span><br>
            <small style="color:var(--muted);">Free Legal Defense</small>
          </div>
          <div style="background:#081224; padding:12px; border-radius:10px; border:1px solid var(--line);">
            <strong style="color:var(--gold2);">Women Helpline</strong><br>
            <span style="font-size:18px; color:#fff;">📞 1091 / 181</span><br>
            <small style="color:var(--muted);">24/7 Domestic & Safety</small>
          </div>
        </div>
      </div>
    `;
  }
}

// Search Logic
async function executeSearch() {
  const q = document.getElementById('userQueryInput').value.trim();
  const resBox = document.getElementById('aiQueryResult');
  if (!q) return;
  resBox.style.display = 'block';
  resBox.innerHTML = '<em>Searching statutory articles and penal codes...</em>';
  
  try {
    const res = await fetch('/api/query', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: q})
    });
    const d = await res.json();
    resBox.innerHTML = `<strong>Relevant Statute:</strong> ${d.statute || 'Constitution / BNS'}<br><strong>Action Plan:</strong> ${d.action_plan || 'Consult nearest Legal Aid Center.'}`;
  } catch (e) {
    resBox.innerHTML = `<strong>Legal Guidance:</strong> For your query "${q}", protection is guaranteed under Indian constitutional and criminal laws. You may file a complaint at your local police station or contact DLSA (Helpline: 15100).`;
  }
}

// Draft Generator Logic
function generateDraftPreview() {
  const type = document.getElementById('draftType').value;
  const desc = document.getElementById('draftDetails').value;
  const out = document.getElementById('draftOutput');
  out.style.display = 'block';
  out.innerText = `TO WHOMSOEVER IT MAY CONCERN\n\nSUBJECT: Formal Notice / Application regarding ${type.toUpperCase()}\n\nDETAILS:\n${desc || 'Incident description as submitted by citizen.'}\n\nPRAYER:\nImmediate action is requested under governing provisions of the law.\n\nDate: 04/Nov/2026\nApplicant Signature: [Applicant Name]`;
}

window.addEventListener('DOMContentLoaded', () => {
  renderArticles();
});
