/**
 * SubSloth AI - Frontend Client Logic
 * Powers zero-click benchmarks, real-time 3-layer execution trace,
 * Backboard memory inspection, and 3-tier legal document copy.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const statementInput = document.getElementById("statement-input");
  const btnRunAudit = document.getElementById("btn-run-audit");
  const btnClear = document.getElementById("btn-clear");
  const auditSpinner = document.getElementById("audit-spinner");
  const traceFeed = document.getElementById("trace-feed");
  const pipelineStatus = document.getElementById("pipeline-status");

  // Dashboard Metrics
  const annualRescuedEl = document.getElementById("annual-rescued");
  const monthlyLeakEl = document.getElementById("monthly-leak");
  const hoursAvoidedEl = document.getElementById("hours-avoided");
  const slothStateEl = document.getElementById("sloth-state");
  const darkPatternCountEl = document.getElementById("dark-pattern-count");

  // Results
  const resultsSection = document.getElementById("results-section");
  const subscriptionsContainer = document.getElementById("subscriptions-container");
  const resultsSummaryBadge = document.getElementById("results-summary-badge");

  // Escalation Modal
  const escalationModal = document.getElementById("escalation-modal");
  const btnModalClose = document.getElementById("btn-modal-close");
  const btnModalDismiss = document.getElementById("btn-modal-dismiss");
  const modalMerchantTitle = document.getElementById("modal-merchant-title");
  const modalLegalBasis = document.getElementById("modal-legal-basis");
  const noticeContent = document.getElementById("notice-content");
  const tierExplanation = document.getElementById("tier-explanation");
  const btnCopyNotice = document.getElementById("btn-copy-notice");
  const tabButtons = document.querySelectorAll(".modal-tabs .tab-btn");

  // Memory Modal
  const memoryModal = document.getElementById("memory-modal");
  const btnMemoryView = document.getElementById("btn-memory-view");
  const btnMemoryClose = document.getElementById("btn-memory-close");
  const btnMemoryDismiss = document.getElementById("btn-memory-dismiss");
  const memoryRecordsList = document.getElementById("memory-records-list");
  const memoryCountEl = document.getElementById("memory-count");
  const btnSimulateZombie = document.getElementById("btn-simulate-zombie");

  // State
  let currentActiveEscalation = null;
  let currentTier = "tier_1";
  let benchmarksData = [];

  // 1. Load Benchmarks
  async function loadBenchmarks() {
    try {
      const resp = await fetch("/api/benchmarks");
      if (resp.ok) {
        benchmarksData = await resp.json();
      }
    } catch (err) {
      console.warn("Using offline benchmark presets:", err);
    }
  }
  loadBenchmarks();

  // 2. Benchmark Button Click Handlers
  document.querySelectorAll(".benchmark-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const presetId = btn.getAttribute("data-preset");
      const found = benchmarksData.find((b) => b.id === presetId);
      if (found) {
        statementInput.value = found.statement_text;
      } else {
        // Fallback preset values
        if (presetId === "gym_trap") {
          statementInput.value = "2026-10-01 PLANET FITNESS DALLAS TX $29.99/MO\nIn-person club visit or certified mail cancellation required.\n2026-10-01 PLANET FITNESS ANNUAL MAINTENANCE FEE $49.00";
        } else if (presetId === "sneaky_saas") {
          statementInput.value = "2026-10-01 CLOUDSCALE AI PRO TRIAL CONVERTED $79.00/MO\n2026-10-01 CLOUDSCALE PRIORITY SUPPORT ADDON $19.99/MO";
        } else if (presetId === "ghost_micro_fee") {
          statementInput.value = "2026-10-05 STREAMMAX STANDARD STREAMING $14.99/MO\n2026-10-05 STREAMMAX 4K ULTRA STREAM ADDON $4.99/MO\n2026-10-05 STREAMMAX AD-FREE VIP BOOST $3.99/MO";
        } else {
          statementInput.value = "2026-10-01 PLANET FITNESS DALLAS TX $29.99/mo (In-person cancel required)\n2026-10-02 CLOUDSCALE AI PRO TRIAL CONVERTED $79.00/mo\n2026-10-05 STREAMMAX 4K ULTRA STREAM ADDON $4.99/mo\n2026-10-10 SPOTIFY PREMIUM $11.99/mo";
        }
      }
      runAudit();
    });
  });

  // Clear button
  btnClear.addEventListener("click", () => {
    statementInput.value = "";
    resultsSection.classList.add("hidden");
    traceFeed.innerHTML = `<div class="trace-step trace-idle"><span class="step-num">[0]</span><span class="step-text">Awaiting statement input or benchmark click...</span></div>`;
    pipelineStatus.textContent = "Idle";
    pipelineStatus.className = "panel-badge";
    annualRescuedEl.textContent = "$0.00";
    monthlyLeakEl.textContent = "$0.00";
    hoursAvoidedEl.textContent = "0.0 hrs";
    slothStateEl.textContent = "Chilling";
    darkPatternCountEl.textContent = "0 Dark Patterns Flagged";
  });

  // 3. Run Audit Pipeline
  async function runAudit() {
    const text = statementInput.value.trim();
    if (!text) {
      alert("Please paste statement lines or click a benchmark button above.");
      return;
    }

    // Set UI Loading State
    auditSpinner.classList.remove("hidden");
    btnRunAudit.disabled = true;
    pipelineStatus.textContent = "Auditing...";
    pipelineStatus.className = "panel-badge badge-active";

    // Initialize Trace Feed
    traceFeed.innerHTML = "";
    addTraceStep(1, "Layer 1: Deterministic Engine scanning line tokens & cadence keywords...", "trace-idle");

    try {
      const resp = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ statement_text: text }),
      });

      if (!resp.ok) {
        throw new Error(`Audit failed with status ${resp.status}`);
      }

      const data = await resp.json();

      // Step 1 Success Trace
      addTraceStep(1, `Layer 1: Deterministic Engine: Parsed ${data.total_items} items. Flagged ${data.dark_patterns_count} dark patterns.`, "trace-success");
      
      // Step 2 Memory Trace
      addTraceStep(2, `Layer 2: Backboard Memory Session: Cross-referenced active cancellations & zombie checks.`, "trace-success");

      // Check for Zombie alerts
      const hasZombie = data.subscriptions.some((s) => s.zombie_recharge_alert);
      if (hasZombie) {
        addTraceStep(2, `CRITICAL ZOMBIE REBILL INTERCEPTED: Cancelled merchant detected charging again! Escalating to Tier 3.`, "trace-alert");
      }

      // Step 3 Output Format Trace
      addTraceStep(3, `Layer 3: 3-Tier Output Sanitizer ready for Google Gemma 2 legal notice generation.`, "trace-success");
      pipelineStatus.textContent = "Complete";

      // Update Dashboard Counters
      annualRescuedEl.textContent = `$${data.total_annual_drain.toFixed(2)}`;
      monthlyLeakEl.textContent = `$${data.total_monthly_drain.toFixed(2)}`;
      hoursAvoidedEl.textContent = `${data.lazy_payoff.hours_saved} hrs`;
      slothStateEl.textContent = data.lazy_payoff.sloth_rating.split(" ")[0];
      darkPatternCountEl.textContent = `${data.dark_patterns_count} Dark Patterns Flagged`;

      // Render Subscriptions
      renderSubscriptions(data.subscriptions);
      resultsSection.classList.remove("hidden");
      resultsSummaryBadge.textContent = `${data.total_items} Subscriptions Detected ($${data.total_annual_drain.toFixed(2)}/yr total)`;

      // Refresh memory count
      updateMemoryCount();

    } catch (err) {
      addTraceStep("!", `Audit error: ${err.message}`, "trace-alert");
      pipelineStatus.textContent = "Error";
    } finally {
      auditSpinner.classList.add("hidden");
      btnRunAudit.disabled = false;
    }
  }

  btnRunAudit.addEventListener("click", runAudit);

  function addTraceStep(num, text, cssClass) {
    const div = document.createElement("div");
    div.className = `trace-step ${cssClass}`;
    div.innerHTML = `<span class="step-num">[${num}]</span><span class="step-text">${text}</span>`;
    traceFeed.appendChild(div);
    traceFeed.scrollTop = traceFeed.scrollHeight;
  }

  // 4. Render Subscription Cards
  function renderSubscriptions(subs) {
    subscriptionsContainer.innerHTML = "";
    if (subs.length === 0) {
      subscriptionsContainer.innerHTML = `<div class="empty-memory">No recurring subscription charges detected in input.</div>`;
      return;
    }

    subs.forEach((sub) => {
      const card = document.createElement("div");
      card.className = `sub-card ${sub.dark_pattern_detected ? "has-dark-pattern" : ""} ${sub.zombie_recharge_alert ? "is-zombie" : ""}`;

      let badgeClass = "badge-standard";
      let badgeLabel = "Standard Subscription";
      if (sub.zombie_recharge_alert) {
        badgeClass = "badge-zombie";
        badgeLabel = "🧟 ZOMBIE REBILL VIOLATION";
      } else if (sub.dark_pattern_type === "GYM_TRAP") {
        badgeClass = "badge-gym";
        badgeLabel = "🏋️ GYM TRAP: IN-PERSON BARRIER";
      } else if (sub.dark_pattern_type === "SNEAKY_SAAS_TRIAL") {
        badgeClass = "badge-saas";
        badgeLabel = "💻 SNEAKY SAAS: TRIAL AUTO-CONVERSION";
      } else if (sub.dark_pattern_type === "GHOST_MICRO_FEE") {
        badgeClass = "badge-ghost";
        badgeLabel = "👻 GHOST MICRO-FEE: UNDISCLOSED ADDON";
      }

      card.innerHTML = `
        <div>
          <div class="card-top">
            <div>
              <div class="card-merchant">${escapeHtml(sub.merchant)}</div>
              <div class="card-cadence">${sub.cadence.toUpperCase()} RECURRING</div>
            </div>
            <div class="card-amount">$${sub.amount.toFixed(2)}<small style="font-size: 0.8rem; font-weight: 500;">/${sub.cadence === 'annual' ? 'yr' : 'mo'}</small></div>
          </div>
          <span class="pattern-badge ${badgeClass}">${badgeLabel}</span>
          <p class="card-reason">${escapeHtml(sub.reason)}</p>
          <div class="card-clause">⚖️ ${escapeHtml(sub.ftc_clause_id)}: ${escapeHtml(sub.ftc_title)}</div>
        </div>
        <div class="card-bottom">
          <span class="annual-drain-tag">Annual Drain: <strong>$${sub.annual_drain.toFixed(2)}/yr</strong></span>
          <button class="btn-primary btn-escalate" data-sub='${JSON.stringify(sub).replace(/'/g, "&apos;")}'>
            ⚡ Generate 3-Tier Notice
          </button>
        </div>
      `;
      subscriptionsContainer.appendChild(card);
    });

    // Wire up escalate buttons
    document.querySelectorAll(".btn-escalate").forEach((btn) => {
      btn.addEventListener("click", () => {
        const subData = JSON.parse(btn.getAttribute("data-sub"));
        openEscalationModal(subData);
      });
    });
  }

  // 5. Open Escalation Modal
  async function openEscalationModal(sub) {
    escalationModal.classList.remove("hidden");
    modalMerchantTitle.textContent = `${sub.merchant} — 3-Tier Escalation`;
    modalLegalBasis.textContent = `Citing ${sub.ftc_clause_id} (${sub.ftc_title})`;
    noticeContent.textContent = "Synthesizing legally grounded notice via Google Gemma 2 & Backboard Memory...";

    try {
      const resp = await fetch("/api/escalate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          merchant: sub.merchant,
          amount: sub.amount,
          cadence: sub.cadence,
          dark_pattern_type: sub.dark_pattern_type,
          ftc_clause_id: sub.ftc_clause_id,
          ftc_title: sub.ftc_title,
          citation: sub.citation,
          account_id: `SUB-${Math.floor(10000 + Math.random() * 90000)}`
        }),
      });

      if (!resp.ok) {
        throw new Error("Failed to synthesize notice");
      }

      currentActiveEscalation = await resp.json();
      switchTier("tier_1");
      updateMemoryCount();
    } catch (err) {
      noticeContent.textContent = `Error synthesizing notice: ${err.message}`;
    }
  }

  // Tier tab switching
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentTier = btn.getAttribute("data-tier");
      renderActiveTier();
    });
  });

  function switchTier(tierKey) {
    currentTier = tierKey;
    tabButtons.forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-tier") === tierKey);
    });
    renderActiveTier();
  }

  function renderActiveTier() {
    if (!currentActiveEscalation) return;

    if (currentTier === "tier_1") {
      tierExplanation.innerHTML = `<strong>Tier 1: Diplomatic Request</strong> — Polite, 1-click customer service cancellation. Gives merchant 24-48 hours to confirm before legal escalation.`;
      noticeContent.textContent = currentActiveEscalation.tiers.tier_1_diplomatic;
    } else if (currentTier === "tier_2") {
      tierExplanation.innerHTML = `<strong>Tier 2: FTC Legal Notice</strong> — Formal regulatory cease-and-desist citing <strong>16 CFR Part 425 § 425.6 (Click-to-Cancel)</strong>. Mentions civil penalties up to $50,120.`;
      noticeContent.textContent = currentActiveEscalation.tiers.tier_2_ftc_legal;
    } else {
      tierExplanation.innerHTML = `<strong>Tier 3: Bank Chargeback Affidavit</strong> — Dispute document for Visa/Mastercard/Bank under <strong>12 CFR § 1005.10 (EFTA Reg E)</strong> for immediate reversal of unauthorized debits.`;
      noticeContent.textContent = currentActiveEscalation.tiers.tier_3_chargeback;
    }
  }

  // Copy notice button
  btnCopyNotice.addEventListener("click", () => {
    const text = noticeContent.textContent;
    navigator.clipboard.writeText(text).then(() => {
      const originalText = btnCopyNotice.textContent;
      btnCopyNotice.textContent = "✓ Copied to Clipboard!";
      setTimeout(() => {
        btnCopyNotice.textContent = originalText;
      }, 2000);
    });
  });

  // Close escalation modal
  btnModalClose.addEventListener("click", () => escalationModal.classList.add("hidden"));
  btnModalDismiss.addEventListener("click", () => escalationModal.classList.add("hidden"));

  // 6. Memory Modal & Zombie Simulation
  btnMemoryView.addEventListener("click", openMemoryModal);
  btnMemoryClose.addEventListener("click", () => memoryModal.classList.add("hidden"));
  btnMemoryDismiss.addEventListener("click", () => memoryModal.classList.add("hidden"));

  async function openMemoryModal() {
    memoryModal.classList.remove("hidden");
    await refreshMemoryUI();
  }

  async function refreshMemoryUI() {
    try {
      const resp = await fetch("/api/memory");
      if (resp.ok) {
        const data = await resp.json();
        renderMemoryRecords(data.records);
        memoryCountEl.textContent = data.total_active_cancellations;
      }
    } catch (err) {
      console.warn("Failed to fetch memory records:", err);
    }
  }

  function renderMemoryRecords(records) {
    if (!records || records.length === 0) {
      memoryRecordsList.innerHTML = `<div class="empty-memory">No active cancellations saved in memory yet. Run an audit and click 'Generate 3-Tier Notice' to track one!</div>`;
      return;
    }

    memoryRecordsList.innerHTML = "";
    records.forEach((rec) => {
      const item = document.createElement("div");
      item.className = "memory-item";
      item.innerHTML = `
        <div>
          <div class="memory-merchant">${escapeHtml(rec.merchant)} — $${rec.amount.toFixed(2)}</div>
          <div class="memory-notice-id">Notice ID: ${rec.notice_id} | Cancelled: ${rec.cancelled_at}</div>
        </div>
        <div>
          <span class="badge ${rec.zombie_alerts_count > 0 ? 'badge-ftc' : 'badge-backboard'}">
            ${rec.zombie_alerts_count > 0 ? `⚠️ ${rec.zombie_alerts_count} Zombie Intercepts` : 'Active Protection'}
          </span>
        </div>
      `;
      memoryRecordsList.appendChild(item);
    });
  }

  async function updateMemoryCount() {
    try {
      const resp = await fetch("/api/memory");
      if (resp.ok) {
        const data = await resp.json();
        memoryCountEl.textContent = data.total_active_cancellations;
      }
    } catch (_) {}
  }
  updateMemoryCount();

  // Simulate Zombie Rebilling Attack (Judges Favorite Demonstration)
  btnSimulateZombie.addEventListener("click", async () => {
    btnSimulateZombie.disabled = true;
    btnSimulateZombie.textContent = "Simulating Charge...";

    try {
      const resp = await fetch("/api/simulate-zombie-rebill", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          merchant: "Planet Fitness",
          amount: 29.99,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        alert(
          `🧟 ZOMBIE REBILL INTERCEPTED BY BACKBOARD MEMORY!\n\n` +
          `Merchant: ${data.merchant}\n` +
          `Unauthorized Debit: $${data.unauthorized_amount}\n` +
          `Prior Cancellation Notice: ${data.cancellation_notice_id}\n\n` +
          `Recommended Action: ${data.recommended_escalation}\n` +
          `Legal Mandate: ${data.legal_basis}\n\n` +
          `Backboard Memory proves to the bank that this debit was formally revoked!`
        );
        await refreshMemoryUI();
      }
    } catch (err) {
      alert("Error simulating zombie charge: " + err.message);
    } finally {
      btnSimulateZombie.disabled = false;
      btnSimulateZombie.textContent = "🧟 Simulate Zombie Rebilling Attack";
    }
  });

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
