const fullConstitutionData = [
  {
    no: "Preamble",
    title: "ભારતનું બંધારણ - આમુખ",
    part: "બંધારણનો આત્મા",
    desc: "અમે, ભારતના લોકો, ભારતને એક સાર્વભૌમ, સમાજવાદી, બિનસાંપ્રદાયિક, લોકશાહી પ્રજાસત્તાક બનાવવા માટે અને તેના તમામ નાગરિકોને: સામાજિક, આર્થિક અને રાજકીય ન્યાય; વિચાર, અભિવ્યક્તિ, માન્યતા, શ્રદ્ધા અને ઉપાસનાની સ્વતંત્રતા; દરજ્જા અને તકની સમાનતા સુનિશ્ચિત કરવાનો દ્રઢ સંકલ્પ કરીએ છીએ.",
    remedy: "આમુખ એ ભારતીય ન્યાય વ્યવસ્થાનો પાયો છે. કોઈ પણ કાયદાકીય અસમંજસ વખતે કોર્ટ આમુખના સિદ્ધાંતોનું પાલન કરે છે."
  },
  {
    no: "Article 14",
    title: "કાયદા સમક્ષ સમાનતા (Right to Equality)",
    part: "ભાગ ૩ - મૂળભૂત અધિકારો",
    desc: "રાજ્ય ભારતના સમગ્ર ક્ષેત્રમાં કોઈપણ વ્યક્તિને કાયદા સમક્ષ સમાનતા અથવા કાયદાના સમાન રક્ષણથી વંચિત રાખશે નહીં. અમીર, ગરીબ, અધિકારી કે સામાન્ય નાગરિક - કાયદો બધા માટે એકસમાન છે.",
    remedy: "જો સરકારી તંત્ર કે કોઈ સંસ્થા જાતિ, ધર્મ કે વગના આધારે ભેદભાવ કરે, તો હાઇકોર્ટ (કલમ ૨૨૬) અથવા સુપ્રીમ કોર્ટ (કલમ ૩૨) માં સીધી રીટ અરજી કરી શકાય."
  },
  {
    no: "Article 19",
    title: "વાણી અને અભિવ્યક્તિની સ્વતંત્રતા (Freedom of Speech)",
    part: "ભાગ ૩ - મૂળભૂત અધિકારો",
    desc: "તમામ નાગરિકોને વાણી અને અભિવ્યક્તિની સ્વતંત્રતા, શાંતિપૂર્ણ રીતે અને શસ્ત્રો વિના ભેગા થવાની, સંગઠનો રચવાની અને સમગ્ર દેશમાં મુક્તપણે હરવા-ફરવાની સ્વતંત્રતા છે.",
    remedy: "ગેરકાયદેસર સેન્સરશીપ કે શાંતિપૂર્ણ વિરોધ પર પ્રતિબંધ સામે કોર્ટમાં રક્ષણ માંગી શકાય."
  },
  {
    no: "Article 21",
    title: "જીવન અને અંગત સ્વાતંત્ર્યનું રક્ષણ (Right to Life & Liberty)",
    part: "ભાગ ૩ - મૂળભૂત અધિકારો",
    desc: "કાયદા દ્વારા સ્થાપિત પ્રક્રિયા સિવાય કોઈપણ વ્યક્તિને તેના જીવન અથવા વ્યક્તિગત સ્વતંત્રતાથી વંચિત કરી શકાશે નહીં. આમાં ગૌરવપૂર્ણ જીવન, ગોપનીયતા (Privacy), સ્વચ્છ પર્યાવરણ અને આરોગ્યનો સમાવેશ થાય છે.",
    remedy: "પોલીસ કે તંત્ર દ્વારા બિનકાયદેસર અટકાયત કે હિંસા સામે હાઇકોર્ટમાં તાત્કાલિક હેબિયસ કોર્પસ (Habeas Corpus) અરજી કરી મુક્તિ મેળવાય."
  },
  {
    no: "Article 21A",
    title: "મફત અને ફરજિયાત શિક્ષણ (Right to Education)",
    part: "ભાગ ૩ - મૂળભૂત અધિકારો",
    desc: "રાજ્ય ૬ થી ૧૪ વર્ષની વયના તમામ બાળકોને કાયદા દ્વારા નક્કી કરવામાં આવે તે રીતે મફત અને ફરજિયાત પ્રાથમિક શિક્ષણ પૂરું પાડશે.",
    remedy: "જો કોઈ શાળા પ્રવેશ ન આપે કે ફી માંગે, તો જિલ્લા શિક્ષણ અધિકારી (DEO) અને બાળ અધિકાર આયોગમાં તાત્કાલિક ફરિયાદ કરી શકાય."
  },
  {
    no: "Article 22",
    title: "ધરપકડ સામે રક્ષણ (Protection Against Arrest)",
    part: "ભાગ ૩ - મૂળભૂત અધિકારો",
    desc: "ધરપકડ કરાયેલ વ્યક્તિને કારણ જાણવાનો અધિકાર છે, પોતાની પસંદગીના વકીલની સલાહ લેવાનો અધિકાર છે અને ૨૪ કલાકની અંદર નજીકના મેજિસ્ટ્રેટ સમક્ષ રજૂ થવાનો અબાધિત હક છે.",
    remedy: "જો ૨૪ કલાકમાં મેજિસ્ટ્રેટ સમક્ષ હાજર ન કરાય તો ધરપકડ ગેરકાયદેસર ગણાય અને તાત્કાલિક જામીન માટે મેજિસ્ટ્રેટને જાણ કરી શકાય."
  },
  {
    no: "Article 32",
    title: "બંધારણીય ઉપચારોનો અધિકાર (Right to Remedies)",
    part: "ભાગ ૩ - મૂળભૂત અધિકારો (ડો. આંબેડકરે આને બંધારણનું 'હૃદય અને આત્મા' ગણાવ્યું)",
    desc: "જ્યારે કોઈપણ નાગરિકના મૂળભૂત અધિકારોનું હનન થાય, ત્યારે તે વચેટિયા વગર સીધો દેશની સર્વોચ્ચ અદાલત (સુપ્રીમ કોર્ટ) નો દરવાજો ખખડાવી શકે છે.",
    remedy: "સુપ્રીમ કોર્ટ ૫ પ્રકારની રિટ્સ (Habeas Corpus, Mandamus, Prohibition, Quo-Warranto, Certiorari) બહાર પાડીને ન્યાય આપે છે."
  },
  {
    no: "Article 39A",
    title: "મફત કાનૂની સહાય (Free Legal Aid)",
    part: "ભાગ ૪ - રાજનીતિના માર્ગદર્શક સિદ્ધાંતો",
    desc: "ગરીબી કે આર્થિક મુશ્કેલીને કારણે કોઈ પણ નાગરિક ન્યાયથી વંચિત ન રહેવો જોઈએ. સરકારે તમામ જરૂરિયાતમંદોને મફત વકીલ પૂરા પાડવા પડશે.",
    remedy: "કોઈપણ તાલુકા કે જિલ્લા કોર્ટમાં આવેલી DLSA ઑફિસમાંથી તરત જ સરકારી ખર્ચે મફત વકીલ મેળવી શકાય છે."
  }
];

