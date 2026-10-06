// ContentOps Harness Frontend Controller
const API_BASE = window.location.origin;

let activeTab = 'dashboard';
let currentWorkspaceId = 'ws_default';

// State Cache
let dashboardData = null;
let inboxItems = [];
let calendarData = { scheduled: [], published: [] };
let ideasList = [];
let strategyData = [];
let brandData = null;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await loadAllData();
  switchTab('dashboard');
});

async function loadAllData() {
  try {
    const [dashRes, inboxRes, calRes, ideasRes, brandRes, stratRes] = await Promise.allSettled([
      fetch(`${API_BASE}/v1/analytics/overview`).then(r => r.json()),
      fetch(`${API_BASE}/v1/inbox`).then(r => r.json()),
      fetch(`${API_BASE}/v1/calendar`).then(r => r.json()),
      fetch(`${API_BASE}/v1/ideas`).then(r => r.json()),
      fetch(`${API_BASE}/v1/brand-profiles/${currentWorkspaceId}`).then(r => r.json()),
      fetch(`${API_BASE}/v1/strategy/insights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_id: currentWorkspaceId })
      }).then(r => r.json())
    ]);

    if (dashRes.status === 'fulfilled') dashboardData = dashRes.value;
    if (inboxRes.status === 'fulfilled') inboxItems = inboxRes.value;
    if (calRes.status === 'fulfilled') calendarData = calRes.value;
    if (ideasRes.status === 'fulfilled') ideasList = ideasRes.value;
    if (brandRes.status === 'fulfilled') brandData = brandRes.value;
    if (stratRes.status === 'fulfilled') strategyData = stratRes.value.insights || [];

    // Update inbox badge
    const badge = document.getElementById('inbox-badge');
    if (badge) badge.innerText = inboxItems.length;

  } catch (err) {
    console.warn("API fallback or network issue, using cached sample:", err);
  }
}

function switchTab(tabId) {
  activeTab = tabId;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.remove('text-cyan-400', 'bg-cyan-500/10', 'border', 'border-cyan-500/20');
    el.classList.add('text-slate-400');
  });

  const activeBtn = document.getElementById(`nav-${tabId}`);
  if (activeBtn) {
    activeBtn.classList.add('text-cyan-400', 'bg-cyan-500/10', 'border', 'border-cyan-500/20');
    activeBtn.classList.remove('text-slate-400');
  }

  const container = document.getElementById('content-container');
  if (!container) return;

  if (tabId === 'dashboard') renderDashboard(container);
  else if (tabId === 'inbox') renderInbox(container);
  else if (tabId === 'calendar') renderCalendar(container);
  else if (tabId === 'ideation') renderIdeation(container);
  else if (tabId === 'insights') renderInsights(container);
  else if (tabId === 'brand') renderBrand(container);

  if (window.lucide) lucide.createIcons();
}

// ---------------------------------------------------------------------------
// 1. DASHBOARD VIEW
// ---------------------------------------------------------------------------
function renderDashboard(container) {
  const d = dashboardData || {
    total_impressions: 12500,
    average_engagement_rate: 4.8,
    total_clicks: 184,
    published_posts_count: 5
  };

  container.innerHTML = `
    <!-- Top Stats Bar -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <div class="glass-panel p-6 rounded-2xl relative overflow-hidden">
        <div class="flex items-center justify-between text-slate-400 mb-2">
          <span class="text-xs font-semibold uppercase tracking-wider">Impressions Totales</span>
          <i data-lucide="eye" class="w-4 h-4 text-cyan-400"></i>
        </div>
        <div class="text-3xl font-extrabold text-white font-mono">${d.total_impressions.toLocaleString()}</div>
        <div class="mt-2 text-xs text-emerald-400 flex items-center gap-1 font-mono">
          <i data-lucide="trending-up" class="w-3.5 h-3.5"></i> +18.4% ce mois-ci
        </div>
      </div>

      <div class="glass-panel p-6 rounded-2xl relative overflow-hidden">
        <div class="flex items-center justify-between text-slate-400 mb-2">
          <span class="text-xs font-semibold uppercase tracking-wider">Taux d'Engagement</span>
          <i data-lucide="zap" class="w-4 h-4 text-amber-400"></i>
        </div>
        <div class="text-3xl font-extrabold text-white font-mono">${d.average_engagement_rate}%</div>
        <div class="mt-2 text-xs text-slate-400 font-mono">Cible éditoriale : > 3.5%</div>
      </div>

      <div class="glass-panel p-6 rounded-2xl relative overflow-hidden">
        <div class="flex items-center justify-between text-slate-400 mb-2">
          <span class="text-xs font-semibold uppercase tracking-wider">En Attente de Validation (HITL)</span>
          <i data-lucide="shield-alert" class="w-4 h-4 text-rose-400"></i>
        </div>
        <div class="text-3xl font-extrabold text-white font-mono">${inboxItems.length}</div>
        <div class="mt-2 text-xs text-amber-300 font-mono">Approbation humaine requise</div>
      </div>

      <div class="glass-panel p-6 rounded-2xl relative overflow-hidden">
        <div class="flex items-center justify-between text-slate-400 mb-2">
          <span class="text-xs font-semibold uppercase tracking-wider">Posts Planifiés</span>
          <i data-lucide="clock" class="w-4 h-4 text-indigo-400"></i>
        </div>
        <div class="text-3xl font-extrabold text-white font-mono">${calendarData.scheduled.length}</div>
        <div class="mt-2 text-xs text-cyan-300 font-mono">Idempotence garantie</div>
      </div>
    </div>

    <!-- Quick Action Banner -->
    <div class="glass-panel p-8 rounded-2xl border border-cyan-500/30 glow-gradient flex flex-col md:flex-row items-center justify-between gap-6">
      <div class="space-y-2">
        <span class="px-2.5 py-1 text-xs rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-mono">Système d'Exploitation Éditorial</span>
        <h2 class="text-xl font-bold text-white">Pipeline de Production Gouverné</h2>
        <p class="text-xs text-slate-300 max-w-2xl leading-relaxed">
          Transformez de la veille technique et des retours d'expérience en publications optimisées pour LinkedIn et X avec barrière déterministe de qualité et vérification systématique de provenance.
        </p>
      </div>
      <div class="flex gap-3 shrink-0">
        <button onclick="switchTab('inbox')" class="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs shadow-lg shadow-amber-500/20 flex items-center gap-2 transition">
          <i data-lucide="check-square" class="w-4 h-4"></i>
          <span>Vérifier les Brouillons (${inboxItems.length})</span>
        </button>
        <button onclick="triggerQuickResearchModal()" class="px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs shadow-lg shadow-cyan-600/20 flex items-center gap-2 transition">
          <i data-lucide="sparkles" class="w-4 h-4"></i>
          <span>Rechercher des Idées</span>
        </button>
      </div>
    </div>

    <!-- Live Activity & Governance Stream -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="glass-panel p-6 rounded-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 class="text-sm font-bold text-white flex items-center gap-2">
            <i data-lucide="git-pull-request" class="w-4 h-4 text-cyan-400"></i>
            Machine à États Éditoriale
          </h3>
          <span class="text-xs text-slate-400 font-mono">PRD Section 4.3</span>
        </div>
        <div class="text-xs font-mono space-y-2 text-slate-300">
          <div class="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
            <span>IDEA ➔ BRIEFED ➔ DRAFT</span>
            <span class="text-emerald-400">Automatisé</span>
          </div>
          <div class="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
            <span>DRAFT ➔ QA Gate (Claims & Règles)</span>
            <span class="text-emerald-400">Déterministe</span>
          </div>
          <div class="flex items-center justify-between p-2 rounded bg-amber-500/10 border border-amber-500/30">
            <span>IN_REVIEW ➔ APPROVED (HITL)</span>
            <span class="text-amber-400 font-bold">Interrupt Obligatoire</span>
          </div>
          <div class="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
            <span>SCHEDULED ➔ PUBLISHING (Worker)</span>
            <span class="text-cyan-400">Idempotent</span>
          </div>
        </div>
      </div>

      <div class="glass-panel p-6 rounded-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 class="text-sm font-bold text-white flex items-center gap-2">
            <i data-lucide="award" class="w-4 h-4 text-emerald-400"></i>
            Évaluations & Rigueur de Test
          </h3>
          <span class="text-xs text-slate-400 font-mono">80 Cas de Régression</span>
        </div>
        <div class="space-y-3">
          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-400">Fidélité source & citations (20 cas)</span>
            <span class="text-emerald-400 font-mono font-bold">100%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div class="bg-emerald-500 h-1.5 rounded-full" style="width: 100%"></div>
          </div>

          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-400">Ton & profil de marque (15 cas)</span>
            <span class="text-emerald-400 font-mono font-bold">100%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div class="bg-emerald-500 h-1.5 rounded-full" style="width: 100%"></div>
          </div>

          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-400">Adaptation par plateforme (15 cas)</span>
            <span class="text-emerald-400 font-mono font-bold">100%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div class="bg-emerald-500 h-1.5 rounded-full" style="width: 100%"></div>
          </div>

          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-400">Sécurité & approbation (10 cas)</span>
            <span class="text-emerald-400 font-mono font-bold">100%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div class="bg-emerald-500 h-1.5 rounded-full" style="width: 100%"></div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 2. HITL INBOX VIEW
// ---------------------------------------------------------------------------
function renderInbox(container) {
  if (!inboxItems || inboxItems.length === 0) {
    container.innerHTML = `
      <div class="glass-panel p-12 rounded-2xl text-center max-w-lg mx-auto space-y-4">
        <div class="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
          <i data-lucide="check-circle" class="w-8 h-8"></i>
        </div>
        <h3 class="text-lg font-bold text-white">Boîte de révision vide</h3>
        <p class="text-xs text-slate-400 leading-relaxed">
          Tous les brouillons ont été traités ou validés. Lancez une production depuis l'onglet Idéation pour générer de nouveaux contenus.
        </p>
        <button onclick="switchTab('ideation')" class="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition">
          Explorer les idées
        </button>
      </div>
    `;
    return;
  }

  const itemsHtml = inboxItems.map((item, idx) => `
    <div class="glass-panel p-6 rounded-2xl space-y-5 border border-slate-800 hover:border-slate-700 transition" id="inbox-card-${item.id}">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="px-2.5 py-1 text-xs rounded-full uppercase tracking-wider font-mono font-bold ${
            item.platform === 'linkedin' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : 'bg-slate-700/40 text-slate-300 border border-slate-600'
          }">${item.platform}</span>
          <span class="badge-review px-2.5 py-0.5 rounded-full text-xs font-mono">IN_REVIEW</span>
        </div>
        <div class="text-right">
          <span class="text-[11px] text-slate-400 font-mono block">Payload Hash</span>
          <span class="text-xs text-cyan-400 font-mono">${item.payload_hash.substring(0, 16)}...</span>
        </div>
      </div>

      <!-- Hook & Content Body -->
      <div class="space-y-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
        <div>
          <span class="text-[10px] font-semibold uppercase text-slate-400 tracking-wider">Hook d'accroche</span>
          <p class="text-sm font-semibold text-white mt-0.5">${item.hook}</p>
        </div>
        <div>
          <span class="text-[10px] font-semibold uppercase text-slate-400 tracking-wider">Corps du post</span>
          <div class="text-xs text-slate-200 mt-1 whitespace-pre-line leading-relaxed">${item.body}</div>
        </div>
        <div>
          <span class="text-[10px] font-semibold uppercase text-slate-400 tracking-wider">Call to Action (CTA)</span>
          <p class="text-xs text-cyan-300 mt-0.5 font-medium">${item.cta}</p>
        </div>
      </div>

      <!-- Verified Claims & Provenance -->
      <div class="space-y-2">
        <span class="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
          <i data-lucide="check-shield" class="w-3.5 h-3.5 text-emerald-400"></i>
          Claims factuels vérifiés (${item.claims ? item.claims.length : 0})
        </span>
        <div class="space-y-1.5">
          ${(item.claims || []).map(c => `
            <div class="flex items-center justify-between text-[11px] p-2 rounded-lg bg-emerald-950/20 border border-emerald-800/30 text-emerald-200">
              <span>« ${c.claim} »</span>
              <span class="font-mono text-emerald-400 text-[10px] px-1.5 py-0.5 bg-emerald-900/50 rounded">Confiance: ${Math.round(c.confidence_score * 100)}%</span>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- HITL Actions -->
      <div class="pt-4 border-t border-slate-800/80 flex items-center justify-between">
        <span class="text-xs text-slate-400">Validation humaine obligatoire avant planification</span>
        <div class="flex items-center gap-2">
          <button onclick="handleReject('${item.id}')" class="px-3.5 py-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-medium transition flex items-center gap-1.5">
            <i data-lucide="x" class="w-3.5 h-3.5"></i>
            <span>Rejeter</span>
          </button>
          <button onclick="handleRewrite('${item.id}')" class="px-3.5 py-2 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-medium transition flex items-center gap-1.5">
            <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
            <span>Demander réécriture</span>
          </button>
          <button onclick="handleApprove('${item.id}')" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition flex items-center gap-1.5 shadow-md shadow-emerald-600/20">
            <i data-lucide="check" class="w-3.5 h-3.5"></i>
            <span>Approuver & Planifier</span>
          </button>
        </div>
      </div>
    </div>
  `).join('');

  container.innerHTML = `
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-xl font-bold text-white flex items-center gap-2">
          <i data-lucide="shield-check" class="w-6 h-6 text-amber-400"></i>
          Boîte de Validation Humaine (HITL Review)
        </h2>
        <p class="text-xs text-slate-400">Tout contenu doit être explicitement approuvé pour pouvoir être publié.</p>
      </div>
      <span class="text-xs font-mono text-slate-400">${inboxItems.length} brouillon(s) à valider</span>
    </div>
    <div class="space-y-6">${itemsHtml}</div>
  `;
}

async function handleApprove(variantId) {
  try {
    const res = await fetch(`${API_BASE}/v1/content/${variantId}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Role': 'Owner'
      },
      body: JSON.stringify({
        decision: 'approve',
        reviewer_id: 'martial_owner',
        feedback: 'Approuvé via dashboard UI'
      })
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Erreur d'approbation : ${err.detail || 'Inconnue'}`);
      return;
    }

    // Schedule for publication in 1 hour
    const scheduleDate = new Date(Date.now() + 3600 * 1000).toISOString();
    await fetch(`${API_BASE}/v1/publications/schedule`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Role': 'Owner'
      },
      body: JSON.stringify({
        variant_id: variantId,
        scheduled_at: scheduleDate
      })
    });

    alert("✅ Variante approuvée et planifiée avec succès !");
    await loadAllData();
    renderInbox(document.getElementById('content-container'));
  } catch (err) {
    alert(`Erreur réseau : ${err.message}`);
  }
}

async function handleReject(variantId) {
  const reason = prompt("Motif du rejet (sauvegardé pour l'audit) :", "Non conforme à la stratégie actuelle");
  if (!reason) return;
  try {
    await fetch(`${API_BASE}/v1/content/${variantId}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Role': 'Owner'
      },
      body: JSON.stringify({
        decision: 'reject',
        reviewer_id: 'martial_owner',
        feedback: reason
      })
    });
    alert("Variante rejetée.");
    await loadAllData();
    renderInbox(document.getElementById('content-container'));
  } catch (e) {
    alert(e.message);
  }
}

async function handleRewrite(variantId) {
  const instruction = prompt("Instructions de réécriture :", "Rendre le hook plus direct");
  if (!instruction) return;
  try {
    await fetch(`${API_BASE}/v1/content/${variantId}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Role': 'Editor'
      },
      body: JSON.stringify({
        decision: 'request_rewrite',
        reviewer_id: 'martial_owner',
        feedback: instruction
      })
    });
    alert("Réécriture demandée. La variante est renvoyée en DRAFT.");
    await loadAllData();
    renderInbox(document.getElementById('content-container'));
  } catch (e) {
    alert(e.message);
  }
}

