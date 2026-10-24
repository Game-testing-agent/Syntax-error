/**
 * Syntax-Error QA Explorer & Bot Control Dashboard
 * Main Application Logic
 */

let terminal;
let selectedMapId = 0; // 0 = Default Map (Original Game), 1-4 = Benchmark Maps
let currentOffset = 0;
let processPollTimer = null;
let ws = null;
let allPaths = [];
let allMaps = [];

// Waypoint list for W1 / W2
let sequentialWaypoints = [
  { x: 1500, y: 700 },
  { x: 3117, y: 560 }
];

document.addEventListener("DOMContentLoaded", () => {
  terminal = new TerminalViewer("terminal-output");

  setupNavigation();
  setupGlobalControls();
  setupWaypointBuilder();
  setupExplorerModeChange();
  initWebSocket();

  // Initial data fetch
  refreshAllData();

  // Poll process status every 1.5s
  processPollTimer = setInterval(pollProcessStatus, 1500);
});

// ----------------------------------------------------------------------------
// Navigation
// ----------------------------------------------------------------------------
function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const tabId = item.getAttribute("data-tab");
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));

  const targetNav = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
  const targetPane = document.getElementById(`tab-${tabId}`);

  if (targetNav) targetNav.classList.add("active");
  if (targetPane) targetPane.classList.add("active");
}

// ----------------------------------------------------------------------------
// Global Map & Header Controls
// ----------------------------------------------------------------------------
function setupGlobalControls() {
  const mapSelect = document.getElementById("global-map-select");
  if (mapSelect) {
    mapSelect.addEventListener("change", (e) => {
      selectedMapId = parseInt(e.target.value, 10);
      syncSelectedMapUI();
    });
  }

  const refreshBtn = document.getElementById("refresh-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      refreshAllData();
      showNotification("Data refreshed from disk");
    });
  }

  const stopBtn = document.getElementById("stop-process-btn");
  if (stopBtn) {
    stopBtn.addEventListener("click", stopActiveProcess);
  }

  // Terminal toolbar buttons
  const termClearBtn = document.getElementById("term-clear-btn");
  if (termClearBtn) termClearBtn.addEventListener("click", () => terminal.clear());

  const termCopyBtn = document.getElementById("term-copy-btn");
  if (termCopyBtn) termCopyBtn.addEventListener("click", () => {
    terminal.copy();
    showNotification("Terminal logs copied to clipboard");
  });

  const termDownloadBtn = document.getElementById("term-download-btn");
  if (termDownloadBtn) termDownloadBtn.addEventListener("click", () => terminal.download());

  // QA Run Button
  const runQaBtn = document.getElementById("run-qa-eval-btn");
  if (runQaBtn) {
    runQaBtn.addEventListener("click", runQaEvaluator);
  }
}

function syncSelectedMapUI() {
  // Update header selector
  const mapSelect = document.getElementById("global-map-select");
  if (mapSelect) mapSelect.value = selectedMapId;

  // Update map cards highlight in Run Game tab
  document.querySelectorAll(".map-card").forEach(card => {
    const cardId = parseInt(card.getAttribute("data-map-id"), 10);
    if (cardId === selectedMapId) {
      card.classList.add("selected");
    } else {
      card.classList.remove("selected");
    }
  });

  // Update explorer level/map selector
  const expMapSelect = document.getElementById("exp-map-select");
  if (expMapSelect) expMapSelect.value = selectedMapId;
}

// ----------------------------------------------------------------------------
// Dynamic Waypoint Builder (W1 and W2)
// ----------------------------------------------------------------------------
function setupWaypointBuilder() {
  renderWaypointsTable();

  const addBtn = document.getElementById("wp-add-btn");
  if (addBtn) {
    addBtn.addEventListener("click", () => {
      // Default coordinate near previous or start
      const last = sequentialWaypoints[sequentialWaypoints.length - 1] || { x: 1000, y: 700 };
      sequentialWaypoints.push({ x: last.x + 500, y: last.y });
      renderWaypointsTable();
    });
  }

  const clearBtn = document.getElementById("wp-clear-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      sequentialWaypoints = [];
      renderWaypointsTable();
    });
  }

  // Preset chips
  document.querySelectorAll(".wp-preset-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const presetType = chip.getAttribute("data-preset");
      loadWaypointPreset(presetType);
    });
  });
}

