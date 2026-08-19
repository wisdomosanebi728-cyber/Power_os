// POWER OS Full Live Dashboard Controller

const COMMUNITY_ID = "00000000-0000-0000-0000-000000000001";
let socket = null;
let energyChart = null;
let currentEpochId = null;

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
  initClock();
  initChart();
  initAuthSession();
  initWebSocket();
  fetchInitialHistory();
  fetchSettlements();
  fetchESGMetrics();
});

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".nav-tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));

  if (tabId === "live-ops") {
    document.querySelector("button[onclick=\"switchTab('live-ops')\"]").classList.add("active");
    document.getElementById("tab-live-ops").classList.add("active");
  } else if (tabId === "settlements") {
    document.querySelector("button[onclick=\"switchTab('settlements')\"]").classList.add("active");
    document.getElementById("tab-settlements").classList.add("active");
    fetchSettlements();
  } else if (tabId === "esg") {
    document.querySelector("button[onclick=\"switchTab('esg')\"]").classList.add("active");
    document.getElementById("tab-esg").classList.add("active");
    fetchESGMetrics();
  }
}

// Real-time Clock
function initClock() {
  const clockEl = document.getElementById("time-display");
  setInterval(() => {
    const now = new Date();
    clockEl.textContent = now.toISOString().substring(11, 19) + " UTC";
  }, 1000);
}

let wsRetries = 0;
let pollingInterval = null;