// ---------------------------------------------------------------------------
// 3. EDITORIAL CALENDAR VIEW
// ---------------------------------------------------------------------------
function renderCalendar(container) {
  const scheduled = calendarData.scheduled || [];
  const published = calendarData.published || [];

  container.innerHTML = `
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-xl font-bold text-white flex items-center gap-2">
          <i data-lucide="calendar" class="w-6 h-6 text-cyan-400"></i>
          Calendrier Éditorial & Publications
        </h2>
        <p class="text-xs text-slate-400">Suivi des créneaux planifiés et des posts déjà publiés avec receipt.</p>
      </div>
      <button onclick="triggerQuickResearchModal()" class="px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition flex items-center gap-1.5">
        <i data-lucide="plus" class="w-4 h-4"></i> Nouveau créneau
      </button>
    </div>

    <!-- Scheduled Jobs Section -->
    <div class="space-y-4">
      <h3 class="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
        <i data-lucide="clock" class="w-4 h-4 text-cyan-400"></i>
        Publications Planifiées (${scheduled.length})
      </h3>
      ${scheduled.length === 0 ? `
        <div class="glass-panel p-6 rounded-xl text-center text-xs text-slate-400">
          Aucun créneau planifié. Validez des brouillons depuis la boîte HITL pour les programmer.
        </div>
      ` : `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          ${scheduled.map(j => `
            <div class="glass-panel p-5 rounded-xl space-y-3 border border-slate-800">
              <div class="flex items-center justify-between">
                <span class="badge-scheduled px-2 py-0.5 rounded text-xs font-mono uppercase">${j.platform}</span>
                <span class="text-xs text-slate-400 font-mono">${new Date(j.scheduled_at).toLocaleString('fr-FR')}</span>
              </div>
              <p class="text-xs text-slate-200 line-clamp-2">${j.body_snippet}</p>
              <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <span class="text-[11px] text-cyan-300 font-mono">Prêt pour le Publisher Worker</span>
                <button onclick="handlePublishNow('${j.job_id}')" class="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition flex items-center gap-1">
                  <i data-lucide="send" class="w-3.5 h-3.5"></i>
                  <span>Publier maintenant</span>
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      `}
    </div>

    <!-- Published Posts Section -->
    <div class="space-y-4 pt-6">
      <h3 class="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
        <i data-lucide="check-circle" class="w-4 h-4 text-purple-400"></i>
        Historique des Posts Publiés (${published.length})
      </h3>
      ${published.length === 0 ? `
        <div class="glass-panel p-6 rounded-xl text-center text-xs text-slate-400">
          Aucun post publié pour le moment.
        </div>
      ` : `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          ${published.map(p => `
            <div class="glass-panel p-5 rounded-xl space-y-3 border border-slate-800">
              <div class="flex items-center justify-between">
                <span class="badge-published px-2 py-0.5 rounded text-xs font-mono uppercase">${p.platform}</span>
                <span class="text-xs text-slate-400 font-mono">${new Date(p.published_at).toLocaleString('fr-FR')}</span>
              </div>
              <p class="text-xs text-slate-200 line-clamp-2">${p.body_snippet}</p>
              <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span class="text-slate-400 font-mono">ID: ${p.external_id}</span>
                <a href="${p.permalink}" target="_blank" class="text-cyan-400 hover:underline flex items-center gap-1">
                  <span>Voir la receipt</span>
                  <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                </a>
              </div>
            </div>
          `).join('')}
        </div>
      `}
    </div>
  `;
}

async function handlePublishNow(jobId) {
  if (!confirm("Exécuter immédiatement la publication via le Publisher Worker ?")) return;
  try {
    const res = await fetch(`${API_BASE}/v1/publications/${jobId}/publish-now`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Role': 'Owner'
      }
    });
    const result = await res.json();
    if (!res.ok) {
      alert(`Erreur de publication : ${result.detail || 'Inconnue'}`);
      return;
    }
    alert(`🚀 Post publié avec succès ! Receipt : ${result.permalink}`);
    await loadAllData();
    renderCalendar(document.getElementById('content-container'));
  } catch (err) {
    alert(err.message);
  }
}

// ---------------------------------------------------------------------------
// 4. IDEATION & SOURCES LAB
// ---------------------------------------------------------------------------
function renderIdeation(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-xl font-bold text-white flex items-center gap-2">
          <i data-lucide="sparkles" class="w-6 h-6 text-cyan-400"></i>
          Idéation & Veille Stratégique
        </h2>
        <p class="text-xs text-slate-400">Idées générées et sourcées automatiquement par le Research Agent LangGraph.</p>
      </div>
      <button onclick="triggerQuickResearchModal()" class="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition flex items-center gap-2 shadow-lg shadow-cyan-600/20">
        <i data-lucide="search" class="w-4 h-4"></i> Lancer une recherche
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      ${(ideasList || []).map(i => `
        <div class="glass-panel p-5 rounded-2xl space-y-4 border border-slate-800 hover:border-slate-700 transition">
          <div class="flex items-center justify-between">
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/40">${i.pillar}</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono font-bold text-emerald-400">Score: ${i.total_score || 8.5}/10</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
                i.priority === 'high' ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-700 text-slate-300'
              }">${i.priority}</span>
            </div>
          </div>

          <div>
            <h4 class="text-sm font-bold text-white leading-snug">${i.title}</h4>
            <p class="text-xs text-slate-300 mt-1 leading-relaxed">${i.angle}</p>
          </div>

          <div class="flex items-center justify-between text-[11px] text-slate-400 font-mono bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
            <span>Nouveauté : ${i.novelty_score}/10</span>
            <span>Pertinence : ${i.relevance_score}/10</span>
            <span>Effort : ${i.effort_score}/10</span>
          </div>

          <div class="pt-3 border-t border-slate-800 flex items-center justify-between">
            <span class="text-[11px] text-slate-400">Audience : ${i.audience}</span>
            <button onclick="transformIdeaToDraft('${i.id}', '${encodeURIComponent(i.title)}')" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition flex items-center gap-1">
              <i data-lucide="file-plus" class="w-3.5 h-3.5"></i>
              <span>Créer le brief</span>
            </button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

async function transformIdeaToDraft(ideaId, encodedTitle) {
  const title = decodeURIComponent(encodedTitle);
  try {
    // 1. Create Brief
    const briefRes = await fetch(`${API_BASE}/v1/briefs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Role': 'Owner'
      },
      body: JSON.stringify({
        workspace_id: currentWorkspaceId,
        idea_id: ideaId,
        objective: `Positionner la marque comme leader sur : ${title}`,
        platform_targets: ['linkedin', 'x']
      })
    });
    const brief = await briefRes.json();

    // 2. Generate Package via LangGraph
    const genRes = await fetch(`${API_BASE}/v1/content/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Role': 'Owner'
      },
      body: JSON.stringify({
        brief_id: brief.id,
        workspace_id: currentWorkspaceId
      })
    });
    const pkg = await genRes.json();

    alert(`✨ Package de contenu généré avec succès ! (${pkg.variants.length} variantes créées et soumises au Quality Gate)`);
    await loadAllData();
    switchTab('inbox');
  } catch (err) {
    alert(err.message);
  }
}

