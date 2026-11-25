import { api } from "../api.js";

export function renderRegionSearch(container, onSelectLocation) {
  container.innerHTML = `
    <div class="search-row">
      <input id="nominatim-query" class="input" type="search" placeholder="Search place or coordinates" aria-label="Search location">
      <button id="nominatim-btn" class="btn" type="button">Search</button>
    </div>
    <ul id="nominatim-results" class="search-results" hidden></ul>
  `;

  const input = container.querySelector("#nominatim-query");
  const btn = container.querySelector("#nominatim-btn");
  const list = container.querySelector("#nominatim-results");

  async function runSearch() {
    const q = input.value.trim();
    if (!q) return;
    btn.disabled = true;
    list.hidden = true;
    try {
      const results = await api.searchNominatim(q);
      if (!Array.isArray(results) || results.length === 0) {
        list.innerHTML = '<li><button type="button" disabled>No matching locations found</button></li>';
      } else {
        list.innerHTML = results
          .map(
            (r, idx) =>
              `<li><button type="button" data-idx="${idx}">${r.display_name}</button></li>`
          )
          .join("");
        list.querySelectorAll("button[data-idx]").forEach((b) => {
          b.addEventListener("click", () => {
            const item = results[Number(b.getAttribute("data-idx"))];
            onSelectLocation(Number(item.lat), Number(item.lon));
            list.hidden = true;
          });
        });
      }
      list.hidden = false;
    } catch {
      list.innerHTML = '<li><button type="button" disabled>Location search timed out or failed</button></li>';
      list.hidden = false;
    } finally {
      btn.disabled = false;
    }
  }

  btn.addEventListener("click", runSearch);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runSearch();
    }
  });
}