// WebSocket Connection with auto-reconnect & HTTP Polling Fallback
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/live/${COMMUNITY_ID}`;
  const pill = document.getElementById("stream-status-pill");
  const pillText = document.getElementById("stream-status-text");

  try {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      wsRetries = 0;
      if (pollingInterval) clearInterval(pollingInterval);
      pill.className = "status-pill status-live";
      pillText.textContent = "LIVE (1 Hz)";
    };

    socket.onmessage = (event) => {
      try {
        const frame = JSON.parse(event.data);
        if (frame.type === "live_telemetry_frame") {
          updateDashboard(frame);
        }
      } catch (err) {
        console.error("Failed to parse telemetry frame:", err);
      }
    };

    socket.onclose = () => {
      wsRetries++;
      if (wsRetries > 2) {
        pill.className = "status-pill status-live";
        pillText.textContent = "HTTP LIVE (0.5 Hz)";
        if (!pollingInterval) {
          pollTelemetryFallback();
          pollingInterval = setInterval(pollTelemetryFallback, 2000);
        }
      } else {
        pill.className = "status-pill";
        pillText.textContent = "RECONNECTING...";
        setTimeout(initWebSocket, 2000);
      }
    };

    socket.onerror = () => {
      socket.close();
    };
  } catch (e) {
    console.warn("WebSocket init error, falling back to HTTP polling", e);
    pill.className = "status-pill status-live";
    pillText.textContent = "HTTP LIVE (0.5 Hz)";
    if (!pollingInterval) {
      pollTelemetryFallback();
      pollingInterval = setInterval(pollTelemetryFallback, 2000);
    }
  }
}

// Fallback HTTP polling if WebSocket is unavailable
async function pollTelemetryFallback() {
  try {
    const res = await fetch(`/api/v1/communities/${COMMUNITY_ID}/energy/live`);
    if (res.ok) {
      const state = await res.json();
      updateDashboard({ energy_state: state, alerts: [], optimization: null });
    }
  } catch (err) {
    console.error("Polling error:", err);
  }
}

// Update DOM with live telemetry & dispatch recommendations
function updateDashboard(frame) {
  const state = frame.energy_state;
  if (!state) return;

  const gen = state.generation || {};
  const storage = state.storage || {};
  const cons = state.consumption || {};
  const grid = state.grid_status || {};
  const diesel = state.generator_status || {};

  // Tickers
  document.getElementById("val-solar-kw").textContent = (gen.solar_kw || 0).toFixed(1);
  
  const batKw = (storage.battery_charging_kw > 0 ? -storage.battery_charging_kw : gen.battery_discharge_kw) || 0;
  document.getElementById("val-battery-kw").textContent = batKw.toFixed(1);
  
  const soc = storage.state_of_charge_percent || 80.0;
  document.getElementById("val-battery-soc").textContent = soc.toFixed(1) + "%";
  document.getElementById("val-battery-health").textContent = (storage.battery_health_percent || 99.2).toFixed(1) + "%";
  document.getElementById("soc-bar").style.width = `${Math.min(100, Math.max(0, soc))}%`;

  const totalDemand = cons.total_demand_kw || 0;
  document.getElementById("val-total-demand").textContent = totalDemand.toFixed(1);
  document.getElementById("val-critical-load").textContent = `${(cons.critical_load_kw || 0).toFixed(1)} kW`;
  document.getElementById("val-noncrit-load").textContent = `${(cons.non_critical_load_kw || 0).toFixed(1)} kW`;

  document.getElementById("val-lcoe").textContent = `$${(state.current_lcoe_per_kwh || 0.018).toFixed(3)}`;

  // Flow Diagram Values
  document.getElementById("flow-solar-val").textContent = `${(gen.solar_kw || 0).toFixed(1)} kW`;
  document.getElementById("flow-battery-val").textContent = batKw < 0 ? `${batKw.toFixed(1)} kW (Chg)` : `${batKw.toFixed(1)} kW (Dis)`;
  document.getElementById("flow-grid-val").textContent = grid.available ? `${(gen.grid_import_kw || 0).toFixed(1)} kW (Active)` : `0.0 kW (Offline)`;
  document.getElementById("flow-gen-val").textContent = diesel.running ? `${(gen.generator_kw || 0).toFixed(1)} kW (Active)` : `0.0 kW (Off)`;

  const loads = cons.breakdown_by_category || {};
  document.getElementById("load-coldstore-val").textContent = `${(loads.commercial_cold_store || 7.2).toFixed(1)} kW`;
  document.getElementById("load-res-val").textContent = `${(loads.residential || 5.4).toFixed(1)} kW`;
  document.getElementById("load-work-val").textContent = `${(loads.workshop_barber || 3.8).toFixed(1)} kW`;
  document.getElementById("load-clinic-val").textContent = `${(loads.community_facility || 2.1).toFixed(1)} kW`;

  // Optimization Section
  if (frame.optimization) {
    const opt = frame.optimization;
    document.getElementById("opt-action-name").textContent = `ACTION: ${opt.action.replace(/_/g, " ").toUpperCase()}`;
    document.getElementById("opt-explanation-text").textContent = opt.explanation || "System operating in optimal state.";
    
    if (opt.financial_impact) {
      document.getElementById("opt-baseline-cost").textContent = `$${opt.financial_impact.unoptimized_baseline_cost_per_hour.toFixed(2)}/hr`;
      document.getElementById("opt-current-cost").textContent = `$${opt.financial_impact.current_cost_rate_per_hour.toFixed(2)}/hr`;
      document.getElementById("val-hourly-savings").textContent = `+$${opt.financial_impact.hourly_savings.toFixed(2)} / hr`;
      document.getElementById("badge-savings-pct").textContent = `${opt.financial_impact.savings_percentage.toFixed(0)}% SAVINGS`;
    }

    if (opt.shortage_risk) {
      document.getElementById("opt-autonomy").textContent = `${opt.shortage_risk.hours_of_battery_autonomy.toFixed(1)} hrs`;
      const riskEl = document.getElementById("opt-risk");
      riskEl.textContent = opt.shortage_risk.risk_level;
      riskEl.className = `val risk-${opt.shortage_risk.risk_level.toLowerCase()}`;
    }
  }

  // Alerts Feed
  updateAlertsFeed(frame.alerts || []);
}

function updateAlertsFeed(alerts) {
  const container = document.getElementById("alerts-feed-container");
  const countBadge = document.getElementById("alerts-count");

  if (!alerts || alerts.length === 0) {
    countBadge.textContent = "0 ACTIVE";
    countBadge.style.background = "rgba(16, 185, 129, 0.15)";
    countBadge.style.color = "#10b981";
    container.innerHTML = `
      <div class="alert-item alert-info">
        <div class="alert-header">
          <span class="alert-type">HEALTH CHECK</span>
          <span class="alert-time">Real-time</span>
        </div>
        <div class="alert-msg">All power flows, voltages, and thermal states are nominal.</div>
      </div>
    `;
    return;
  }

  countBadge.textContent = `${alerts.length} ACTIVE`;
  countBadge.style.background = "rgba(239, 68, 68, 0.2)";
  countBadge.style.color = "#ef4444";

  container.innerHTML = alerts.map(a => `
    <div class="alert-item alert-${a.severity || 'warning'}">
      <div class="alert-header">
        <span class="alert-type">${(a.type || 'ANOMALY').toUpperCase()}</span>
        <span class="alert-time">${a.timestamp ? a.timestamp.substring(11, 19) : 'Just now'}</span>
      </div>
      <div class="alert-msg">${a.message || 'System excursion detected'}</div>
    </div>
  `).join('');
}

// Trigger Scenario from button clicks
async function applyScenario(scenarioName) {
  document.querySelectorAll(".btn-scenario").forEach(btn => {
    if (btn.getAttribute("data-scenario") === scenarioName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  try {
    await fetch("/api/v1/simulator/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        community_id: COMMUNITY_ID,
        scenario: scenarioName,
      })
    });
  } catch (err) {
    console.error("Failed to trigger scenario:", err);
  }
}

// 24-Hour History Chart Setup
function initChart() {
  const ctx = document.getElementById("energyChart").getContext("2d");
  energyChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Solar Generation (kW)",
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245, 158, 11, 0.1)",
          data: [],
          tension: 0.35,
          fill: true,
        },
        {
          label: "Total Demand (kW)",
          borderColor: "#a855f7",
          backgroundColor: "transparent",
          data: [],
          borderDash: [5, 5],
          tension: 0.35,
        },
        {
          label: "Battery Discharge (kW)",
          borderColor: "#10b981",
          backgroundColor: "transparent",
          data: [],
          tension: 0.35,
        },
        {
          label: "Grid Import (kW)",
          borderColor: "#06b6d4",
          backgroundColor: "transparent",
          data: [],
          tension: 0.35,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: "#94a3b8", font: { family: "Outfit", size: 11 } }
        }
      },
      scales: {
        x: {
          ticks: { color: "#64748b", font: { family: "Outfit", size: 10 } },
          grid: { color: "rgba(255, 255, 255, 0.05)" }
        },
        y: {
          ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 10 } },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          title: { display: true, text: "kW", color: "#64748b" }
        }
      }
    }
  });
}

async function fetchInitialHistory() {
  try {
    const res = await fetch(`/api/v1/communities/${COMMUNITY_ID}/energy/history?range_hours=24`);
    if (res.ok) {
      const data = await res.json();
      if (data.series && energyChart) {
        energyChart.data.labels = data.series.map(d => d.timestamp.substring(11, 16));
        energyChart.data.datasets[0].data = data.series.map(d => d.solar_generation_kw);
        energyChart.data.datasets[1].data = data.series.map(d => d.total_demand_kw);
        energyChart.data.datasets[2].data = data.series.map(d => Math.max(0, d.battery_power_kw));
        energyChart.data.datasets[3].data = data.series.map(d => d.grid_import_kw);
        energyChart.update();
      }
    }
  } catch (err) {
    console.error("Failed to load chart history:", err);
  }
}

// ==========================================
// SETTLEMENTS & MERKLE NOTARIZATION LOGIC
// ==========================================

async function fetchSettlements() {
  try {
    const res = await fetch(`/api/v1/communities/${COMMUNITY_ID}/settlements/epochs`);
    if (res.ok) {
      const epochs = await res.json();
      if (epochs && epochs.length > 0) {
        const latest = epochs[epochs.length - 1];
        currentEpochId = latest.epoch_id;
        renderSettlementSummary(latest);
      }
    }
  } catch (err) {
    console.error("Failed to fetch settlements:", err);
  }
}

function renderSettlementSummary(epoch) {
  document.getElementById("epoch-status").textContent = epoch.settlement_status.toUpperCase();
  document.getElementById("epoch-consumption").textContent = `${epoch.total_energy_consumed_kwh.toFixed(1)} kWh`;
  document.getElementById("epoch-savings").textContent = `+$${epoch.total_savings.toFixed(2)}`;
  
  const root = epoch.merkle_root_hash || "0x0000000000000000000000000000000000000000000000000000000000000000";
  document.getElementById("epoch-merkle-root").textContent = `${root.substring(0, 10)}...${root.substring(58)}`;

  const tbody = document.getElementById("invoices-table-body");
  tbody.innerHTML = (epoch.invoices || []).map(inv => `
    <tr>
      <td><strong>${inv.user_name}</strong></td>
      <td><code>${inv.meter_device_id}</code></td>
      <td>${inv.consumption_kwh.toFixed(1)} kWh</td>
      <td>${inv.allocated_solar_kwh.toFixed(1)} kWh</td>
      <td>${inv.allocated_battery_kwh.toFixed(1)} kWh</td>
      <td>$${inv.blended_tariff_per_kwh.toFixed(3)}/kWh</td>
      <td><strong>$${inv.total_amount_due.toFixed(2)}</strong></td>
      <td>
        <button class="btn-verify-proof" onclick="verifyInvoiceProof('${inv.user_id}')">
          🔐 Verify Proof
        </button>
      </td>
    </tr>
  `).join('');
}

async function closeNewEpoch() {
  try {
    const res = await fetch(`/api/v1/communities/${COMMUNITY_ID}/settlements/close-epoch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ community_id: COMMUNITY_ID, notarize_on_chain: true })
    });
    if (res.ok) {
      const newEpoch = await res.json();
      currentEpochId = newEpoch.epoch_id;
      renderSettlementSummary(newEpoch);
    }
  } catch (err) {
    console.error("Failed to close epoch:", err);
  }
}

