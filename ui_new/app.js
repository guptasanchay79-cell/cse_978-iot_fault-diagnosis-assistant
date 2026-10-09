// P_311 dashboard logic
// API, SSE events and endpoints are unchanged from the previous version.
// Changed: presentation only (segmented bars, monochrome chart, theme switch, hero state).

const API_BASE = (window.location.protocol === "file:" || !window.location.port)
  ? "http://localhost:8080"
  : "";

let telemetryChart = null;
const MAX_POINTS = 30;
const SEGMENTS = 20;
const timeLabels = [];
const tempData = [];
const vibData = [];
const pressData = [];
let historyRecords = [];

document.addEventListener("DOMContentLoaded", () => {
  initClock();
  initChart();
  initTheme();
  initSSE();
  loadInitialStatus();
});

/* ---------- Clock (browser local time) ---------- */
function initClock() {
  const clockEl = document.getElementById("live-clock");
  const tick = () => {
    clockEl.textContent = new Date().toTimeString().split(" ")[0];
  };
  tick();
  setInterval(tick, 1000);
}

/* ---------- Theme ---------- */
function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function initTheme() {
  const btn = document.getElementById("theme-toggle");
  const sync = () => {
    const light = document.documentElement.dataset.theme === "light";
    btn.setAttribute("aria-checked", String(light));
    applyChartTheme();
  };
  btn.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("p311-theme", next); } catch (e) { /* storage blocked */ }
    sync();
  });
  sync();
}

/* ---------- Chart: monochrome, told apart by line pattern ---------- */
function initChart() {
  const ctx = document.getElementById("telemetryChart").getContext("2d");

  Chart.defaults.font.family = "'Space Mono', ui-monospace, monospace";
  Chart.defaults.font.size = 10;

  const line = (label, data, axis, dash) => ({
    label,
    data,
    yAxisID: axis,
    borderWidth: 1.5,
    borderDash: dash,
    pointRadius: 0,
    pointHoverRadius: 3,
    tension: 0,
    fill: false,
  });

  telemetryChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: timeLabels,
      datasets: [
        line("Temp °C", tempData, "yTemp", []),
        line("Vib mm/s", vibData, "yVib", [6, 4]),
        line("Press bar", pressData, "yPress", [1, 4]),
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false }, // legend lives in the HTML
        tooltip: {
          displayColors: false,
          borderWidth: 1,
          cornerRadius: 4,
          padding: 10,
        },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 6, maxRotation: 0 }, grid: { drawTicks: false } },
        yTemp: { type: "linear", position: "left", min: 40, max: 100, grid: { drawTicks: false } },
        yVib: { type: "linear", position: "right", min: 0, max: 8, grid: { drawOnChartArea: false, drawTicks: false } },
        yPress: { type: "linear", display: false, min: 0, max: 7 },
      },
    },
  });

  applyChartTheme();
}

function applyChartTheme() {
  if (!telemetryChart) return;
  const ink = cssVar("--t-display");
  const mid = cssVar("--t-secondary");
  const low = cssVar("--t-disabled");
  const grid = cssVar("--line");
  const edge = cssVar("--line-strong");

  const [temp, vib, press] = telemetryChart.data.datasets;
  temp.borderColor = ink;
  vib.borderColor = mid;
  press.borderColor = low;

  const o = telemetryChart.options;
  o.scales.x.ticks.color = low;
  o.scales.x.grid.color = grid;
  o.scales.x.border = { color: edge };
  o.scales.yTemp.ticks = { ...o.scales.yTemp.ticks, color: mid };
  o.scales.yTemp.grid.color = grid;
  o.scales.yTemp.border = { color: edge };
  o.scales.yVib.ticks = { ...o.scales.yVib.ticks, color: mid };
  o.scales.yVib.border = { color: edge };

  const tip = o.plugins.tooltip;
  tip.backgroundColor = cssVar("--tooltip-bg");
  tip.borderColor = edge;
  tip.titleColor = mid;
  tip.bodyColor = ink;

  telemetryChart.update("none");
}

/* ---------- Initial sync ---------- */
function loadInitialStatus() {
  fetch(`${API_BASE}/api/status`)
    .then((res) => res.json())
    .then((data) => {
      if (data.mode) updateActiveButton(data.mode, data.submode);
      if (data.history && data.history.length > 0) {
        data.history.forEach((r) => appendDataPoint(r));
        if (telemetryChart) telemetryChart.update();
      }
      if (data.latest_reading) updateSensorCards(data.latest_reading);
      if (data.latest_diagnosis) {
        // A logged incident from an earlier run must not flip the hero while the pump is in normal mode.
        renderDiagnosis(data.latest_diagnosis, { historic: data.mode === "normal" });
      }
      loadHistoryTable();
    })
    .catch((err) => console.warn("Initial status fetch error:", err));
}