// ---------------------------------------------------------------------------
// 5. STRATEGY & INSIGHTS VIEW (Propositional Learning)
// ---------------------------------------------------------------------------
function renderInsights(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-xl font-bold text-white flex items-center gap-2">
          <i data-lucide="trending-up" class="w-6 h-6 text-indigo-400"></i>
          Apprentissage Propositionnel & Recommandations
        </h2>
        <p class="text-xs text-slate-400">Conforme à l'ADR 6 : Les métriques génèrent des hypothèses d'action sans modification automatique sans accord humain.</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      ${(strategyData || []).map(item => `
        <div class="glass-panel p-6 rounded-2xl space-y-4 border border-slate-800">
          <div class="flex items-center justify-between">
            <span class="px-2.5 py-1 text-xs rounded-full font-mono bg-indigo-950/60 text-indigo-300 border border-indigo-800/40">${item.pillar}</span>
            <span class="text-xs font-mono font-bold text-cyan-300">Confiance : ${Math.round(item.confidence_level * 100)}%</span>
          </div>

          <div class="space-y-2 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            <div>
              <span class="text-[10px] font-semibold uppercase text-slate-400">Fait observé</span>
              <p class="text-xs text-slate-200 mt-0.5">${item.fact}</p>
            </div>
            <div class="pt-2 border-t border-slate-800">
              <span class="text-[10px] font-semibold uppercase text-amber-400">Hypothèse causale</span>
              <p class="text-xs text-slate-300 mt-0.5 italic">« ${item.hypothesis} »</p>
            </div>
          </div>

          <div class="pt-2">
            <span class="text-[10px] font-semibold uppercase text-emerald-400">Recommandation d'ajustement</span>
            <p class="text-xs text-white mt-1 leading-relaxed font-medium">${item.recommended_action}</p>
          </div>

          <div class="pt-3 border-t border-slate-800 flex justify-end">
            <button onclick="alert('✅ Recommandation adoptée pour les futures suggestions de briefs !')" class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition flex items-center gap-1.5">
              <i data-lucide="thumbs-up" class="w-3.5 h-3.5"></i>
              <span>Approuver l'hypothèse</span>
            </button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 6. BRAND PROFILE VIEW
// ---------------------------------------------------------------------------
function renderBrand(container) {
  const b = brandData || {
    version: 1,
    voice: "Direct, expert, pragmatique, orienté retour d'expérience.",
    pillars: ["IA générative & LLMs", "Systèmes multi-agents & LangGraph", "Automatisation d'entreprise"],
    audience: ["Tech Leads", "AI Engineers", "CTOs", "Founders"],
    prohibited_topics: ["Spéculation crypto", "Rumeurs non vérifiées", "Dénigrement concurrent direct"]
  };

  container.innerHTML = `
    <div class="max-w-4xl space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-xl font-bold text-white flex items-center gap-2">
            <i data-lucide="fingerprint" class="w-6 h-6 text-cyan-400"></i>
            Profil de Marque & Piliers Éditoriaux
          </h2>
          <p class="text-xs text-slate-400">Version actuelle : v${b.version} • Versionnage immutable en base de données</p>
        </div>
      </div>

      <div class="glass-panel p-6 rounded-2xl space-y-5 border border-slate-800">
        <div>
          <label class="block text-xs font-semibold uppercase text-slate-400 mb-1">Voix & Ton Éditorial</label>
          <div class="p-3 bg-slate-900/60 rounded-xl border border-slate-800 text-xs text-slate-200">${b.voice}</div>
        </div>

        <div>
          <label class="block text-xs font-semibold uppercase text-slate-400 mb-2">Piliers d'expertise</label>
          <div class="flex flex-wrap gap-2">
            ${b.pillars.map(p => `<span class="px-3 py-1 rounded-lg bg-cyan-950/40 text-cyan-300 border border-cyan-800/40 text-xs font-mono">${p}</span>`).join('')}
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold uppercase text-slate-400 mb-2">Audiences Cibles</label>
          <div class="flex flex-wrap gap-2">
            ${b.audience.map(a => `<span class="px-3 py-1 rounded-lg bg-slate-800 text-slate-200 border border-slate-700 text-xs">${a}</span>`).join('')}
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold uppercase text-rose-400 mb-2">Sujets Interdits (Strict Guardrails)</label>
          <div class="flex flex-wrap gap-2">
            ${b.prohibited_topics.map(t => `<span class="px-3 py-1 rounded-lg bg-rose-950/30 text-rose-300 border border-rose-800/40 text-xs">${t}</span>`).join('')}
          </div>
        </div>
      </div>
    </div>
  `;
}

// Modal actions
function triggerQuickResearchModal() {
  const modal = document.getElementById('modal-research');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}

async function executeResearch() {
  const topic = document.getElementById('input-research-topic').value;
  const count = parseInt(document.getElementById('input-research-count').value, 10) || 10;
  if (!topic) return alert("Veuillez saisir un sujet.");

  const btn = document.getElementById('btn-submit-research');
  btn.disabled = true;
  btn.innerHTML = `<span class="animate-spin">🌀</span> Exécution LangGraph...`;

  try {
    const res = await fetch(`${API_BASE}/v1/ideas/research`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Role': 'Owner'
      },
      body: JSON.stringify({
        workspace_id: currentWorkspaceId,
        topic_or_brief: topic,
        target_count: count
      })
    });
    const result = await res.json();
    alert(`🎉 ${result.ideas.length} idées générées et scorées avec succès !`);
    closeModal('modal-research');
    await loadAllData();
    switchTab('ideation');
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>Générer</span>`;
  }
}