async function verifyInvoiceProof(userId) {
  if (!currentEpochId) return;
  try {
    const res = await fetch(`/api/v1/communities/${COMMUNITY_ID}/settlements/epochs/${currentEpochId}/proofs/${userId}`);
    if (res.ok) {
      const proofData = await res.json();
      const box = document.getElementById("proof-box");
      box.style.display = "block";
      document.getElementById("proof-leaf").textContent = proofData.leaf;
      document.getElementById("proof-root").textContent = proofData.root;
      document.getElementById("proof-status").textContent = proofData.verified ? "VALID CRYPTOGRAPHIC MERKLE INCLUSION PROOF ✓" : "INVALID PROOF ✕";
      document.getElementById("proof-status").className = proofData.verified ? "positive" : "negative";
    }
  } catch (err) {
    console.error("Failed to verify Merkle proof:", err);
  }
}

function closeProofBox() {
  document.getElementById("proof-box").style.display = "none";
}

// ==========================================
// ESG METRICS LOGIC
// ==========================================

async function fetchESGMetrics() {
  try {
    const res = await fetch(`/api/v1/communities/${COMMUNITY_ID}/energy/esg`);
    if (res.ok) {
      const esg = await res.json();
      document.getElementById("esg-clean-fraction").textContent = `${esg.clean_energy_fraction_percent.toFixed(1)}%`;
      document.getElementById("esg-co2-avoided").textContent = `${esg.estimated_daily_co2_avoided_kg.toFixed(1)} kg`;
      document.getElementById("esg-carbon-intensity").textContent = `${esg.current_emission_rate_kg_co2_per_hour.toFixed(2)} kg/hr`;
      document.getElementById("esg-rating").textContent = esg.esg_rating;
    }
  } catch (err) {
    console.error("Failed to fetch ESG metrics:", err);
  }
}