/* ---------- Server-Sent Events ---------- */
function setStreamState(live) {
  const dot = document.getElementById("dot-stream");
  document.getElementById("val-stream").textContent = live ? "Live" : "Reconnecting";
  dot.className = live ? "dot on" : "dot off";
}

function initSSE() {
  try {
    const sse = new EventSource(`${API_BASE}/api/stream`);

    sse.onopen = () => setStreamState(true);

    sse.addEventListener("init", (e) => {
      const data = JSON.parse(e.data);
      if (data.mode) updateActiveButton(data.mode);
      if (data.latest_diagnosis) {
        renderDiagnosis(data.latest_diagnosis, { historic: data.mode === "normal" });
      }
    });

    sse.addEventListener("telemetry", (e) => {
      const r = JSON.parse(e.data).latest;
      updateSensorCards(r);
      appendDataPoint(r);
      if (telemetryChart) telemetryChart.update();
    });

    sse.addEventListener("diagnosis", (e) => {
      renderDiagnosis(JSON.parse(e.data));
      loadHistoryTable();
    });

    sse.onerror = () => {
      setStreamState(false);
      console.warn("SSE connection interrupted. Reconnecting in background...");
    };
  } catch (e) {
    console.error("SSE initialization failed:", e);
    setStreamState(false);
  }
}

/* ---------- Readings ---------- */
function setBar(el, pct) {
  if (!el) return;
  if (el.children.length !== SEGMENTS) {
    el.innerHTML = "";
    for (let i = 0; i < SEGMENTS; i++) el.appendChild(document.createElement("i"));
  }
  const on = Math.round((Math.max(0, Math.min(100, pct)) / 100) * SEGMENTS);
  for (let i = 0; i < SEGMENTS; i++) el.children[i].classList.toggle("on", i < on);
}

function setReading(key, valueText, state, label, pct) {
  document.getElementById(`val-${key}`).textContent = valueText;
  const badge = document.getElementById(`badge-${key}`);
  badge.className = `kpi-status-badge status-${state}`;
  badge.textContent = label;
  document.getElementById(`card-${key}`).dataset.state = state;
  setBar(document.getElementById(`bar-${key}`), pct);
}

// Thresholds mirror the previous version of this file.
function updateSensorCards(reading) {
  const t = reading.temperature;
  const tPct = (t - 40) / 0.5;
  if (t === -999.0) setReading("temp", t.toFixed(1), "critical", "DISCONNECT (-999)", 100);
  else if (t >= 75.0) setReading("temp", t.toFixed(1), "critical", "CRITICAL HIGH", tPct);
  else if (t >= 70.0) setReading("temp", t.toFixed(1), "warning", "WARNING", tPct);
  else setReading("temp", t.toFixed(1), "normal", "NORMAL", tPct);

  const v = reading.vibration;
  const vPct = (v / 7.0) * 100;
  if (v >= 4.5) setReading("vib", v.toFixed(2), "critical", "ZONE D DANGER", vPct);
  else if (v >= 2.8) setReading("vib", v.toFixed(2), "warning", "ZONE C ALERT", vPct);
  else setReading("vib", v.toFixed(2), "normal", "ZONE A/B GOOD", vPct);

  const p = reading.pressure;
  const pPct = (p / 6.0) * 100;
  if (p < 3.0) setReading("press", p.toFixed(2), "critical", "LOW HYDRAULIC", pPct);
  else setReading("press", p.toFixed(2), "normal", "NOMINAL", pPct);
}

