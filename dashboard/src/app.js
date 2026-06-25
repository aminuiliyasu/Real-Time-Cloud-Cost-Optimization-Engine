const API_BASE_STORAGE_KEY = "rtcco_dashboard_api_base";
const DEFAULT_DEV_API_KEY = "change_me_strong_key";
const WORKFLOW_ACTOR = "finops-dashboard";

const kpisNode = document.getElementById("kpis");
const hoursNode = document.getElementById("hours");
const hoursLabelNode = document.getElementById("hours-label");
const refreshOverviewNode = document.getElementById("refresh-overview");
const chartNode = document.getElementById("trend-chart");
const chartNoteNode = document.getElementById("chart-note");
const recommendationsBodyNode = document.getElementById("recommendations-body");
const resourcesBodyNode = document.getElementById("resources-body");
const apiBaseNode = document.getElementById("api-base");
const actionsNoteNode = document.getElementById("actions-note");
const reloadRecommendationsNode = document.getElementById("reload-recommendations");
const statusBannerNode = document.getElementById("status-banner");
const healthInlineNode = document.getElementById("health-inline");
const heroStatsNode = document.getElementById("hero-stats");
const accountsGridNode = document.getElementById("accounts-grid");
const optBreakdownNode = document.getElementById("opt-breakdown");
const simCardNode = document.getElementById("sim-card");
const simCardDescNode = document.getElementById("sim-card-desc");
const simReductionNode = document.getElementById("sim-reduction");
const simReductionLabelNode = document.getElementById("sim-reduction-label");
const simRunNode = document.getElementById("sim-run");
const simResultNode = document.getElementById("sim-result");
const simCloseNode = document.getElementById("sim-close");
const simHistoryWrapNode = document.getElementById("sim-history-wrap");
const simHistoryNode = document.getElementById("sim-history");
const runPipelineNode = document.getElementById("btn-run-pipeline");
const runAllRulesNode = document.getElementById("run-all-rules");

let activeSimulationRecId = null;

function getApiBase() {
  const raw = apiBaseNode.value.trim() || "http://127.0.0.1:8000";
  return raw.replace(/\/$/, "");
}

function getApiKey() {
  try {
    const fromQuery = new URLSearchParams(window.location.search).get("api_key");
    if (fromQuery && fromQuery.trim()) return fromQuery.trim();
  } catch {
    /* ignore */
  }
  return DEFAULT_DEV_API_KEY;
}

function persistApiBase() {
  try {
    localStorage.setItem(API_BASE_STORAGE_KEY, getApiBase());
  } catch {
    /* ignore */
  }
}

function loadStoredApiBase() {
  try {
    const stored = localStorage.getItem(API_BASE_STORAGE_KEY);
    if (stored) apiBaseNode.value = stored;
  } catch {
    /* ignore */
  }
}

function setStatusBanner(message, kind) {
  if (!message) {
    statusBannerNode.hidden = true;
    statusBannerNode.textContent = "";
    statusBannerNode.classList.remove("is-error", "is-success", "is-info");
    return;
  }
  statusBannerNode.hidden = false;
  statusBannerNode.textContent = message;
  statusBannerNode.classList.remove("is-error", "is-success", "is-info");
  if (kind === "error") statusBannerNode.classList.add("is-error");
  if (kind === "success") statusBannerNode.classList.add("is-success");
  if (kind === "info") statusBannerNode.classList.add("is-info");
}

function setButtonBusy(button, busy) {
  if (!button) return;
  if (busy) {
    if (!button.dataset.defaultLabel) button.dataset.defaultLabel = button.textContent.trim();
    button.classList.add("is-busy");
    button.disabled = true;
  } else {
    button.classList.remove("is-busy");
    button.disabled = false;
    if (button.dataset.defaultLabel) button.textContent = button.dataset.defaultLabel;
  }
}

