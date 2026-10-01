
document.querySelectorAll('.app-tabs .tab-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    document.querySelectorAll('.app-tabs .tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.app-workspace .tab-panel').forEach(p => p.classList.remove('active'));
    e.target.classList.add('active');
    document.getElementById('tab-' + e.target.dataset.target).classList.add('active');
  });
});

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
  
  try {
    const r = await fetch(`${API_BASE}/api/upload/dataset`, { method: 'POST', body: formData });
    if (!r.ok) {
        const errorData = await r.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Upload failed');
    }
    const data = await r.json();
    document.getElementById('topbar-ds-name').textContent = `Dataset: ${file.name}`;
    window.uploadedDatasetPath = data.dataset_path;
  } catch (err) {
    document.getElementById('ds-meta-filename').textContent = `Error: ${err.message}`;
    document.getElementById('ds-meta-filename').style.color = 'var(--danger)';
  }
});

document.getElementById('btn-start-audit').addEventListener('click', async () => {
  if (!window.uploadedDatasetPath) {
    alert("Please upload a dataset file first!");
    return;
  }
  
  if (document.getElementById('ds-upload-area')) {
    document.getElementById('ds-upload-area').hidden = true;
  }
  if (document.getElementById('topbar-status')) {
    document.getElementById('topbar-status').textContent = 'AUDITING';
    document.getElementById('topbar-status').className = 'topbar-status badge review';
  }
  
  if (document.getElementById('ds-current-op')) {
    document.getElementById('ds-current-op').textContent = 'Initializing background audit...';
    document.getElementById('ds-live-calc').innerHTML = '<div class="text-gray">Starting...</div>';
    document.getElementById('ds-event-history').innerHTML = '';
    document.getElementById('ds-findings-tbody').innerHTML = '';
    document.getElementById('ds-evidence-tbody').innerHTML = '';
  }
  
  let auditId = null;
  let seenEventIds = new Set();
  
  try {
    const r = await fetch(`${API_BASE}/api/audit/dataset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_path: window.uploadedDatasetPath, format: document.getElementById('ds-meta-format').value, seed: 42 })
    });

    const data = await r.json();
    if (!r.ok) {
      throw new Error(data.detail || 'Audit failed');
    }
    
    auditId = data.audit_id;
    
    const intv = setInterval(async () => {
      try {
        const rs = await fetch(`${API_BASE}/api/audit/events/${auditId}`);
        if (rs.ok) {
          const eventsData = await rs.json();
          let isComplete = false;
          let isError = false;
          
          for (const ev of eventsData.events) {
            if (!seenEventIds.has(ev.event_id)) {
              seenEventIds.add(ev.event_id);
              
              // Append to history
              const histLine = document.createElement('div');
              histLine.className = 'mb-1';
              const ts = new Date(ev.timestamp * 1000).toISOString().substring(11,19);
              
              const isPass = ev.status_code === 'PASS';
              const isErr = ev.status_code === 'ERROR' || ev.status_code === 'FAILED';
              const isWarn = ev.status_code === 'WARNING';
              const color = isPass ? 'var(--pass)' : (isErr ? 'var(--danger)' : (isWarn ? 'var(--warning)' : 'var(--text-color)'));
              
              histLine.innerHTML = `<span class="text-gray">[${ts}]</span> <span style="color:var(--primary)">${ev.check_name}</span>: ${ev.observation_type} = <span style="color:${color}">${ev.status_code}</span>`;
              document.getElementById('ds-event-history').appendChild(histLine);
              
              // Update live calc
              if (ev.formula) {
                 document.getElementById('ds-current-op').textContent = `${ev.check_name}: ${ev.observation_type}`;
                 const inputs = JSON.stringify(ev.inputs || {});
                 document.getElementById('ds-live-calc').innerHTML = `
                    <div style="color:var(--info)">Formula: ${ev.formula}</div>
                    <div class="text-gray mt-1">Inputs: ${inputs}</div>
                    <div class="mt-1">Result: ${ev.result_str}</div>
                 `;
              }
              
              if (ev.status_code === 'ERROR') isError = true;
              if (ev.check_name === 'Finalization' && ev.status_code === 'PASS') isComplete = true;
            }
          }
          
          document.getElementById('ds-event-history').scrollTop = document.getElementById('ds-event-history').scrollHeight;
          
          if (isComplete || isError) {
             clearInterval(intv);
             if (document.getElementById('topbar-status')) {
               document.getElementById('topbar-status').textContent = isComplete ? 'COMPLETED' : 'FAILED';
               document.getElementById('topbar-status').className = isComplete ? 'topbar-status badge pass' : 'topbar-status badge fail';
             }
             if (document.getElementById('ds-current-op')) {
                 document.getElementById('ds-current-op').textContent = 'Audit Finished';
             }
             
             // Auto download JSONL
             document.getElementById('btn-export-jsonl').disabled = false;
             document.getElementById('btn-export-json').disabled = false;
             
             try {
                const blob = new Blob([eventsData.events.map(e => JSON.stringify(e)).join('\\n')], { type: 'application/x-ndjson' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `trusttrace_audit_${auditId}_${new Date().toISOString().replace(/[:.]/g,'-')}.jsonl`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
             } catch(e) {
                console.error("Auto-download blocked", e);
             }
             
             // Fetch the final report to populate the findings table
             try {
                 const rep_res = await fetch(`${API_BASE}/api/reports`);
                 if (rep_res.ok) {
                     const reports = await rep_res.json();
                     if (reports.length > 0) {
                         const latest = reports[0];
                         renderDatasetResults(latest);
                     }
                 }
             } catch (e) { console.error(e); }
          }
        }
      } catch (e) {}
    }, 500);

    // Setup manual download buttons
    document.getElementById('btn-export-jsonl').onclick = async () => {
        const rs = await fetch(`${API_BASE}/api/audit/events/${auditId}`);
        const evs = await rs.json();
        const blob = new Blob([evs.events.map(e => JSON.stringify(e)).join('\\n')], { type: 'application/x-ndjson' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `trusttrace_audit_${auditId}.jsonl`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    };
    
  } catch (err) {
    if (document.getElementById('ds-current-op')) document.getElementById('ds-current-op').textContent = `Error: ${err.message}`;
    if (document.getElementById('topbar-status')) {
      document.getElementById('topbar-status').textContent = 'FAILED';
      document.getElementById('topbar-status').className = 'topbar-status badge fail';
    }
  }

  }
});

function renderDatasetResults(data) {
  // Normalize: the backend may return either a direct findings array (legacy)
  // or a report schema with sections. Flatten both into one `findings` array.
  let findings = [];
  if (Array.isArray(data.findings)) {
    findings = data.findings;
  } else if (data.sections) {
    // Report schema: sections is an object keyed by section name, each with a findings array
    for (const section of Object.values(data.sections)) {
      if (Array.isArray(section.findings)) findings = findings.concat(section.findings);
    }
  }
  
  // Store for viewFinding()
  currentState.datasetAuditData = { ...data, findings };

  // Render Summary (if elements exist)
  const totalImages = (data.records ? data.records.length : null) || data.findings_count || '—';
  if (document.getElementById('ds-sum-images')) document.getElementById('ds-sum-images').textContent = totalImages;
  if (document.getElementById('ds-sum-anns')) document.getElementById('ds-sum-anns').textContent = data.records ? data.records.reduce((acc, r) => acc + (r.annotations || []).length, 0) : '—';
  if (document.getElementById('ds-sum-format')) document.getElementById('ds-sum-format').textContent = document.getElementById('ds-meta-format').value;
  if (document.getElementById('ds-sum-hash')) document.getElementById('ds-sum-hash').textContent = data.dataset_sha256 || '—';
  if (document.getElementById('ds-sum-status')) document.getElementById('ds-sum-status').innerHTML = resultText(data.verdict);
  
  const sev = data.severity_summary || {};
  const activeFindings = findings.filter(f => f.result !== 'NOT_ASSESSED');

  // Render Findings Table
  const tbody = document.getElementById('ds-findings-tbody');
  if (tbody) {
    tbody.innerHTML = findings.map((f, i) => `
      <tr>
        <td><span class="${sevClass(f.severity)}">${f.severity || 'INFO'}</span></td>
        <td class="font-medium">${f.finding_type || f.name || '—'}</td>
        <td>${f.asset_id || '—'}</td>
        <td>${f.method || 'System Heuristic'}</td>
        <td class="text-gray text-sm">${f.confidence_basis || (f.confidence ? f.confidence + ' Confidence' : 'N/A')}</td>
        <td><button class="btn btn-outline" onclick="viewFinding(${i}, 'dataset')">View Details</button></td>
      </tr>
    `).join('');
  }
  
  // Render Evidence Table
  const evBody = document.getElementById('ds-evidence-tbody');
  if (evBody) {
    evBody.innerHTML = findings.map(f => `
      <tr>
        <td class="font-mono text-sm">${f.evidence_id || f.check_id || '—'}</td>
        <td>${f.category || f.name || '—'}</td>
        <td class="text-gray text-sm">${f.observations || f.description || '—'}</td>
      </tr>
    `).join('');
  }
  
  if (document.getElementById('ds-perf-card')) {
    document.getElementById('ds-perf-card').hidden = true;
  }

  // Render Thumbnails
  const strip = document.getElementById('thumbnail-strip');
  if (strip) {
    strip.innerHTML = (data.records || []).slice(0, 50).map((r, i) => {
      const isFlagged = data.findings.some(f => f.asset_id === r.filename || f.asset_id === r.image_id);
      return `<img src="${API_BASE}/api/image?path=${encodeURIComponent(r.url_path)}" class="thumb ${isFlagged?'flagged':''}" onclick="viewSample(${i})" id="thumb-${i}">`;
    }).join('');
  }

  if (data.records && data.records.length > 0) viewSample(0);
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
  document.getElementById('dt-res').textContent = rec.resolution || '—';
  document.getElementById('dt-sha').textContent = rec.sha256 || '—';

  const viewer = document.getElementById('bbox-viewer');
  viewer.innerHTML = `<img src="${API_BASE}/api/image?path=${encodeURIComponent(rec.url_path)}" class="viewer-img" id="main-img" style="display: block; width: 100%; height: 100%; object-fit: contain;">
                      <div id="bbox-layer" style="position: absolute; pointer-events: none; overflow: hidden;"></div>`;

  const tbody = document.getElementById('dt-objects-tbody');
  tbody.innerHTML = '';
  
  const img = document.getElementById('main-img');
  
  if (window._bboxResizeObserver) {
    window._bboxResizeObserver.disconnect();
  }
  
  function updateBboxPositions() {
    if (!img.naturalWidth) return;
    const format = document.getElementById('ds-meta-format').value;
    const origW = rec.width || img.naturalWidth || 1;
    const origH = rec.height || img.naturalHeight || 1;
    
    // Calculate letterboxing mathematically
    const containerW = viewer.clientWidth;
    const containerH = viewer.clientHeight;
    const imgRatio = origW / origH;
    const containerRatio = containerW / containerH;
    
    let renderW, renderH, offsetX, offsetY;
    if (imgRatio > containerRatio) {
      // Letterbox vertically
      renderW = containerW;
      renderH = containerW / imgRatio;
      offsetX = 0;
      offsetY = (containerH - renderH) / 2;
    } else {
      // Letterbox horizontally
      renderH = containerH;
      renderW = containerH * imgRatio;
      offsetX = (containerW - renderW) / 2;
      offsetY = 0;
    }
    
    const bboxLayer = document.getElementById('bbox-layer');
    bboxLayer.style.left = offsetX + 'px';
    bboxLayer.style.top = offsetY + 'px';
    bboxLayer.style.width = renderW + 'px';
    bboxLayer.style.height = renderH + 'px';
    
    let tbodyHtml = '';
    let bboxesHtml = '';
    
    (rec.annotations || []).forEach((a, annIdx) => {
      let x_min, y_min, box_w, box_h;
      
      if (format === 'yolo') {
        x_min = (a.x_center - a.width / 2) * origW;
        y_min = (a.y_center - a.height / 2) * origH;
        box_w = a.width * origW;
        box_h = a.height * origH;
      } else {
        const [x, y, w, h] = a.bbox;
        x_min = x; y_min = y; box_w = w; box_h = h;
      }
      
      let leftPct = (x_min / origW) * 100;
      let topPct = (y_min / origH) * 100;
      let widthPct = (box_w / origW) * 100;
      let heightPct = (box_h / origH) * 100;
      
      leftPct = Math.max(0, Math.min(100, leftPct));
      topPct = Math.max(0, Math.min(100, topPct));
      widthPct = Math.max(0, Math.min(100 - leftPct, widthPct));
      heightPct = Math.max(0, Math.min(100 - topPct, heightPct));
      
      bboxesHtml += `
        <div class="bbox-overlay gt" style="left:${leftPct}%; top:${topPct}%; width:${widthPct}%; height:${heightPct}%; pointer-events: auto;" title="${a.class_name || 'Class ' + a.class_id}">
          <span class="bbox-label">${a.class_name || 'Class ' + a.class_id}</span>
        </div>
      `;
      
      tbodyHtml += `
        <tr>
          <td class="font-medium">${a.class_name || a.class_id}</td>
          <td class="text-gray">${a.confidence !== undefined ? a.confidence.toFixed(3) : 'N/A'}</td>
          <td class="font-mono text-gray">${Math.round(x_min)}</td>
          <td class="font-mono text-gray">${Math.round(y_min)}</td>
          <td class="font-mono text-gray">${Math.round(box_w)}</td>
          <td class="font-mono text-gray">${Math.round(box_h)}</td>
          <td><span class="badge ${a.source === 'MODEL' ? 'amber' : 'pass'}">${a.source || 'GROUND_TRUTH'}</span></td>
          <td><button class="btn btn-outline" style="padding: 2px 8px; font-size: 11px;" onclick="viewBboxTrace(${idx}, ${annIdx})">Trace</button></td>
        </tr>
      `;
    });
    
    bboxLayer.innerHTML = bboxesHtml;
    tbody.innerHTML = tbodyHtml;
  }
  
  img.onload = () => {
    updateBboxPositions();
    window._bboxResizeObserver = new ResizeObserver(updateBboxPositions);
    window._bboxResizeObserver.observe(viewer);
  };
}

function viewBboxTrace(imgIdx, annIdx) {
  const data = currentState.datasetAuditData;
  if (!data) return;
  const rec = data.records[imgIdx];
  const a = rec.annotations[annIdx];
  const format = document.getElementById('ds-meta-format').value;
  const W = rec.width || 1;
  const H = rec.height || 1;
  
  let mathHtml = '';
  if (format === 'yolo') {
    mathHtml = `
      <div class="ev-block"><div class="ev-label">Formula</div>
      <div class="ev-value font-mono text-sm bg-gray-100 p-2 rounded">
        x_min = (x_center - width / 2) * W<br>
        y_min = (y_center - height / 2) * H<br>
        box_width = width * W<br>
        box_height = height * H<br>
        x_max = x_min + box_width<br>
        y_max = y_min + box_height
      </div></div>
      <div class="ev-block"><div class="ev-label">Inputs</div>
      <div class="ev-value font-mono text-sm">
        x_center=${a.x_center}, y_center=${a.y_center}, width=${a.width}, height=${a.height}<br>
        W=${W} px, H=${H} px
      </div></div>
      <div class="ev-block"><div class="ev-label">Substitution & Calculation</div>
      <div class="ev-value font-mono text-sm">
        x_min = (${a.x_center} - ${a.width} / 2) * ${W} = ${(a.x_center - a.width/2) * W} px<br>
        y_min = (${a.y_center} - ${a.height} / 2) * ${H} = ${(a.y_center - a.height/2) * H} px<br>
        box_width = ${a.width} * ${W} = ${a.width * W} px<br>
        box_height = ${a.height} * ${H} = ${a.height * H} px
      </div></div>
      <div class="ev-block"><div class="ev-label">Validation (Bounds Check)</div>
      <div class="ev-value font-mono text-sm">
        0 <= x_center <= 1: ${0 <= a.x_center && a.x_center <= 1 ? 'PASS' : 'FAIL'}<br>
        0 <= y_center <= 1: ${0 <= a.y_center && a.y_center <= 1 ? 'PASS' : 'FAIL'}<br>
        0 < width <= 1: ${0 < a.width && a.width <= 1 ? 'PASS' : 'FAIL'}<br>
        0 < height <= 1: ${0 < a.height && a.height <= 1 ? 'PASS' : 'FAIL'}
      </div></div>
    `;
  } else {
    mathHtml = `
      <div class="ev-block"><div class="ev-label">Format</div><div class="ev-value">COCO [x_min, y_min, width, height]</div></div>
      <div class="ev-block"><div class="ev-label">Inputs</div><div class="ev-value font-mono">[${a.bbox.join(', ')}]</div></div>
      <div class="ev-block"><div class="ev-label">Validation</div><div class="ev-value font-mono text-sm">
        width > 0: ${a.bbox[2] > 0 ? 'PASS' : 'FAIL'}<br>
        height > 0: ${a.bbox[3] > 0 ? 'PASS' : 'FAIL'}
      </div></div>
    `;
  }
  
  openDrawer('Math Trace: Bounding Box', mathHtml);
}

function viewFinding(idx, type) {
  let f;
  if (type === 'dataset') f = currentState.datasetAuditData.findings[idx];
  else if (type === 'model') f = currentState.modelAuditData.findings[idx];
  else if (type === 'inference') f = currentState.inferenceAuditData.findings[idx];
  else if (type === 'report') f = currentState.fullReportData.findings[idx];
  
  if (!f) return;

  let html = `
    <div class="ev-block"><div class="ev-label">Asset / ID</div><div class="ev-value font-mono">${f.asset_id || f.evidence_id || '—'}</div></div>
    <div class="ev-block"><div class="ev-label">Method</div><div class="ev-value">${f.method}</div></div>
    <div class="ev-block"><div class="ev-label">Observation</div><div class="ev-value">${f.observations || f.description || '—'}</div></div>
    <div class="ev-block"><div class="ev-label">Severity</div><div class="ev-value"><span class="${sevClass(f.severity)}">${f.severity}</span></div></div>
    <div class="ev-block"><div class="ev-label">Confidence Basis</div><div class="ev-value">${f.confidence_basis || '—'}</div></div>
    <div class="ev-block"><div class="ev-label">Limitations</div><div class="ev-value">${f.limitations || f.limitation || '—'}</div></div>
    <div class="ev-block"><div class="ev-label">Action</div><div class="ev-value font-medium text-amber">${f.recommended_action || '—'}</div></div>
  `;
  
  if (f.trace) {
    html += `
      <div style="background:#f8fafc; padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px; margin: 15px 0;">
        <h4 style="margin-top:0; margin-bottom:10px; color:#0f172a;">Mathematical Trace: ${f.trace.operation_id}</h4>
        <div class="ev-block"><div class="ev-label">Operation</div><div class="ev-value">${f.trace.operation_type}</div></div>
        <div class="ev-block"><div class="ev-label">Formula</div><div class="ev-value font-mono text-sm p-2 bg-gray-100 rounded">${f.trace.formula}</div></div>
        <div class="ev-block"><div class="ev-label">Inputs</div><div class="ev-value font-mono text-sm">${JSON.stringify(f.trace.inputs, null, 2)}</div></div>
        <div class="ev-block"><div class="ev-label">Intermediate</div><div class="ev-value font-mono text-sm">${JSON.stringify(f.trace.intermediate_values, null, 2)}</div></div>
        <div class="ev-block"><div class="ev-label">Result</div><div class="ev-value font-medium">${f.trace.result}</div></div>
        <div class="ev-block"><div class="ev-label">Comparison</div><div class="ev-value font-mono text-sm">${f.trace.comparison} (Threshold: ${f.trace.threshold})</div></div>
        <div class="ev-block"><div class="ev-label">Conclusion</div><div class="ev-value font-medium text-blue">${f.trace.decision}</div></div>
        <div class="ev-block"><div class="ev-label">Explanation</div><div class="ev-value text-gray text-sm">${f.trace.explanation}</div></div>
      </div>
    `;
  }
  
  if (f.evidence) {
    html += `<div class="ev-block"><div class="ev-label">Raw Evidence</div><div class="ev-box">${JSON.stringify(f.evidence, null, 2)}</div></div>`;
  }
  
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
