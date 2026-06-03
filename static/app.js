/* ──────────────────────────────────────────────────────────────
   LocalWebManager — Frontend
   ────────────────────────────────────────────────────────────── */

const servicesEl = document.getElementById("services");
const pinnedEl = document.getElementById("pinnedServices");
const pinnedSection = document.getElementById("pinnedSection");
const metaEl = document.getElementById("meta");
const lastUpdatedEl = document.getElementById("lastUpdated");
const refreshBtn = document.getElementById("refreshBtn");
const webOnlyToggle = document.getElementById("webOnlyToggle");
const cardTemplate = document.getElementById("cardTemplate");
const emptyState = document.getElementById("emptyState");

/* ── Framework icon map ───────────────────────────────────── */
const FRAMEWORK_ICONS = {
  Vite: "⚡",
  "Next.js": "▲",
  Nuxt: "💚",
  Astro: "🚀",
  SvelteKit: "🔥",
  Remix: "💿",
  Webpack: "📦",
  Parcel: "📦",
  "Create React App": "⚛️",
  "Angular CLI": "🅰️",
  Flask: "🐍",
  Django: "🐍",
  Uvicorn: "🦄",
  Gunicorn: "🦄",
  FastAPI: "⚡",
  "Python HTTP": "🐍",
  Rails: "💎",
  Hugo: "📝",
  "PHP Built-in": "🐘",
  Gatsby: "💜",
  Express: "🟢",
  Fastify: "🟢",
  Hono: "🔥",
  Elysia: "🦊",
  Bun: "🍞",
  Deno: "🦕",
  TSX: "📘",
};

/* ── Pinning (localStorage) ──────────────────────────────── */

const PINS_KEY = "lwm_pinned";