function fmtMoney(value) {
  return `$${Number(value || 0).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function fetchJson(path, options = {}) {
  const res = await fetch(`${getApiBase()}${path}`, options);
  const text = await res.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const detail = body && typeof body === "object" && body.detail !== undefined ? body.detail : body;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

function adminHeaders() {
  return { "X-API-Key": getApiKey(), "X-Role": "admin" };
}

function renderHero(portfolio) {
  if (!portfolio) {
    heroStatsNode.innerHTML = `
      <article class="hero-stat hero-stat-muted">
        <span class="hero-stat-value">—</span>
        <span class="hero-stat-label">Run analysis to load live AWS data</span>
      </article>`;
    return;
  }

  const cards = [
    [fmtMoney(portfolio.annual_waste_identified), "Annual waste identified"],
    [`${portfolio.accounts_monitored}`, "Cloud accounts"],
    [`${portfolio.manual_review_reduction_pct}%`, "Less manual review time"],
    [fmtMoney(portfolio.monthly_waste_identified), "Monthly savings potential"],
    [`${portfolio.open_recommendations}`, "Open recommendations"],
    [fmtMoney(portfolio.realized_monthly_savings), "Realized / month"],
  ];

  heroStatsNode.innerHTML = cards
    .map(
      ([value, label]) => `
      <article class="hero-stat">
        <span class="hero-stat-value">${value}</span>
        <span class="hero-stat-label">${label}</span>
      </article>`
    )
    .join("");
}

function renderAccounts(portfolio) {
  const accounts = portfolio?.accounts || [];
  if (!accounts.length) {
    accountsGridNode.innerHTML =
      '<p class="table-empty">No accounts yet. Click <strong>Run full analysis</strong> to ingest from AWS.</p>';
    return;
  }
  accountsGridNode.innerHTML = accounts
    .map(
      (a) => `
    <article class="account-card">
      <span class="account-provider">${escapeHtml(a.cloud_provider.toUpperCase())}</span>
      <span class="account-id">${escapeHtml(a.account_id)}</span>
      <dl class="account-meta">
        <div><dt>Resources</dt><dd>${a.resource_count}</dd></div>
        <div><dt>Open recs</dt><dd>${a.open_recommendations}</dd></div>
        <div><dt>Potential</dt><dd>${fmtMoney(a.monthly_savings_potential)}/mo</dd></div>
      </dl>
    </article>`
    )
    .join("");
}

function renderOptBreakdown(portfolio) {
  const b = portfolio?.optimization_breakdown;
  if (!b) {
    optBreakdownNode.innerHTML = "";
    return;
  }
  const items = [
    ["Rightsizing", b.rightsizing, "Downsize over-provisioned compute"],
    ["Scheduled shutdowns", b.scheduled_shutdown, "Off-hours stop for idle workloads"],
    ["Migrations", b.migration, "Move to smaller instance families"],
    ["Other", b.other, "Additional optimizations"],
  ];
  optBreakdownNode.innerHTML = items
    .map(
      ([title, count, desc]) => `
    <article class="opt-item">
      <span class="opt-count">${count}</span>
      <div>
        <h3 class="opt-title">${title}</h3>
        <p class="opt-desc">${desc}</p>
      </div>
    </article>`
    )
    .join("");
}

function renderKpis(kpis) {
  const cards = [
    ["Resources", kpis.total_resources],
    ["Recommendations", kpis.total_recommendations],
    ["Open", kpis.open_recommendations],
    ["Executed", kpis.executed_recommendations],
    ["Potential / mo", fmtMoney(kpis.total_estimated_monthly_savings)],
    ["Realized / mo", fmtMoney(kpis.realized_monthly_savings)],
  ];
  kpisNode.innerHTML = cards
    .map(([label, value]) => `<article class="kpi"><div class="label">${label}</div><div class="value">${value}</div></article>`)
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
    <polyline fill="none" stroke="#5b8def" stroke-width="2" points="${cpuLine}" />
    <polyline fill="none" stroke="#6dd4b0" stroke-width="2" points="${memoryLine}" />
  `;
  chartNoteNode.textContent = points.length
    ? `${points.length} hourly data points from CloudWatch`
    : "No metrics yet — run full analysis to pull live AWS data.";
}

function severityClass(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "high" || s === "critical") return "severity-high";
  if (s === "medium") return "severity-medium";
  return "severity-low";
}

