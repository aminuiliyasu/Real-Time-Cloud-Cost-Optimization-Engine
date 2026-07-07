const API_BASE_KEY = "rtcco_api_base";
const API_KEY_KEY = "rtcco_api_key";

const $ = (id) => document.getElementById(id);

const nodes = {
  apiBase: $("api-base"),
  apiKey: $("api-key"),
  status: $("status-banner"),
  health: $("health-inline"),
  hero: $("hero-stats"),
  accounts: $("accounts-grid"),
  opt: $("opt-breakdown"),
  kpis: $("kpis"),
  hours: $("hours"),
  chart: $("trend-chart"),
  chartNote: $("chart-note"),
  resources: $("resources-body"),
  recommendations: $("recommendations-body"),
  simCard: $("sim-card"),
  simDesc: $("sim-card-desc"),
  simReduction: $("sim-reduction"),
  simLabel: $("sim-reduction-label"),
  simResult: $("sim-result"),
  simHistoryWrap: $("sim-history-wrap"),
  simHistory: $("sim-history"),
};

let activeSimRecId = null;

function apiBase() {
  return (nodes.apiBase.value.trim() || "http://127.0.0.1:8000").replace(/\/$/, "");
}

function apiKey() {
  if (nodes.apiKey.value.trim()) return nodes.apiKey.value.trim();
  const fromQuery = new URLSearchParams(location.search).get("api_key");
  if (fromQuery) {
    localStorage.setItem(API_KEY_KEY, fromQuery.trim());
    return fromQuery.trim();
  }
  return localStorage.getItem(API_KEY_KEY) || "";
}

function adminHeaders() {
  return { "X-API-Key": apiKey(), "X-Role": "admin" };
}

function setStatus(message, kind) {
  if (!message) {
    nodes.status.hidden = true;
    nodes.status.textContent = "";
    nodes.status.className = "banner";
    return;
  }
  nodes.status.hidden = false;
  nodes.status.textContent = message;
  nodes.status.className = `banner is-${kind || "info"}`;
}

function setBusy(button, busy) {
  if (!button) return;
  button.disabled = busy;
}

