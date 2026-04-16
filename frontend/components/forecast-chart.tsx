"use client";

import { ForecastResponse } from "@/lib/api";

type ForecastChartProps = {
  forecast: ForecastResponse;
};

type LineSeries = {
  label: string;
  color: string;
  values: number[];
  startIndex: number;
  dashed?: boolean;
  strokeWidth?: number;
};

type BarDatum = {
  label: string;
  note?: string;
  value: number;
  display: string;
  color: string;
};

const LINE_CHART_WIDTH = 1280;
const LINE_CHART_HEIGHT = 420;
const LINE_CHART_LEFT = 88;
const LINE_CHART_RIGHT = 40;
const LINE_CHART_TOP = 28;
const LINE_CHART_BOTTOM = 52;

export function ForecastChart({ forecast }: ForecastChartProps) {
  const historical = forecast.historical_prices;
  const lastHistorical = historical.at(-1)?.value ?? 0;
  const futurePointCount = forecast.ensemble_forecast.length;
  const totalPoints = historical.length + futurePointCount;

  const series: LineSeries[] = [
    {
      label: "Historical Price",
      color: "#f0f0fa",
      values: historical.map((point) => point.value),
      startIndex: 0,
      strokeWidth: 2.2,
    },
    {
      label: "Market Influence",
      color: "#c9d1ff",
      values: [lastHistorical, ...forecast.final_combined_forecast.map((point) => point.value)],
      startIndex: Math.max(historical.length - 1, 0),
      dashed: true,
      strokeWidth: 2,
    },
    {
      label: "ARIMA",
      color: "#f4c68d",
      values: [lastHistorical, ...forecast.arima_forecast.map((point) => point.value)],
      startIndex: Math.max(historical.length - 1, 0),
      dashed: true,
      strokeWidth: 2,
    },
    {
      label: "XGBoost",
      color: "#8fe6d8",
      values: [lastHistorical, ...forecast.ml_forecast.map((point) => point.value)],
      startIndex: Math.max(historical.length - 1, 0),
      dashed: true,
      strokeWidth: 2,
    },
    {
      label: "Combined Forecast",
      color: "#ffffff",
      values: [lastHistorical, ...forecast.ensemble_forecast.map((point) => point.value)],
      startIndex: Math.max(historical.length - 1, 0),
      strokeWidth: 3,
    },
  ].filter((item) => item.values.length > 1);

  const allValues = series.flatMap((item) => item.values);
  const minValue = Math.min(...allValues);
  const maxValue = Math.max(...allValues);
  const valueRange = maxValue - minValue || 1;
  const yMax = maxValue + valueRange * 0.08;
  const yMin = minValue - valueRange * 0.08;
  const xSpan = Math.max(totalPoints - 1, 1);
  const gridLabels = buildGridLabels(yMin, yMax, 5);
  const forecastDividerIndex = Math.max(historical.length - 1, 0);
  const forecastDividerX = scaleLineX(forecastDividerIndex, xSpan);
  const startDate = historical[0]?.date ?? null;
  const splitDate = historical.at(-1)?.date ?? null;
  const endDate = forecast.ensemble_forecast.at(-1)?.date ?? splitDate;

  const weightRows: BarDatum[] = forecast.ensemble_components.map((component) => ({
    label: component.display_name,
    note: formatCurrency(component.terminal_price),
    value: component.weight,
    display: formatPercentValue(component.weight * 100, 1, "%"),
    color: pickSeriesColor(component.model_id),
  }));

  const benchmarkRows: BarDatum[] = forecast.benchmark_candidates.slice(0, 5).map((candidate) => ({
    label: candidate.symbol,
    note: candidate.name,
    value: Math.max(candidate.correlation, 0),
    display: candidate.correlation.toFixed(4),
    color: "#9eb7ff",
  }));

  return (
    <section className="scene-chart">
      <div className="scene-heading">
        <span className="scene-kicker">Forecast Visuals</span>
        <h2>Forecast comparison, model weights, and benchmark ranking.</h2>
      </div>

      <div className="chart-dashboard">
        <article className="chart-panel chart-panel-large">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Price Forecast Timeline</h3>
              <p className="panel-copy">
                Historical prices and forecast paths shown on a single time axis.
              </p>
            </div>
            <span className="panel-meta">{forecast.horizon_days} day forecast horizon</span>
          </div>

          <svg
            aria-label="Price forecast timeline"
            className="chart-svg"
            role="img"
            viewBox={`0 0 ${LINE_CHART_WIDTH} ${LINE_CHART_HEIGHT}`}
          >
            <rect
              className="chart-surface"
              height={LINE_CHART_HEIGHT - LINE_CHART_TOP - LINE_CHART_BOTTOM}
              rx="18"
              width={LINE_CHART_WIDTH - LINE_CHART_LEFT - LINE_CHART_RIGHT}
              x={LINE_CHART_LEFT}
              y={LINE_CHART_TOP}
            />

            {gridLabels.map((label) => {
              const y = scaleLineY(label, yMin, yMax);
              return (
                <g key={label}>
                  <line
                    className="chart-grid-line"
                    x1={LINE_CHART_LEFT}
                    x2={LINE_CHART_WIDTH - LINE_CHART_RIGHT}
                    y1={y}
                    y2={y}
                  />
                  <text className="chart-axis-text" textAnchor="end" x={LINE_CHART_LEFT - 12} y={y + 5}>
                    {label.toFixed(2)}
                  </text>
                </g>
              );
            })}

            <line
              className="chart-divider-line"
              x1={forecastDividerX}
              x2={forecastDividerX}
              y1={LINE_CHART_TOP}
              y2={LINE_CHART_HEIGHT - LINE_CHART_BOTTOM}
            />

            <text className="chart-phase-text" textAnchor="middle" x={forecastDividerX} y={LINE_CHART_TOP - 8}>
              Forecast Start
            </text>

            {series.map((item) => (
              <path
                key={item.label}
                d={buildLinePath(item.values, item.startIndex, xSpan, yMin, yMax)}
                fill="none"
                stroke={item.color}
                strokeDasharray={item.dashed ? "10 10" : undefined}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={item.strokeWidth ?? 2}
              />
            ))}

            {renderXAxisLabel(startDate, LINE_CHART_LEFT, LINE_CHART_HEIGHT - 14, "start")}
            {renderXAxisLabel(splitDate, forecastDividerX, LINE_CHART_HEIGHT - 14, "middle")}
            {renderXAxisLabel(endDate, LINE_CHART_WIDTH - LINE_CHART_RIGHT, LINE_CHART_HEIGHT - 14, "end")}
          </svg>

          <div className="chart-legend">
            {series.map((item) => (
              <div className="legend-item" key={item.label}>
                <span className="legend-swatch" style={{ backgroundColor: item.color }} />
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </article>

        <BarPanel
          rows={weightRows}
          description="Relative contribution of each model in the combined forecast."
          title="Model Weights"
        />

        <BarPanel
          rows={benchmarkRows}
          description="Top benchmark candidates ranked by correlation score."
          title="Benchmark Correlation"
        />
      </div>
    </section>
  );
}

function BarPanel({
  title,
  description,
  rows,
}: {
  title: string;
  description: string;
  rows: BarDatum[];
}) {
  const maxValue = Math.max(...rows.map((row) => row.value), 0.0001);

  return (
    <article className="chart-panel">
      <div className="panel-header">
        <div>
          <h3 className="panel-title">{title}</h3>
          <p className="panel-copy">{description}</p>
        </div>
      </div>

      <div className="metric-bar-list">
        {rows.map((row) => {
          const width = `${Math.max((row.value / maxValue) * 100, 6)}%`;

          return (
            <div className="metric-bar-row" key={`${title}-${row.label}`}>
              <div className="metric-bar-header">
                <span className="metric-bar-label">{row.label}</span>
                <span className="metric-bar-value">{row.display}</span>
              </div>
              {row.note ? <span className="metric-bar-note">{row.note}</span> : null}
              <div className="metric-bar-track">
                <span className="metric-bar-fill" style={{ backgroundColor: row.color, width }} />
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}

function renderXAxisLabel(date: string | null, x: number, y: number, align: "start" | "middle" | "end") {
  if (!date) {
    return null;
  }

  const textAnchor = align === "middle" ? "middle" : align === "end" ? "end" : "start";

  return (
    <text className="chart-axis-text" textAnchor={textAnchor} x={x} y={y}>
      {formatShortDate(date)}
    </text>
  );
}

function buildLinePath(
  values: number[],
  startIndex: number,
  xSpan: number,
  yMin: number,
  yMax: number,
): string {
  return values
    .map((value, index) => {
      const x = scaleLineX(startIndex + index, xSpan);
      const y = scaleLineY(value, yMin, yMax);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function scaleLineX(index: number, xSpan: number): number {
  const usableWidth = LINE_CHART_WIDTH - LINE_CHART_LEFT - LINE_CHART_RIGHT;
  return LINE_CHART_LEFT + (index / Math.max(xSpan, 1)) * usableWidth;
}

function scaleLineY(value: number, minValue: number, maxValue: number): number {
  const usableHeight = LINE_CHART_HEIGHT - LINE_CHART_TOP - LINE_CHART_BOTTOM;
  const ratio = (value - minValue) / Math.max(maxValue - minValue, 1);
  return LINE_CHART_HEIGHT - LINE_CHART_BOTTOM - ratio * usableHeight;
}

function buildGridLabels(minValue: number, maxValue: number, count: number): number[] {
  return Array.from({ length: count }, (_, index) => {
    const ratio = index / Math.max(count - 1, 1);
    return minValue + (maxValue - minValue) * ratio;
  });
}

function pickSeriesColor(modelId: string): string {
  if (modelId === "market_influence") {
    return "#c9d1ff";
  }

  if (modelId === "arima") {
    return "#f4c68d";
  }

  if (modelId === "xgboost") {
    return "#8fe6d8";
  }

  return "#ffffff";
}

function formatShortDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatCurrency(value: number | null): string {
  if (value == null) {
    return "Unavailable";
  }

  return `${value.toFixed(2)} USD`;
}

function formatPercentValue(value: number, digits: number, suffix: string): string {
  return `${value.toFixed(digits)}${suffix}`;
}
