// P_311 SCADA Dashboard Interactive Logic

let telemetryChart = null;
const MAX_POINTS = 30;
const timeLabels = [];
const tempData = [];
const vibData = [];
const pressData = [];

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
  initClock();
  initChart();
  initSSE();
  loadInitialStatus();
});

// Live UTC Clock
function initClock() {
  const clockEl = document.getElementById("live-clock");
  setInterval(() => {
    const now = new Date();
    clockEl.textContent = now.toTimeString().split(" ")[0];
  }, 1000);
}

// Chart.js Multi-axis Waveform (styling only; data arrays and axis ranges unchanged)
function initChart() {
  const ctx = document.getElementById("telemetryChart").getContext("2d");

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
          titleFont: { family: FONT, size: 11 },
          bodyFont: { family: FONT, size: 11 },
          borderColor: "#343a3f",
          borderWidth: 1,
          cornerRadius: 3,
          padding: 8,
        },
      },
      scales: {
        x: {
          ticks: { ...tickStyle, maxRotation: 0, autoSkipPadding: 24 },
          grid: { color: GRID },
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

// Initial Sync
function loadInitialStatus() {
  fetch("/api/status")
    .then((res) => res.json())
    .then((data) => {
      if (data.mode) {
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
      loadHistoryTable();
    })
    .catch((err) => console.warn("Initial status fetch error:", err));
}

// Server-Sent Events (SSE) Stream
function initSSE() {
  try {
    const sse = new EventSource("/api/stream");

    sse.addEventListener("init", (e) => {
      const data = JSON.parse(e.data);
      if (data.mode) updateActiveButton(data.mode);
      if (data.latest_diagnosis) renderDiagnosis(data.latest_diagnosis);
    });

    sse.addEventListener("telemetry", (e) => {
      const payload = JSON.parse(e.data);
      const r = payload.latest;
      updateSensorCards(r);
      appendDataPoint(r);
      if (telemetryChart) telemetryChart.update();
    });

    sse.addEventListener("diagnosis", (e) => {
      const diag = JSON.parse(e.data);
      renderDiagnosis(diag);
      loadHistoryTable();
    });

    sse.onerror = () => {
      console.warn("SSE connection interrupted. Reconnecting in background...");
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
  const ts = new Date(reading.timestamp);
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

// Render 4-Section AI Diagnosis Card
function renderDiagnosis(diag) {
  if (!diag) return;

  const emptyView = document.getElementById("empty-state-view");
  const reportView = document.getElementById("active-report-view");
  const condBadge = document.getElementById("diag-condition-badge");
  const metaTime = document.getElementById("diag-meta-time");
  const latencyEl = document.getElementById("diag-latency");

  emptyView.classList.add("hidden");
  reportView.classList.remove("hidden");

  // Condition Badge
  condBadge.className = "condition-badge condition-fault";
  condBadge.textContent = "FAULT: " + (diag.fault_category || "DETECTED").toUpperCase();

  // Meta Time
  const d = new Date(diag.timestamp);
  metaTime.textContent = `Incident detected at ${d.toLocaleTimeString()} | Device: ${diag.device_id}`;

  // Sections
  const secs = diag.sections || {};
  document.getElementById("report-likely-fault").textContent =
    secs["Likely Fault"] || secs["likely_fault"] || "Abnormal telemetry pattern identified.";
  document.getElementById("report-why").textContent =
    secs["Why"] || secs["why"] || (diag.symptoms ? diag.symptoms.join("; ") : "Evidence from sensor signals.");
  document.getElementById("report-checks").textContent =
    secs["Recommended Checks"] || secs["recommended_checks"] || "1. Check field sensor connections.\n2. Isolate power (LOTO).\n3. Consult operating manual.";
  document.getElementById("report-confidence").textContent =
    secs["Confidence and Limitations"] || secs["confidence_limitations"] || "Confidence: High (ISO Grounded).";
  document.getElementById("report-symptoms").textContent =
    diag.symptoms && diag.symptoms.length > 0 ? diag.symptoms.join("\n") : "--";

  // Latency & Runtime
  if (diag.latency_seconds) {
    latencyEl.textContent = `Inference Latency: ${diag.latency_seconds.toFixed(2)}s`;
  }
  if (diag.runtime) {
    document.getElementById("diag-runtime-tag").textContent = `Runtime: ${diag.runtime}`;
  }

  // Sources Chips
  const sourcesContainer = document.getElementById("report-sources");
  sourcesContainer.innerHTML = "";
  if (diag.retrieved_sources && diag.retrieved_sources.length > 0) {
    diag.retrieved_sources.forEach((src) => {
      const chip = document.createElement("div");
      chip.className = "source-chip";
      chip.innerHTML = `<span class="src-name">${src.source}</span>` + (src.section ? `<span class="src-section">${src.section}</span>` : "") + `<span class="score">Score: ${src.score}</span>`;
      sourcesContainer.appendChild(chip);
    });
  }
}

// Set Fault Mode via API
function setMode(mode, submode = "flatline") {
  fetch("/api/mode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, submode }),
  })
    .then((res) => res.json())
    .then(() => {
      updateActiveButton(mode, submode);
      if (mode === "normal") {
        const condBadge = document.getElementById("diag-condition-badge");
        condBadge.className = "condition-badge condition-healthy";
        condBadge.textContent = "SYSTEM HEALTHY";
      }
    })
    .catch((err) => console.error("Error setting mode:", err));
}

// Update Active Button UI
function updateActiveButton(mode, submode = "flatline") {
  document.querySelectorAll(".btn-mode").forEach((b) => b.classList.remove("active"));
  if (mode === "normal") {
    document.getElementById("btn-mode-normal").classList.add("active");
  } else if (mode === "bearing_wear") {
    document.getElementById("btn-mode-bearing").classList.add("active");
  } else if (mode === "overheating") {
    document.getElementById("btn-mode-overheat").classList.add("active");
  } else if (mode === "pressure_drop") {
    document.getElementById("btn-mode-pressure").classList.add("active");
  } else if (mode === "sensor_failure") {
    if (submode === "disconnect") {
      document.getElementById("btn-mode-disconnect").classList.add("active");
    } else {
      document.getElementById("btn-mode-flatline").classList.add("active");
    }
  }
}

// Load Incident History Table
function loadHistoryTable() {
  fetch("/api/diagnoses")
    .then((res) => res.json())
    .then((records) => {
      const tbody = document.getElementById("history-table-body");
      if (!records || records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-table">No incidents recorded yet.</td></tr>';
        return;
      }
      tbody.innerHTML = "";
      records.slice(0, 10).forEach((rec) => {
        const tr = document.createElement("tr");
        const dt = new Date(rec.timestamp).toLocaleTimeString();
        const topSrc = rec.retrieved_sources && rec.retrieved_sources[0] ? rec.retrieved_sources[0].source : "N/A";
        const r = rec.readings || {};
        const telemetryStr = `T:${r.temperature ? r.temperature.toFixed(1) : "-"}°C | V:${r.vibration ? r.vibration.toFixed(2) : "-"} | P:${r.pressure ? r.pressure.toFixed(2) : "-"}`;
        
        tr.innerHTML = `
          <td>${dt}</td>
          <td><span class="history-badge status-critical">${(rec.fault_category || "").toUpperCase()}</span></td>
          <td>${telemetryStr}</td>
          <td>${topSrc}</td>
          <td><button class="btn-inspect" onclick='viewHistoricDiagnosis(${JSON.stringify(rec)})'>Inspect</button></td>
        `;
        tbody.appendChild(tr);
      });
    })
    .catch((err) => console.warn("Error loading history table:", err));
}

function viewHistoricDiagnosis(record) {
  renderDiagnosis(record);
}
