const servicesEl = document.getElementById("services");
const metaEl = document.getElementById("meta");
const refreshBtn = document.getElementById("refreshBtn");
const webOnlyToggle = document.getElementById("webOnlyToggle");
const cardTemplate = document.getElementById("cardTemplate");

function text(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

async function loadServices() {
  refreshBtn.disabled = true;

  try {
    const response = await fetch("/api/services");
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    const payload = await response.json();
    const services = payload.services || [];
    const webOnly = webOnlyToggle ? webOnlyToggle.checked : false;
    const filtered = webOnly
      ? services.filter((service) => Boolean(service.likely_web))
      : services;

    servicesEl.innerHTML = "";

    if (filtered.length === 0) {
      metaEl.textContent = "No local web services detected.";
      return;
    }

    metaEl.textContent = `${filtered.length} shown (${services.length} total local services).`;

    for (const service of filtered) {
      const card = cardTemplate.content.firstElementChild.cloneNode(true);
      card.querySelector(".service-url").textContent = service.url;
      card.querySelector(".app-name").textContent = text(service.app_name);
      card.querySelector(".process-name").textContent = text(service.process_name);
      card.querySelector(".pid").textContent = text(service.pid);
      card.querySelector(".port").textContent = text(service.port);
      card.querySelector(".cwd").textContent = text(service.cwd);
      card.querySelector(".cmdline").textContent = text(service.cmdline);

      const link = card.querySelector(".open-link");
      link.href = service.url;

      servicesEl.appendChild(card);
    }
  } catch (error) {
    metaEl.textContent = `Unable to load services: ${error.message}`;
  } finally {
    refreshBtn.disabled = false;
  }
}

refreshBtn.addEventListener("click", loadServices);
if (webOnlyToggle) {
  webOnlyToggle.addEventListener("change", loadServices);
}

loadServices();
setInterval(loadServices, 5000);