function appendDataPoint(reading) {
  const ts = new Date(reading.timestamp);
  timeLabels.push(ts.toTimeString().split(" ")[0]);
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

/* ---------- Hero + diagnosis report ---------- */
function setHero(state, category) {
  const el = document.getElementById("diag-condition-badge");
  if (state === "fault") {
    el.className = "condition-badge condition-fault";
    el.textContent = String(category || "fault detected").replace(/_/g, " ").toUpperCase();
  } else {
    el.className = "condition-badge condition-healthy";
    el.textContent = "NOMINAL";
  }
}

function renderDiagnosis(diag, { historic = false } = {}) {
  if (!diag) return;

  document.getElementById("empty-state-view").classList.add("hidden");
  document.getElementById("active-report-view").classList.remove("hidden");

  const when = new Date(diag.timestamp).toLocaleTimeString();
  const metaTime = document.getElementById("diag-meta-time");
  if (!historic) {
    setHero("fault", diag.fault_category);
    metaTime.textContent = `Incident detected ${when} · ${diag.device_id}`;
  }
  document.getElementById("report-meta").textContent =
    `${historic ? "Logged" : "Detected"} ${when} · ${diag.device_id} · ${String(diag.fault_category || "fault").replace(/_/g, " ")}`;

  const secs = diag.sections || {};
  document.getElementById("report-likely-fault").textContent =
    secs["Likely Fault"] || secs["likely_fault"] || "Abnormal telemetry pattern identified.";
  document.getElementById("report-why").textContent =
    secs["Why"] || secs["why"] || (diag.symptoms ? diag.symptoms.join("; ") : "Evidence from sensor signals.");
  document.getElementById("report-checks").textContent =
    secs["Recommended Checks"] || secs["recommended_checks"] ||
    "1. Check field sensor connections.\n2. Isolate power (LOTO).\n3. Consult operating manual.";
  document.getElementById("report-confidence").textContent =
    secs["Confidence and Limitations"] || secs["confidence_limitations"] || "Confidence: High (ISO Grounded).";

  if (diag.latency_seconds) {
    document.getElementById("diag-latency").textContent =
      `Inference latency: ${diag.latency_seconds.toFixed(2)}s`;
  }
  if (diag.runtime) {
    document.getElementById("diag-runtime-tag").textContent = `Runtime: ${diag.runtime}`;
  }

  const list = document.getElementById("report-sources");
  list.innerHTML = "";
  (diag.retrieved_sources || []).forEach((src) => {
    const li = document.createElement("li");
    li.className = "source-row";
    const name = document.createElement("span");
    name.textContent = src.source;
    const score = document.createElement("span");
    score.className = "score";
    score.textContent = typeof src.score === "number" ? src.score.toFixed(2) : String(src.score ?? "");
    li.append(name, score);
    list.appendChild(li);
  });
}

/* ---------- Fault injection ---------- */
function setMode(mode, submode = "flatline") {
  fetch(`${API_BASE}/api/mode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, submode }),
  })
    .then((res) => res.json())
    .then(() => {
      updateActiveButton(mode, submode);
      if (mode === "normal") {
        setHero("ok");
        document.getElementById("diag-meta-time").textContent = "Monitoring — no active fault";
      }
    })
    .catch((err) => console.error("Error setting mode:", err));
}

function updateActiveButton(mode, submode = "flatline") {
  document.querySelectorAll(".btn-mode").forEach((b) => {
    b.classList.remove("active");
    b.setAttribute("aria-pressed", "false");
  });

  let id = null;
  if (mode === "normal") id = "btn-mode-normal";
  else if (mode === "bearing_wear") id = "btn-mode-bearing";
  else if (mode === "overheating") id = "btn-mode-overheat";
  else if (mode === "pressure_drop") id = "btn-mode-pressure";
  else if (mode === "sensor_failure") id = submode === "disconnect" ? "btn-mode-disconnect" : "btn-mode-flatline";

  const btn = id && document.getElementById(id);
  if (btn) {
    btn.classList.add("active");
    btn.setAttribute("aria-pressed", "true");
  }
}

/* ---------- Incident log ---------- */
function td(text, className) {
  const cell = document.createElement("td");
  if (className) cell.className = className;
  cell.textContent = text;
  return cell;
}

function loadHistoryTable() {
  fetch(`${API_BASE}/api/diagnoses`)
    .then((res) => res.json())
    .then((records) => {
      const tbody = document.getElementById("history-table-body");
      tbody.innerHTML = "";

      if (!records || records.length === 0) {
        const tr = document.createElement("tr");
        tr.appendChild(Object.assign(td("[ No incidents ]", "empty-table"), { colSpan: 5 }));
        tbody.appendChild(tr);
        historyRecords = [];
        return;
      }

      historyRecords = records.slice(0, 10);
      historyRecords.forEach((rec, i) => {
        const r = rec.readings || {};
        const num = (x, d) => (typeof x === "number" ? x.toFixed(d) : "-");
        const top = rec.retrieved_sources && rec.retrieved_sources[0] ? rec.retrieved_sources[0].source : "N/A";

        const tr = document.createElement("tr");
        tr.appendChild(td(new Date(rec.timestamp).toLocaleTimeString()));
        tr.appendChild(td(String(rec.fault_category || "").replace(/_/g, " "), "history-badge"));
        tr.appendChild(td(`T ${num(r.temperature, 1)} · V ${num(r.vibration, 2)} · P ${num(r.pressure, 2)}`));
        tr.appendChild(td(top));

        const action = document.createElement("td");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn-ghost";
        btn.textContent = "Inspect";
        btn.addEventListener("click", () => renderDiagnosis(historyRecords[i], { historic: true }));
        action.appendChild(btn);
        tr.appendChild(action);

        tbody.appendChild(tr);
      });
    })
    .catch((err) => console.warn("Error loading history table:", err));
}
