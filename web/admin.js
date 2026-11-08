/* NYAYMITRA 2.0 — administration console (vanilla JS, no CDN). */
(function () {
  'use strict';
  var API = '/api/v1';
  var TOKEN_KEY = 'nyaymitra.adminToken';

  function $(sel) { return document.querySelector(sel); }

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function toast(message) {
    var node = document.createElement('div');
    node.className = 'toast';
    node.textContent = message;
    $('#toastRegion').appendChild(node);
    setTimeout(function () { node.remove(); }, 4000);
  }

  function getToken() {
    try { return sessionStorage.getItem(TOKEN_KEY) || ''; } catch (e) { return ''; }
  }

  async function api(path, options) {
    options = options || {};
    var init = { method: options.method || 'GET', headers: { 'X-Admin-Token': getToken() } };
    if (options.body) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(options.body);
    }
    var response = await fetch(API + path, init);
    var text = await response.text();
    var data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      var err = (data && data.error) || {};
      var error = new Error(err.message || ('HTTP ' + response.status));
      error.code = err.code;
      throw error;
    }
    return data;
  }

  function table(headers, rows) {
    if (!rows.length) return '<p class="muted small">No records.</p>';
    return '<div class="table-wrap"><table><thead><tr>' +
      headers.map(function (h) { return '<th>' + esc(h) + '</th>'; }).join('') +
      '</tr></thead><tbody>' + rows.map(function (row) {
        return '<tr>' + row.map(function (cell) { return '<td>' + esc(cell) + '</td>'; }).join('') + '</tr>';
      }).join('') + '</tbody></table></div>';
  }

  async function loadAll() {
    try {
      var stats = await api('/admin/stats');
      $('#statsPanel').innerHTML = table(['metric', 'value'],
        Object.keys(stats.counts).map(function (key) { return [key, stats.counts[key]]; })
          .concat(Object.keys(stats.ai).map(function (key) { return ['ai.' + key, stats.ai[key]]; })));

      var queue = await api('/admin/verification-queue');
      $('#queuePanel').innerHTML =
        '<h3>Articles (' + queue.articles.length + ' pending)</h3>' +
        table(['article', 'text', 'verification', 'last checked'],
          queue.articles.map(function (a) { return [a.article_label, a.text_status, a.verification_status, a.last_checked_at || 'never']; })) +
        '<h3>Departments (' + queue.departments.length + ' pending)</h3>' +
        table(['department', 'verification', 'verified on'],
          queue.departments.map(function (d) { return [d.department_key, d.verification_status, d.verified_on || 'never']; })) +
        '<p class="small muted">' + esc(queue.note) + '</p>';

      var metrics = await api('/admin/metrics');
      var counters = Object.keys(metrics.counters).map(function (key) {
        return [key, metrics.counters[key]];
      });
      $('#metricsPanel').innerHTML =
        table(['counter', 'value'], counters) +
        '<p class="small muted">uptime: ' + esc(metrics.uptime_s) + ' s</p>';

      var queries = await api('/admin/queries?limit=25');
      $('#queriesPanel').innerHTML = table(['time', 'lang', 'category', 'provider', 'ms', 'status', 'query (redacted)'],
        queries.items.map(function (q) {
          return [q.created_at, q.language, q.category || '—', q.provider || '—', q.latency_ms, q.status + (q.error_code ? '/' + q.error_code : ''), q.query_text || ''];
        }));

      var errors = await api('/admin/errors?limit=25');
      $('#errorsPanel').innerHTML = table(['time', 'request', 'method', 'path', 'status', 'type', 'message'],
        errors.items.map(function (e) {
          return [e.at, e.request_id, e.method, e.path, e.status_code, e.error_type, e.message || ''];
        }));

      var complaints = await api('/admin/complaints?limit=25');
      var notice = document.createElement('p');
      $('#complaintsPanel').innerHTML = '<p class="small muted">' + esc(complaints.note) + '</p>' +
        table(['reference', 'category', 'status', 'district', 'created'],
          complaints.items.map(function (c) {
            return [c.reference, c.category, c.status, c.district || '—', c.created_at];
          }));

      var docs = await api('/admin/documents?limit=25');
      $('#documentsPanel').innerHTML = '<p class="small muted">' + esc(docs.note) + '</p>' +
        table(['id', 'file', 'type', 'size', 'sha256', 'extraction', 'created'], docs.items.map(function (d) {
          return [d.id, d.original_name, d.mime_type, d.size_bytes, (d.sha256 || '').slice(0, 12), d.extraction_status, d.created_at];
        }));

      var legacy = await api('/admin/legacy-chunks?limit=10');
      $('#legacyPanel').innerHTML = '<p class="small muted">' + esc(legacy.note) + '</p>' +
        table(['legacy id', 'label', 'script', 'excerpt'],
          legacy.items.map(function (l) { return [l.legacy_id, l.article_no, l.script, l.excerpt]; })) +
        '<p class="small">Total quarantined rows: ' + esc(legacy.total) + '</p>';
      if (notice) notice.remove();
    } catch (error) {
      toast(error.message);
      if (error.code === 'unauthorized' || error.code === 'forbidden') {
        $('#adminPanels').classList.add('hidden');
      }
    }
  }

  function init() {
    var stored = getToken();
    if (stored) {
      $('#adminToken').value = stored;
      $('#adminPanels').classList.remove('hidden');
      loadAll();
      $('#authStatus').innerHTML = '<div class="notice ok small">Signed in with a stored session token.</div>';
    }
    $('#authForm').addEventListener('submit', function (event) {
      event.preventDefault();
      var token = $('#adminToken').value.trim();
      if (!token) return;
      try { sessionStorage.setItem(TOKEN_KEY, token); } catch (e) { /* ignore */ }
      $('#adminPanels').classList.remove('hidden');
      $('#authStatus').innerHTML = '<div class="notice ok small">Token stored for this tab.</div>';
      loadAll();
    });
    $('#refreshBtn').addEventListener('click', function () { loadAll(); toast('Refreshed'); });
    $('#backupBtn').addEventListener('click', async function () {
      try {
        var result = await api('/admin/backup', { method: 'POST' });
        toast('Backup created: ' + result.file);
      } catch (error) {
        toast(error.message);
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
