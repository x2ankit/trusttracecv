/* =========================================================
   TRUSTTRACE CV – Frontend Application Logic
   SIH26228 Computer Vision Assurance System
========================================================= */

const API_BASE = '';  // same origin

// =========================================================
// State
// =========================================================
let activePanel = 'dataset';

// =========================================================
// Navigation
// =========================================================
function activatePanel(name) {
  activePanel = name;
  document.querySelectorAll('.panel').forEach(p => {
    p.hidden = (p.id !== `panel-${name}`);
  });
  document.querySelectorAll('.nav-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.panel === name);
  });
  if (name === 'coverage') loadCoverage();
}

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => activatePanel(btn.dataset.panel));
});

// =========================================================
// Health check
// =========================================================
async function checkHealth() {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  try {
    const r = await fetch(`${API_BASE}/api/health`);
    if (r.ok) {
      dot.className  = 'status-dot online';
      text.textContent = 'Backend connected';
    } else throw new Error('non-ok');
  } catch {
    dot.className  = 'status-dot offline';
    text.textContent = 'Backend offline';
  }
}
checkHealth();
setInterval(checkHealth, 15000);

// =========================================================
// Utilities
// =========================================================
function resultBadge(result) {
  const cls = `rb-${result.replace(/ /g,'_')}`;
  return `<span class="result-badge ${cls}">${result}</span>`;
}

function severityText(sev) {
  return `<span class="sev-${sev}">${sev}</span>`;
}

function verdictBadge(verdict) {
  const icons = {
    PASS:'✔',ANOMALIES_DETECTED:'⚠',FAIL:'✖',INCONCLUSIVE:'?','NOT_ASSESSED':'—'
  };
  const cls = `verdict-badge verdict-${verdict}`;
  return `<span class="${cls}">${icons[verdict]||''} ${verdict.replace(/_/g,' ')}</span>`;
}

function severityChips(summary) {
  const cols = {CRITICAL:'chip-critical',HIGH:'chip-high',MEDIUM:'chip-medium',LOW:'chip-low',INFO:'chip-info'};
  return Object.entries(summary)
    .filter(([,v]) => v > 0)
    .map(([k,v]) => `<span class="chip ${cols[k]||''}">${k}: ${v}</span>`)
    .join('');
}

function showModal(title, data) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').textContent  = JSON.stringify(data, null, 2);
  document.getElementById('modal-backdrop').hidden    = false;
}

document.getElementById('modal-close').addEventListener('click', () => {
  document.getElementById('modal-backdrop').hidden = true;
});
document.getElementById('modal-backdrop').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-backdrop'))
    document.getElementById('modal-backdrop').hidden = true;
});

function renderFindingsTable(tbodyId, findings) {
  const tbody = document.getElementById(tbodyId);
  if (!findings || findings.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="color:var(--gray-400);text-align:center;padding:20px">No findings</td></tr>`;
    return;
  }
  tbody.innerHTML = findings.map((f, i) => `
    <tr>
      <td class="code-cell">${f.check_id||'—'}</td>
      <td>${f.name||'—'}</td>
      <td>${resultBadge(f.result||'—')}</td>
      <td>${severityText(f.severity||'INFO')}</td>
      <td style="color:var(--gray-500);font-size:13px">${f.confidence||'—'}</td>
      <td><button class="detail-btn" data-idx="${i}">View</button></td>
    </tr>`).join('');
  tbody.querySelectorAll('.detail-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const f = findings[+btn.dataset.idx];
      showModal(`${f.check_id} — ${f.name}`, {
        result: f.result, severity: f.severity, confidence: f.confidence,
        description: f.description, recommended_action: f.recommended_action,
        limitation: f.limitation, evidence: f.evidence,
      });
    });
  });
}

function setLoading(prefix, loading) {
  document.getElementById(`${prefix}-spinner`).hidden = !loading;
  document.getElementById(`${prefix}-results`).hidden = loading;
  document.getElementById(`${prefix}-error`).hidden   = true;
  const btn = document.querySelector(`#btn-audit-${prefix.split('-')[0]}, #btn-full-audit`);
  if (btn) btn.disabled = loading;
}

function showError(prefix, msg) {
  document.getElementById(`${prefix}-spinner`).hidden = true;
  const el = document.getElementById(`${prefix}-error`);
  el.textContent = `Error: ${msg}`;
  el.hidden = false;
}

// =========================================================
// Dataset Upload
// =========================================================
document.getElementById('ds-upload').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  formData.append('format', document.getElementById('ds-format').value);
  
  const status = document.getElementById('ds-upload-status');
  status.textContent = 'Uploading...';
  
  try {
    const r = await fetch(`${API_BASE}/api/upload/dataset`, {
      method: 'POST',
      body: formData
    });
    if (!r.ok) { const err = await r.json(); throw new Error(err.detail || r.statusText); }
    const data = await r.json();
    document.getElementById('ds-path').value = data.dataset_path;
    status.textContent = 'Uploaded successfully!';
    setTimeout(() => status.textContent = '', 3000);
  } catch (err) {
    status.textContent = `Upload failed: ${err.message}`;
  }
});