function renderWaypointsTable() {
  const tbody = document.getElementById("waypoints-tbody");
  const countEl = document.getElementById("wp-count-display");
  if (!tbody) return;

  tbody.innerHTML = "";
  if (countEl) countEl.innerText = sequentialWaypoints.length;

  if (sequentialWaypoints.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:var(--text-dim);padding:14px;">No waypoints added yet. Click "+ Add Waypoint" or choose a preset.</td></tr>`;
    return;
  }

  sequentialWaypoints.forEach((wp, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>#${idx + 1}</td>
      <td>
        <input type="number" class="coord-input wp-x-input" data-index="${idx}" value="${wp.x}" step="10"> px
      </td>
      <td>
        <input type="number" class="coord-input wp-y-input" data-index="${idx}" value="${wp.y}" step="10"> px
      </td>
      <td>
        <button class="coord-remove-btn" data-index="${idx}" title="Remove waypoint">&times;</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Attach change listeners
  tbody.querySelectorAll(".wp-x-input").forEach(input => {
    input.addEventListener("change", (e) => {
      const idx = parseInt(e.target.getAttribute("data-index"), 10);
      sequentialWaypoints[idx].x = parseFloat(e.target.value) || 0;
    });
  });

  tbody.querySelectorAll(".wp-y-input").forEach(input => {
    input.addEventListener("change", (e) => {
      const idx = parseInt(e.target.getAttribute("data-index"), 10);
      sequentialWaypoints[idx].y = parseFloat(e.target.value) || 0;
    });
  });

  tbody.querySelectorAll(".coord-remove-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const idx = parseInt(e.target.getAttribute("data-index"), 10);
      sequentialWaypoints.splice(idx, 1);
      renderWaypointsTable();
    });
  });
}

function loadWaypointPreset(presetType) {
  if (presetType === "level1_intro") {
    sequentialWaypoints = [
      { x: 850, y: 750 },
      { x: 1500, y: 700 },
      { x: 3117, y: 560 }
    ];
  } else if (presetType === "level1_full") {
    sequentialWaypoints = [
      { x: 850, y: 750 },
      { x: 2100, y: 640 },
      { x: 3117, y: 560 },
      { x: 4300, y: 560 },
      { x: 5778, y: 480 },
      { x: 7342, y: 160 }
    ];
  } else if (presetType === "map3_sky") {
    sequentialWaypoints = [
      { x: 5440, y: 560 },
      { x: 7040, y: 560 },
      { x: 14638, y: 800 }
    ];
  } else if (presetType === "bug_hunt") {
    sequentialWaypoints = [
      { x: 2320, y: 800 }, // Floor void gap
      { x: 3040, y: 560 }, // Enemy4 collision
      { x: 3360, y: 480 }  // 7th coin pickup
    ];
  }
  renderWaypointsTable();
  showNotification(`Loaded preset: ${presetType}`);
}

// ----------------------------------------------------------------------------
// Explorer Mode Change (Dynamic Fields Toggle)
// ----------------------------------------------------------------------------
function setupExplorerModeChange() {
  const modeSelect = document.getElementById("exp-mode-select");
  if (!modeSelect) return;

  const updateModeFields = () => {
    const mode = modeSelect.value;

    const waypointPanel = document.getElementById("exp-waypoint-config");
    const targetCoordPanel = document.getElementById("exp-target-coord-config");
    const scriptedPanel = document.getElementById("exp-scripted-config");
    const seedPanel = document.getElementById("exp-seed-config");

    // Waypoints mode W1 & W2
    if (mode === "waypoints_sequential" || mode === "waypoints_interactive") {
      waypointPanel.style.display = "block";
      const isSequential = mode === "waypoints_sequential";
      document.getElementById("wp-sequential-details").style.display = isSequential ? "block" : "none";
      document.getElementById("wp-mode-badge").innerText = isSequential ? "W2: Sequential Mode" : "W1: Interactive Mode";
    } else {
      waypointPanel.style.display = "none";
    }

    // Target coordinate mode
    targetCoordPanel.style.display = (mode === "target_coord") ? "block" : "none";

    // Scripted mode
    scriptedPanel.style.display = (mode === "scripted") ? "block" : "none";

    // Seeded modes
    seedPanel.style.display = (mode === "random" || mode === "hybrid_variation") ? "block" : "none";
  };

  modeSelect.addEventListener("change", updateModeFields);
  updateModeFields();
}

