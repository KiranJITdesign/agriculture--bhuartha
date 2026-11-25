import { baseChartOptions } from "../chartTheme.js";

export function renderNdviHistogram(canvasEl, classStats) {
  if (!window.Chart) return null;
  const labels = classStats.map((s) => s.vigour_class);
  const values = classStats.map((s) => Number(s.area_ha));

  return new window.Chart(canvasEl.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Cropland area (ha)",
          data: values,
          backgroundColor: "#10B981",
          borderRadius: 3,
        },
      ],
    },
    options: baseChartOptions({ xTitle: "Vigour class", yTitle: "Area (ha)" }),
  });
}
