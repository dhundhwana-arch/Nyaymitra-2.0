const fullConstitutionData = [
  {
    "no": "Preamble",
    "part": "Preamble",
    "title": "Preamble of the Constitution",
    "desc": "Sovereign Socialist Secular Democratic Republic securing Justice, Liberty, Equality and Fraternity.",
    "remedy": "બંધારણનો આત્મા અને સમગ્ર કાયદાનું માર્ગદર્શક દર્શન."
  },
  {
    "no": "Article 14",
    "part": "Part III",
    "title": "Equality before Law",
    "desc": "The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India.",
    "remedy": "જો ભેદભાવ થાય તો હાઇકોર્ટ (Art. 226) અથવા સુપ્રીમ કોર્ટ (Art. 32) માં રિટ કરી શકાય."
  },
  {
    "no": "Article 19",
    "part": "Part III",
    "title": "Protection of certain rights regarding freedom of speech, etc.",
    "desc": "All citizens shall have the right to freedom of speech and expression, to assemble peaceably and without arms, to form associations or unions, and to move freely throughout India.",
    "remedy": "અયોગ્ય પ્રતિબંધ સામે બંધારણીય અધિકાર રક્ષણ."
  },
  {
    "no": "Article 21",
    "part": "Part III",
    "title": "Protection of life and personal liberty",
    "desc": "No person shall be deprived of his life or personal liberty except according to procedure established by law.",
    "remedy": "ગેરકાયદે ધરપકડ સામે Habeas Corpus રિટ અરજી."
  },
  {
    "no": "Article 32",
    "part": "Part III",
    "title": "Remedies for enforcement of rights conferred by this Part",
    "desc": "The right to move the Supreme Court by appropriate proceedings for the enforcement of the rights conferred by this Part is guaranteed.",
    "remedy": "સુપ્રીમ કોર્ટ સીધો આદેશ જાહેર કરી ન્યાય અપાવે છે."
  }
];

function renderConstitutionLibrary() {
  const listContainer = document.querySelector('.library-layout');
  if(!listContainer) return;
  
  let leftHtml = '<div style="max-height: 520px; overflow-y: auto; padding-right: 5px;">';
  fullConstitutionData.forEach((item, index) => {
    let displayTitle = item.title.length > 42 ? item.title.substring(0, 42) + '...' : item.title;
    leftHtml += `<button class="list-item" onclick="openArticleDetail(${index})" style="width:100%; text-align:left; margin-bottom:8px; cursor:pointer;">
      <strong>${item.no}</strong><br><small style="color:var(--gold);">${displayTitle}</small>
    </button>`;
  });
  leftHtml += '</div>';
  
  const rightHtml = `<div class="panel" id="articleDisplayPanel" style="min-height: 420px;">
    <h3 style="color:var(--gold2); margin-top:0;" id="viewArtTitle">Select an Article</h3>
    <span class="muted" id="viewArtPart">Click any constitutional section from the left</span>
    <hr style="border:0; border-top:1px solid var(--line); margin:15px 0;">
    <div class="article-view" id="viewArtDesc" style="font-size:15px; line-height:1.7; max-height:260px; overflow-y:auto;">Constitutional text will appear here.</div>
    <div id="viewArtRemedy" style="margin-top:15px; padding:12px; background:#071224; border-left:4px solid var(--gold); border-radius:6px;"></div>
  </div>`;
  
  listContainer.innerHTML = leftHtml + rightHtml;
  if(fullConstitutionData.length > 0) openArticleDetail(0);
}

function openArticleDetail(idx) {
  const data = fullConstitutionData[idx];
  document.getElementById('viewArtTitle').innerText = `${data.no}: ${data.title}`;
  document.getElementById('viewArtPart').innerText = data.part;
  document.getElementById('viewArtDesc').innerText = data.desc;
  
  const remedyBox = document.getElementById('viewArtRemedy');
  remedyBox.style.display = 'block';
  remedyBox.innerHTML = `<strong>Legal Remedy / Enforcement:</strong><br>${data.remedy}`;
}

window.addEventListener('DOMContentLoaded', renderConstitutionLibrary);
