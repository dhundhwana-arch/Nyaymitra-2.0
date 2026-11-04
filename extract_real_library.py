import sys, os, sqlite3, json
from pathlib import Path

# જૂના ડેટાબેઝનો પાથ
old_db_candidates = [
    Path.home() / "NYAYMITRA-AI/database/nyaymitra.db",
    Path.home() / "NYAYMITRA-AI/database/nyaymitra_pre_constitution_backup.db",
    Path.home() / "NYAYMITRA-AI/database/nyaymitra_before_library.db"
]

db_path = None
for p in old_db_candidates:
    if p.exists():
        db_path = p
        break

print(f"Using database: {db_path}")

articles_list = []

if db_path:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # ઉપલબ્ધ ટેબલ્સ ચેક કરો
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cur.fetchall()]
    print("Found tables:", tables)
    
    # ૧. જો articles ટેબલ હોય
    for tbl in ['articles', 'constitution_articles', 'documents', 'document_pages', 'pages']:
        if tbl in tables:
            print(f"Attempting extraction from table: {tbl}")
            cur.execute(f"PRAGMA table_info({tbl})")
            cols = [c[1] for c in cur.fetchall()]
            
            if 'article_number' in cols or 'article_no' in cols:
                art_col = 'article_number' if 'article_number' in cols else 'article_no'
                title_col = 'title' if 'title' in cols else art_col
                text_col = 'content' if 'content' in cols else ('text' if 'text' in cols else cols[-1])
                
                cur.execute(f"SELECT {art_col}, {title_col}, {text_col} FROM {tbl} LIMIT 500")
                for r in cur.fetchall():
                    articles_list.append({
                        "no": f"Article {r[0]}".replace("Article Article", "Article"),
                        "part": "Constitution of India",
                        "title": str(r[1]) if r[1] else f"Article {r[0]}",
                        "desc": str(r[2]) if r[2] else "Full text available.",
                        "remedy": "Enforceable under Article 32 (Supreme Court) / 226 (High Court)."
                    })
                break
            elif 'page_number' in cols and ('text' in cols or 'content' in cols):
                # PDF Ingestion Pages
                text_col = 'text' if 'text' in cols else 'content'
                cur.execute(f"SELECT page_number, {text_col} FROM {tbl} WHERE document_id=3 OR document_id=1 LIMIT 400")
                for r in cur.fetchall():
                    raw_text = r[1] or ""
                    first_line = raw_text.strip().split('\n')[0][:50] if raw_text else f"Page {r[0]}"
                    articles_list.append({
                        "no": f"Section/Page {r[0]}",
                        "part": "The Constitution of India",
                        "title": first_line,
                        "desc": raw_text,
                        "remedy": "Constitutional Provision & Legal Directives."
                    })
                break
    conn.close()

# જો સીધા ટેબલમાંથી ન મળ્યું હોય તો constitution_library મોડ્યુલ લોડ કરો
if len(articles_list) == 0:
    print("Using ConstitutionLibrary module direct extraction...")
    sys.path.append(str(Path.home() / "NYAYMITRA-AI/backend/modules"))
    try:
        from constitution_library import ConstitutionLibrary
        lib = ConstitutionLibrary(db_path=db_path)
        if hasattr(lib, 'get_all_articles'):
            raw_arts = lib.get_all_articles()
            for a in raw_arts:
                articles_list.append({
                    "no": str(a.get('number', a.get('article_no', 'Article'))),
                    "part": str(a.get('part', 'Constitution of India')),
                    "title": str(a.get('title', 'Article')),
                    "desc": str(a.get('content', a.get('text', ''))),
                    "remedy": "Available under Constitutional Remedies."
                })
    except Exception as e:
        print("Module extraction notice:", e)

print(f"Total extracted items: {len(articles_list)}")

# ફ્રન્ટએન્ડ માટે library_fix.js તૈયાર કરો
js_code = 'const fullConstitutionData = ' + json.dumps(articles_list, ensure_ascii=False, indent=2) + ';' + '''

function renderConstitutionLibrary() {
  const listContainer = document.querySelector('.library-layout');
  if(!listContainer) return;
  
  let leftHtml = '<div style="max-height: 520px; overflow-y: auto; padding-right: 5px;">';
  fullConstitutionData.forEach((item, index) => {
    let cleanTitle = (item.title || item.no).substring(0, 40);
    leftHtml += `<button class="list-item" onclick="openArticleDetail(${index})" style="width:100%; text-align:left; margin-bottom:8px; cursor:pointer;">
      <strong>${item.no}</strong><br><small style="color:var(--gold);">${cleanTitle}...</small>
    </button>`;
  });
  leftHtml += '</div>';
  
  const rightHtml = `<div class="panel" id="articleDisplayPanel" style="min-height: 420px;">
    <h3 style="color:var(--gold2); margin-top:0;" id="viewArtTitle">Select an Article</h3>
    <span class="muted" id="viewArtPart">Click any section from the left</span>
    <hr style="border:0; border-top:1px solid var(--line); margin:15px 0;">
    <div class="article-view" id="viewArtDesc" style="font-size:15px; line-height:1.7; max-height:260px; overflow-y:auto;">Full constitutional text will appear here.</div>
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
  remedyBox.innerHTML = `<strong>Legal Context / Remedies:</strong><br>${data.remedy}`;
}

window.addEventListener('DOMContentLoaded', renderConstitutionLibrary);
'''

out_path = Path.home() / "Nyaymitra-2.0/frontend/library_fix.js"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(js_code)

print(f"SUCCESS: Saved {len(articles_list)} English articles into {out_path}")
