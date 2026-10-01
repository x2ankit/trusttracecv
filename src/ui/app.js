const API_BASE = '';

// --- Navigation & State ---
let currentState = {
  activePage: 'overview',
  datasetAuditData: null,
  modelAuditData: null,
  inferenceAuditData: null,
  fullReportData: null
};

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${btn.dataset.target}`).classList.add('active');
    
    if (btn.dataset.target === 'coverage') loadCoverage();
  });
});

// --- Health Check ---
async function checkHealth() {
  const dot = document.getElementById('backend-status-dot');
  const txt = document.getElementById('backend-status-text');
  try {
    const r = await fetch(`${API_BASE}/api/health`);
    if (r.ok) {
      dot.className = 'status-dot online';
      txt.textContent = 'Backend Connected';
    } else throw new Error();
  } catch {
    dot.className = 'status-dot offline';
    txt.textContent = 'Backend Offline';
  }
}
checkHealth();
setInterval(checkHealth, 15000);

// --- Utilities ---
function sevClass(sev) {
  if (sev === 'CRITICAL' || sev === 'HIGH') return 'badge fail';
  if (sev === 'MEDIUM') return 'badge review';
  return 'badge gray';
}

function resultText(res) {
  if (res === 'PASS' || res === 'BEHAVIORALLY_CONSISTENT') return '<span class="text-green font-medium">PASS</span>';
  if (res === 'FAIL' || res === 'ANOMALY_DETECTED' || res === 'BEHAVIORAL_DIVERGENCE') return '<span class="text-red font-medium">FAIL</span>';
  return `<span class="text-gray">${res}</span>`;
}

// --- Drawer ---
function openDrawer(title, contentHtml) {
  document.getElementById('drawer-title').textContent = title;
  document.getElementById('drawer-content').innerHTML = contentHtml;
  document.getElementById('evidence-drawer').classList.add('open');
  document.getElementById('drawer-overlay').classList.add('open');
}

function closeDrawer() {
  document.getElementById('evidence-drawer').classList.remove('open');
  document.getElementById('drawer-overlay').classList.remove('open');
}

document.getElementById('drawer-close').addEventListener('click', closeDrawer);
document.getElementById('drawer-overlay').addEventListener('click', closeDrawer);

// --- Dataset Audit ---
document.getElementById('ds-file-input').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  const formData = new FormData();
  formData.append('file', file);
  formData.append('format', document.getElementById('ds-meta-format').value);
  
  document.getElementById('ds-upload-meta').hidden = false;
  document.getElementById('ds-meta-filename').textContent = file.name;
  document.getElementById('ds-meta-path').textContent = 'Uploading...';
  
  try {
    const r = await fetch(`${API_BASE}/api/upload/dataset`, { method: 'POST', body: formData });
    if (!r.ok) throw new Error('Upload failed');
    const data = await r.json();
    document.getElementById('ds-meta-path').textContent = data.dataset_path;
    document.getElementById('topbar-ds-name').textContent = `Dataset: ${file.name}`;
    window.uploadedDatasetPath = data.dataset_path;
  } catch (err) {
    document.getElementById('ds-meta-path').textContent = 'Upload failed';
  }
});

document.getElementById('btn-start-audit').addEventListener('click', async () => {
  if (!window.uploadedDatasetPath) return;
  
  document.getElementById('ds-upload-area').hidden = true;
  document.getElementById('ds-progress-area').hidden = false;
  document.getElementById('ds-results-area').hidden = true;
  document.getElementById('topbar-status').textContent = 'AUDITING';
  document.getElementById('topbar-status').className = 'topbar-status badge review';
  
  // Fake progress animation for UX
  const items = document.querySelectorAll('.progress-item');
  let pIdx = 2;
  const intv = setInterval(() => {
    if (pIdx < items.length - 1) {
      items[pIdx-1].className = 'progress-item completed';
      items[pIdx-1].innerHTML = items[pIdx-1].textContent.replace('→', '✔').replace('spinner-sm', '✔');
      items[pIdx].className = 'progress-item active';
      items[pIdx].innerHTML = items[pIdx].textContent.replace('→', '<span class="icon spinner-sm"></span>');
      pIdx++;
    }
  }, 800);

  try {
    const r = await fetch(`${API_BASE}/api/audit/dataset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_path: window.uploadedDatasetPath, format: document.getElementById('ds-meta-format').value, seed: 42 })
    });
    clearInterval(intv);
    
    items.forEach(i => {
      i.className = 'progress-item completed';
      i.innerHTML = i.textContent.replace('→', '✔').replace('spinner-sm', '✔');
    });

    const data = await r.json();
    currentState.datasetAuditData = data;
    renderDatasetResults(data);
    
    document.getElementById('ds-progress-area').hidden = true;
    document.getElementById('ds-results-area').hidden = false;
    document.getElementById('topbar-status').textContent = 'COMPLETED';
    document.getElementById('topbar-status').className = 'topbar-status badge pass';
    
    // Update Overview
    document.getElementById('ov-samples').textContent = data.records.length;
    document.getElementById('ov-flagged').textContent = data.findings.length;
    document.getElementById('ov-high-sev').textContent = data.severity_summary.HIGH || 0;
    document.getElementById('ov-empty-state').hidden = true;
    document.getElementById('overview-cards').style.display = 'grid';

  } catch (err) {
    clearInterval(intv);
    alert('Audit failed: ' + err.message);
  }
});

