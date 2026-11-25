const RDBU_11 = [
  "#67001f",
  "#b2182b",
  "#d6604d",
  "#f4a582",
  "#fddbc7",
  "#f7f7f7",
  "#d1e5f0",
  "#92c5de",
  "#4393c3",
  "#2166ac",
  "#053061",
];

export function renderDiffLegend(container) {
  const swatches = RDBU_11.map((hex) => `<span style="background-color:${hex}"></span>`).join("");
  container.innerHTML = `
    <div class="diff-legend" aria-label="Delta NDVI Legend">
      <div><strong>Delta NDVI (Period B - Period A, RdBu 11-class)</strong></div>
      <div class="diff-ramp">${swatches}</div>
      <div class="diff-labels">
        <span>-0.50</span><span>-0.25</span><span>0.00</span><span>+0.25</span><span>+0.50</span>
      </div>
    </div>
  `;
}
