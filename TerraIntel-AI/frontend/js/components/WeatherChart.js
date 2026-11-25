import { baseChartOptions } from "../chartTheme.js";

export function renderWeatherChart(canvasEl, daily) {
  if (!window.Chart) return null;
  const labels = daily.map((d) => d.date);
  const rain = daily.map((d) => Number(d.rainfall_mm));
  const temp = daily.map((d) => Number(d.temperature_c));

  const opts = baseChartOptions({ xTitle: "Date" });
  opts.interaction = { mode: "index", intersect: false };
  opts.plugins.tooltip = {
    callbacks: {
      label: (ctx) => {
        if (ctx.datasetIndex === 0) return `Rainfall: ${ctx.parsed.y.toFixed(2)} mm`;
        return `Temperature: ${ctx.parsed.y.toFixed(2)} C`;
      },
    },
  };
  opts.scales.y = {
    type: "linear",
    position: "left",
    grid: { color: "#1F2937" },
    ticks: { color: "#94A3B8" },
    title: { display: true, text: "Rainfall (mm)", color: "#94A3B8" },
  };
  opts.scales.y1 = {
    type: "linear",
    position: "right",
    grid: { drawOnChartArea: false },
    ticks: { color: "#94A3B8" },
    title: { display: true, text: "Temperature (C)", color: "#94A3B8" },
  };

  return new window.Chart(canvasEl.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Rainfall (mm)",
          data: rain,
          backgroundColor: "#10B981",
          borderRadius: 3,
          yAxisID: "y",
        },
        {
          type: "line",
          label: "Temperature (C)",
          data: temp,
          borderColor: "#F59E0B",
          backgroundColor: "#F59E0B",
          borderWidth: 2,
          pointRadius: 2,
          yAxisID: "y1",
        },
      ],
    },
    options: opts,
  });
}