function loadPins() {
  try {
    const raw = localStorage.getItem(PINS_KEY);
    if (!raw) return {};
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function savePins(pins) {
  localStorage.setItem(PINS_KEY, JSON.stringify(pins));
}

function pinKey(service) {
  return String(service.port);
}

function isPinned(service) {
  return pinKey(service) in loadPins();
}

function togglePin(service) {
  const pins = loadPins();
  const key = pinKey(service);
  if (pins[key]) {
    delete pins[key];
  } else {
    pins[key] = {
      port: service.port,
      host: service.host,
      url: service.url,
      friendly_name: service.friendly_name,
      framework: service.framework,
      app_name: service.app_name,
    };
  }
  savePins(pins);
}

/* ── Helpers ──────────────────────────────────────────────── */

function fallback(value) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function truncatePath(raw) {
  if (!raw) return "—";
  let p = raw;
  const homeMatch = p.match(/^\/home\/[^/]+/);
  if (homeMatch) {
    p = "~" + p.slice(homeMatch[0].length);
  }
  const parts = p.split("/");
  if (parts.length > 5) {
    p = "…/" + parts.slice(-3).join("/");
  }
  return p;
}

function formatTime(date) {
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/* ── Card building ────────────────────────────────────────── */

function buildCard(service, { animateIn = false, offline = false } = {}) {
  const card = cardTemplate.content.firstElementChild.cloneNode(true);
  const key = pinKey(service);
  card.dataset.key = key;

  if (animateIn) card.classList.add("animate-in");
  if (offline) card.classList.add("card-offline");

  populateCard(card, service, offline);
  attachCardListeners(card, service, offline);

  return card;
}

function populateCard(card, service, offline) {
  const friendlyName =
    service.friendly_name || service.app_name || `Port ${service.port}`;
  card.querySelector(".friendly-name").textContent = friendlyName;
  card.querySelector(".friendly-name").title = friendlyName;

  const icon = FRAMEWORK_ICONS[service.framework] || "🌐";
  card.querySelector(".framework-badge").textContent = icon;
  card.querySelector(".port-badge").textContent = `:${service.port}`;
  card.querySelector(".app-name").textContent = fallback(service.app_name);

  const processText =
    offline
      ? "stopped"
      : service.process_name && service.process_name !== "unknown"
        ? `${service.process_name}` +
          (service.pid ? ` · PID ${service.pid}` : "")
        : service.pid
          ? `PID ${service.pid}`
          : "—";
  card.querySelector(".process-info").textContent = processText;

  const cwdEl = card.querySelector(".cwd");
  cwdEl.textContent = offline ? "—" : truncatePath(service.cwd);
  cwdEl.title = service.cwd || "";

  card.querySelector(".cmdline").textContent = offline
    ? "—"
    : fallback(service.cmdline);

  // Pin state
  const pinBtn = card.querySelector(".pin-btn");
  if (isPinned(service)) {
    pinBtn.classList.add("pinned");
    pinBtn.title = "Unpin service";
  } else {
    pinBtn.classList.remove("pinned");
    pinBtn.title = "Pin service";
  }

  // Kill state
  const killBtn = card.querySelector(".kill-btn");
  if (offline || !service.pid) {
    killBtn.disabled = true;
    killBtn.classList.add("btn-disabled");
  } else {
    killBtn.disabled = false;
    killBtn.classList.remove("btn-disabled");
  }

  // Offline/online state
  if (offline) {
    card.classList.add("card-offline");
  } else {
    card.classList.remove("card-offline");
  }
}

function attachCardListeners(card, service, offline) {
  const friendlyName =
    service.friendly_name || service.app_name || `Port ${service.port}`;

  // Open link
  const link = card.querySelector(".open-link");
  link.href = service.url;
  link.addEventListener("click", (e) => {
    e.preventDefault();
    window.open(service.url, "_blank", "noopener,noreferrer");
  });

  // Copy URL
  const copyBtn = card.querySelector(".copy-url");
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(service.url).then(() => {
      copyBtn.classList.add("copied");
      const origHTML = copyBtn.innerHTML;
      copyBtn.innerHTML =
        `<svg width="14" height="14" viewBox="0 0 14 14" fill="none">` +
        `<path d="M3 7.5l2.5 2.5L11 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>` +
        `</svg> Copied!`;
      setTimeout(() => {
        copyBtn.classList.remove("copied");
        copyBtn.innerHTML = origHTML;
      }, 1500);
    });
  });

  // Kill button
  const killBtn = card.querySelector(".kill-btn");
  if (!offline && service.pid) {
    killBtn.addEventListener("click", async () => {
      if (!confirm(`Kill "${friendlyName}" (PID ${service.pid})?`)) return;
      killBtn.disabled = true;
      killBtn.innerHTML =
        `<svg class="spin-target" style="animation:spin .8s linear infinite" width="14" height="14" viewBox="0 0 16 16" fill="none">` +
        `<path d="M14 8A6 6 0 1 1 8 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>` +
        `</svg> Killing…`;
      try {
        const res = await fetch(`/api/services/${service.pid}`, {
          method: "DELETE",
        });
        const data = await res.json();
        if (data.ok) {
          card.classList.add("card-dying");
          setTimeout(() => loadServices(), 1000);
        } else {
          alert(data.error || "Failed to kill process");
          killBtn.disabled = false;
        }
      } catch (err) {
        alert("Error: " + err.message);
        killBtn.disabled = false;
      }
    });
  }

  // Pin button
  const pinBtn = card.querySelector(".pin-btn");
  pinBtn.addEventListener("click", () => {
    togglePin(service);
    loadServices();
  });
}

/* ── Keyed DOM reconciliation (no-flash updates) ──────────── */

let isFirstRender = true;
let prevActiveKeys = new Set();

/**
 * Reconcile a grid container with a list of services.
 * - Existing cards with matching keys get updated in-place (no DOM rebuild).
 * - New cards get inserted with optional entrance animation.
 * - Removed cards get taken out.
 */
function reconcileGrid(container, services, { offline = false } = {}) {
  const newKeys = services.map((s) => pinKey(s));
  const newKeySet = new Set(newKeys);
  const existingByKey = new Map();

  for (const child of [...container.children]) {
    existingByKey.set(child.dataset.key, child);
  }

  // Remove cards no longer in list
  for (const [key, el] of existingByKey) {
    if (!newKeySet.has(key)) {
      el.remove();
      existingByKey.delete(key);
    }
  }

  // Add or update in correct order
  for (let i = 0; i < services.length; i++) {
    const service = services[i];
    const key = pinKey(service);
    const existing = existingByKey.get(key);

    if (existing) {
      // Update text in-place — no DOM teardown
      populateCard(existing, service, offline);
      // Ensure correct position
      if (container.children[i] !== existing) {
        container.insertBefore(existing, container.children[i]);
      }
    } else {
      // New card
      const shouldAnimate = isFirstRender || !prevActiveKeys.has(key);
      const card = buildCard(service, { animateIn: shouldAnimate, offline });
      if (container.children[i]) {
        container.insertBefore(card, container.children[i]);
      } else {
        container.appendChild(card);
      }
    }
  }
}

/* ── Main render loop ─────────────────────────────────────── */

async function loadServices() {
  refreshBtn.classList.add("refreshing");
  refreshBtn.disabled = true;

  try {
    const response = await fetch("/api/services");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const payload = await response.json();
    const services = payload.services || [];
    const webOnly = webOnlyToggle ? webOnlyToggle.checked : false;
    const filtered = webOnly
      ? services.filter((s) => Boolean(s.likely_web))
      : services;

    // Split pinned vs unpinned
    const pins = loadPins();
    const activePorts = new Set(filtered.map((s) => String(s.port)));
    const pinnedActive = filtered.filter((s) => pins[pinKey(s)]);
    const unpinned = filtered.filter((s) => !pins[pinKey(s)]);

    // Pinned services that are offline (saved but not currently running)
    const pinnedOffline = [];
    for (const [key, pinData] of Object.entries(pins)) {
      if (!activePorts.has(key)) {
        pinnedOffline.push(pinData);
      }
    }

    // ── Pinned section ───────────────────────────────────────
    const allPinned = [...pinnedActive, ...pinnedOffline];
    if (allPinned.length > 0) {
      pinnedSection.classList.remove("hidden");
      // Reconcile pinned-active cards
      reconcileGrid(pinnedEl, pinnedActive);
      // For offline pins, we need to handle them separately since
      // they might share keys with active ones in the other grid
      const offlineKeys = new Set(pinnedOffline.map((p) => String(p.port)));

      // Remove stale offline cards
      for (const child of [...pinnedEl.children]) {
        const key = child.dataset.key;
        if (
          !pinnedActive.some((s) => pinKey(s) === key) &&
          !offlineKeys.has(key)
        ) {
          child.remove();
        }
      }

      // Add/update offline pinned cards
      for (const pinData of pinnedOffline) {
        const key = String(pinData.port);
        let existing = null;
        for (const child of pinnedEl.children) {
          if (child.dataset.key === key) {
            existing = child;
            break;
          }
        }
        if (existing) {
          populateCard(existing, pinData, true);
        } else {
          const card = buildCard(pinData, { animateIn: isFirstRender, offline: true });
          pinnedEl.appendChild(card);
        }
      }
    } else {
      pinnedSection.classList.add("hidden");
      pinnedEl.innerHTML = "";
    }

    // ── Active (unpinned) section ────────────────────────────
    if (unpinned.length === 0 && allPinned.length === 0) {
      emptyState.classList.remove("hidden");
      servicesEl.innerHTML = "";
    } else {
      emptyState.classList.add("hidden");
      reconcileGrid(servicesEl, unpinned);
    }

    // ── Status bar ───────────────────────────────────────────
    const shown = filtered.length;
    const total = services.length;
    const pinnedCount = allPinned.length;
    const parts = [];
    parts.push(
      `<span class="count">${shown}</span> service${shown !== 1 ? "s" : ""} active`
    );
    if (pinnedCount > 0) {
      parts.push(`<span class="count">${pinnedCount}</span> pinned`);
    }
    if (shown !== total) {
      parts.push(`${total} total`);
    }
    metaEl.innerHTML =
      `<span class="live-dot"></span>` +
      parts.join(` <span style="color:var(--muted)">·</span> `);

    lastUpdatedEl.textContent = `Updated ${formatTime(new Date())}`;

    // Track for next diff
    prevActiveKeys = new Set([
      ...filtered.map((s) => pinKey(s)),
      ...pinnedOffline.map((p) => String(p.port)),
    ]);
    isFirstRender = false;
  } catch (error) {
    metaEl.innerHTML = `<span style="color:var(--red)">⚠ Unable to load services: ${error.message}</span>`;
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.classList.remove("refreshing");
  }
}

/* ── Event listeners ─────────────────────────────────────── */

refreshBtn.addEventListener("click", loadServices);
if (webOnlyToggle) {
  webOnlyToggle.addEventListener("change", loadServices);
}

loadServices();
setInterval(loadServices, 5000);
