import { LegalPage } from "@/components/legal-page";

export default function FinancialDisclaimerPage() {
  return (
    <LegalPage title="Financial Disclaimer" updated="April 30, 2026">
      <p>
        PrismForecast is for academic research, education, and exploratory analysis only. It is not
        an investment adviser, broker-dealer, trading platform, or portfolio-management service.
      </p>
      <p>
        The forecasts, charts, benchmark comparisons, diagnostics, and GPT-generated explanations
        are not financial, investment, legal, tax, or trading advice. They are not recommendations
        to buy, sell, hold, short, or otherwise trade any stock or security.
      </p>
      <p>
        Outputs are based on historical data, third-party data availability, statistical models,
        machine-learning models, and reliability checks. Market conditions can change quickly, data
        can be delayed or incomplete, and model projections can be wrong. Past performance and model
        forecasts do not guarantee future results.
      </p>
      <p>
        You are solely responsible for your financial decisions. Consult a qualified professional
        before making investment decisions or relying on any market analysis.
      </p>
    </LegalPage>
  );
}
