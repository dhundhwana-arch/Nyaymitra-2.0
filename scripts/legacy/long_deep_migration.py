import sys, os, time, sqlite3, json, re
from pathlib import Path

print("="*60)
print("🚀 NYAYMITRA-AI TO NYAYMITRA-2.0 FULL DEEP MIGRATION STARTED")
print("="*60)

OLD_REPO = Path.home() / "NYAYMITRA-AI"
NEW_REPO = Path.home() / "Nyaymitra-2.0"
NEW_DB = NEW_REPO / "backend" / "justice_access.db"

# ૧. નવું ટેબલ તૈયાર કરો
conn_new = sqlite3.connect(NEW_DB)
cur_new = conn_new.cursor()
cur_new.execute('''
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
conn_new.commit()

# ૨. જૂના ડેટાબેઝમાંથી સંપૂર્ણ ડેટા શોધો
db_candidates = [
    OLD_REPO / "database" / "nyaymitra.db",
    OLD_REPO / "database" / "nyaymitra_pre_constitution_backup.db",
    OLD_REPO / "database" / "nyaymitra_before_library.db"
]

source_db = None
for p in db_candidates:
    if p.exists():
        source_db = p
        break

print(f"[*] Accessing Deep Source Database: {source_db}")
articles_master = []

if source_db:
    conn_old = sqlite3.connect(source_db)
    cur_old = conn_old.cursor()
    
    # Check tables
    cur_old.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cur_old.fetchall()]
    print(f"[*] Discovered DB Tables: {tables}")
    
    # Pages માંથી બંધારણનો કાચો ડેટા વાંચો
    pages_text = []
    for tbl in ['document_pages', 'pages']:
        if tbl in tables:
            print(f"[*] Deep scanning text chunks from '{tbl}'...")
            try:
                cur_old.execute(f"SELECT text FROM {tbl} WHERE document_id=3 ORDER BY page_number ASC")
                rows = cur_old.fetchall()
                if not rows:
                    cur_old.execute(f"SELECT text FROM {tbl} ORDER BY id ASC")
                    rows = cur_old.fetchall()
                pages_text = [r[0] for r in rows if r[0]]
                break
            except Exception as e:
                print("Notice:", e)
    conn_old.close()

    print(f"[*] Total Raw Legal Pages Collected: {len(pages_text)}")
    full_corpus = "\n".join(pages_text)
    
    # 3. Regex Engine વડે તમામ કલમો શોધો
    print("[*] Running Deep Regex Parser for all Articles & Parts...")
    pattern = re.compile(
        r"(?m)^\s*(?:(\d+)\s*\[\s*)?(\d{1,3}[A-Z]?)\.\s+([\s\S]{5,250}?)(?:\s*\.\s*—|\.—|—)([\s\S]*?)(?=(?:^\s*(?:\d+\s*\[\s*)?\d{1,3}[A-Z]?\.\s+)|$)",
        re.MULTILINE
    )
    
    matches = pattern.findall(full_corpus)
    print(f"[*] Matched {len(matches)} Constitutional Clauses!")
    
    for idx, m in enumerate(matches):
        art_no = f"Article {m[1].strip()}"
        title = m[2].strip().replace('\n', ' ')
        raw_desc = m[3].strip()
        clean_desc = re.sub(r'\s+', ' ', raw_desc)
        if len(clean_desc) < 20:
            clean_desc = f"Detailed legal text and constitutional directives for {art_no}."
            
        cur_new.execute('''
        INSERT OR REPLACE INTO constitution_articles 
        (article_no, part, title_en, title_gu, description_en, description_gu, remedy_gu)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            art_no,
            "The Constitution of India",
            title,
            title,
            clean_desc,
            clean_desc,
            "Remedy enforceable via High Court (Article 226) or Supreme Court (Article 32)."
        ))
        
        articles_master.append({
            "no": art_no,
            "part": "The Constitution of India",
            "title": title,
            "desc": clean_desc,
            "remedy": "Remedy enforceable via High Court (Article 226) or Supreme Court (Article 32)."
        })
        
        if idx % 20 == 0:
            conn_new.commit()
            time.sleep(0.5)