function renderDatasetResults(data) {
  // Render Summary
  const sev = data.severity_summary || {};
  document.getElementById('ds-findings-summary').innerHTML = `
    <div class="f-stat"><span class="ev-label">Total</span><span class="f-val">${data.records.length}</span></div>
    <div class="f-stat"><span class="ev-label">Flagged</span><span class="f-val text-red">${data.findings.length}</span></div>
    <div class="f-stat"><span class="ev-label">High</span><span class="f-val text-amber">${sev.HIGH||0}</span></div>
  `;

  // Render Findings Table
  const tbody = document.getElementById('ds-findings-tbody');
  tbody.innerHTML = data.findings.map((f, i) => `
    <tr>
      <td><span class="${sevClass(f.severity)}">${f.severity}</span></td>
      <td class="font-medium">${f.finding_type || f.name}</td>
      <td>${f.asset_id || '—'}</td>
      <td>${f.method}</td>
      <td class="text-gray text-sm">${f.confidence_basis}</td>
      <td><button class="btn btn-outline" onclick="viewFinding(${i}, 'dataset')">View Evidence</button></td>
    </tr>
  `).join('');

  // Render Thumbnails
  const strip = document.getElementById('thumbnail-strip');
  strip.innerHTML = data.records.slice(0, 50).map((r, i) => {
    const isFlagged = data.findings.some(f => f.asset_id === r.filename || f.asset_id === r.image_id);
    return `<img src="${API_BASE}/api/image?path=${encodeURIComponent(r.url_path)}" class="thumb ${isFlagged?'flagged':''}" onclick="viewSample(${i})" id="thumb-${i}">`;
  }).join('');

  if (data.records.length > 0) viewSample(0);
}

function viewSample(idx) {
  const data = currentState.datasetAuditData;
  if (!data) return;
  const rec = data.records[idx];
  
  document.querySelectorAll('.thumb').forEach(t => t.classList.remove('active'));
  const t = document.getElementById(`thumb-${idx}`);
  if (t) t.classList.add('active');

  document.getElementById('viewer-filename').textContent = rec.filename;
  document.getElementById('dt-id').textContent = rec.image_id || '—';
  document.getElementById('dt-res').textContent = rec.resolution ? rec.resolution.join(' × ') : '—';
  document.getElementById('dt-sha').textContent = rec.sha256 || '—';
  document.getElementById('dt-ann-count').textContent = (rec.annotations||[]).length;

  const viewer = document.getElementById('bbox-viewer');
  viewer.innerHTML = `<img src="${API_BASE}/api/image?path=${encodeURIComponent(rec.url_path)}" class="viewer-img" id="main-img">`;

  const tbody = document.getElementById('dt-objects-tbody');
  tbody.innerHTML = '';
  
  const img = document.getElementById('main-img');
  img.onload = () => {
    const format = document.getElementById('ds-meta-format').value;
    const [origW, origH] = rec.resolution || [1, 1];
    
    (rec.annotations || []).forEach(a => {
      let left, top, width, height;
      if (format === 'yolo') {
        left = (a.x_center - a.width/2) * 100; top = (a.y_center - a.height/2) * 100;
        width = a.width * 100; height = a.height * 100;
      } else {
        const [x, y, w, h] = a.bbox;
        left = (x / origW) * 100; top = (y / origH) * 100;
        width = (w / origW) * 100; height = (h / origH) * 100;
      }
      
      viewer.innerHTML += `
        <div class="bbox-overlay gt" style="left:${left}%; top:${top}%; width:${width}%; height:${height}%;">
          <span class="bbox-label">${a.class_name || 'Class ' + a.class_id}</span>
        </div>
      `;
      
      tbody.innerHTML += `
        <tr>
          <td><span class="badge pass">GT</span></td>
          <td class="font-medium">${a.class_name || a.class_id}</td>
          <td class="text-gray">—</td>
          <td class="font-mono text-gray">[${format==='yolo' ? `${a.x_center.toFixed(2)},${a.y_center.toFixed(2)}` : a.bbox.map(x=>Math.round(x)).join(',')}]</td>
        </tr>
      `;
    });
  };
}