// =========================================================
// Image Grid Helper
// =========================================================
function renderImageGrid(gridId, datasetRecords, inferenceRecords, format) {
  const grid = document.getElementById(gridId);
  const records = (datasetRecords || []).slice(0, 20);
  if (records.length === 0) {
    grid.innerHTML = `<div style="color:var(--gray-400);font-size:13px">No image records returned.</div>`;
    return;
  }
  
  // Map inference records by image filename (naive match for simplicity)
  const infMap = {};
  if (inferenceRecords) {
    inferenceRecords.forEach(ir => {
      infMap[ir.image_id] = ir;
      // also try matching with extensions
      infMap[ir.image_id + '.jpg'] = ir;
      infMap[ir.image_id + '.png'] = ir;
    });
  }

  grid.innerHTML = records.map(rec => {
    const ok   = rec.checks?.file_exists?.result === 'PASS';
    const warn = rec.checks?.non_blank?.result === 'WARN';
    const anns = (rec.annotations || []).filter(a => a.class_id !== undefined || a.bbox !== undefined);
    
    // Find matching inference record
    const baseName = rec.filename.split('.')[0];
    const infRec = infMap[rec.filename] || infMap[baseName];
    const preds = infRec ? (infRec.predictions || []) : [];
    
    let boxesHtml = '';
    if (ok && rec.url_path && rec.resolution) {
      const [imgW, imgH] = rec.resolution;
      
      // Draw Ground Truth (Green)
      boxesHtml += anns.map(a => {
        let left, top, width, height;
        if (format === 'yolo') {
          left = (a.x_center - a.width/2) * 100; top = (a.y_center - a.height/2) * 100;
          width = a.width * 100; height = a.height * 100;
        } else {
          const [x, y, w, h] = a.bbox;
          left = (x / imgW) * 100; top = (y / imgH) * 100;
          width = (w / imgW) * 100; height = (h / imgH) * 100;
        }
        return `<div class="bbox" style="left:${left}%; top:${top}%; width:${width}%; height:${height}%; border: 2px solid #10b981; position: absolute; box-sizing: border-box;">
                  <span style="background: #10b981; color: white; font-size: 10px; position: absolute; top: -14px; left: -2px; padding: 0 4px; white-space: nowrap;">GT: ${a.class_name || 'cls ' + a.class_id}</span>
                </div>`;
      }).join('');
      
      // Draw Predictions (Purple)
      boxesHtml += preds.map(p => {
        if (!p.bbox) return '';
        const [x, y, w, h] = p.bbox;
        // inference bbox is typically absolute pixels [x_min, y_min, w, h] or normalized? 
        // Our fixture has [10, 10, 40, 40] which looks like pixels. Let's assume absolute.
        const left = (x / imgW) * 100; const top = (y / imgH) * 100;
        const width = (w / imgW) * 100; const height = (h / imgH) * 100;
        return `<div class="bbox" style="left:${left}%; top:${top}%; width:${width}%; height:${height}%; border: 2px dashed #8b5cf6; position: absolute; box-sizing: border-box;">
                  <span style="background: #8b5cf6; color: white; font-size: 10px; position: absolute; bottom: -14px; left: -2px; padding: 0 4px; white-space: nowrap;">Pred: cls ${p.class_id} (${p.score})</span>
                </div>`;
      }).join('');
    }

    const imgContainer = ok && rec.url_path ? 
      `<div style="position:relative; width:100%; aspect-ratio: 1; background:#000; overflow:hidden;">
         <img src="${API_BASE}/api/image?path=${encodeURIComponent(rec.url_path)}" style="width:100%; height:100%; object-fit:contain;" />
         ${boxesHtml}
       </div>` : 
      `<div class="image-placeholder" aria-hidden="true">${ok ? '🖼' : '✕'}</div>`;

    return `
      <div class="image-card">
        ${imgContainer}
        <div class="image-info">
          <div class="image-name" title="${rec.filename}">${rec.filename}</div>
          <div class="image-meta">${rec.resolution ? rec.resolution.join('×') : '—'}</div>
          ${warn ? '<div class="image-check-err">Blank image</div>' : ''}
          ${!ok  ? '<div class="image-check-err">File missing</div>' : ''}
          <div class="image-anns">
            ${anns.slice(0,2).map(a => `<span class="ann-chip">${a.class_name || 'cls ' + a.class_id}</span>`).join('')}
            ${preds.length > 0 ? `<span class="ann-chip" style="background:#ede9fe; color:#6d28d9">Preds: ${preds.length}</span>` : ''}
          </div>
        </div>
      </div>`;
  }).join('');
}

