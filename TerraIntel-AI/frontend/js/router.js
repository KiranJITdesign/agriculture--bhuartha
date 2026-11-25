import { renderNav } from "./components/Nav.js";
import { applyChartDefaults } from "./chartTheme.js";
import { renderExplorerPage } from "./pages/explorer.js";
import { renderRegionsPage } from "./pages/regions.js";
import { renderCropHealthPage } from "./pages/cropHealth.js";
import { renderWeatherPage } from "./pages/weather.js";
import { renderComparePage } from "./pages/compare.js";

const PAGE_MAP = {
  "#/explorer": renderExplorerPage,
  "#/regions": renderRegionsPage,
  "#/crop-health": renderCropHealthPage,
  "#/weather": renderWeatherPage,
  "#/compare": renderComparePage,
};

function navigate() {
  const hash = window.location.hash || "#/explorer";
  const routeKey = PAGE_MAP[hash] ? hash : "#/explorer";
  const navEl = document.getElementById("app-nav");
  const mainEl = document.getElementById("app-main");
  renderNav(navEl, routeKey);
  PAGE_MAP[routeKey](mainEl);
}

applyChartDefaults();
window.addEventListener("hashchange", navigate);
window.addEventListener("DOMContentLoaded", navigate);