// ==========================================
// AUTHENTICATION & LOGIN PORTAL MANAGER
// ==========================================

let currentUser = null;
let currentToken = null;

async function initAuthSession() {
  const savedToken = localStorage.getItem("poweros_token");
  const savedUserJson = localStorage.getItem("poweros_user");

  if (savedToken && savedUserJson) {
    try {
      currentToken = savedToken;
      currentUser = JSON.parse(savedUserJson);
      
      // Verify token with backend
      const res = await fetch("/api/v1/auth/me", {
        headers: { "Authorization": `Bearer ${savedToken}` }
      });
      if (res.ok) {
        currentUser = await res.json();
        localStorage.setItem("poweros_user", JSON.stringify(currentUser));
        updateUserSessionUI(currentUser);
        closeLoginOverlay();
        return;
      }
    } catch (e) {
      console.warn("Session verification failed, requesting login", e);
    }
  }

  // If no valid session, show login overlay
  openLoginOverlay();
}

function openLoginOverlay() {
  const overlay = document.getElementById("login-overlay");
  if (overlay) {
    overlay.classList.remove("hidden");
  }
}

function closeLoginOverlay() {
  const overlay = document.getElementById("login-overlay");
  if (overlay) {
    overlay.classList.add("hidden");
  }
}

function switchLoginTab(tab) {
  document.querySelectorAll(".login-tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".login-tab-panel").forEach(panel => panel.classList.remove("active"));

  if (tab === "quick") {
    document.getElementById("tab-btn-quick").classList.add("active");
    document.getElementById("login-tab-quick").classList.add("active");
  } else if (tab === "user") {
    document.getElementById("tab-btn-user").classList.add("active");
    document.getElementById("login-tab-user").classList.add("active");
  } else if (tab === "register") {
    document.getElementById("tab-btn-register").classList.add("active");
    document.getElementById("login-tab-register").classList.add("active");
  }
}

function updateUserSessionUI(user) {
  if (!user) return;
  const roleBadge = document.getElementById("user-role-badge");
  const nameDisplay = document.getElementById("user-display-name");

  if (roleBadge) {
    const roleStr = (user.role || "guest").toLowerCase();
    roleBadge.textContent = roleStr.toUpperCase();
    roleBadge.className = `user-role-badge role-badge-${roleStr}`;
  }

  if (nameDisplay) {
    nameDisplay.textContent = user.full_name || user.email || "User";
  }
}

function setSession(token, user) {
  currentToken = token;
  currentUser = user;
  localStorage.setItem("poweros_token", token);
  localStorage.setItem("poweros_user", JSON.stringify(user));
  updateUserSessionUI(user);
  closeLoginOverlay();
}

async function handleGuestLogin() {
  try {
    const res = await fetch("/api/v1/auth/guest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guest_name: "Guest Visitor" })
    });
    if (res.ok) {
      const data = await res.json();
      setSession(data.access_token, data.user);
    } else {
      alert("Failed to initialize guest session.");
    }
  } catch (err) {
    console.error("Guest login error:", err);
    setSession("guest-offline-token", {
      id: "guest-001",
      email: "guest@poweros.energy",
      full_name: "Guest Visitor",
      role: "guest"
    });
  }
}