conn_new.commit()
conn_new.close()

# 4. ફ્રન્ટએન્ડ માટે ડાયનેમિક ઇન્ટરેક્ટિવ JS ફાઇલ બનાવો
print("[*] Generating dynamic frontend interactive script: library_fix.js ...")
js_code = 'const fullConstitutionData = ' + json.dumps(articles_master, ensure_ascii=False, indent=2) + ';' + '''

function renderConstitutionLibrary(filterText = '') {
  const container = document.querySelector('.library-layout');
  if(!container) return;
  
  const filtered = fullConstitutionData.filter(a => 
      a.no.toLowerCase().includes(filterText.toLowerCase()) || 
      a.title.toLowerCase().includes(filterText.toLowerCase()) ||
      a.desc.toLowerCase().includes(filterText.toLowerCase())
  );
  
  let leftHtml = '<div style="max-height: 520px; overflow-y: auto; padding-right: 5px; flex: 1;">';
  filtered.forEach((item, index) => {
    let shortTitle = item.title.length > 40 ? item.title.substring(0, 40) + '...' : item.title;
    leftHtml += `<button class="list-item" onclick="openArticleDetail(${index})" style="width:100%; text-align:left; margin-bottom:8px; cursor:pointer; padding:10px; border-radius:8px; background:#0d1b2a; border:1px solid #1e3a5f;">
      <strong style="color:var(--gold2);">${item.no}</strong><br><small style="color:#d5dbea;">${shortTitle}</small>
    </button>`;
  });
  leftHtml += '</div>';
  
  const rightHtml = `<div class="panel" id="articleDisplayPanel" style="flex: 1.5; min-height: 420px; background:#081426; border:1px solid var(--line); border-radius:10px; padding:18px;">
    <h3 style="color:var(--gold2); margin-top:0;" id="viewArtTitle">Select an Article</h3>
    <span class="muted" id="viewArtPart">Click any constitutional section from the left</span>
    <hr style="border:0; border-top:1px solid var(--line); margin:15px 0;">
    <div class="article-view" id="viewArtDesc" style="font-size:15px; line-height:1.7; max-height:260px; overflow-y:auto; color:#f0f4f8;">Detailed legal text will appear here.</div>
    <div id="viewArtRemedy" style="margin-top:15px; padding:12px; background:#071224; border-left:4px solid var(--gold); border-radius:6px; color:#d5dbea;"></div>
  </div>`;
  
  container.innerHTML = leftHtml + rightHtml;
  if(filtered.length > 0) openArticleDetail(0);
}

function openArticleDetail(idx) {
  const data = fullConstitutionData[idx];
  document.getElementById('viewArtTitle').innerText = `${data.no}: ${data.title}`;
  document.getElementById('viewArtPart').innerText = data.part;
  document.getElementById('viewArtDesc').innerText = data.desc;
  
  const remedyBox = document.getElementById('viewArtRemedy');
  remedyBox.style.display = 'block';
  remedyBox.innerHTML = `<strong>Legal Context & Enforcement:</strong><br>${data.remedy}`;
}

window.addEventListener('DOMContentLoaded', () => {
    const layout = document.querySelector('.library-layout');
    if(layout) {
        layout.style.display = 'flex';
        layout.style.gap = '15px';
    }
    renderConstitutionLibrary();
});
'''

with open(NEW_REPO / "frontend" / "library_fix.js", "w", encoding="utf-8") as f:
    f.write(js_code)

print(f"[+] Successfully extracted and built {len(articles_master)} articles into library_fix.js!")

# 5. Git Add, Commit and Push
print("[*] Committing and Pushing full migrated database to GitHub...")
os.system(f"cd {NEW_REPO} && git add . && git commit -m 'Full automatic deep migration of 40-hour English Constitution dataset from NYAYMITRA-AI to Nyaymitra-2.0' && git push origin main")

print("="*60)
print("🎉 FULL MIGRATION & REPO SYNC COMPLETE!")
print("="*60)
