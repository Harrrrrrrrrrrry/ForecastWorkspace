const metricCards = [
  { label: "Selected Benchmark", value: "Pending model run" },
  { label: "Alpha Weight", value: "--" },
  { label: "Predicted Price", value: "--" },
  { label: "Percent Change", value: "--" },
  { label: "Confidence", value: "Pending Phase 5" },
  { label: "Warning Status", value: "No result yet" },
];

export function MetricCards() {
  return (
    <div className="metric-grid">
      {metricCards.map((metric) => (
        <div className="metric-card" key={metric.label}>
          <span className="metric-label">{metric.label}</span>
          <span className="metric-value">{metric.value}</span>
        </div>
      ))}
    </div>
  );
}