// ----------------------------------------------------------------------------
// WebSocket & Live Logs
// ----------------------------------------------------------------------------
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("[WS] Connected to live log stream");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "log" && data.line) {
          terminal.append(data.line);
        }
      } catch (e) {
        terminal.append(event.data);
      }
    };

    ws.onclose = () => {
      // Reconnect after 3s if lost
      setTimeout(initWebSocket, 3000);
    };

    ws.onerror = (err) => {
      console.warn("[WS] Socket error, falling back to polling", err);
    };
  } catch (err) {
    console.error("Failed to initialize WebSocket:", err);
  }
}

// Fallback polling for process status & logs if WS is unavailable
async function pollProcessStatus() {
  try {
    const res = await fetch("/api/process/status");
    if (!res.ok) return;
    const st = await res.json();

    const dot = document.getElementById("status-dot");
    const text = document.getElementById("status-text");
    const stopBtn = document.getElementById("stop-process-btn");

    if (dot && text) {
      dot.className = `status-dot ${st.status}`;
      if (st.status === "running") {
        text.innerText = `RUNNING (${st.workflow}) - ${st.elapsed_sec}s`;
        if (stopBtn) stopBtn.style.display = "flex";
      } else if (st.status === "completed") {
        text.innerText = `IDLE (Finished ${st.workflow})`;
        if (stopBtn) stopBtn.style.display = "none";
      } else if (st.status === "failed") {
        text.innerText = `ERROR (Code ${st.exit_code})`;
        if (stopBtn) stopBtn.style.display = "none";
      } else if (st.status === "stopped") {
        text.innerText = `STOPPED`;
        if (stopBtn) stopBtn.style.display = "none";
      } else {
        text.innerText = "READY / IDLE";
        if (stopBtn) stopBtn.style.display = "none";
      }
    }

    // Incremental log poll if ws isn't open
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      const logsRes = await fetch(`/api/process/logs?offset=${currentOffset}`);
      if (logsRes.ok) {
        const logData = await logsRes.json();
        if (logData.lines && logData.lines.length > 0) {
          logData.lines.forEach(l => terminal.append(l));
          currentOffset = logData.offset;
        }
      }
    }
  } catch (e) {
    console.warn("Poll status error:", e);
  }
}

async function stopActiveProcess() {
  try {
    const res = await fetch("/api/process/stop", { method: "POST" });
    const data = await res.json();
    showNotification("Process termination requested");
    pollProcessStatus();
  } catch (e) {
    showNotification("Failed to stop process: " + e.message, true);
  }
}

// ----------------------------------------------------------------------------
// API Fetchers & UI Renderers
// ----------------------------------------------------------------------------
async function refreshAllData() {
  await Promise.all([
    fetchOverview(),
    fetchMaps(),
    fetchPaths(),
    fetchTelemetry()
  ]);
}

async function fetchOverview() {
  try {
    const res = await fetch("/api/overview");
    if (!res.ok) throw new Error("Failed to load overview");
    const data = await res.json();

    // Stats KPIs
    document.getElementById("kpi-total-bugs").innerText = data.stats.total_bugs_detected;
    document.getElementById("kpi-critical-bugs").innerText = data.stats.critical_bugs;
    document.getElementById("kpi-high-bugs").innerText = data.stats.high_bugs;
    document.getElementById("kpi-covered-benchmark").innerText = `${data.stats.benchmark_bugs_covered}/${data.stats.benchmark_bugs_total}`;
    document.getElementById("kpi-events-count").innerText = data.stats.telemetry_events_logged;
    document.getElementById("kpi-agentic-runs").innerText = data.stats.agentic_test_runs;

    // Discovered Bugs Table
    renderBugsTable(data.findings);

    // Benchmark Checklist
    renderBenchmarkChecklist(data.benchmark_bugs);

    // Recent Agentic Runs
    renderAgenticRuns(data.recent_agentic_runs);

  } catch (err) {
    console.error("fetchOverview error:", err);
  }
}

