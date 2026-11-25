const ROUTES = [
  { hash: "#/explorer", label: "Explorer" },
  { hash: "#/regions", label: "Regions" },
  { hash: "#/crop-health", label: "Crop Health" },
  { hash: "#/weather", label: "Weather" },
  { hash: "#/compare", label: "Compare" },
];

export function renderNav(container, currentHash) {
  const links = ROUTES.map((route) => {
    const active = currentHash === route.hash ? 'aria-current="page"' : "";
    return `<li><a class="nav-link" href="${route.hash}" ${active}>${route.label}</a></li>`;
  }).join("");

  container.innerHTML = `
    <div class="topbar-brand">
      <h1 class="brand-title">TerraIntel</h1>
      <p class="brand-subtitle">Agriculture &amp; Crop Health Workbench</p>
    </div>
    <nav class="topbar-nav" aria-label="Module sections">
      <ul class="nav-list">${links}</ul>
    </nav>
  `;
}