async function handleAdminLogin() {
  try {
    const res = await fetch("/api/v1/auth/admin-demo", {
      method: "POST"
    });
    if (res.ok) {
      const data = await res.json();
      setSession(data.access_token, data.user);
    } else {
      alert("Admin login failed.");
    }
  } catch (err) {
    console.error("Admin login error:", err);
    setSession("admin-offline-token", {
      id: "admin-001",
      email: "admin@poweros.energy",
      full_name: "System Administrator",
      role: "admin"
    });
  }
}

async function handleGmailAuth() {
  const userGmail = prompt("Enter your Gmail address to register / sign in:", "operator.alex@gmail.com");
  if (!userGmail || !userGmail.includes("@")) return;

  const userName = prompt("Enter your full name:", userGmail.split("@")[0].replace(".", " ").toUpperCase());

  try {
    const res = await fetch("/api/v1/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: userGmail.trim(),
        full_name: userName || "Gmail User",
        google_token: "google_oauth_token_" + Date.now(),
        role: "consumer"
      })
    });

    if (res.ok) {
      const data = await res.json();
      setSession(data.access_token, data.user);
    } else {
      const errData = await res.json();
      alert(`Gmail Sign-in failed: ${errData.detail || 'Unknown error'}`);
    }
  } catch (err) {
    console.error("Gmail auth error:", err);
    setSession("gmail-token-" + Date.now(), {
      id: "gmail-user-1",
      email: userGmail.trim(),
      full_name: userName || "Gmail User",
      role: "consumer"
    });
  }
}

async function handleUserLoginForm(event) {
  event.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;

  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    if (res.ok) {
      const data = await res.json();
      setSession(data.access_token, data.user);
    } else {
      const errData = await res.json();
      alert(`Login failed: ${errData.detail || 'Invalid email or password'}`);
    }
  } catch (err) {
    console.error("Login form error:", err);
    alert("Network error during login.");
  }
}

async function handleRegisterForm(event) {
  event.preventDefault();
  const fullName = document.getElementById("reg-name").value;
  const email = document.getElementById("reg-email").value;
  const password = document.getElementById("reg-password").value;
  const role = document.getElementById("reg-role").value;

  try {
    const res = await fetch("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name: fullName, email, password, role })
    });

    if (res.ok) {
      alert("Registration successful! Logging in...");
      const loginRes = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      if (loginRes.ok) {
        const data = await loginRes.json();
        setSession(data.access_token, data.user);
      }
    } else {
      const errData = await res.json();
      alert(`Registration failed: ${errData.detail || 'Could not create account'}`);
    }
  } catch (err) {
    console.error("Registration form error:", err);
    alert("Network error during registration.");
  }
}

function logout() {
  localStorage.removeItem("poweros_token");
  localStorage.removeItem("poweros_user");
  currentToken = null;
  currentUser = null;
  
  const roleBadge = document.getElementById("user-role-badge");
  const nameDisplay = document.getElementById("user-display-name");
  if (roleBadge) {
    roleBadge.textContent = "GUEST";
    roleBadge.className = "user-role-badge role-badge-guest";
  }
  if (nameDisplay) {
    nameDisplay.textContent = "Guest Visitor";
  }

  openLoginOverlay();
}

