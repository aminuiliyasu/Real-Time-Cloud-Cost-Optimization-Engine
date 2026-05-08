const API_BASE = "http://127.0.0.1:8000";

const kpisNode = document.getElementById("kpis");
const hoursNode = document.getElementById("hours");
const refreshNode = document.getElementById("refresh");
const chartNode = document.getElementById("trend-chart");
const chartNoteNode = document.getElementById("chart-note");

function fmtMoney(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function renderKpis(kpis) {
  const cards = [
    ["Resources", kpis.total_resources],
    ["Recommendations", kpis.total_recommendations],
    ["Open", kpis.open_recommendations],
    ["Executed", kpis.executed_recommendations],
    ["Estimated Savings", fmtMoney(kpis.total_estimated_monthly_savings)],
    ["Realized Savings", fmtMoney(kpis.realized_monthly_savings)],
  ];

  kpisNode.innerHTML = cards
    .map(
      ([label, value]) => `
      <article class="kpi">
        <div class="label">${label}</div>
        <div class="value">${value}</div>
      </article>`
    )
    .join("");
}

function toLine(points, key, width, height, pad) {
  if (!points.length) return "";
  const values = points.map((p) => Number(p[key] || 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  return points
    .map((p, i) => {
      const x = pad + (i * (width - pad * 2)) / Math.max(points.length - 1, 1);
      const y = height - pad - ((Number(p[key] || 0) - min) / range) * (height - pad * 2);
      return `${x},${y}`;
    })
    .join(" ");
}

function renderChart(points) {
  const width = 1000;
  const height = 320;
  const pad = 24;

  const cpuLine = toLine(points, "avg_cpu_utilization", width, height, pad);
  const memoryLine = toLine(points, "avg_memory_utilization", width, height, pad);

  chartNode.innerHTML = `
    <polyline fill="none" stroke="#58a6ff" stroke-width="2" points="${cpuLine}" />
    <polyline fill="none" stroke="#3fb950" stroke-width="2" points="${memoryLine}" />
  `;

  chartNoteNode.textContent = points.length
    ? `Showing ${points.length} hourly points`
    : "No trend points available yet.";
}

async function loadDashboard() {
  const hours = Number(hoursNode.value || 24);
  const [kpisRes, trendsRes] = await Promise.all([
    fetch(`${API_BASE}/dashboard/kpis`),
    fetch(`${API_BASE}/dashboard/trends?hours=${hours}`),
  ]);

  if (!kpisRes.ok || !trendsRes.ok) {
    throw new Error("Failed to load dashboard data from API");
  }

  const kpis = await kpisRes.json();
  const trends = await trendsRes.json();
  renderKpis(kpis);
  renderChart(trends.points || []);
}

refreshNode.addEventListener("click", () => {
  loadDashboard().catch((err) => {
    chartNoteNode.textContent = err.message;
  });
});

loadDashboard().catch((err) => {
  chartNoteNode.textContent = err.message;
});
