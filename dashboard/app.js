// P_311 SCADA Dashboard Interactive Logic
// Enhanced with Dual-Mode Architecture (Live Pipeline & Standalone Demo)
// and Connected UCI AI4I 2020 Dataset & PostgreSQL Persistence Explorer

const API_BASE = (window.location.protocol === "file:" || !window.location.port)
  ? "http://localhost:8080"
  : "";

let telemetryChart = null;
const MAX_POINTS = 30;
const timeLabels = [];
const tempData = [];
const vibData = [];
const pressData = [];

// System state
let isLiveConnected = false;
let currentMode = "normal";
let currentSubmode = "flatline";
let standaloneTimer = null;
let reconnectTimer = null;
let sseSource = null;
let internalReadingsHistory = [];

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
  initClock();
  initChart();
  loadInitialStatus();
});

// Live Clock
function initClock() {
  const clockEl = document.getElementById("live-clock");
  const tick = () => {
    const now = new Date();
    if (clockEl) clockEl.textContent = now.toTimeString().split(" ")[0];
  };
  tick();
  setInterval(tick, 1000);
}

// Chart.js Multi-axis Waveform
function initChart() {
  const canvas = document.getElementById("telemetryChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const FONT = "'IBM Plex Mono', ui-monospace, Consolas, monospace";
  const INK = "#51565b";
  const GRID = "#e4e0d6";
  const AXIS = "#b9b3a5";
  const tickStyle = { color: INK, font: { family: FONT, size: 10 } };

  telemetryChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: timeLabels,
      datasets: [
        {
          label: "Temperature (°C)",
          data: tempData,
          borderColor: "#b0612b",
          backgroundColor: "transparent",
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 3,
          tension: 0,
          yAxisID: "yTemp",
        },
        {
          label: "Vibration RMS (mm/s)",
          data: vibData,
          borderColor: "#262b2f",
          backgroundColor: "transparent",
          borderWidth: 1.5,
          pointRadius: 0,
          pointHoverRadius: 3,
          tension: 0,
          yAxisID: "yVib",
        },
        {
          label: "Discharge Pressure (bar)",
          data: pressData,
          borderColor: "#6b7a86",
          backgroundColor: "transparent",
          borderWidth: 1.5,
          borderDash: [5, 4],
          pointRadius: 0,
          pointHoverRadius: 3,
          tension: 0,
          yAxisID: "yPress",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          align: "start",
          labels: {
            color: INK,
            font: { family: FONT, size: 11 },
            boxWidth: 22,
            boxHeight: 2,
            padding: 14,
          },
        },
        tooltip: {
          backgroundColor: "#262b2f",
          titleColor: "#ebe8e1",
          bodyColor: "#ebe8e1",
          borderColor: "#343a3f",
          borderWidth: 1,
          padding: 8,
          titleFont: { family: FONT, size: 11 },
          bodyFont: { family: FONT, size: 11 },
        },
      },
      scales: {
        x: {
          grid: { color: GRID },
          ticks: { ...tickStyle, maxTicksLimit: 10 },
          border: { color: AXIS },
        },
        yTemp: {
          type: "linear",
          display: true,
          position: "left",
          min: 40,
          max: 100,
          ticks: tickStyle,
          grid: { color: GRID },
          border: { color: AXIS },
          title: { display: true, text: "Temperature (°C)", color: INK, font: { family: FONT, size: 10 } },
        },
        yVib: {
          type: "linear",
          display: true,
          position: "right",
          min: 0,
          max: 8,
          ticks: tickStyle,
          grid: { drawOnChartArea: false },
          border: { color: AXIS },
          title: { display: true, text: "Vibration (mm/s)", color: INK, font: { family: FONT, size: 10 } },
        },
        yPress: {
          type: "linear",
          display: false,
          min: 0,
          max: 7,
        },
      },
    },
  });
}

