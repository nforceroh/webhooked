document.addEventListener("click", async (event) => {
  const copyButton = event.target.closest("[data-copy]");
  if (copyButton) {
    try {
      await navigator.clipboard.writeText(copyButton.dataset.copy);
      const original = copyButton.textContent;
      copyButton.textContent = "Copied";
      window.setTimeout(() => { copyButton.textContent = original; }, 1400);
    } catch {
      window.prompt("Copy the capture URL:", copyButton.dataset.copy);
    }
  }

  const confirmButton = event.target.closest("[data-confirm]");
  if (confirmButton && !window.confirm(confirmButton.dataset.confirm)) {
    event.preventDefault();
    event.stopPropagation();
  }
});

document.addEventListener("change", (event) => {
  if (!event.target.matches("[data-select-all]")) return;
  document.querySelectorAll('#bulk-form input[name="delivery_ids"]').forEach((checkbox) => {
    checkbox.checked = event.target.checked;
  });
});

if (document.querySelector("#delivery-results")) {
  window.setInterval(async () => {
    if (document.hidden || document.activeElement.matches("input, select, textarea")) return;
    if (document.querySelector('#bulk-form input[name="delivery_ids"]:checked')) return;
    const status = document.querySelector("[data-poll-status]");
    try {
      const response = await fetch(window.location.href, { headers: { "X-Requested-With": "fetch" } });
      if (!response.ok) throw new Error(`Refresh failed (${response.status}).`);
      const html = new DOMParser().parseFromString(await response.text(), "text/html");
      const freshResults = html.querySelector("#delivery-results");
      const currentResults = document.querySelector("#delivery-results");
      if (!freshResults || !currentResults) throw new Error("Delivery list was missing in refresh.");
      currentResults.replaceWith(freshResults);
      if (status) status.textContent = "Auto-refreshes every 10 seconds";
    } catch {
      if (status) status.textContent = "Refresh failed; retrying…";
    }
  }, 10000);
}

document.querySelector("[data-theme-toggle]")?.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("theme", next);
});