function money(value) {
  return `$${Number(value || 0).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function esc(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

async function fetchJson(path, options = {}) {
  const res = await fetch(`${apiBase()}${path}`, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = body.detail ?? res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

function renderHero(portfolio) {
  if (!portfolio) {
    nodes.hero.innerHTML = `<div class="stat"><span class="stat-value">—</span><span class="stat-label">Run analysis to load data</span></div>`;
    return;
  }

  const lastSync = portfolio.last_sync_at
    ? new Date(portfolio.last_sync_at).toLocaleString()
    : "Not synced yet";

  const items = [
    [money(portfolio.annual_waste_identified), "Annual waste identified"],
    [`${portfolio.accounts_monitored}`, "Accounts monitored"],
    [`${portfolio.automated_coverage_pct}%`, "Resources with findings"],
    [money(portfolio.monthly_waste_identified), "Monthly potential"],
    [`${portfolio.open_recommendations}`, "Open recommendations"],
    [lastSync, "Last metric sync"],
  ];

  nodes.hero.innerHTML = items
    .map(
      ([value, label]) =>
        `<div class="stat"><span class="stat-value">${esc(value)}</span><span class="stat-label">${esc(label)}</span></div>`
    )
    .join("");
}

function renderAccounts(portfolio) {
  const accounts = portfolio?.accounts || [];
  if (!accounts.length) {
    nodes.accounts.innerHTML = `<p class="muted">No accounts yet. Run full analysis.</p>`;
    return;
  }
  nodes.accounts.innerHTML = accounts
    .map(
      (a) => `
      <article class="account-card">
        <span class="account-provider">${esc(a.cloud_provider)}</span>
        <span class="account-id">${esc(a.account_id)}</span>
        <dl class="account-meta">
          <div><dt>Resources</dt><dd>${a.resource_count}</dd></div>
          <div><dt>Open</dt><dd>${a.open_recommendations}</dd></div>
          <div><dt>Potential</dt><dd>${money(a.monthly_savings_potential)}/mo</dd></div>
        </dl>
      </article>`
    )
    .join("");
}

function renderBreakdown(portfolio) {
  const b = portfolio?.optimization_breakdown;
  if (!b) {
    nodes.opt.innerHTML = "";
    return;
  }
  const rows = [
    ["Rightsizing", b.rightsizing],
    ["Scheduled shutdowns", b.scheduled_shutdown],
    ["Migrations", b.migration],
    ["Other", b.other],
  ];
  nodes.opt.innerHTML = rows
    .map(
      ([title, count]) =>
        `<article class="opt-item"><span class="opt-count">${count}</span><span class="opt-desc">${title}</span></article>`
    )
    .join("");
}

function renderKpis(kpis) {
  const rows = [
    ["Resources", kpis.total_resources],
    ["Recommendations", kpis.total_recommendations],
    ["Open", kpis.open_recommendations],
    ["Executed", kpis.executed_recommendations],
    ["Potential / mo", money(kpis.total_estimated_monthly_savings)],
    ["Realized / mo", money(kpis.realized_monthly_savings)],
  ];
  nodes.kpis.innerHTML = rows
    .map(([label, value]) => `<article class="kpi"><span class="value">${value}</span><span class="label">${label}</span></article>`)
    .join("");
}

function line(points, key, width, height, pad) {
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
  nodes.chart.innerHTML = `
    <polyline fill="none" stroke="#2563eb" stroke-width="2" points="${line(points, "avg_cpu_utilization", 1000, 280, 20)}" />
    <polyline fill="none" stroke="#059669" stroke-width="2" points="${line(points, "avg_memory_utilization", 1000, 280, 20)}" />
  `;
  nodes.chartNote.textContent = points.length
    ? `${points.length} hourly points`
    : "No metrics yet. Run analysis or pull metrics.";
}

const ruleNames = {
  idle_vm: "Idle VM",
  ecs_underutilized_service: "ECS underutilized",
  scheduled_shutdown: "Scheduled shutdown",
  migration_candidate: "Migration",
};

const actionNames = {
  rightsizing_downsize_instance: "Rightsize",
  reduce_task_size_or_scale_schedule: "Rightsize ECS",
  schedule_shutdown_weeknights: "Schedule shutdown",
  migrate_to_smaller_instance_family: "Migrate",
};

function renderRecommendations(items) {
  if (!items.length) {
    nodes.recommendations.innerHTML = `<tr><td colspan="6" class="table-empty">No recommendations yet.</td></tr>`;
    return;
  }
  nodes.recommendations.innerHTML = items
    .map((rec) => {
      const canApprove = rec.status === "open";
      const canExecute = rec.status === "approved";
      return `
      <tr>
        <td>${esc(ruleNames[rec.rule_name] || rec.rule_name)}</td>
        <td>${esc(actionNames[rec.action] || rec.action || "—")}</td>
        <td><span class="sev severity-${rec.severity || "low"}">${esc(rec.severity || "—")}</span></td>
        <td><span class="badge ${rec.status}">${rec.status}</span></td>
        <td>${money(rec.estimated_monthly_savings)}</td>
        <td class="workflow-cell">
          <button class="btn secondary small" data-simulate="${rec.id}">What-if</button>
          <button class="btn secondary small" data-action="approve" data-id="${rec.id}" ${canApprove ? "" : "disabled"}>Approve</button>
          <button class="btn primary small" data-action="execute" data-id="${rec.id}" ${canExecute ? "" : "disabled"}>Apply</button>
        </td>
      </tr>`;
    })
    .join("");
}

function renderResources(items) {
  if (!items.length) {
    nodes.resources.innerHTML = `<tr><td colspan="5" class="table-empty">No resources yet.</td></tr>`;
    return;
  }
  nodes.resources.innerHTML = items
    .map(
      (r) => `
      <tr>
        <td>${esc(r.cloud_provider)}</td>
        <td><code>${esc(r.account_id || "—")}</code></td>
        <td>${esc(r.resource_type)}</td>
        <td><code>${esc(r.resource_id)}</code></td>
        <td>${esc(r.region || "—")}</td>
      </tr>`
    )
    .join("");
}

async function loadOverview() {
  const hours = Number(nodes.hours.value || 24);
  const [kpis, trends, portfolio, resources] = await Promise.all([
    fetchJson("/dashboard/kpis"),
    fetchJson(`/dashboard/trends?hours=${hours}`),
    fetchJson("/dashboard/portfolio").catch(() => null),
    fetchJson("/resources").catch(() => []),
  ]);
  renderHero(portfolio);
  renderAccounts(portfolio);
  renderBreakdown(portfolio);
  renderKpis(kpis);
  renderChart(trends.points || []);
  renderResources(Array.isArray(resources) ? resources : []);
}

async function loadRecommendations() {
  renderRecommendations(await fetchJson("/recommendations"));
}

async function refreshAll() {
  await Promise.all([loadOverview(), loadRecommendations()]);
}

async function postAdmin(path, query = "") {
  return fetchJson(`${path}${query}`, { method: "POST", headers: adminHeaders() });
}

async function runAllRules() {
  await postAdmin("/dev/recommendations/run-ecs-underutilized-rule");
  await postAdmin("/dev/recommendations/run-idle-vm-rule");
  await postAdmin("/dev/recommendations/run-scheduled-shutdown-rule");
  await postAdmin("/dev/recommendations/run-migration-candidate-rule");
}

function openSim(recId) {
  activeSimRecId = recId;
  nodes.simCard.hidden = false;
  nodes.simDesc.textContent = `Recommendation #${recId}`;
  nodes.simResult.innerHTML = "";
  loadSimHistory(recId);
}