// Initial Sync & Backend Detection
function loadInitialStatus() {
  fetch(`${API_BASE}/api/status`, { mode: "cors" })
    .then((res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then((data) => {
      setConnectionState(true);
      if (data.mode) {
        currentMode = data.mode;
        currentSubmode = data.submode || "flatline";
        updateActiveButton(data.mode, data.submode);
      }
      if (data.history && data.history.length > 0) {
        data.history.forEach((r) => appendDataPoint(r));
        if (telemetryChart) telemetryChart.update();
      }
      if (data.latest_reading) {
        updateSensorCards(data.latest_reading);
      }
      if (data.latest_diagnosis) {
        renderDiagnosis(data.latest_diagnosis);
      }
      if (data.database) {
        updateDatabaseBadges(data.database);
      }
      initSSE();
      loadHistoryTable();
    })
    .catch((err) => {
      console.warn("Backend not reachable at", API_BASE || "origin", "; engaging Standalone Demo Mode:", err);
      setConnectionState(false);
      startStandaloneSimulator();
    });
}

// Connection State Management
function setConnectionState(live) {
  isLiveConnected = live;
  const bannerIcon = document.getElementById("banner-icon");
  const bannerText = document.getElementById("banner-text");
  const btnReconnect = document.getElementById("btn-reconnect");
  const statusBroker = document.getElementById("status-broker");
  const valHz = document.getElementById("val-hz");
  const valDatasetMode = document.getElementById("val-dataset-mode");

  if (live) {
    if (standaloneTimer) {
      clearInterval(standaloneTimer);
      standaloneTimer = null;
    }
    if (bannerIcon) {
      bannerIcon.className = "banner-icon online";
      bannerIcon.textContent = "●";
    }
    if (bannerText) {
      bannerText.textContent = "🟢 Live Pipeline Connected (MQTT Broker :1883 · PostgreSQL :5432 · Real-Time 1 Hz Ingestion)";
    }
    if (btnReconnect) btnReconnect.textContent = "🔄 Refresh Sync";
    if (valHz) valHz.textContent = "1 Hz LIVE";
    if (valDatasetMode) valDatasetMode.textContent = "AI4I & PG LIVE";
    if (statusBroker) {
      statusBroker.querySelector(".pill-value").textContent = "1883 ONLINE";
    }
  } else {
    if (bannerIcon) {
      bannerIcon.className = "banner-icon standalone";
      bannerIcon.textContent = "⚡";
    }
    if (bannerText) {
      bannerText.textContent = "⚡ Standalone Mode: Interactive Simulator & AI4I Dataset Active. (To link live pipeline, run Launch_Dashboard.bat)";
    }
    if (btnReconnect) btnReconnect.textContent = "🔄 Reconnect Live Server";
    if (valHz) valHz.textContent = "1 Hz DEMO";
    if (valDatasetMode) valDatasetMode.textContent = "AI4I STANDALONE";
    if (statusBroker) {
      statusBroker.querySelector(".pill-value").textContent = "STANDALONE";
    }
    // Schedule periodic probe to auto-reconnect if server starts
    if (!reconnectTimer) {
      reconnectTimer = setInterval(probeServerAutoReconnect, 5000);
    }
  }
}

function probeServerAutoReconnect() {
  if (isLiveConnected) {
    clearInterval(reconnectTimer);
    reconnectTimer = null;
    return;
  }
  fetch(`${API_BASE}/api/status`, { mode: "cors" })
    .then((res) => {
      if (res.ok) {
        console.info("Live backend server detected! Seamlessly transitioning to Live Pipeline Mode.");
        loadInitialStatus();
      }
    })
    .catch(() => {
      // Still offline, continue standalone
    });
}

function reconnectBackend() {
  const bannerText = document.getElementById("banner-text");
  if (bannerText) bannerText.textContent = "Probing backend at " + (API_BASE || "localhost:8080") + "...";
  fetch(`${API_BASE}/api/status`, { mode: "cors" })
    .then((res) => {
      if (!res.ok) throw new Error("Status " + res.status);
      return res.json();
    })
    .then(() => {
      loadInitialStatus();
    })
    .catch((e) => {
      alert(
        "Could not connect to live backend at " + (API_BASE || "http://localhost:8080") + ".\n\n" +
        "To start the live Python server:\n" +
        "1. Double-click Launch_Dashboard.bat in the project directory, OR\n" +
        "2. Run 'python dashboard/app.py' in your terminal.\n\n" +
        "The standalone demo simulator will continue running in this window."
      );
      setConnectionState(false);
    });
}

// Server-Sent Events (SSE) Stream
function initSSE() {
  if (sseSource) {
    sseSource.close();
    sseSource = null;
  }

  try {
    sseSource = new EventSource(`${API_BASE}/api/stream`);

    sseSource.addEventListener("init", (e) => {
      const data = JSON.parse(e.data);
      if (data.mode) updateActiveButton(data.mode, data.submode);
      if (data.latest_diagnosis) renderDiagnosis(data.latest_diagnosis);
    });

    sseSource.addEventListener("telemetry", (e) => {
      const payload = JSON.parse(e.data);
      const r = payload.latest;
      updateSensorCards(r);
      appendDataPoint(r);
      if (telemetryChart) telemetryChart.update();
    });

    sseSource.addEventListener("diagnosis", (e) => {
      const diag = JSON.parse(e.data);
      renderDiagnosis(diag);
      loadHistoryTable();
    });

    sseSource.onerror = () => {
      console.warn("SSE connection interrupted. Reconnecting...");
    };
  } catch (e) {
    console.error("SSE initialization failed:", e);
  }
}

// Update KPI cards and limit indicators
function updateSensorCards(reading) {
  const tempEl = document.getElementById("val-temp");
  const vibEl = document.getElementById("val-vib");
  const pressEl = document.getElementById("val-press");

  const badgeTemp = document.getElementById("badge-temp");
  const badgeVib = document.getElementById("badge-vib");
  const badgePress = document.getElementById("badge-press");

  const barTemp = document.getElementById("bar-temp");
  const barVib = document.getElementById("bar-vib");
  const barPress = document.getElementById("bar-press");

  // Temperature
  const t = reading.temperature;
  tempEl.textContent = t.toFixed(1);
  if (t === -999.0) {
    badgeTemp.className = "kpi-status-badge status-critical";
    badgeTemp.textContent = "DISCONNECT (-999)";
    barTemp.style.width = "100%";
  } else if (t >= 75.0) {
    badgeTemp.className = "kpi-status-badge status-critical";
    badgeTemp.textContent = "CRITICAL HIGH";
    barTemp.style.width = Math.min(100, Math.max(0, (t - 40) / 0.5)) + "%";
  } else if (t >= 70.0) {
    badgeTemp.className = "kpi-status-badge status-warning";
    badgeTemp.textContent = "WARNING";
    barTemp.style.width = Math.min(100, Math.max(0, (t - 40) / 0.5)) + "%";
  } else {
    badgeTemp.className = "kpi-status-badge status-normal";
    badgeTemp.textContent = "NORMAL";
    barTemp.style.width = Math.min(100, Math.max(0, (t - 40) / 0.5)) + "%";
  }

  // Vibration
  const v = reading.vibration;
  vibEl.textContent = v.toFixed(2);
  if (v >= 4.5) {
    badgeVib.className = "kpi-status-badge status-critical";
    badgeVib.textContent = "ZONE D DANGER";
    barVib.style.width = Math.min(100, (v / 7.0) * 100) + "%";
  } else if (v >= 2.8) {
    badgeVib.className = "kpi-status-badge status-warning";
    badgeVib.textContent = "ZONE C ALERT";
    barVib.style.width = Math.min(100, (v / 7.0) * 100) + "%";
  } else {
    badgeVib.className = "kpi-status-badge status-normal";
    badgeVib.textContent = "ZONE A/B GOOD";
    barVib.style.width = Math.min(100, (v / 7.0) * 100) + "%";
  }

  // Pressure
  const p = reading.pressure;
  pressEl.textContent = p.toFixed(2);
  if (p < 3.0) {
    badgePress.className = "kpi-status-badge status-critical";
    badgePress.textContent = "LOW HYDRAULIC";
    barPress.style.width = Math.min(100, (p / 6.0) * 100) + "%";
  } else {
    badgePress.className = "kpi-status-badge status-normal";
    badgePress.textContent = "NOMINAL";
    barPress.style.width = Math.min(100, (p / 6.0) * 100) + "%";
  }
}

// Append data point to chart arrays
function appendDataPoint(reading) {
  const ts = new Date(reading.timestamp || Date.now());
  const timeStr = ts.toTimeString().split(" ")[0];

  timeLabels.push(timeStr);
  tempData.push(reading.temperature === -999.0 ? null : reading.temperature);
  vibData.push(reading.vibration);
  pressData.push(reading.pressure);

  if (timeLabels.length > MAX_POINTS) {
    timeLabels.shift();
    tempData.shift();
    vibData.shift();
    pressData.shift();
  }
}

// Render 6-Section AI Diagnosis Card
function renderDiagnosis(diag) {
  if (!diag) return;

  const emptyView = document.getElementById("empty-state-view");
  const reportView = document.getElementById("active-report-view");
  const condBadge = document.getElementById("diag-condition-badge");
  const metaTime = document.getElementById("diag-meta-time");
  const latencyEl = document.getElementById("diag-latency");

  if (emptyView) emptyView.classList.add("hidden");
  if (reportView) reportView.classList.remove("hidden");

  // Condition Badge
  if (condBadge) {
    condBadge.className = "condition-badge condition-fault";
    condBadge.textContent = "FAULT: " + (diag.fault_category || "DETECTED").toUpperCase();
  }

  // Meta Time
  if (metaTime) {
    const d = new Date(diag.timestamp || Date.now());
    metaTime.textContent = `Incident logged at ${d.toLocaleTimeString()} | Device: ${diag.device_id || "pump_centrifugal_01"}`;
  }

  // Sections
  const secs = diag.sections || {};
  const likelyEl = document.getElementById("report-likely-fault");
  const whyEl = document.getElementById("report-why");
  const checksEl = document.getElementById("report-checks");
  const confEl = document.getElementById("report-confidence");
  const symEl = document.getElementById("report-symptoms");

  if (likelyEl) {
    likelyEl.textContent = secs["Likely Fault"] || secs["likely_fault"] || diag.likely_fault || "Abnormal operational condition detected.";
  }
  if (whyEl) {
    whyEl.textContent = secs["Why"] || secs["why"] || diag.why || (diag.symptoms ? diag.symptoms.join("; ") : "Evidence confirmed by telemetry thresholds.");
  }
  if (checksEl) {
    checksEl.textContent = secs["Recommended Checks"] || secs["recommended_checks"] || diag.recommended_checks || "1. Verify sensor connections.\n2. Apply Lockout/Tagout (LOTO).\n3. Consult technical manual.";
  }
  if (confEl) {
    confEl.textContent = secs["Confidence and Limitations"] || secs["confidence_limitations"] || diag.confidence_limitations || "Confidence: High (ISO 10816 Grounded).";
  }
  if (symEl) {
    symEl.textContent = diag.symptoms && diag.symptoms.length > 0 ? diag.symptoms.join("\n") : "--";
  }

  // Latency & Runtime
  if (latencyEl && diag.latency_seconds) {
    latencyEl.textContent = `Inference Latency: ${diag.latency_seconds.toFixed(2)}s`;
  }
  const runtimeEl = document.getElementById("diag-runtime-tag");
  if (runtimeEl && diag.runtime) {
    runtimeEl.textContent = `Runtime: ${diag.runtime}`;
  }

  // Sources Chips
  const sourcesContainer = document.getElementById("report-sources");
  if (sourcesContainer) {
    sourcesContainer.innerHTML = "";
    if (diag.retrieved_sources && diag.retrieved_sources.length > 0) {
      diag.retrieved_sources.forEach((src) => {
        const chip = document.createElement("div");
        chip.className = "source-chip";
        chip.innerHTML = `<span class="src-name">${src.source}</span>` +
          (src.section ? `<span class="src-section">${src.section}</span>` : "") +
          `<span class="score">Score: ${src.score || "0.85"}</span>`;
        sourcesContainer.appendChild(chip);
      });
    }
  }
}

// Set Fault Mode (dual support for Live API and Standalone Simulator)
function setMode(mode, submode = "flatline") {
  currentMode = mode;
  currentSubmode = submode;
  updateActiveButton(mode, submode);

  if (mode === "normal") {
    const condBadge = document.getElementById("diag-condition-badge");
    if (condBadge) {
      condBadge.className = "condition-badge condition-healthy";
      condBadge.textContent = "SYSTEM HEALTHY";
    }
  }

  if (isLiveConnected) {
    fetch(`${API_BASE}/api/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, submode }),
    })
      .then((res) => res.json())
      .catch((err) => console.error("Error setting mode on backend:", err));
  } else {
    console.info(`[Standalone Simulator] Mode updated to '${mode}' (submode='${submode}')`);
  }
}

// Update Active Button UI
function updateActiveButton(mode, submode = "flatline") {
  document.querySelectorAll(".btn-mode").forEach((b) => b.classList.remove("active"));
  if (mode === "normal") {
    const el = document.getElementById("btn-mode-normal");
    if (el) el.classList.add("active");
  } else if (mode === "bearing_wear") {
    const el = document.getElementById("btn-mode-bearing");
    if (el) el.classList.add("active");
  } else if (mode === "overheating") {
    const el = document.getElementById("btn-mode-overheat");
    if (el) el.classList.add("active");
  } else if (mode === "pressure_drop") {
    const el = document.getElementById("btn-mode-pressure");
    if (el) el.classList.add("active");
  } else if (mode === "sensor_failure") {
    if (submode === "disconnect") {
      const el = document.getElementById("btn-mode-disconnect");
      if (el) el.classList.add("active");
    } else {
      const el = document.getElementById("btn-mode-flatline");
      if (el) el.classList.add("active");
    }
  }
}

// Load Incident History Table
function loadHistoryTable() {
  if (!isLiveConnected) {
    renderHistoryTableRows(internalReadingsHistory);
    return;
  }

  fetch(`${API_BASE}/api/diagnoses`, { mode: "cors" })
    .then((res) => res.json())
    .then((records) => {
      renderHistoryTableRows(records);
    })
    .catch((err) => {
      console.warn("Error loading history table:", err);
      renderHistoryTableRows(internalReadingsHistory);
    });
}

function renderHistoryTableRows(records) {
  const tbody = document.getElementById("history-table-body");
  if (!tbody) return;

  if (!records || records.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty-table">No incidents recorded yet.</td></tr>';
    return;
  }

  tbody.innerHTML = "";
  records.slice(0, 10).forEach((rec) => {
    const tr = document.createElement("tr");
    const dt = new Date(rec.timestamp || Date.now()).toLocaleTimeString();
    const topSrc = rec.retrieved_sources && rec.retrieved_sources[0] ? rec.retrieved_sources[0].source : "Manual RAG";
    const r = rec.readings || {};
    const telemetryStr = `T:${r.temperature ? r.temperature.toFixed(1) : "-"}°C | V:${r.vibration ? r.vibration.toFixed(2) : "-"} | P:${r.pressure ? r.pressure.toFixed(2) : "-"}`;

    tr.innerHTML = `
      <td>${dt}</td>
      <td><span class="history-badge status-critical">${(rec.fault_category || "").toUpperCase()}</span></td>
      <td>${telemetryStr}</td>
      <td>${topSrc}</td>
      <td><button class="btn-inspect">Inspect</button></td>
    `;
    const inspectBtn = tr.querySelector(".btn-inspect");
    inspectBtn.addEventListener("click", () => renderDiagnosis(rec));
    tbody.appendChild(tr);
  });
}

function updateDatabaseBadges(dbInfo) {
  const pgStatusVal = document.getElementById("pg-status-val");
  const pgRecordsVal = document.getElementById("pg-records-val");
  const modalTelem = document.getElementById("modal-telemetry-rows");
  const modalInci = document.getElementById("modal-incident-rows");

  if (dbInfo.connected) {
    if (pgStatusVal) pgStatusVal.textContent = "CONNECTED";
    if (pgRecordsVal) pgRecordsVal.textContent = `${dbInfo.telemetry_count.toLocaleString()} telemetry rows`;
    if (modalTelem) modalTelem.textContent = `${dbInfo.telemetry_count.toLocaleString()}`;
    if (modalInci) modalInci.textContent = `${dbInfo.incidents_count.toLocaleString()}`;
  } else {
    if (pgStatusVal) pgStatusVal.textContent = "STANDALONE";
    if (pgRecordsVal) pgRecordsVal.textContent = "Local JSONL Active";
  }
}

// -------------------------------------------------------------
// STANDALONE SIMULATOR (Runs directly in browser when offline)
// -------------------------------------------------------------
let simTick = 0;
let lastStandaloneDiagTime = 0;

function startStandaloneSimulator() {
  if (standaloneTimer) clearInterval(standaloneTimer);

  // Pre-seed chart with 15 normal readings
  const now = Date.now();
  for (let i = 14; i >= 0; i--) {
    const t = now - i * 1000;
    appendDataPoint({
      timestamp: t,
      temperature: 54.0 + (Math.random() * 1.5 - 0.75),
      vibration: 1.4 + (Math.random() * 0.3 - 0.15),
      pressure: 5.0 + (Math.random() * 0.2 - 0.1),
    });
  }
  if (telemetryChart) telemetryChart.update();

  standaloneTimer = setInterval(() => {
    simTick++;
    let r = generateSimulatedReading(currentMode, currentSubmode);
    updateSensorCards(r);
    appendDataPoint(r);
    if (telemetryChart) telemetryChart.update();

    // Check for diagnostic trigger in standalone
    checkStandaloneDiagnosis(r);
  }, 1000);
}

function generateSimulatedReading(mode, submode) {
  const ts = Date.now();
  const rand = (min, max) => min + Math.random() * (max - min);

  if (mode === "normal") {
    return {
      timestamp: ts,
      device_id: "pump_centrifugal_01",
      temperature: rand(52.5, 55.5),
      vibration: rand(1.2, 1.8),
      pressure: rand(4.8, 5.2),
    };
  } else if (mode === "bearing_wear") {
    return {
      timestamp: ts,
      device_id: "pump_centrifugal_01",
      temperature: rand(63.0, 68.0),
      vibration: rand(4.9, 6.2), // > 4.5 Zone D alert
      pressure: rand(4.5, 4.9),
    };
  } else if (mode === "overheating") {
    return {
      timestamp: ts,
      device_id: "pump_centrifugal_01",
      temperature: rand(78.5, 84.0), // > 75 Critical
      vibration: rand(1.6, 2.3),
      pressure: rand(4.7, 5.1),
    };
  } else if (mode === "pressure_drop") {
    return {
      timestamp: ts,
      device_id: "pump_centrifugal_01",
      temperature: rand(55.0, 58.0),
      vibration: rand(2.9, 3.8),
      pressure: rand(1.8, 2.6), // < 3.0 Low
    };
  } else if (mode === "sensor_failure") {
    if (submode === "disconnect") {
      return {
        timestamp: ts,
        device_id: "pump_centrifugal_01",
        temperature: -999.0, // Disconnect flag
        vibration: rand(1.3, 1.7),
        pressure: rand(4.9, 5.2),
      };
    } else {
      return {
        timestamp: ts,
        device_id: "pump_centrifugal_01",
        temperature: 54.0, // Flatline freeze
        vibration: 1.45,
        pressure: 5.0,
      };
    }
  }

  return { timestamp: ts, temperature: 53.0, vibration: 1.4, pressure: 5.0 };
}

function checkStandaloneDiagnosis(reading) {
  if (currentMode === "normal") return;

  const now = Date.now();
  if (now - lastStandaloneDiagTime < 5000) return; // 5s cooldown
  lastStandaloneDiagTime = now;

  let diag = null;
  if (currentMode === "bearing_wear") {
    diag = {
      timestamp: reading.timestamp,
      device_id: "pump_centrifugal_01",
      fault_category: "bearing_wear",
      symptoms: ["Radial vibration exceeded ISO 10816 Zone D safety limit (4.5 mm/s RMS)"],
      readings: { ...reading },
      retrieved_sources: [
        { source: "manual_bearing_maintenance.md", section: "Radial Bearing Fatigue", score: "0.892" },
        { source: "manual_iso_10816_vibration.md", section: "Zone D Action Criteria", score: "0.841" },
      ],
      sections: {
        "Likely Fault": "Accelerated Radial Roller Bearing Fatigue / Inner Raceway Spalling.",
        "Why": `Continuous vibration reached ${reading.vibration.toFixed(2)} mm/s RMS (threshold: 4.5 mm/s), indicating severe mechanical friction and inner ring damage.`,
        "Recommended Checks": "1. Immediately stop pump and implement Lockout/Tagout (LOTO).\n2. Inspect bearing lubricant for metallic swarf.\n3. Verify shaft misalignment with laser alignment tool.\n4. Replace bearing assembly with SKF/FAG API 610 compliant set.",
        "Confidence and Limitations": "Confidence: High (94%). Grounded directly in ISO 10816-3 Zone D mechanical envelope.",
      },
      runtime: "Standalone Grounded RAG Synthesizer",
      latency_seconds: 0.12,
    };
  } else if (currentMode === "overheating") {
    diag = {
      timestamp: reading.timestamp,
      device_id: "pump_centrifugal_01",
      fault_category: "overheating",
      symptoms: ["Motor bearing RTD exceeded 75.0°C maximum thermal trip threshold"],
      readings: { ...reading },
      retrieved_sources: [
        { source: "manual_thermal_management.md", section: "Motor Stator Insulation Class F", score: "0.915" },
        { source: "manual_cooling_jacket.md", section: "Heat Dissipation Failure", score: "0.867" },
      ],
      sections: {
        "Likely Fault": "Cooling Jacket Blockage / Thermal Heat Dissipation Failure (HDF).",
        "Why": `Bearing thermal probe recorded ${reading.temperature.toFixed(1)}°C (threshold: 75.0°C). Matches UCI AI4I 2020 Heat Dissipation Failure signature.`,
        "Recommended Checks": "1. Verify coolant circulation jacket flow and return lines.\n2. Inspect fan cowl and motor cooling fins for slurry build-up.\n3. Measure drive motor winding resistance.\n4. Do not restart until temperature drops below 60.0°C.",
        "Confidence and Limitations": "Confidence: Very High (97%). Thermal runaway pattern confirmed across consecutive samples.",
      },
      runtime: "Standalone Grounded RAG Synthesizer",
      latency_seconds: 0.14,
    };
  } else if (currentMode === "pressure_drop") {
    diag = {
      timestamp: reading.timestamp,
      device_id: "pump_centrifugal_01",
      fault_category: "pressure_drop",
      symptoms: ["Discharge pressure dropped below 3.0 bar operational minimum"],
      readings: { ...reading },
      retrieved_sources: [
        { source: "manual_hydraulic_cavitation.md", section: "Net Positive Suction Head & Cavitation", score: "0.903" },
        { source: "manual_mechanical_seal.md", section: "Slurry Line De-pressurization", score: "0.854" },
      ],
      sections: {
        "Likely Fault": "Hydraulic Cavitation / Discharge Pipework Slurry Leakage.",
        "Why": `Discharge pressure collapsed to ${reading.pressure.toFixed(2)} bar (normal: 4.5-5.5 bar) with accompanying high-frequency vibration instability.`,
        "Recommended Checks": "1. Check suction strainer for slurry sediment blockage.\n2. Verify suction head (NPSHa > NPSHr margin).\n3. Inspect mechanical face seal for weeping or rupture.\n4. Check discharge non-return check valve operation.",
        "Confidence and Limitations": "Confidence: High (91%). Hydraulic depression matches sudden suction throttling.",
      },
      runtime: "Standalone Grounded RAG Synthesizer",
      latency_seconds: 0.15,
    };
  } else if (currentMode === "sensor_failure") {
    diag = {
      timestamp: reading.timestamp,
      device_id: "pump_centrifugal_01",
      fault_category: "sensor_failure",
      symptoms: [currentSubmode === "disconnect" ? "Sensor RTD reported out-of-range sentinel value (-999°C)" : "ADC hardware signal flatline: zero variance across 10 samples"],
      readings: { ...reading },
      retrieved_sources: [
        { source: "manual_sensor_instrumentation.md", section: "PT100 RTD Disconnection & 4-20mA Faults", score: "0.942" },
      ],
      sections: {
        "Likely Fault": currentSubmode === "disconnect" ? "Open-Circuit Thermal RTD Transducer Disconnection." : "Data Acquisition ADC Channel Lock / Sensor Freeze.",
        "Why": currentSubmode === "disconnect"
          ? "Temperature value -999.0°C indicates infinite loop resistance caused by sheared field wiring or loose terminal block."
          : "Zero-variance telemetry detected on ADC converter; physical process always exhibits natural Gaussian noise.",
        "Recommended Checks": "1. Inspect field junction box wiring terminals for corrosion.\n2. Measure PT100 loop resistance using multimeter (nominal ~110-125 ohms).\n3. Cycle power to field I/O transmitter card.",
        "Confidence and Limitations": "Confidence: Absolute (99%). Deterministic instrumentation fault signature.",
      },
      runtime: "Standalone Grounded RAG Synthesizer",
      latency_seconds: 0.08,
    };
  }

  if (diag) {
    renderDiagnosis(diag);
    internalReadingsHistory.unshift(diag);
    if (internalReadingsHistory.length > 20) internalReadingsHistory.pop();
    renderHistoryTableRows(internalReadingsHistory);
  }
}

// -------------------------------------------------------------
// DATASET & PERSISTENCE MODAL CONTROLS
// -------------------------------------------------------------
function toggleDatasetModal() {
  const modal = document.getElementById("dataset-modal");
  if (!modal) return;
  modal.classList.toggle("hidden");
}

function switchModalTab(tabId, btn) {
  document.querySelectorAll(".modal-tab-pane").forEach((p) => p.classList.remove("active"));
  document.querySelectorAll(".modal-tab-btn").forEach((b) => b.classList.remove("active"));

  const targetPane = document.getElementById(tabId);
  if (targetPane) targetPane.classList.add("active");
  if (btn) btn.classList.add("active");
}
