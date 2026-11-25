const YLGN_9 = [
  "#ffffe5",
  "#f7fcb9",
  "#d9f0a3",
  "#addd8e",
  "#78c679",
  "#41ab5d",
  "#238443",
  "#006837",
  "#004529",
];

export function renderNdviLegend(container) {
  const swatches = YLGN_9.map((hex) => `<span style="background-color:${hex}"></span>`).join("");
  container.innerHTML = `
    <div class="ndvi-legend" aria-label="NDVI Colour Legend">
      <div><strong>NDVI (unitless, YlGn)</strong></div>
      <div class="legend-ramp">${swatches}</div>
      <div class="legend-labels"><span>0.00</span><span>0.45</span><span>0.90</span></div>
      <div class="legend-nodata">
        <span class="nodata-swatch"></span>
        <span>No data / masked</span>
      </div>
      <div class="legend-nodata">
        <span style="width:14px;height:10px;border:1px solid #F59E0B;background:rgba(239,68,68,0.35);display:inline-block"></span>
        <span>Low greenness zone</span>
      </div>
    </div>
  `;
}