function renderBugsTable(findings) {
  const tbody = document.getElementById("bugs-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!findings || findings.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:16px;color:var(--text-dim);">No findings recorded yet. Run Agent Explorer or QA Auditor.</td></tr>`;
    return;
  }

  findings.forEach((f, idx) => {
    const tr = document.createElement("tr");
    const sevClass = (f.severity || "medium").toLowerCase();
    const confPct = Math.round((f.confidence || 0) * 100);
    const frames = (f.evidence_frames || []).join(", ") || "N/A";
    const pathLabel = (f.path || "path1").toUpperCase();

    tr.innerHTML = `
      <td>#${idx + 1}</td>
      <td><span class="severity-pill ${sevClass}">${f.severity || "UNKNOWN"}</span></td>
      <td style="font-weight:600;color:#fff;">${escapeHtml(f.title || "Anomaly")}</td>
      <td><span class="path-badge">${pathLabel}</span></td>
      <td>
        <div style="display:flex;align-items:center;gap:6px;">
          <div style="background:#1e293b;border-radius:3px;height:6px;width:50px;overflow:hidden;">
            <div style="background:var(--accent-cyan);height:100%;width:${confPct}%;"></div>
          </div>
          <span style="font-size:11px;font-family:var(--font-mono);">${confPct}%</span>
        </div>
      </td>
      <td style="font-family:var(--font-mono);color:var(--text-muted);font-size:11.5px;">${escapeHtml(f.suspected_code || "N/A")}</td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="showFindingModal(${idx})">Inspect</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Store globally for modal inspection
  window.currentFindings = findings;
}

function showFindingModal(idx) {
  const f = window.currentFindings[idx];
  if (!f) return;

  const modal = document.getElementById("finding-modal");
  document.getElementById("modal-finding-title").innerText = f.title || "Bug Details";
  document.getElementById("modal-finding-sev").className = `severity-pill ${(f.severity || "medium").toLowerCase()}`;
  document.getElementById("modal-finding-sev").innerText = f.severity || "UNKNOWN";
  document.getElementById("modal-finding-path").innerText = `Mechanism: ${(f.path || "path1").toUpperCase()}`;
  document.getElementById("modal-finding-code").innerText = f.suspected_code || "N/A";
  document.getElementById("modal-finding-frames").innerText = (f.evidence_frames || []).join(", ") || "None";
  document.getElementById("modal-finding-expl").innerText = f.explanation || "No explanation provided.";
  document.getElementById("modal-finding-source").innerText = f.source_file || "Game_QA";

  modal.classList.add("show");
}

function closeFindingModal() {
  document.getElementById("finding-modal").classList.remove("show");
}

function renderBenchmarkChecklist(benchmarks) {
  const container = document.getElementById("benchmark-checklist-container");
  if (!container) return;
  container.innerHTML = "";

  benchmarks.forEach(b => {
    const card = document.createElement("div");
    card.className = "card";
    card.style.padding = "12px 16px";
    card.style.marginBottom = "8px";
    card.style.borderLeft = b.detected ? "4px solid var(--accent-green)" : "4px solid rgba(255,255,255,0.1)";

    const statusBadge = b.detected
      ? `<span class="severity-pill" style="background:rgba(16,185,129,0.2);color:#6ee7b7;border:1px solid rgba(16,185,129,0.4)">VERIFIED BUG</span>`
      : `<span class="severity-pill low">BENCHMARK GROUND TRUTH</span>`;

    card.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-family:var(--font-mono);font-weight:700;color:var(--accent-cyan);">[${b.id}]</span>
          <span style="font-weight:600;color:#fff;">${escapeHtml(b.description)}</span>
        </div>
        ${statusBadge}
      </div>
      <div style="font-size:11.5px;color:var(--text-muted);display:flex;gap:16px;">
        <span><strong>Map:</strong> ${escapeHtml(b.map)}</span>
        <span><strong>Coords:</strong> <code style="color:var(--accent-cyan);">${escapeHtml(b.coords)}</code></span>
        <span><strong>Log Tag:</strong> <code>${escapeHtml(b.identifier)}</code></span>
      </div>
      <div style="margin-top:6px;font-size:11.5px;color:var(--text-dim);">
        <span style="color:#fca5a5;">Actual:</span> ${escapeHtml(b.actual)}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderAgenticRuns(runs) {
  const container = document.getElementById("agentic-runs-container");
  if (!container) return;
  container.innerHTML = "";

  if (!runs || runs.length === 0) {
    container.innerHTML = `<div style="color:var(--text-dim);font-size:12px;">No agentic runs recorded yet.</div>`;
    return;
  }

  runs.forEach(r => {
    const el = document.createElement("div");
    el.style.background = "var(--bg-input)";
    el.style.border = "1px solid var(--border-color)";
    el.style.borderRadius = "var(--radius-sm)";
    el.style.padding = "10px 14px";
    el.style.marginBottom = "8px";

    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-family:var(--font-mono);font-size:12px;font-weight:600;color:var(--accent-cyan);">${escapeHtml(r.run_id)}</span>
        <span style="font-size:11px;color:var(--text-dim);">${r.start_time ? new Date(r.start_time).toLocaleString() : ""}</span>
      </div>
      <div style="margin-top:6px;font-size:12px;display:flex;gap:14px;">
        <span>Total Cases: <strong>${r.total_cases}</strong></span>
        <span style="color:var(--accent-green);">Reached: <strong>${r.success_cases}</strong></span>
        <span style="color:var(--accent-yellow);">Budget Exhausted: <strong>${r.budget_cases}</strong></span>
        <span style="color:var(--accent-red);">Deaths: <strong>${r.death_cases}</strong></span>
      </div>
    `;
    container.appendChild(el);
  });
}

async function fetchMaps() {
  try {
    const res = await fetch("/api/maps");
    if (!res.ok) return;
    const data = await res.json();
    allMaps = data.maps || [];

    // Populate header selector
    const headerSelect = document.getElementById("global-map-select");
    const expMapSelect = document.getElementById("exp-map-select");

    [headerSelect, expMapSelect].forEach(sel => {
      if (!sel) return;
      sel.innerHTML = "";
      allMaps.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m.id;
        opt.innerText = m.title;
        if (m.id === selectedMapId) opt.selected = true;
        sel.appendChild(opt);
      });
    });

    // Render Map Cards in Run Game tab
    renderMapCards(allMaps);

  } catch (err) {
    console.error("fetchMaps error:", err);
  }
}

function renderMapCards(maps) {
  const container = document.getElementById("maps-grid-container");
  if (!container) return;
  container.innerHTML = "";

  maps.forEach(m => {
    const card = document.createElement("div");
    card.className = `map-card ${m.id === selectedMapId ? "selected" : ""}`;
    card.setAttribute("data-map-id", m.id);

    const isDefault = (m.id === 0);
    const mapBadgeClass = "map-badge";
    const mapNumLabel = isDefault ? "Default Map" : `Benchmark Map #${m.id}`;
    const runBtnText = isDefault ? "Run Default Game" : `Run Map ${m.id}`;

    let bugsSection = "";
    if (isDefault) {
      bugsSection = `
        <div class="map-bugs-list">
          <div class="map-bugs-title">Campaign Scope</div>
          <div><span class="map-bug-tag" style="background:rgba(56,189,248,0.2);color:#7dd3fc;border-color:rgba(56,189,248,0.3);">Baseline Level01 + Level02</span> <span class="map-bug-tag" style="background:rgba(16,185,129,0.2);color:#6ee7b7;border-color:rgba(16,185,129,0.3);">MainScreen Launcher</span></div>
        </div>
      `;
    } else {
      const bugTags = (m.benchmark_bugs || []).map(b => 
        `<span class="map-bug-tag" title="${escapeHtml(b.description)}">[${b.id}] ${escapeHtml(b.id)}</span>`
      ).join("");
      bugsSection = `
        <div class="map-bugs-list">
          <div class="map-bugs-title">Documented Benchmark Bugs (${m.benchmark_bugs.length})</div>
          <div>${bugTags || "<span style='color:var(--text-dim);font-size:10.5px;'>None</span>"}</div>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="map-header">
        <span class="${mapBadgeClass}" ${isDefault ? 'style="background:rgba(245,158,11,0.2);color:#fcd34d;border:1px solid rgba(245,158,11,0.4);"' : ''}>${m.difficulty}</span>
        <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-dim);">${mapNumLabel}</span>
      </div>
      <h3 class="map-title">${escapeHtml(m.title)}</h3>
      <p class="map-desc">${escapeHtml(m.description)}</p>
      
      ${bugsSection}

      <div class="map-meta">
        <span>Target: (${m.target_coord ? m.target_coord.join(", ") : "None"})</span>
        <span>${m.slug}</span>
      </div>

      <div style="display:flex;gap:8px;margin-top:auto;">
        <button class="btn btn-secondary btn-sm" style="flex:1;" onclick="selectMap(${m.id})">
          ${m.id === selectedMapId ? "Selected" : "Select Map"}
        </button>
        <button class="btn btn-sm" style="flex:1;" onclick="launchMapDirectly(${m.id})">
          ${runBtnText}
        </button>
      </div>
    `;

    card.addEventListener("click", (e) => {
      if (e.target.tagName !== "BUTTON") {
        selectMap(m.id);
      }
    });

    container.appendChild(card);
  });
}

function selectMap(mapId) {
  selectedMapId = mapId;
  syncSelectedMapUI();
  showNotification(`Active Map changed to Map ${mapId}`);
}

async function fetchPaths() {
  try {
    const res = await fetch("/api/paths");
    if (!res.ok) return;
    const data = await res.json();
    allPaths = data.paths || [];

    const select = document.getElementById("exp-scripted-path-select");
    if (select) {
      select.innerHTML = "";
      allPaths.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.relative_path;
        opt.innerText = `${p.name} (${p.steps_count} steps) - ${p.description}`;
        select.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("fetchPaths error:", err);
  }
}

async function fetchTelemetry() {
  try {
    const res = await fetch("/api/telemetry/events?limit=25");
    if (!res.ok) return;
    const data = await res.json();
    const tbody = document.getElementById("telemetry-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    (data.events || []).forEach(ev => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-family:var(--font-mono);">${ev.event_id || "-"}</td>
        <td><span class="path-badge" style="background:rgba(56,189,248,0.15);color:var(--accent-cyan);border-color:rgba(56,189,248,0.3);">${ev.category || "general"}</span></td>
        <td style="font-weight:600;color:#fff;">${ev.event_name || "-"}</td>
        <td style="font-family:var(--font-mono);">${ev.physics_frame || "-"}</td>
        <td style="font-family:var(--font-mono);">${ev.elapsed_ms ? ev.elapsed_ms + "ms" : "-"}</td>
        <td style="font-size:11px;font-family:var(--font-mono);color:var(--text-muted);">${JSON.stringify(ev.data || {}).substring(0, 60)}...</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("fetchTelemetry error:", err);
  }
}

// ----------------------------------------------------------------------------
// Workflow Launch Handlers
// ----------------------------------------------------------------------------

// Workflow 1: Run Game
async function launchGameWorkflow() {
  const mode = document.getElementById("game-launch-mode").value;
  const withBot = document.getElementById("game-with-bot-checkbox").checked;
  const framesVal = document.getElementById("game-frames-input").value;
  const frames = framesVal ? parseInt(framesVal, 10) : null;

  const payload = {
    map_num: selectedMapId,
    mode: mode,
    frames: frames,
    with_bot: withBot
  };

  try {
    const res = await fetch("/api/execute/run-game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Launch failed");

    showNotification(`Game launched on Map ${selectedMapId}!`);
    switchTab("terminal");
    pollProcessStatus();
  } catch (err) {
    showNotification(err.message, true);
  }
}

async function launchMapDirectly(mapId) {
  selectMap(mapId);
  launchGameWorkflow();
}

// Workflow 2: Agent Explorer
async function launchAgentExplorerWorkflow() {
  const budget = parseInt(document.getElementById("agent-budget-input").value, 10) || 20;
  const strategy = document.getElementById("agent-strategy-select").value;
  const mode = document.getElementById("agent-mode-select").value;
  const maxSteps = parseInt(document.getElementById("agent-maxsteps-input").value, 10) || 350;
  const tolerance = parseFloat(document.getElementById("agent-tolerance-input").value) || 70.0;
  const launchWindow = document.getElementById("agent-launch-window-check").checked;
  const verbose = document.getElementById("agent-verbose-check").checked;

  const payload = {
    budget: budget,
    strategy: strategy,
    mode: mode,
    max_steps_per_target: maxSteps,
    tolerance: tolerance,
    launch: launchWindow,
    verbose: verbose
  };

  try {
    const res = await fetch("/api/execute/agent-explorer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Launch failed");

    showNotification(`Agent Explorer started (Budget: ${budget}, Strategy: ${strategy})`);
    switchTab("terminal");
    pollProcessStatus();
  } catch (err) {
    showNotification(err.message, true);
  }
}

// Workflow 3: Normal Explorer (run_explorer)
async function launchRunExplorerWorkflow() {
  const mode = document.getElementById("exp-mode-select").value;
  const maxActions = parseInt(document.getElementById("exp-maxactions-input").value, 10) || 350;
  const seed = parseInt(document.getElementById("exp-seed-input").value, 10) || 42;
  const port = parseInt(document.getElementById("exp-port-input").value, 10) || 4242;
  const launchWindow = document.getElementById("exp-launch-window-check").checked;
  const closeOnExit = document.getElementById("exp-close-exit-check").checked;
  const verbose = document.getElementById("exp-verbose-check").checked;
  const mapNum = parseInt(document.getElementById("exp-map-select").value, 10) || null;

  // Flatten coordinates for sequential waypoints
  const waypointsFlat = [];
  sequentialWaypoints.forEach(wp => {
    waypointsFlat.push(wp.x);
    waypointsFlat.push(wp.y);
  });

  const waypointWait = parseFloat(document.getElementById("wp-wait-input").value) || 3.0;
  const tolerance = parseFloat(document.getElementById("wp-tolerance-input").value) || 60.0;

  const targetX = parseFloat(document.getElementById("exp-target-x").value) || 3117.0;
  const targetY = parseFloat(document.getElementById("exp-target-y").value) || 560.0;
  const scriptedPath = document.getElementById("exp-scripted-path-select").value;

  const payload = {
    mode: mode,
    waypoints: waypointsFlat,
    waypoint_wait: waypointWait,
    tolerance: tolerance,
    target_coord: [targetX, targetY],
    path: scriptedPath,
    seed: seed,
    max_actions: maxActions,
    routes: "level_routes.json",
    port: port,
    fps: 60,
    map_num: mapNum,
    launch: launchWindow,
    close_on_exit: closeOnExit,
    verbose: verbose
  };

  try {
    const res = await fetch("/api/execute/run-explorer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Launch failed");

    showNotification(`Explorer launched: ${mode}`);
    switchTab("terminal");
    pollProcessStatus();
  } catch (err) {
    showNotification(err.message, true);
  }
}

// QA Auditor Workflow
async function runQaEvaluator() {
  try {
    const res = await fetch("/api/execute/run-qa-eval", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "QA audit failed");

    showNotification("Game_QA Evaluator started!");
    switchTab("terminal");
    pollProcessStatus();
  } catch (err) {
    showNotification(err.message, true);
  }
}

// ----------------------------------------------------------------------------
// Utilities
// ----------------------------------------------------------------------------
function showNotification(msg, isError = false) {
  let toast = document.getElementById("dashboard-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "dashboard-toast";
    toast.style.position = "fixed";
    toast.style.bottom = "24px";
    toast.style.right = "24px";
    toast.style.padding = "10px 18px";
    toast.style.borderRadius = "var(--radius-sm)";
    toast.style.fontFamily = "var(--font-sans)";
    toast.style.fontSize = "13px";
    toast.style.fontWeight = "600";
    toast.style.zIndex = "9999";
    toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.5)";
    toast.style.transition = "all 0.3s ease";
    document.body.appendChild(toast);
  }

  toast.style.background = isError ? "var(--accent-red)" : "var(--accent-cyan)";
  toast.style.color = isError ? "#fff" : "#04101e";
  toast.innerText = msg;
  toast.style.opacity = "1";
  toast.style.transform = "translateY(0)";

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
  }, 3200);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

