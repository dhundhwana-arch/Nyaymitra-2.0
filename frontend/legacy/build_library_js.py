import sqlite3, json

conn = sqlite3.connect('/data/data/com.termux/files/home/Nyaymitra-2.0/backend/justice_access.db')
cur = conn.cursor()
cur.execute('SELECT article_no, part, title_en, description_en, remedy_gu FROM constitution_articles ORDER BY id ASC')
rows = cur.fetchall()
conn.close()

data = []
for r in rows:
    data.append({
        'no': r[0],
        'part': r[1] or 'Constitution of India',
        'title': r[2] or r[0],
        'desc': r[3] or 'Full constitutional text available in database.',
        'remedy': r[4] or 'Legal remedies under Article 32 (Supreme Court) / 226 (High Court).'
    })

js_content = 'const fullConstitutionData = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';' + '''

function renderConstitutionLibrary() {
  const listContainer = document.querySelector('.library-layout');
  if(!listContainer) return;
  
  let leftHtml = '<div style="max-height: 520px; overflow-y: auto; padding-right: 5px;">';
  fullConstitutionData.forEach((item, index) => {
    let shortTitle = item.title.length > 40 ? item.title.substring(0, 40) + '...' : item.title;
    leftHtml += `<button class="list-item" onclick="openArticleDetail(${index})" style="width:100%; text-align:left; margin-bottom:8px; cursor:pointer;">
      <strong>${item.no}</strong><br><small style="color:var(--gold);">${shortTitle}</small>
    </button>`;
  });
  leftHtml += '</div>';
  
  const rightHtml = `<div class="panel" id="articleDisplayPanel" style="min-height: 400px;">
    <h3 style="color:var(--gold2); margin-top:0;" id="viewArtTitle">Select an Article</h3>
    <span class="muted" id="viewArtPart">Click any constitutional section from the left</span>
    <hr style="border:0; border-top:1px solid var(--line); margin:15px 0;">
    <div class="article-view" id="viewArtDesc" style="font-size:15px; line-height:1.7; max-height:280px; overflow-y:auto;">Detailed English text will appear here.</div>
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

with open('/data/data/com.termux/files/home/Nyaymitra-2.0/frontend/library_fix.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f"Successfully generated library_fix.js with {len(data)} articles!")
