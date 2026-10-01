import os

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TRUSTTRACE CV – Computer Vision Integrity Assurance</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <!-- HEADER -->
  <header class="app-header">
    <div class="header-left">
      <h1 class="brand-title">TRUSTTRACE CV</h1>
      <h2 class="brand-subtitle">Computer Vision Integrity Assurance</h2>
    </div>
    <div class="header-right">
      <div class="status-badge"><span class="dot green" id="backend-status-dot"></span> <span id="backend-status-text">Backend Connected</span></div>
      <div class="status-badge"><span class="dot yellow"></span> Offline Mode: ACTIVE</div>
      <div class="status-badge">Status: <span id="topbar-status">Idle</span></div>
      <button class="btn btn-outline" id="btn-export-json">Export Report</button>
    </div>
  </header>

  <!-- TABS -->
  <nav class="app-tabs">
    <button class="tab-btn active" data-target="dataset">DATASET AUDIT</button>
    <button class="tab-btn" data-target="model">MODEL INTEGRITY</button>
    <button class="tab-btn" data-target="inference">INFERENCE PROVENANCE</button>
    <button class="tab-btn" data-target="report">ASSURANCE REPORT</button>
    <button class="tab-btn" data-target="system">SYSTEM STATUS</button>
  </nav>

  <!-- WORKSPACE -->
  <main class="app-workspace">
    <!-- DATASET AUDIT TAB -->
    <section id="tab-dataset" class="tab-panel active">
      <div class="panel-col left-col">
        <div class="panel-heading">IMAGE INSPECTION</div>
        <div class="panel-body flex-col">
          <!-- Upload Bar -->
          <div class="upload-bar">
             <input type="file" id="ds-file-input" accept=".zip" hidden>
             <button class="btn btn-primary" onclick="document.getElementById('ds-file-input').click()">Browse Dataset ZIP</button>
             <div id="ds-upload-meta" hidden class="meta-info">
               <span id="topbar-ds-name" class="font-medium"></span>
               <span id="ds-meta-filename" class="text-gray text-sm ml-2"></span>
               <select id="ds-meta-format" class="input-select-sm ml-auto">
                 <option value="yolo">YOLO (Auto-detected)</option>
                 <option value="coco">COCO (Override)</option>
               </select>
             </div>
          </div>
          
          <div class="viewer-header mt-4">
            <span id="viewer-filename" class="font-mono font-medium">No Image Selected</span>
            <div class="viewer-legend">
              <span class="legend-item"><span class="legend-color gt"></span> Ground Truth</span>
              <span class="legend-item"><span class="legend-color pred"></span> Prediction</span>
            </div>
          </div>
          <div class="viewer-container" id="bbox-viewer">
            <!-- image injected here -->
          </div>
          
          <!-- Sample Explorer -->
          <div class="explorer-header mt-2">
            <input type="text" class="input-text-sm" placeholder="Search filename..." id="search-explorer" style="flex: 1;">
            <select class="input-select-sm" id="filter-explorer">
              <option value="all">All Samples</option>
              <option value="flagged">Flagged Only</option>
            </select>
          </div>
          <div class="thumbnail-strip" id="thumbnail-strip"></div>
        </div>
      </div>
      
      <div class="panel-col right-col">
        <div class="panel-heading">VALIDATION AND EVIDENCE</div>
        <div class="panel-body scrollable">
          <div id="ds-progress-area" hidden>
             <div id="ds-audit-live-status" class="text-sm font-medium" style="color: var(--primary)">Initializing audit...</div>
          </div>
          <div id="ds-results-area" hidden>
             
             <!-- Dataset Summary -->
             <div class="summary-stats">
               <div class="stat"><div class="s-label">Images</div><div class="s-val" id="ds-sum-images">—</div></div>
               <div class="stat"><div class="s-label">Annotations</div><div class="s-val" id="ds-sum-anns">—</div></div>
               <div class="stat"><div class="s-label">Format</div><div class="s-val" id="ds-sum-format">—</div></div>
               <div class="stat"><div class="s-label">Status</div><div class="s-val" id="ds-sum-status">—</div></div>
             </div>
             
             <!-- Metadata -->
             <div class="section-title mt-4">Current Image Metadata</div>
             <div class="meta-grid text-sm">
               <div>ID: <span id="dt-id" class="font-mono">—</span></div>
               <div>Res: <span id="dt-res">—</span></div>
               <div style="grid-column: 1 / -1">SHA256: <span id="dt-sha" class="font-mono">—</span></div>
               <div id="ds-sum-hash" hidden></div>
             </div>
             
             <!-- Object Table -->
             <div class="section-title mt-4">Object Annotations</div>
             <div class="table-wrap">
               <table class="data-table">
                 <thead><tr><th>Class</th><th>Conf</th><th>X</th><th>Y</th><th>W</th><th>H</th><th>Src</th></tr></thead>
                 <tbody id="dt-objects-tbody"></tbody>
               </table>
             </div>
             
             <!-- Findings -->
             <div class="section-title mt-4">Integrity Findings</div>
             <div id="ds-findings-summary" class="mb-2 text-sm"></div>
             <div class="table-wrap">
               <table class="data-table">
                 <thead><tr><th>Sev</th><th>Finding</th><th>Affected</th><th>Method</th><th>Conf</th><th>Action</th></tr></thead>
                 <tbody id="ds-findings-tbody"></tbody>
               </table>
             </div>

             <!-- Evidence -->
             <div class="section-title mt-4">Evidence Log</div>
             <div class="table-wrap">
               <table class="data-table">
                 <thead><tr><th>ID</th><th>Category</th><th>Observations</th></tr></thead>
                 <tbody id="ds-evidence-tbody"></tbody>
               </table>
             </div>
          </div>
        </div>
      </div>
    </section>

    <!-- placeholders for other tabs -->
    <section id="tab-model" class="tab-panel">
       <div class="panel-col left-col"><div class="panel-heading">MODEL IDENTITY</div><div class="panel-body scrollable text-gray">Not implemented in this prototype.</div></div>
       <div class="panel-col right-col"><div class="panel-heading">MODEL BEHAVIOR & INTEGRITY</div><div class="panel-body scrollable text-gray">Not implemented in this prototype.</div></div>
    </section>
    <section id="tab-inference" class="tab-panel">
       <div class="panel-col left-col"><div class="panel-heading">INFERENCE RECORD</div><div class="panel-body scrollable text-gray">Not implemented in this prototype.</div></div>
       <div class="panel-col right-col"><div class="panel-heading">PROVENANCE VERIFICATION</div><div class="panel-body scrollable text-gray">Not implemented in this prototype.</div></div>
    </section>
    <section id="tab-report" class="tab-panel">
       <div class="panel-col left-col"><div class="panel-heading">OVERALL ASSESSMENT</div><div class="panel-body scrollable text-gray">Not implemented in this prototype.</div></div>
       <div class="panel-col right-col"><div class="panel-heading">DETAILED FINDINGS</div><div class="panel-body scrollable text-gray">Not implemented in this prototype.</div></div>
    </section>
    <section id="tab-system" class="tab-panel">
       <div class="panel-col left-col"><div class="panel-heading">SYSTEM HEALTH</div><div class="panel-body scrollable text-gray">Not implemented in this prototype.</div></div>
       <div class="panel-col right-col"><div class="panel-heading">CAPABILITIES</div><div class="panel-body scrollable text-gray">Not implemented in this prototype.</div></div>
    </section>
    
    <div class="drawer-overlay" id="drawer-overlay"></div>
    <div class="evidence-drawer" id="evidence-drawer">
      <div class="drawer-header">
        <h3>Finding Details</h3>
        <button class="icon-btn" id="drawer-close">✕</button>
      </div>
      <div class="drawer-content" id="drawer-content"></div>
    </div>
  </main>

  <!-- BOTTOM ACTION BAR -->
  <footer class="app-footer">
    <div class="footer-left text-sm text-gray" id="footer-status">Ready.</div>
    <div class="footer-right">
      <button class="btn btn-primary" id="btn-start-audit">RUN DATASET AUDIT</button>
      <button class="btn btn-secondary text-gray" style="cursor:not-allowed">RUN FULL ASSURANCE AUDIT</button>
    </div>
  </footer>
  
  <script src="/static/app.js"></script>