function friendlyAction(action) {
  const map = {
    rightsizing_downsize_instance: "Rightsize instance",
    reduce_task_size_or_scale_schedule: "Rightsize ECS tasks",
    schedule_shutdown_weeknights: "Schedule shutdown",
    migrate_to_smaller_instance_family: "Migrate instance type",
  };
  return map[action] || action || "—";
}

function friendlyRule(rule) {
  const map = {
    idle_vm: "Idle VM",
    ecs_underutilized_service: "ECS underutilized",
    scheduled_shutdown: "Scheduled shutdown",
    migration_candidate: "Migration candidate",
  };
  return map[rule] || rule;
}

function renderRecommendations(recommendations) {
  if (!recommendations.length) {
    recommendationsBodyNode.innerHTML =
      '<tr><td colspan="6" class="table-empty">No recommendations yet. Run <strong>full analysis</strong> or <strong>all rules</strong>.</td></tr>';
    return;
  }
  recommendationsBodyNode.innerHTML = recommendations
    .map((rec) => {
      const canApprove = rec.status === "open";
      const canExecute = rec.status === "approved";
      return `
      <tr>
        <td>${escapeHtml(friendlyRule(rec.rule_name))}</td>
        <td>${escapeHtml(friendlyAction(rec.action))}</td>
        <td><span class="sev ${severityClass(rec.severity)}">${escapeHtml(rec.severity || "—")}</span></td>
        <td><span class="badge ${rec.status}">${rec.status}</span></td>
        <td>${fmtMoney(rec.estimated_monthly_savings)}</td>
        <td class="workflow-cell">
          <button type="button" class="btn btn-sm btn-ghost" data-simulate="${rec.id}">What-if</button>
          <button type="button" class="btn btn-sm btn-secondary" data-action="approve" data-id="${rec.id}" ${canApprove ? "" : "disabled"}>Approve</button>
          <button type="button" class="btn btn-sm btn-primary" data-action="execute" data-id="${rec.id}" ${canExecute ? "" : "disabled"}>Apply</button>
        </td>
      </tr>`;
    })
    .join("");
}

function renderResources(resources) {
  if (!resources.length) {
    resourcesBodyNode.innerHTML =
      '<tr><td colspan="5" class="table-empty">No resources yet. Run <strong>full analysis</strong> to discover AWS inventory.</td></tr>';
    return;
  }
  resourcesBodyNode.innerHTML = resources
    .map(
      (r) => `
    <tr>
      <td>${escapeHtml(r.cloud_provider)}</td>
      <td><code>${escapeHtml(r.account_id || "—")}</code></td>
      <td>${escapeHtml(r.resource_type)}</td>
      <td><code>${escapeHtml(r.resource_id)}</code></td>
      <td>${escapeHtml(r.region || "—")}</td>
    </tr>`
    )
    .join("");
}

async function loadPortfolio() {
  return fetchJson("/dashboard/portfolio").catch(() => null);
}

async function loadOverview() {
  const hours = Number(hoursNode.value || 24);
  hoursLabelNode.textContent = hours >= 168 ? "7 days" : `${hours} hours`;
  const [kpis, trends, portfolio, resources] = await Promise.all([
    fetchJson("/dashboard/kpis"),
    fetchJson(`/dashboard/trends?hours=${hours}`),
    loadPortfolio(),
    fetchJson("/resources").catch(() => []),
  ]);
  renderHero(portfolio);
  renderAccounts(portfolio);
  renderOptBreakdown(portfolio);
  renderKpis(kpis);
  renderChart(trends.points || []);
  renderResources(Array.isArray(resources) ? resources : []);
}

async function loadRecommendations() {
  const recommendations = await fetchJson("/recommendations");
  renderRecommendations(recommendations);
}