function renderConstitutionLibrary() {
  const listContainer = document.querySelector('.library-layout');
  if(!listContainer) return;
  
  let leftHtml = '<div style="max-height: 480px; overflow-y: auto; padding-right: 5px;">';
  fullConstitutionData.forEach((item, index) => {
    leftHtml += `<button class="list-item" onclick="openArticleDetail(${index})" style="width:100%; text-align:left; margin-bottom:8px; cursor:pointer;">
      <strong>${item.no}</strong><br><small style="color:var(--gold);">${item.title}</small>
    </button>`;
  });
  leftHtml += '</div>';
  
  const rightHtml = `<div class="panel" id="articleDisplayPanel" style="min-height: 350px;">
    <h3 style="color:var(--gold2); margin-top:0;" id="viewArtTitle">કલમ પસંદ કરો</h3>
    <span class="muted" id="viewArtPart">ડાબી બાજુની કોઈપણ બંધારણીય કલમ પર ક્લિક કરો</span>
    <hr style="border:0; border-top:1px solid var(--line); margin:15px 0;">
    <div class="article-view" id="viewArtDesc" style="font-size:15px; line-height:1.7;">અહીં સંપૂર્ણ બંધારણીય કલમ અને તેના અર્થની વિગતો જોવા મળશે.</div>
    <div id="viewArtRemedy" style="margin-top:15px; padding:12px; background:#071224; border-left:4px solid var(--gold); border-radius:6px; display:none;"></div>
  </div>`;
  
  listContainer.innerHTML = leftHtml + rightHtml;
  openArticleDetail(0);
}

function openArticleDetail(idx) {
  const data = fullConstitutionData[idx];
  document.getElementById('viewArtTitle').innerText = `${data.no}: ${data.title}`;
  document.getElementById('viewArtPart').innerText = data.part;
  document.getElementById('viewArtDesc').innerText = data.desc;
  
  const remedyBox = document.getElementById('viewArtRemedy');
  remedyBox.style.display = 'block';
  remedyBox.innerHTML = `<strong>ન્યાયિક માર્ગદર્શન / કાનૂની ઉપાય:</strong><br>${data.remedy}`;
}

window.addEventListener('DOMContentLoaded', renderConstitutionLibrary);
