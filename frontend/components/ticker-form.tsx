type TickerFormProps = {
  defaultTicker?: string;
};

export function TickerForm({ defaultTicker = "AAPL" }: TickerFormProps) {
  return (
    <form className="ticker-form">
      <div>
        <h2>Forecast Input</h2>
        <p>
          Enter a ticker to run the Market Influence Model. Phase 2 will connect this form to
          the backend historical data pipeline.
        </p>
      </div>

      <div className="ticker-row">
        <input
          aria-label="Stock ticker"
          defaultValue={defaultTicker}
          name="ticker"
          placeholder="Enter a ticker like AAPL"
        />
        <button type="button">Run Forecast</button>
      </div>

      <div className="pill-row">
        <div className="pill">
          <span className="pill-label">Model Core</span>
          <span className="pill-value">Quantitative only</span>
        </div>
        <div className="pill">
          <span className="pill-label">Forecast Horizon</span>
          <span className="pill-value">2 weeks</span>
        </div>
        <div className="pill">
          <span className="pill-label">Explanation Layer</span>
          <span className="pill-value">LLM after modeling</span>
        </div>
      </div>
    </form>
  );
}