async function mutateRecommendation(id, action) {
  const res = await fetch(`${getApiBase()}/recommendations/${id}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": getApiKey(),
      "X-Role": action === "approve" ? "operator" : "admin",
    },
    body: JSON.stringify({
      actor: WORKFLOW_ACTOR,
      notes: action === "approve" ? "approved from dashboard" : "executed from dashboard",
    }),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload.detail || `Failed to ${action} recommendation ${id}`);
}

function chartHours() {
  return Number(hoursNode.value || 24);
}

function openSimulationPanel(recId) {
  activeSimulationRecId = recId;
  simCardNode.hidden = false;
  simCardDescNode.textContent = `Recommendation #${recId} — adjust reduction %, then run what-if.`;
  simResultNode.innerHTML = "";
  simHistoryWrapNode.hidden = true;
  simHistoryNode.innerHTML = "";
  simCardNode.scrollIntoView({ behavior: "smooth", block: "nearest" });
  void loadSimulationHistory(recId);
}

function closeSimulationPanel() {
  activeSimulationRecId = null;
  simCardNode.hidden = true;
}

async function loadSimulationHistory(recId) {
  try {
    const runs = await fetchJson(`/recommendations/${recId}/simulations`);
    if (!Array.isArray(runs) || !runs.length) {
      simHistoryWrapNode.hidden = true;
      return;
    }
    simHistoryWrapNode.hidden = false;
    simHistoryNode.innerHTML = runs
      .slice(0, 6)
      .map(
        (r) =>
          `<li>${r.reduction_percent}% reduction → save ${fmtMoney(r.projected_monthly_savings)}/mo, risk <strong>${escapeHtml(r.risk_level)}</strong></li>`
      )
      .join("");
  } catch {
    simHistoryWrapNode.hidden = true;
  }
}

function renderSimulationOut(data) {
  if (!data) return;
  simResultNode.innerHTML = `
    <dl class="sim-dl">
      <div><dt>Current / mo</dt><dd>${fmtMoney(data.current_monthly_cost)}</dd></div>
      <div><dt>Projected / mo</dt><dd>${fmtMoney(data.projected_monthly_cost)}</dd></div>
      <div><dt>Savings / mo</dt><dd>${fmtMoney(data.projected_monthly_savings)}</dd></div>
      <div><dt>Risk</dt><dd>${escapeHtml(data.risk_level)}</dd></div>
    </dl>`;
}

async function postAdminJson(path, query = "") {
  return fetchJson(`${path}${query}`, { method: "POST", headers: adminHeaders() });
}

async function runAllRules() {
  await postAdminJson("/dev/recommendations/run-ecs-underutilized-rule");
  await postAdminJson("/dev/recommendations/run-idle-vm-rule");
  await postAdminJson("/dev/recommendations/run-scheduled-shutdown-rule");
  await postAdminJson("/dev/recommendations/run-migration-candidate-rule");
}

async function refreshAll() {
  await Promise.all([loadOverview(), loadRecommendations()]);
}

refreshOverviewNode.addEventListener("click", () => {
  setButtonBusy(refreshOverviewNode, true);
  refreshAll()
    .then(() => setStatusBanner("Dashboard updated.", "success"))
    .catch((err) => setStatusBanner(err.message, "error"))
    .finally(() => setButtonBusy(refreshOverviewNode, false));
});

hoursNode.addEventListener("change", () => {
  loadOverview().catch((err) => setStatusBanner(err.message, "error"));
});

runPipelineNode.addEventListener("click", async () => {
  setButtonBusy(runPipelineNode, true);
  setStatusBanner("Running full analysis on live AWS…", "info");
  try {
    const h = chartHours();
    await postAdminJson("/dev/pipeline/run-full-analysis", `?hours=${h}`);
    await refreshAll();
    setStatusBanner("Full analysis complete — resources ingested, rules run, savings calculated.", "success");
  } catch (e) {
    setStatusBanner(e.message, "error");
  } finally {
    setButtonBusy(runPipelineNode, false);
  }
});

runAllRulesNode.addEventListener("click", async () => {
  setButtonBusy(runAllRulesNode, true);
  try {
    await runAllRules();
    await refreshAll();
    setStatusBanner("All optimization rules executed.", "success");
  } catch (e) {
    setStatusBanner(e.message, "error");
  } finally {
    setButtonBusy(runAllRulesNode, false);
  }
});

reloadRecommendationsNode.addEventListener("click", () => {
  setButtonBusy(reloadRecommendationsNode, true);
  loadRecommendations()
    .then(() => setStatusBanner("Recommendations reloaded.", "success"))
    .catch((err) => setStatusBanner(err.message, "error"))
    .finally(() => setButtonBusy(reloadRecommendationsNode, false));
});

recommendationsBodyNode.addEventListener("click", async (event) => {
  const simBtn = event.target.closest("button[data-simulate]");
  if (simBtn) {
    openSimulationPanel(Number(simBtn.getAttribute("data-simulate")));
    return;
  }
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = button.getAttribute("data-id");
  const action = button.getAttribute("data-action");
  setButtonBusy(button, true);
  try {
    await mutateRecommendation(id, action);
    setStatusBanner(`Recommendation ${id} ${action === "approve" ? "approved" : "applied"}.`, "success");
    await refreshAll();
    if (activeSimulationRecId === Number(id)) await loadSimulationHistory(Number(id));
  } catch (err) {
    setStatusBanner(err.message, "error");
  } finally {
    setButtonBusy(button, false);
  }
});

simReductionNode.addEventListener("input", () => {
  simReductionLabelNode.textContent = `${simReductionNode.value}%`;
});

simCloseNode.addEventListener("click", closeSimulationPanel);

simRunNode.addEventListener("click", async () => {
  if (!activeSimulationRecId) return;
  setButtonBusy(simRunNode, true);
  try {
    const out = await fetchJson(`/recommendations/${activeSimulationRecId}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reduction_percent: Number(simReductionNode.value) }),
    });
    renderSimulationOut(out);
    setStatusBanner("What-if simulation complete.", "success");
    await loadSimulationHistory(activeSimulationRecId);
  } catch (e) {
    simResultNode.innerHTML = `<p class="sim-error">${escapeHtml(e.message)}</p>`;
    setStatusBanner(e.message, "error");
  } finally {
    setButtonBusy(simRunNode, false);
  }
});

apiBaseNode.addEventListener("change", persistApiBase);
apiBaseNode.addEventListener("blur", persistApiBase);

document.getElementById("btn-list-resources").addEventListener("click", async () => {
  const btn = document.getElementById("btn-list-resources");
  setButtonBusy(btn, true);
  try {
    const list = await fetchJson("/resources");
    renderResources(list);
  } catch (e) {
    setStatusBanner(e.message, "error");
  } finally {
    setButtonBusy(btn, false);
  }
});

async function ingestAction(fn, label) {
  try {
    await fn();
    await refreshAll();
    setStatusBanner(label, "success");
  } catch (e) {
    setStatusBanner(e.message, "error");
  }
}

document.getElementById("ingest-aws-resources").addEventListener("click", () =>
  ingestAction(() => postAdminJson("/dev/ingest/aws/resources"), "EC2 discovery complete.")
);
document.getElementById("ingest-ecs-resources").addEventListener("click", () =>
  ingestAction(() => postAdminJson("/dev/ingest/aws/ecs/resources"), "ECS discovery complete.")
);
document.getElementById("ingest-aws-metrics").addEventListener("click", async () => {
  const h = chartHours();
  await ingestAction(
    () =>
      Promise.all([
        postAdminJson("/dev/ingest/aws/metrics", `?hours=${h}`),
        postAdminJson("/dev/ingest/aws/ecs/metrics", `?hours=${h}`),
      ]),
    "Metrics ingested from AWS."
  );
});

document.getElementById("btn-health").addEventListener("click", async () => {
  const btn = document.getElementById("btn-health");
  setButtonBusy(btn, true);
  healthInlineNode.hidden = false;
  const checks = [
    ["API", "/health"],
    ["Database", "/db-check"],
    ["Redis", "/redis-check"],
  ];
  const lines = [];
  for (const [label, path] of checks) {
    try {
      await fetchJson(path);
      lines.push(`<p class="health-line health-ok">✓ ${label}</p>`);
    } catch (e) {
      lines.push(`<p class="health-line health-bad">✗ ${label} — ${escapeHtml(e.message)}</p>`);
    }
  }
  healthInlineNode.innerHTML = lines.join("");
  setButtonBusy(btn, false);
});

loadStoredApiBase();
Promise.all([loadOverview(), loadRecommendations()]).catch((err) => {
  setStatusBanner(err.message, "error");
});
