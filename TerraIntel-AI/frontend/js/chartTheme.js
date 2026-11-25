/**
 * Shared Chart.js theme configuration matching dark workbench tokens.
 */
export function applyChartDefaults() {
  if (!window.Chart) return;
  const { Chart } = window;
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size = 11;
  Chart.defaults.color = "#94A3B8";
  Chart.defaults.borderColor = "#1F2937";
}

export function baseChartOptions({ xTitle = "", yTitle = "" } = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: {
        labels: {
          color: "#F1F5F9",
          boxWidth: 10,
          font: { size: 11, weight: "500" },
        },
      },
    },
    scales: {
      x: {
        grid: { color: "#1F2937" },
        ticks: { color: "#94A3B8" },
        title: { display: Boolean(xTitle), text: xTitle, color: "#94A3B8" },
      },
      y: {
        grid: { color: "#1F2937" },
        ticks: { color: "#94A3B8" },
        title: { display: Boolean(yTitle), text: yTitle, color: "#94A3B8" },
      },
    },
  };
}