// =========================================================
// Dataset Audit
// =========================================================
document.getElementById('btn-audit-dataset').addEventListener('click', async () => {
  const path   = document.getElementById('ds-path').value.trim();
  const format = document.getElementById('ds-format').value;
  const seed   = +document.getElementById('ds-seed').value;

  document.getElementById('ds-spinner').hidden  = false;
  document.getElementById('ds-results').hidden  = true;
  document.getElementById('ds-error').hidden    = true;
  document.getElementById('btn-audit-dataset').disabled = true;

  try {
    const r = await fetch(`${API_BASE}/api/audit/dataset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_path: path, format, seed }),
    });
    if (!r.ok) {
      const e = await r.json();
      throw new Error(e.detail || r.statusText);
    }
    const data = await r.json();

    // Verdict + severity
    document.getElementById('ds-verdict-badge').innerHTML = verdictBadge(data.verdict);
    document.getElementById('ds-severity-chips').innerHTML = severityChips(data.severity_summary || {});

    // Findings
    renderFindingsTable('ds-findings-body', data.findings || []);

    // Image grid
    renderImageGrid('ds-image-grid', data.records, null, format);

    document.getElementById('ds-results').hidden = false;
  } catch (err) {
    document.getElementById('ds-error').textContent = `Error: ${err.message}`;
    document.getElementById('ds-error').hidden = false;
  } finally {
    document.getElementById('ds-spinner').hidden = true;
    document.getElementById('btn-audit-dataset').disabled = false;
  }
});

// =========================================================
// Model Audit
// =========================================================
document.getElementById('btn-audit-model').addEventListener('click', async () => {
  const modelPath    = document.getElementById('mdl-path').value.trim();
  const manifestPath = document.getElementById('mdl-manifest').value.trim();

  document.getElementById('mdl-spinner').hidden  = false;
  document.getElementById('mdl-results').hidden  = true;
  document.getElementById('mdl-error').hidden    = true;
  document.getElementById('btn-audit-model').disabled = true;

  try {
    const r = await fetch(`${API_BASE}/api/audit/model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_path: modelPath, manifest_path: manifestPath }),
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail||r.statusText); }
    const data = await r.json();

    document.getElementById('mdl-verdict-badge').innerHTML  = verdictBadge(data.verdict);
    document.getElementById('mdl-severity-chips').innerHTML = severityChips(data.severity_summary||{});

    // Metadata cards
    const rec = data.model_record || {};
    const metaItems = [
      ['Filename', rec.filename||'—'],
      ['Format',   rec.format||'—'],
      ['Size',     rec.size_bytes ? `${(rec.size_bytes/1024).toFixed(1)} KB` : '—'],
      ['SHA-256',  rec.sha256 ? rec.sha256.slice(0,16)+'...' : '—'],
    ];
    document.getElementById('mdl-meta-grid').innerHTML = metaItems.map(([l,v]) =>
      `<div class="meta-card"><div class="meta-label">${l}</div><div class="meta-value">${v}</div></div>`
    ).join('');

    renderFindingsTable('mdl-findings-body', data.findings||[]);
    document.getElementById('mdl-results').hidden = false;
  } catch (err) {
    document.getElementById('mdl-error').textContent = `Error: ${err.message}`;
    document.getElementById('mdl-error').hidden = false;
  } finally {
    document.getElementById('mdl-spinner').hidden = true;
    document.getElementById('btn-audit-model').disabled = false;
  }
});

