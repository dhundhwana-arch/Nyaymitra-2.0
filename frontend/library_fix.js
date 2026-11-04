const fullConstitutionData = [];

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