function viewFinding(idx, type) {
  let f;
  if (type === 'dataset') f = currentState.datasetAuditData.findings[idx];
  else if (type === 'model') f = currentState.modelAuditData.findings[idx];
  else if (type === 'inference') f = currentState.inferenceAuditData.findings[idx];
  else if (type === 'report') f = currentState.fullReportData.findings[idx];
  
  if (!f) return;

  const html = `
    <div class="ev-block"><div class="ev-label">Asset / ID</div><div class="ev-value font-mono">${f.asset_id || f.evidence_id || '—'}</div></div>
    <div class="ev-block"><div class="ev-label">Method</div><div class="ev-value">${f.method}</div></div>
    <div class="ev-block"><div class="ev-label">Observation</div><div class="ev-value">${f.observations || f.description || '—'}</div></div>
    <div class="ev-block"><div class="ev-label">Severity</div><div class="ev-value"><span class="${sevClass(f.severity)}">${f.severity}</span></div></div>
    <div class="ev-block"><div class="ev-label">Confidence Basis</div><div class="ev-value">${f.confidence_basis || '—'}</div></div>
    <div class="ev-block"><div class="ev-label">Limitations</div><div class="ev-value">${f.limitations || '—'}</div></div>
    <div class="ev-block"><div class="ev-label">Action</div><div class="ev-value font-medium text-amber">${f.recommended_action || '—'}</div></div>
    ${f.evidence ? `<div class="ev-block"><div class="ev-label">Raw Evidence</div><div class="ev-box">${JSON.stringify(f.evidence, null, 2)}</div></div>` : ''}
  `;
  openDrawer(f.finding_type || f.name, html);
}