// =========================================================
// Inference Audit
// =========================================================
document.getElementById('btn-audit-inference').addEventListener('click', async () => {
  const logPath = document.getElementById('inf-log').value.trim();

  document.getElementById('inf-spinner').hidden  = false;
  document.getElementById('inf-results').hidden  = true;
  document.getElementById('inf-error').hidden    = true;
  document.getElementById('btn-audit-inference').disabled = true;

  try {
    const r = await fetch(`${API_BASE}/api/audit/inference`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ log_path: logPath }),
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail||r.statusText); }
    const data = await r.json();

    document.getElementById('inf-verdict-badge').innerHTML  = verdictBadge(data.verdict);
    document.getElementById('inf-severity-chips').innerHTML = severityChips(data.severity_summary||{});

    // Records table
    const recsTbody = document.getElementById('inf-records-body');
    (data.records||[]).forEach(rec => {
      const tr = document.createElement('tr');
      const preds = (rec.predictions||[]).map(p => `cls${p.class_id}:${p.score}`).join(', ');
      tr.innerHTML = `
        <td class="code-cell" style="max-width:120px;overflow:hidden;text-overflow:ellipsis" title="${rec.record_id}">${(rec.record_id||'').slice(0,8)}...</td>
        <td>${rec.image_id||'—'}</td>
        <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis" title="${rec.model_id}">${(rec.model_id||'').slice(0,20)}...</td>
        <td>${preds||'—'}</td>
        <td><span class="result-badge ${rec.payload_hash?'rb-PASS':'rb-NOT_ASSESSED'}">${rec.payload_hash?'Signed':'Unsigned'}</span></td>
        <td><span class="result-badge ${rec.hmac_sig?'rb-PASS':'rb-NOT_ASSESSED'}">${rec.hmac_sig?'Present':'Absent'}</span></td>`;
      recsTbody.appendChild(tr);
    });

    renderFindingsTable('inf-findings-body', data.findings||[]);
    document.getElementById('inf-results').hidden = false;
  } catch (err) {
    document.getElementById('inf-error').textContent = `Error: ${err.message}`;
    document.getElementById('inf-error').hidden = false;
  } finally {
    document.getElementById('inf-spinner').hidden = true;
    document.getElementById('btn-audit-inference').disabled = false;
  }
});

