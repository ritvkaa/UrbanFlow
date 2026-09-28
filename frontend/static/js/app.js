/**
 * UrbanFlow Frontend
 * Connects to FastAPI backend at /api/*
 */

const API = '';   // same origin
let autoTimer = null;
let historyData = [];
let lastReadings = [];

// ─── API helpers ─────────────────────────────────────────────────────────────

async function apiFetch(path, opts = {}) {
  try {
    const res = await fetch(API + path, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('API error', path, err);
    setConnStatus(false);
    throw err;
  }
}

function setConnStatus(ok) {
  const dot = document.getElementById('conn-dot');
  const lbl = document.getElementById('conn-label');
  if (ok) {
    dot.className = 'status-dot live';
    lbl.textContent = 'LIVE';
    document.getElementById('side-live-dot').className = 'side-live-dot live';
    document.getElementById('side-status').textContent = 'LIVE';
    document.getElementById('footer-status').textContent = '● SYSTEM NOMINAL';
    document.getElementById('footer-status').style.color = 'var(--accent2)';
  } else {
    dot.className = 'status-dot error';
    lbl.textContent = 'OFFLINE';
    document.getElementById('side-live-dot').className = 'side-live-dot error';
    document.getElementById('side-status').textContent = 'OFFLINE';
    document.getElementById('footer-status').textContent = '● BACKEND UNREACHABLE';
    document.getElementById('footer-status').style.color = 'var(--danger)';
  }
}

// ─── Clock ───────────────────────────────────────────────────────────────────

function updateClock() {
  const n = new Date();
  document.getElementById('clock').textContent =
    [n.getHours(), n.getMinutes(), n.getSeconds()]
      .map(v => String(v).padStart(2, '0')).join(':');
}
setInterval(updateClock, 1000);
updateClock();

// ─── Main refresh ────────────────────────────────────────────────────────────

async function refreshData() {
  document.getElementById('live-badge').textContent = 'REFRESHING…';
  try {
    const data = await apiFetch('/api/readings/refresh', { method: 'POST' });
    setConnStatus(true);
    lastReadings = data.readings;
    renderHeatmap(data.readings);
    renderBars(data.readings);
    renderAlerts(data.alerts);
    renderRoutes(data.routes);
    updateKPIs(data.metrics, data.alerts);
    await loadHistory();
    document.getElementById('live-badge').textContent = 'LIVE';
    document.getElementById('live-badge').className = 'panel-badge warn';
  } catch {
    document.getElementById('live-badge').textContent = 'ERROR';
    document.getElementById('live-badge').className = 'panel-badge danger';
  }
}

// ─── KPIs ────────────────────────────────────────────────────────────────────

function updateKPIs(metrics, alerts) {
  if (!metrics) return;
  document.getElementById('kpi-total').textContent = (metrics.total_people || 0).toLocaleString();
  document.getElementById('kpi-zones').textContent = `across ${metrics.total_zones} zones`;
  const clear = (metrics.total_zones || 0) - (metrics.congested_count || 0);
  document.getElementById('kpi-clear').textContent = clear;
  const active = alerts ? alerts.length : 0;
  document.getElementById('kpi-alerts').textContent = active;
  const crit = alerts ? alerts.filter(a => a.severity === 'CRITICAL').length : 0;
  document.getElementById('kpi-alert-sub').textContent = `${crit} critical`;
  document.getElementById('kpi-rate').textContent = (metrics.congestion_rate || 0) + '%';
  document.getElementById('kpi-rate-sub').textContent = `${metrics.congested_count || 0} zones congested`;

  // Keep the compact left dashboard synced with the existing KPIs.
  document.getElementById('side-total').textContent = (metrics.total_people || 0).toLocaleString();
  document.getElementById('side-rate').textContent = (metrics.congestion_rate || 0) + '%';
  document.getElementById('side-clear').textContent = clear;
  document.getElementById('side-alerts').textContent = active;

  const badge = document.getElementById('alert-badge');
  badge.textContent = `${active} ACTIVE`;
  badge.className = `panel-badge ${crit > 0 ? 'danger' : active > 0 ? 'warn' : ''}`;
}

// ─── Heatmap ─────────────────────────────────────────────────────────────────

function renderHeatmap(readings) {
  const grid = document.getElementById('zone-grid');

  grid.innerHTML = '';

  // ---------------------------------------------------------
  // Canvas
  // ---------------------------------------------------------
  const canvas = document.createElement('canvas');
  canvas.className = 'heatmap-canvas';

  grid.appendChild(canvas);

  const ctx = canvas.getContext('2d');

  // Make canvas match the displayed size
  const rect = grid.getBoundingClientRect();
  const width = Math.max(rect.width, 500);
  const height = Math.max(rect.height, 360);

  const dpr = window.devicePixelRatio || 1;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';

  ctx.scale(dpr, dpr);

  // ---------------------------------------------------------
  // Dark map background
  // ---------------------------------------------------------
  ctx.fillStyle = '#18251d';
  ctx.fillRect(0, 0, width, height);

  // Subtle pixel/map grid
  ctx.strokeStyle = 'rgba(180, 220, 150, 0.10)';
  ctx.lineWidth = 1;

  for (let x = 0; x < width; x += 32) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  for (let y = 0; y < height; y += 32) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // ---------------------------------------------------------
  // Map-like paths
  // ---------------------------------------------------------
  ctx.strokeStyle = 'rgba(220, 220, 170, 0.18)';
  ctx.lineWidth = 10;
  ctx.lineCap = 'round';

  ctx.beginPath();
  ctx.moveTo(width * 0.05, height * 0.82);
  ctx.bezierCurveTo(
    width * 0.25, height * 0.65,
    width * 0.35, height * 0.88,
    width * 0.55, height * 0.58
  );
  ctx.bezierCurveTo(
    width * 0.68, height * 0.38,
    width * 0.82, height * 0.52,
    width * 0.96, height * 0.18
  );
  ctx.stroke();

  ctx.lineWidth = 3;
  ctx.strokeStyle = 'rgba(255, 255, 220, 0.28)';
  ctx.stroke();

  // ---------------------------------------------------------
  // Density helpers
  // ---------------------------------------------------------
  const maxDensity = Math.max(
    ...readings.map(r => Number(r.density) || 0),
    2.5
  );

  function heatColor(value) {
    const t = Math.max(0, Math.min(value / maxDensity, 1));

    if (t < 0.25) {
      // green → yellow
      const p = t / 0.25;
      return [
        Math.round(40 + 215 * p),
        Math.round(190 + 45 * p),
        Math.round(90 - 50 * p)
      ];
    }

    if (t < 0.55) {
      // yellow → orange
      const p = (t - 0.25) / 0.30;
      return [
        255,
        Math.round(235 - 100 * p),
        Math.round(40 - 20 * p)
      ];
    }

    // orange → red
    const p = (t - 0.55) / 0.45;

    return [
      255,
      Math.round(135 - 105 * p),
      Math.round(20 - 15 * p)
    ];
  }

  // ---------------------------------------------------------
  // Position zones in a 5 × 4 spatial layout
  // ---------------------------------------------------------
  function getPosition(zoneId) {
    const match = String(zoneId).match(/^([A-D])([1-5])$/);

    if (!match) {
      return null;
    }

    const row = match[1].charCodeAt(0) - 65;
    const col = Number(match[2]) - 1;

    return {
      x: width * (0.10 + col * 0.20),
      y: height * (0.15 + row * 0.23)
    };
  }

  // ---------------------------------------------------------
  // Draw smooth heat fields
  // ---------------------------------------------------------
  readings.forEach(r => {
    const pos = getPosition(r.zone_id);

    if (!pos) return;

    const density = Number(r.density) || 0;
    const [red, green, blue] = heatColor(density);

    const radius = Math.min(width, height) * 0.27;

    const gradient = ctx.createRadialGradient(
      pos.x,
      pos.y,
      0,
      pos.x,
      pos.y,
      radius
    );

    gradient.addColorStop(
      0,
      `rgba(${red}, ${green}, ${blue}, 0.92)`
    );

    gradient.addColorStop(
      0.25,
      `rgba(${red}, ${green}, ${blue}, 0.65)`
    );

    gradient.addColorStop(
      0.55,
      `rgba(${red}, ${green}, ${blue}, 0.28)`
    );

    gradient.addColorStop(
      1,
      `rgba(${red}, ${green}, ${blue}, 0)`
    );

    ctx.fillStyle = gradient;

    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
    ctx.fill();
  });

  // ---------------------------------------------------------
  // Zone markers + invisible hover areas
  // ---------------------------------------------------------
  readings.forEach(r => {
    const pos = getPosition(r.zone_id);

    if (!pos) return;

    // Small location marker
    ctx.fillStyle = '#fff4c4';
    ctx.strokeStyle = '#33281d';
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.arc(pos.x, pos.y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Zone label
    ctx.font = 'bold 12px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    ctx.fillStyle = '#fff4c4';
    ctx.strokeStyle = 'rgba(0,0,0,0.8)';
    ctx.lineWidth = 3;

    ctx.strokeText(r.zone_id, pos.x, pos.y - 18);
    ctx.fillText(r.zone_id, pos.x, pos.y - 18);

    // Invisible hover area
    const hit = document.createElement('div');

    hit.className = 'heat-zone-hit';

    hit.style.left = (pos.x - 45) + 'px';
    hit.style.top = (pos.y - 45) + 'px';
    hit.style.width = '90px';
    hit.style.height = '90px';

    hit.addEventListener('mousemove', e => showTooltip(e, r));
    hit.addEventListener('mouseleave', hideTooltip);

    grid.appendChild(hit);
  });
}

// ─── Bar chart ───────────────────────────────────────────────────────────────

function renderBars(readings) {
  const chart = document.getElementById('bar-chart');
  chart.innerHTML = '';
  const maxCount = Math.max(...readings.map(r => r.people_count), 1);
  readings.forEach(r => {
    const pct = Math.round((r.people_count / maxCount) * 100);
    const col = document.createElement('div');
    col.className = 'bar-col';
    col.innerHTML = `
      <div class="bar-value">${r.people_count}</div>
      <div class="bar-track">
        <div class="bar-fill ${r.status.toLowerCase()}" style="height:${pct}%"></div>
      </div>
      <div class="bar-label">${r.zone_id}</div>
    `;
    chart.appendChild(col);
  });
}

// ─── Alert feed ──────────────────────────────────────────────────────────────

const ALERT_ICONS = { CRITICAL: '🔴', WARNING: '🟡', INFO: 'ℹ️' };

function renderAlerts(alerts) {
  const wrap = document.getElementById('alerts-wrap');
  if (!alerts || alerts.length === 0) {
    wrap.innerHTML = '<div class="loading-msg">✅ No active alerts.</div>';
    return;
  }
  wrap.innerHTML = '';
  alerts.forEach(a => {
    const ts = new Date(a.timestamp).toLocaleTimeString();
    const div = document.createElement('div');
    div.className = `alert-item ${a.severity}`;
    div.dataset.id = a.id || '';
    div.innerHTML = `
      <span class="alert-icon">${ALERT_ICONS[a.severity] || 'ℹ️'}</span>
      <div class="alert-body">
        <div class="alert-title">${a.severity}: Zone ${a.zone_id} – ${a.alert_type}</div>
        <div class="alert-msg">${a.message}</div>
        <div class="alert-suggestion">→ ${a.suggestion}</div>
      </div>
      <span class="alert-time">${ts}</span>
    `;
    if (a.id) {
      div.title = 'Click to acknowledge';
      div.onclick = () => ackAlert(a.id, div);
    }
    wrap.appendChild(div);
  });
}

async function ackAlert(id, el) {
  try {
    await apiFetch(`/api/alerts/${id}/ack`, { method: 'POST' });
    el.classList.add('acked');
  } catch { /* ignore */ }
}

// ─── Route suggestions ───────────────────────────────────────────────────────

const ROUTE_ICONS = ['↗', '↙', '↖', '↗'];

function renderRoutes(routes) {
  const wrap = document.getElementById('routes-wrap');
  wrap.innerHTML = '';
  if (!routes || !routes.length) {
    wrap.innerHTML = '<div class="loading-msg">No routes loaded.</div>';
    return;
  }
  routes.forEach((r, i) => {
    const div = document.createElement('div');
    div.className = 'route-item';
    div.innerHTML = `
      <span class="route-icon">${ROUTE_ICONS[i % 4]}</span>
      <div class="route-info">
        <div class="route-name">${r.route_name}</div>
        <div class="route-via">via ${r.via_zones}</div>
        <div class="route-score">Score: ${r.score}/100</div>
      </div>
      <span class="route-status ${r.status}">${r.status}</span>
    `;
    wrap.appendChild(div);
  });
}

// ─── Trend / History chart ───────────────────────────────────────────────────

async function loadHistory() {
  const zoneId = document.getElementById('history-zone').value;
  const url = zoneId ? `/api/history?zone_id=${zoneId}&limit=60` : `/api/history?limit=120`;
  try {
    const data = await apiFetch(url);
    historyData = data;
    renderTrend(data, zoneId);
  } catch { /* skip */ }
}

function renderTrend(data, zoneId) {
  const canvas = document.getElementById('trend-canvas');
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth || 800;
  canvas.height = 80;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!data.length) return;

  // Average density per timestamp if no zone selected
  let points;
  if (zoneId) {
    points = data.map(r => r.density);
  } else {
    const byTs = {};
    data.forEach(r => {
      const t = r.timestamp;
      if (!byTs[t]) byTs[t] = [];
      byTs[t].push(r.density);
    });
    points = Object.values(byTs).map(arr => arr.reduce((a, b) => a + b, 0) / arr.length);
  }

  if (!points.length) return;

  const maxD = Math.max(...points, 3);
  const w = canvas.width, h = canvas.height;
  const pad = 4;

  // Threshold line
  const threshY = h - pad - ((1.5 / maxD) * (h - pad * 2));
  ctx.strokeStyle = 'rgba(255,58,92,0.5)';
  ctx.setLineDash([6, 4]);
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, threshY);
  ctx.lineTo(w, threshY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Area fill
  ctx.beginPath();
  points.forEach((d, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = h - pad - (d / maxD) * (h - pad * 2);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath();
  ctx.fillStyle = 'rgba(0,200,255,0.07)';
  ctx.fill();

  // Line
  ctx.beginPath();
  ctx.strokeStyle = '#00c8ff';
  ctx.lineWidth = 2;
  points.forEach((d, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = h - pad - (d / maxD) * (h - pad * 2);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────

function showTooltip(e, r) {
  const tt = document.getElementById('tooltip');
  document.getElementById('tt-title').textContent = `Zone ${r.zone_id}`;
  document.getElementById('tt-count').innerHTML = `<span>${r.people_count}</span>`;
  document.getElementById('tt-density').innerHTML = `<span>${r.density}</span>`;
  document.getElementById('tt-status').innerHTML = `<span>${r.status}</span>`;
  document.getElementById('tt-anomaly').innerHTML = `<span>${r.anomaly ? '⚡ YES' : 'No'}</span>`;
  tt.style.left = (e.clientX + 14) + 'px';
  tt.style.top = (e.clientY - 10) + 'px';
  tt.classList.add('visible');
}

function hideTooltip() {
  document.getElementById('tooltip').classList.remove('visible');
}

// ─── Simulation controls ─────────────────────────────────────────────────────

async function triggerSpike() {
  await apiFetch('/api/simulate/spike', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(['C4', 'A2', 'B4', 'C2']),
  });
  await refreshData();
}

async function clearSpike() {
  await apiFetch('/api/simulate/clear', { method: 'POST' });
  await refreshData();
}

// ─── Auto refresh ────────────────────────────────────────────────────────────

function toggleAuto(on) {
  if (autoTimer) clearInterval(autoTimer);
  if (on) autoTimer = setInterval(refreshData, 10000);
}

// ─── CSV upload ──────────────────────────────────────────────────────────────

document.getElementById('csv-input').addEventListener('change', async function () {
  const file = this.files[0];
  if (!file) return;

  const msg = document.getElementById('upload-msg');

  try {
    msg.textContent = 'Reading CSV…';

    const text = await file.text();

    const lines = text.split(/\r?\n/).filter(line => line.trim());

    if (lines.length < 2) {
      throw new Error('CSV is empty.');
    }

    // Parse header
    const headers = lines[0]
      .split(',')
      .map(h => h.trim().toLowerCase().replace(/\s+/g, '_'));

    const locationIndex = headers.indexOf('location_id');

    const countCandidates = [
      'total_of_directions',
      'pedestrian_count',
      'pedestrians',
      'footfall',
      'count',
      'people_count',
      'people'
    ];

    const countIndex = countCandidates
      .map(name => headers.indexOf(name))
      .find(index => index !== -1);

    if (locationIndex === -1) {
      throw new Error('Location_ID column not found.');
    }

    if (countIndex === undefined) {
      throw new Error('Pedestrian count column not found.');
    }

    // Aggregate pedestrian counts by Location_ID
    const totals = {};

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',');

      const location = values[locationIndex]?.trim();
      const count = Number(values[countIndex]);

      if (!location || !Number.isFinite(count)) continue;

      if (!totals[location]) {
        totals[location] = {
          location_id: location,
          total: 0,
          rows: 0
        };
      }

      totals[location].total += count;
      totals[location].rows += 1;
    }

    const aggregated = Object.values(totals);

    if (!aggregated.length) {
      throw new Error('No valid Location_ID / pedestrian count data found.');
    }

    // Convert aggregated data into the format expected by the existing backend
    let csv = 'Location_ID,Total_of_Directions\n';

    aggregated.forEach(item => {
      const average = item.total / item.rows;

      csv += `${item.location_id},${average}\n`;
    });

    msg.textContent = `Processing ${aggregated.length} locations…`;

    // Send only the tiny aggregated CSV to the existing endpoint
    const blob = new Blob([csv], { type: 'text/csv' });
    const form = new FormData();
    form.append('file', blob, 'urbanflow_aggregated.csv');

    const res = await apiFetch('/api/readings/upload', {
      method: 'POST',
      body: form
    });

    msg.textContent = `✓ ${res.rows_processed} zones processed. Refreshing…`;

    await refreshData();

  } catch (error) {
    console.error('CSV upload error:', error);
    msg.textContent = `✗ ${error.message || 'Upload failed'}`;
  }

  this.value = '';
});

// ─── Populate zone selector ───────────────────────────────────────────────────

async function populateZoneSelector() {
  try {
    const zones = await apiFetch('/api/zones');
    const sel = document.getElementById('history-zone');
    zones.forEach(z => {
      const opt = document.createElement('option');
      opt.value = z.zone_id;
      opt.textContent = `${z.zone_id} – ${z.name}`;
      sel.appendChild(opt);
    });
  } catch { /* skip */ }
}

// ─── Boot ────────────────────────────────────────────────────────────────────

(async () => {
  await populateZoneSelector();
  await refreshData();
})();

window.addEventListener('resize', () => {
  if (historyData.length) renderTrend(historyData, document.getElementById('history-zone').value);
});