</body>
</html>
"""

STYLE_CSS = """
:root {
  --bg-main: #f8fafc;
  --bg-panel: #ffffff;
  --bg-header: #0f172a;
  --bg-footer: #ffffff;
  
  --text-main: #1e293b;
  --text-gray: #64748b;
  --text-light: #f8fafc;
  
  --border-color: #e2e8f0;
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  
  --color-pass: #10b981;
  --color-fail: #ef4444;
  --color-review: #f59e0b;
  
  --font-sans: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-sans);
  background: var(--bg-main);
  color: var(--text-main);
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  font-size: 14px;
}

/* HEADER */
.app-header {
  height: 50px;
  background: var(--bg-header);
  color: var(--text-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 1.5rem;
  flex-shrink: 0;
}
.header-left { display: flex; align-items: baseline; gap: 1rem; }
.brand-title { font-size: 1.1rem; font-weight: 700; letter-spacing: 0.05em; }
.brand-subtitle { font-size: 0.8rem; color: #94a3b8; font-weight: 400; text-transform: uppercase; }

.header-right { display: flex; align-items: center; gap: 1.5rem; font-size: 0.8rem; }
.status-badge { display: flex; align-items: center; gap: 0.4rem; color: #cbd5e1; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.green { background: var(--color-pass); }
.dot.yellow { background: var(--color-review); }

/* TABS */
.app-tabs {
  height: 40px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  padding: 0 1rem;
  flex-shrink: 0;
}
.tab-btn {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 0 1rem;
  font-family: var(--font-sans);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-gray);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: all 0.2s;
}
.tab-btn:hover { color: var(--text-main); }
.tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); }