// =========================================================
// Full Audit / Report
// =========================================================
document.getElementById('btn-full-audit').addEventListener('click', async () => {
  const dsPath  = document.getElementById('rep-ds').value.trim();
  const mdlPath = document.getElementById('rep-mdl').value.trim();
  const mPath   = document.getElementById('rep-manifest').value.trim();
  const infPath = document.getElementById('rep-inf').value.trim();

  document.getElementById('rep-spinner').hidden  = false;
  document.getElementById('rep-results').hidden  = true;
  document.getElementById('rep-error').hidden    = true;
  document.getElementById('btn-full-audit').disabled = true;

  try {
    const r = await fetch(`${API_BASE}/api/audit/full`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_path:  dsPath  || null,
        model_path:    mdlPath || null,
        manifest_path: mPath   || null,
        inference_log: infPath || null,
      }),
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail||r.statusText); }
    const data = await r.json();

    // Summary card
    const totalFindings = (data.findings||[]).length;
    const sev = data.severity_summary || {};
    document.getElementById('rep-summary-card').innerHTML = `
      <div class="report-verdict-col">
        <div class="report-verdict-label">Assurance Verdict</div>
        <div class="report-verdict-value">${(data.verdict||'').replace(/_/g,' ')}</div>
      </div>
      <div class="report-meta-col">
        <div class="report-meta-item"><label>Total Findings</label><span>${totalFindings}</span></div>
        <div class="report-meta-item"><label>Critical</label><span>${sev.CRITICAL||0}</span></div>
        <div class="report-meta-item"><label>High</label><span>${sev.HIGH||0}</span></div>
        <div class="report-meta-item"><label>Medium</label><span>${sev.MEDIUM||0}</span></div>
        <div class="report-meta-item"><label>Report ID</label><span style="font-size:12px">${(data.report_id||'—').slice(0,8)}...</span></div>
        <div class="report-meta-item"><label>Low</label><span>${sev.LOW||0}</span></div>
      </div>`;

    renderFindingsTable('rep-findings-body', data.findings||[]);

    // Coverage prose
    document.getElementById('rep-confidence').textContent =
      'Deterministic checks (hash comparison, HMAC verification, exact duplicate detection) carry HIGH confidence. '
      + 'Statistical checks (Z-score, Mahalanobis distance, entropy) carry LOW to MEDIUM confidence and require human review. '
      + 'All anomaly findings represent candidates for investigation, not confirmed attacks.';

    // Actions
    const actions = (data.findings||[])
      .filter(f => f.result === 'ANOMALY_DETECTED' || f.result === 'FAIL')
      .map(f => f.recommended_action)
      .filter(Boolean);
    const actList = document.getElementById('rep-actions');
    actList.innerHTML = actions.length
      ? actions.map(a => `<li>${a}</li>`).join('')
      : '<li style="color:var(--gray-400)">No recommended actions (no anomalies detected).</li>';

    // Limitations
    const coverage = data.coverage || {};
    const limList = document.getElementById('rep-limitations');
    limList.innerHTML = (coverage.known_limitations||[]).map(l => `<li>${l}</li>`).join('');

    // Image grid with dataset and inference records
    // Assume format is YOLO unless we added logic to know. For Full Audit, it defaults to YOLO but could be COCO.
    // Let's pass 'yolo' or check if there's an annotations.json in dataset_path in the future.
    renderImageGrid('rep-image-grid', data.dataset_records, data.inference_records, 'yolo');

    document.getElementById('rep-results').hidden = false;
  } catch (err) {
    document.getElementById('rep-error').textContent = `Error: ${err.message}`;
    document.getElementById('rep-error').hidden = false;
  } finally {
    document.getElementById('rep-spinner').hidden = true;
    document.getElementById('btn-full-audit').disabled = false;
  }
});

// =========================================================
// Coverage
// =========================================================
async function loadCoverage() {
  const container = document.getElementById('coverage-content');
  try {
    const r    = await fetch(`${API_BASE}/api/coverage`);
    if (!r.ok) throw new Error(r.statusText);
    const cov  = await r.json();

    const sections = [
      { key: 'implemented',     label: 'Implemented',     cls: 'green', icon: '✔' },
      { key: 'partial',         label: 'Partial Support',  cls: 'amber', icon: '~' },
      { key: 'unsupported',     label: 'Unsupported',      cls: 'red',   icon: '✕' },
      { key: 'assumptions',     label: 'Assumptions',      cls: 'blue',  icon: 'ℹ' },
      { key: 'known_limitations', label: 'Known Limitations', cls: 'gray', icon: '⚠' },
    ];

    container.innerHTML = sections.map(s => `
      <div class="coverage-card">
        <div class="coverage-card-title ${s.cls}">${s.icon} ${s.label}</div>
        <ul class="coverage-list" style="color:var(--${s.cls === 'green' ? 'green' : s.cls === 'amber' ? 'amber' : s.cls === 'red' ? 'red' : s.cls === 'blue' ? 'blue' : 'gray'}-600)">
          ${(cov[s.key]||[]).map(item => `<li>${item}</li>`).join('')}
        </ul>
      </div>`).join('');
  } catch (err) {
    container.innerHTML = `<div class="error-banner">Failed to load coverage: ${err.message}</div>`;
  }
}