async function loadSimHistory(recId) {
  try {
    const runs = await fetchJson(`/recommendations/${recId}/simulations`);
    if (!runs.length) {
      nodes.simHistoryWrap.hidden = true;
      return;
    }
    nodes.simHistoryWrap.hidden = false;
    nodes.simHistory.innerHTML = runs
      .slice(0, 5)
      .map((r) => `<li>${r.reduction_percent}% → save ${money(r.projected_monthly_savings)}/mo (${esc(r.risk_level)} risk)</li>`)
      .join("");
  } catch {
    nodes.simHistoryWrap.hidden = true;
  }
}

function renderSim(data) {
  nodes.simResult.innerHTML = `
    <dl class="sim-dl">
      <div><dt>Current / mo</dt><dd>${money(data.current_monthly_cost)}</dd></div>
      <div><dt>Projected / mo</dt><dd>${money(data.projected_monthly_cost)}</dd></div>
      <div><dt>Savings / mo</dt><dd>${money(data.projected_monthly_savings)}</dd></div>
      <div><dt>Risk</dt><dd>${esc(data.risk_level)}</dd></div>
    </dl>`;
}

async function mutateRec(id, action) {
  const res = await fetch(`${apiBase()}/recommendations/${id}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey(),
      "X-Role": action === "approve" ? "operator" : "admin",
    },
    body: JSON.stringify({ actor: "dashboard", notes: `${action} from dashboard` }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `Failed to ${action}`);
}

function bindEvents() {
  $("refresh-overview").addEventListener("click", async (e) => {
    setBusy(e.target, true);
    try {
      await refreshAll();
      setStatus("Dashboard refreshed.", "success");
    } catch (err) {
      setStatus(err.message, "error");
    } finally {
      setBusy(e.target, false);
    }
  });

  nodes.hours.addEventListener("change", () => loadOverview().catch((e) => setStatus(e.message, "error")));

  $("btn-run-pipeline").addEventListener("click", async (e) => {
    setBusy(e.target, true);
    setStatus("Running full analysis...", "info");
    try {
      await postAdmin("/dev/pipeline/run-full-analysis", `?hours=${Number(nodes.hours.value || 24)}`);
      await refreshAll();
      setStatus("Analysis complete.", "success");
    } catch (err) {
      setStatus(err.message, "error");
    } finally {
      setBusy(e.target, false);
    }
  });

  $("run-all-rules").addEventListener("click", async (e) => {
    setBusy(e.target, true);
    try {
      await runAllRules();
      await refreshAll();
      setStatus("Rules finished.", "success");
    } catch (err) {
      setStatus(err.message, "error");
    } finally {
      setBusy(e.target, false);
    }
  });

  $("reload-recommendations").addEventListener("click", () => loadRecommendations().catch((e) => setStatus(e.message, "error")));

  nodes.recommendations.addEventListener("click", async (event) => {
    const simBtn = event.target.closest("[data-simulate]");
    if (simBtn) {
      openSim(Number(simBtn.dataset.simulate));
      return;
    }
    const btn = event.target.closest("[data-action]");
    if (!btn) return;
    setBusy(btn, true);
    try {
      await mutateRec(btn.dataset.id, btn.dataset.action);
      await refreshAll();
      if (activeSimRecId === Number(btn.dataset.id)) await loadSimHistory(activeSimRecId);
      setStatus(`Recommendation ${btn.dataset.action}d.`, "success");
    } catch (err) {
      setStatus(err.message, "error");
    } finally {
      setBusy(btn, false);
    }
  });

  nodes.simReduction.addEventListener("input", () => {
    nodes.simLabel.textContent = `${nodes.simReduction.value}%`;
  });

  $("sim-close").addEventListener("click", () => {
    activeSimRecId = null;
    nodes.simCard.hidden = true;
  });

  $("sim-run").addEventListener("click", async (e) => {
    if (!activeSimRecId) return;
    setBusy(e.target, true);
    try {
      const out = await fetchJson(`/recommendations/${activeSimRecId}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reduction_percent: Number(nodes.simReduction.value) }),
      });
      renderSim(out);
      await loadSimHistory(activeSimRecId);
    } catch (err) {
      setStatus(err.message, "error");
    } finally {
      setBusy(e.target, false);
    }
  });

  $("btn-health").addEventListener("click", async (e) => {
    setBusy(e.target, true);
    nodes.health.hidden = false;
    const checks = [
      ["API", "/health"],
      ["Database", "/db-check"],
      ["Redis", "/redis-check"],
    ];
    const lines = [];
    for (const [label, path] of checks) {
      try {
        await fetchJson(path);
        lines.push(`<p>✓ ${label}</p>`);
      } catch (err) {
        lines.push(`<p>✗ ${label}: ${esc(err.message)}</p>`);
      }
    }
    nodes.health.innerHTML = lines.join("");
    setBusy(e.target, false);
  });

  const ingest = async (fn, okMessage) => {
    try {
      await fn();
      await refreshAll();
      setStatus(okMessage, "success");
    } catch (err) {
      setStatus(err.message, "error");
    }
  };

  $("ingest-aws-resources").addEventListener("click", () =>
    ingest(() => postAdmin("/dev/ingest/aws/resources"), "AWS inventory synced.")
  );
  $("ingest-gcp-resources").addEventListener("click", () =>
    ingest(() => postAdmin("/dev/ingest/gcp/resources"), "GCP inventory synced.")
  );
  $("ingest-aws-metrics").addEventListener("click", () =>
    ingest(
      () =>
        Promise.all([
          postAdmin("/dev/ingest/aws/metrics", `?hours=${Number(nodes.hours.value || 24)}`),
          postAdmin("/dev/ingest/aws/ecs/metrics", `?hours=${Number(nodes.hours.value || 24)}`),
          postAdmin("/dev/ingest/gcp/metrics", `?hours=${Number(nodes.hours.value || 24)}`),
        ]),
      "Metrics pulled."
    )
  );
  $("btn-list-resources").addEventListener("click", () =>
    fetchJson("/resources").then(renderResources).catch((e) => setStatus(e.message, "error"))
  );

  nodes.apiBase.addEventListener("change", () => localStorage.setItem(API_BASE_KEY, apiBase()));
  nodes.apiKey.addEventListener("change", () => localStorage.setItem(API_KEY_KEY, apiKey()));
}

const storedBase = localStorage.getItem(API_BASE_KEY);
if (storedBase) nodes.apiBase.value = storedBase;
if (apiKey()) nodes.apiKey.value = apiKey();

bindEvents();
refreshAll().catch((err) => setStatus(err.message, "error"));