/* WORKSPACE */
.app-workspace {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
  padding: 1rem;
}

.tab-panel {
  flex: 1;
  display: none;
  gap: 1rem;
}
.tab-panel.active { display: flex; }

.panel-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  min-width: 0;
  overflow: hidden;
}
.panel-heading {
  background: #f1f5f9;
  padding: 0.6rem 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-gray);
  border-bottom: 1px solid var(--border-color);
  text-transform: uppercase;
  flex-shrink: 0;
}
.panel-body {
  flex: 1;
  padding: 1rem;
  min-height: 0;
}
.panel-body.scrollable { overflow-y: auto; }
.panel-body.flex-col { display: flex; flex-direction: column; }

/* FOOTER */
.app-footer {
  height: 60px;
  background: var(--bg-footer);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 1.5rem;
  flex-shrink: 0;
}
.footer-right { display: flex; gap: 1rem; }

/* UTILS */
.btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  font-family: var(--font-sans);
}
.btn-primary { background: var(--primary); color: white; }
.btn-primary:hover { background: var(--primary-hover); }
.btn-secondary { background: #e2e8f0; color: var(--text-gray); }
.btn-outline { background: transparent; border-color: var(--border-color); color: var(--text-main); }
.text-sm { font-size: 0.8rem; }
.text-gray { color: var(--text-gray); }
.font-mono { font-family: var(--font-mono); }
.font-medium { font-weight: 500; }
.ml-2 { margin-left: 0.5rem; }
.ml-auto { margin-left: auto; }
.mt-2 { margin-top: 0.5rem; }
.mt-4 { margin-top: 1rem; }
.mb-2 { margin-bottom: 0.5rem; }
.flex-row { display: flex; align-items: center; gap: 0.5rem; }
.truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.block { display: block; }

/* DATASET COMPONENTS */
.upload-bar { display: flex; align-items: center; gap: 1rem; padding: 0.75rem; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; flex-shrink: 0; }
.meta-info { flex: 1; display: flex; align-items: center; }
.input-select-sm, .input-text-sm { padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 4px; font-size: 0.8rem; font-family: var(--font-sans); }

.viewer-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 0.5rem; flex-shrink: 0; }
.viewer-legend { display: flex; gap: 1rem; font-size: 0.75rem; color: var(--text-gray); }
.legend-item { display: flex; align-items: center; gap: 0.25rem; }
.legend-color { width: 10px; height: 10px; border-radius: 2px; }
.legend-color.gt { background: var(--color-pass); }
.legend-color.pred { background: #8b5cf6; }

.viewer-container {
  flex: 1;
  background: #f1f5f9;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  min-height: 0;
}
.viewer-img { max-width: 100%; max-height: 100%; object-fit: contain; }
.bbox-overlay { position: absolute; pointer-events: none; box-sizing: border-box; }
.bbox-label { position: absolute; top: -16px; left: -2px; color: white; font-size: 9px; padding: 1px 4px; white-space: nowrap; font-family: var(--font-mono); font-weight: 600; border-radius: 2px; }
.bbox-overlay.gt { border: 2px solid var(--color-pass); }
.bbox-overlay.gt .bbox-label { background: var(--color-pass); }

.explorer-header { display: flex; gap: 0.5rem; flex-shrink: 0; }
.thumbnail-strip { display: flex; gap: 0.5rem; overflow-x: auto; padding-top: 0.5rem; flex-shrink: 0; }
.thumb { width: 60px; height: 60px; object-fit: cover; border-radius: 4px; cursor: pointer; border: 2px solid transparent; opacity: 0.6; }
.thumb:hover { opacity: 1; }
.thumb.active { border-color: var(--primary); opacity: 1; }
.thumb.flagged { border-color: var(--color-fail); }

.summary-stats { display: flex; gap: 1rem; }
.stat { flex: 1; background: #f8fafc; padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-color); }
.s-label { font-size: 0.7rem; color: var(--text-gray); text-transform: uppercase; font-weight: 600; }
.s-val { font-size: 1.1rem; font-weight: 600; margin-top: 0.25rem; font-family: var(--font-mono); }

.section-title { font-size: 0.75rem; font-weight: 600; color: var(--text-gray); text-transform: uppercase; border-bottom: 1px solid var(--border-color); padding-bottom: 0.25rem; margin-bottom: 0.5rem; }
.meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }

.table-wrap { overflow-x: auto; border: 1px solid var(--border-color); border-radius: 4px; }
.data-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.8rem; }
.data-table th, .data-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border-color); }
.data-table th { background: #f8fafc; font-weight: 600; color: var(--text-gray); white-space: nowrap; }
.data-table tbody tr:last-child td { border-bottom: none; }

.badge { padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
.badge.pass { background: #d1fae5; color: #065f46; }
.badge.fail { background: #fee2e2; color: #991b1b; }
.badge.review { background: #fef3c7; color: #92400e; }
.badge.default { background: #f1f5f9; color: #475569; }

/* DRAWER */
.drawer-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 40; display: none; }
.drawer-overlay.open { display: block; }
.evidence-drawer { position: fixed; top: 0; right: 0; bottom: 0; width: 400px; background: white; box-shadow: -4px 0 15px rgba(0,0,0,0.1); z-index: 50; transform: translateX(100%); transition: transform 0.2s; display: flex; flex-direction: column; }
.evidence-drawer.open { transform: translateX(0); }
.drawer-header { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
.drawer-content { padding: 1.5rem; overflow-y: auto; flex: 1; }
.icon-btn { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: var(--text-gray); }
"""

def rewrite():
    with open("src/ui/index.html", "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)
    with open("src/ui/style.css", "w", encoding="utf-8") as f:
        f.write(STYLE_CSS)

    # Now modify app.js to attach the tab switching logic
    with open("src/ui/app.js", "r", encoding="utf-8") as f:
        app_js = f.read()
    
    # Remove old sidebar logic
    import re
    app_js = re.sub(r"document\.querySelectorAll\('\.sidebar-nav \.nav-item'\).*?\}\);", "", app_js, flags=re.DOTALL)
    
    # Add new tab logic
    tab_logic = """
document.querySelectorAll('.app-tabs .tab-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    document.querySelectorAll('.app-tabs .tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.app-workspace .tab-panel').forEach(p => p.classList.remove('active'));
    e.target.classList.add('active');
    document.getElementById('tab-' + e.target.dataset.target).classList.add('active');
  });
});
"""
    app_js = tab_logic + "\n" + app_js
    
    with open("src/ui/app.js", "w", encoding="utf-8") as f:
        f.write(app_js)

if __name__ == "__main__":
    rewrite()
    print("UI rewrite completed successfully.")