// --- Model Audit ---
document.getElementById('btn-audit-model').addEventListener('click', async () => {
  const modelPath = document.getElementById('mdl-path').value;
  const manifestPath = document.getElementById('mdl-manifest').value;
  if (!modelPath) return;

  try {
    const r = await fetch(`${API_BASE}/api/audit/model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_path: modelPath, manifest_path: manifestPath })
    });
    if (!r.ok) throw new Error('Model audit failed');
    const data = await r.json();
    currentState.modelAuditData = data;
    
    document.getElementById('mdl-results-area').hidden = false;
    document.getElementById('ov-model-status').innerHTML = resultText(data.verdict);
    
    const rec = data.model_record || {};
    document.getElementById('mdl-identity-grid').innerHTML = `
      <div class="dt-label">Format</div><div class="dt-value">${rec.format||'—'}</div>
      <div class="dt-label">SHA-256</div><div class="dt-value font-mono truncate" title="${rec.sha256}">${(rec.sha256||'').slice(0,16)}...</div>
      <div class="dt-label">Size</div><div class="dt-value">${rec.size_bytes ? Math.round(rec.size_bytes/1024)+' KB' : '—'}</div>
    `;

    document.getElementById('mdl-perf-grid').innerHTML = `<div class="dt-value text-gray">Requires dataset predictions for AP/mAP evaluation. See Report for full evaluation.</div>`;
    document.getElementById('mdl-behav-grid').innerHTML = `<div class="dt-value text-gray">Requires behavioral dataset fixtures. See Report for white-box fingerprinting and trigger probes.</div>`;
    
    const tbody = document.getElementById('mdl-findings-tbody');
    tbody.innerHTML = data.findings.map((f, i) => `
      <tr>
        <td><span class="${sevClass(f.severity)}">${f.severity}</span></td>
        <td class="font-medium">${f.finding_type || f.name}</td>
        <td class="text-gray">${f.confidence_basis}</td>
        <td><button class="btn btn-outline" onclick="viewFinding(${i}, 'model')">View</button></td>
      </tr>
    `).join('');
    
  } catch(err) { alert(err.message); }
});

// --- Inference Audit ---
document.getElementById('btn-audit-inference').addEventListener('click', async () => {
  const logPath = document.getElementById('inf-log').value;
  if (!logPath) return;

  try {
    const r = await fetch(`${API_BASE}/api/audit/inference`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ log_path: logPath })
    });
    if (!r.ok) throw new Error('Inference audit failed');
    const data = await r.json();
    currentState.inferenceAuditData = data;
    
    document.getElementById('inf-results-area').hidden = false;
    document.getElementById('ov-inf-status').innerHTML = resultText(data.verdict);

    const tbody = document.getElementById('inf-records-tbody');
    tbody.innerHTML = (data.records || []).slice(0, 50).map(rec => `
      <tr>
        <td class="font-mono">${(rec.record_id||'').slice(0,8)}</td>
        <td>${rec.timestamp||'—'}</td>
        <td class="font-mono truncate" title="${rec.payload_hash}" style="max-width:100px">${(rec.payload_hash||'').slice(0,8)}...</td>
        <td>${rec.hmac_sig ? '<span class="text-green">Verified</span>' : '<span class="text-gray">None</span>'}</td>
        <td>${rec.replay_detected ? '<span class="badge fail">REPLAY</span>' : '<span class="badge pass">OK</span>'}</td>
        <td>${rec.replay_detected ? '<span class="text-red font-medium">FAIL</span>' : '<span class="text-green font-medium">PASS</span>'}</td>
      </tr>
    `).join('');
    
  } catch(err) { alert(err.message); }
});

// --- Report ---
document.getElementById('btn-full-audit').addEventListener('click', async () => {
  const body = {
    dataset_path: document.getElementById('rep-ds').value || null,
    model_path: document.getElementById('rep-mdl').value || null,
    manifest_path: document.getElementById('rep-manifest').value || null,
    inference_log: document.getElementById('rep-inf').value || null,
  };

  try {
    const r = await fetch(`${API_BASE}/api/audit/full`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!r.ok) throw new Error('Report generation failed');
    const data = await r.json();
    currentState.fullReportData = data;
    
    document.getElementById('rep-results-area').hidden = false;
    
    const ovState = document.getElementById('rep-overall-state');
    ovState.textContent = (data.verdict||'').replace(/_/g, ' ');
    ovState.className = 'report-overall ' + (data.verdict === 'PASS' ? 'pass' : data.verdict === 'FAIL' ? 'fail' : 'review');
    
    const hasDsFinding = (data.findings||[]).some(f => f.category === 'DATASET' && (f.result === 'FAIL' || f.result === 'ANOMALY_DETECTED'));
    const hasMdlFinding = (data.findings||[]).some(f => f.category === 'MODEL' && (f.result === 'FAIL' || f.result === 'ANOMALY_DETECTED'));
    const hasInfFinding = (data.findings||[]).some(f => f.category === 'INFERENCE' && (f.result === 'FAIL' || f.result === 'ANOMALY_DETECTED'));
    const hasBehFinding = (data.findings||[]).some(f => f.category === 'MODEL_BEHAVIOR' && f.status === 'FLAGGED');

    document.getElementById('rep-ds-state').innerHTML = body.dataset_path ? (hasDsFinding ? '<span class="text-red">FAIL</span>' : '<span class="text-green">PASS</span>') : '—';
    document.getElementById('rep-mdl-state').innerHTML = body.model_path ? (hasMdlFinding ? '<span class="text-red">FAIL</span>' : '<span class="text-green">PASS</span>') : '—';
    document.getElementById('rep-perf-state').innerHTML = body.model_path && body.dataset_path ? '<span class="text-green">EVALUATED</span>' : '—';
    document.getElementById('rep-behav-state').innerHTML = body.model_path ? (hasBehFinding ? '<span class="text-amber">FLAGGED</span>' : '<span class="text-green">PASS</span>') : '—';
    document.getElementById('rep-prov-state').innerHTML = body.inference_log ? (hasInfFinding ? '<span class="text-red">FAIL</span>' : '<span class="text-green">PASS</span>') : '—';

    const tbody = document.getElementById('rep-findings-tbody');
    tbody.innerHTML = data.findings.map((f, i) => `
      <tr>
        <td><span class="${sevClass(f.severity)}">${f.severity}</span></td>
        <td class="font-mono text-gray">${f.category || 'GENERAL'}</td>
        <td class="font-medium">${f.finding_type || f.name}</td>
        <td class="truncate" style="max-width: 200px">${f.observations || f.description || '—'}</td>
        <td><button class="btn btn-outline" onclick="viewFinding(${i}, 'report')">Review</button></td>
      </tr>
    `).join('');
    
  } catch (err) { alert(err.message); }
});

// --- Coverage ---
async function loadCoverage() {
  try {
    const r = await fetch(`${API_BASE}/api/coverage`);
    if (!r.ok) throw new Error();
    const cov = await r.json();
    
    const mapItems = (items, status, label) => (items||[]).map(i => `
      <div class="cov-row">
        <div class="cov-status ${status}">${label}</div>
        <div class="cov-content">
          <div class="cov-title">${i.split(':')[0]}</div>
          <div class="cov-desc">${i}</div>
        </div>
      </div>
    `).join('');

    document.getElementById('coverage-container').innerHTML = 
      mapItems(cov.implemented, 'supported', 'SUPPORTED') +
      mapItems(cov.partial, 'partial', 'PARTIAL') +
      mapItems(cov.unsupported, 'unassessed', 'NOT ASSESSED');

  } catch (err) {
    document.getElementById('coverage-container').innerHTML = '<div class="text-red">Failed to load coverage matrix.</div>';
  }
}
