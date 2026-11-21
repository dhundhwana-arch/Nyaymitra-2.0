import os, sys, sqlite3, csv, json

BASE_DIR = "/data/data/com.termux/files/home/Nyaymitra-2.0"
DB_PATH = os.path.join(BASE_DIR, "backend/justice_access.db")
CSV_PATH = os.path.join(BASE_DIR, "backend/article_audit_471.csv")
JS_PATH = os.path.join(BASE_DIR, "frontend/library_fix.js")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ૧. ટેબલ બનાવો
cur.execute('''
CREATE TABLE IF NOT EXISTS constitution_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_no TEXT UNIQUE,
    part TEXT,
    title_en TEXT,
    title_gu TEXT,
    description_en TEXT,
    description_gu TEXT,
    remedy_gu TEXT
)
''')

# ૨. મૂળભૂત કાયદાકીય ફાઉન્ડેશન ડેટા
base_articles = [
    ("Preamble", "Preamble", "Preamble of the Constitution", "ભારતનું બંધારણ - આમુખ",
     "Sovereign Socialist Secular Democratic Republic securing Justice, Liberty, Equality and Fraternity.",
     "સાર્વભૌમ, સમાજવાદી, બિનસાંપ્રદાયિક, લોકશાહી પ્રજાસત્તાક - ન્યાય, સ્વતંત્રતા, સમાનતા અને બંધુતાની ખાતરી.",
     "બંધારણનો આત્મા અને સમગ્ર કાયદાનું માર્ગદર્શક દર્શન."),
    ("Article 14", "Part III", "Equality before Law", "કાયદા સમક્ષ સમાનતા",
     "The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India.",
     "કોઈપણ વ્યક્તિ સાથે કાયદા સમક્ષ ભેદભાવ નહીં થાય, દરેક નાગરિકને કાયદાનું સમાન રક્ષણ મળશે.",
     "જો ભેદભાવ થાય તો હાઇકોર્ટ (Art. 226) અથવા સુપ્રીમ કોર્ટ (Art. 32) માં રિટ કરી શકાય."),
    ("Article 19", "Part III", "Protection of certain rights regarding freedom of speech, etc.", "વાણી અને અભિવ્યક્તિની સ્વતંત્રતા",
     "All citizens shall have the right to freedom of speech and expression, to assemble peaceably and without arms, to form associations or unions, and to move freely throughout India.",
     "શાંતિપૂર્ણ રીતે ભેગા થવાની, સંગઠન બનાવવાની, દેશમાં મુક્તપણે ફરવાની અને વ્યવસાય કરવાની સ્વતંત્રતા.",
     "અયોગ્ય પ્રતિબંધ સામે બંધારણીય અધિકાર રક્ષણ."),
    ("Article 21", "Part III", "Protection of life and personal liberty", "જીવન અને વ્યક્તિગત સ્વતંત્રતાનું રક્ષણ",
     "No person shall be deprived of his life or personal liberty except according to procedure established by law.",
     "કોઈપણ નાગરિક પાસેથી કાયદાકીય પ્રક્રિયા વિના જીવન અથવા અંગત આઝાદી છીનવી શકાશે નહીં. નિજતાનો અધિકાર પણ સામેલ.",
     "ગેરકાયદે ધરપકડ સામે Habeas Corpus રિટ અરજી."),
    ("Article 32", "Part III", "Remedies for enforcement of rights conferred by this Part", "બંધારણીય ઉપચારોનો અધિકાર",
     "The right to move the Supreme Court by appropriate proceedings for the enforcement of the rights conferred by this Part is guaranteed.",
     "મૂળભૂત અધિકારોનું ઉલ્લંઘન થાય ત્યારે સીધા સુપ્રીમ કોર્ટમાં જઈને રિટ (Writs) મેળવવાનો અધિકાર.",
     "સુપ્રીમ કોર્ટ સીધો આદેશ જાહેર કરી ન્યાય અપાવે છે.")
]

for art in base_articles:
    cur.execute('''INSERT OR REPLACE INTO constitution_articles 
                   (article_no, part, title_en, title_gu, description_en, description_gu, remedy_gu)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''', art)

# ૩. 471 CSV ફાઇલમાંથી તમારો તૈયાર કરેલો ડેટા લોડ કરો
csv_count = 0
if os.path.exists(CSV_PATH):
    with open(CSV_PATH, mode='r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[0].strip():
                art_id = row[0].strip()
                art_desc = row[1].strip()
                art_title = row[2].strip() if len(row) >= 3 else art_id
                cur.execute('''INSERT OR REPLACE INTO constitution_articles 
                               (article_no, part, title_en, title_gu, description_en, description_gu, remedy_gu)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (art_id, "Constitution of India", art_title, art_title, art_desc, art_desc, "Remedy available under Article 32 / Article 226."))
                csv_count += 1
    print(f"Loaded {csv_count} articles from {CSV_PATH}")

conn.commit()

# ૪. ફ્રન્ટએન્ડ માટે ડેટા ખેંચીને library_fix.js બનાવો
cur.execute('SELECT article_no, part, title_en, description_en, remedy_gu FROM constitution_articles ORDER BY id ASC')
rows = cur.fetchall()
conn.close()

data = []
for r in rows:
    data.append({
        'no': r[0],
        'part': r[1] or 'Constitution of India',
        'title': r[2] or r[0],
        'desc': r[3] or 'Full constitutional text available.',
        'remedy': r[4] or 'Legal remedies under Article 32 / 226.'
    })

js_code = 'const fullConstitutionData = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';' + '''

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
'''

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js_code)

print(f"SUCCESS: {len(data)} articles compiled into {JS_PATH}!")
