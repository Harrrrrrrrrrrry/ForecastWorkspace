import { LegalPage } from "@/components/legal-page";

export default function TermsOfUsePage() {
  return (
    <LegalPage title="Terms of Use" updated="April 30, 2026">
      <p>
        PrismForecast is provided as an academic research and exploratory market-analysis project.
        By using it, you agree to use the site only for lawful, educational, and informational
        purposes.
      </p>
      <p>
        You may enter public stock ticker symbols and forecast settings to generate charts,
        diagnostics, and written explanations. You may not attempt to overload the service, bypass
        rate limits, interfere with APIs, scrape in a way that harms availability, or submit content
        that violates applicable law.
      </p>
      <p>
        Forecast results depend on third-party market data, model assumptions, and active
        development code. The site is provided as-is, without warranties that results will be
        accurate, complete, available, or suitable for any particular use.
      </p>
      <p>
        The project may change, break, pause, or remove features as the research work evolves. You
        are responsible for how you interpret and use any output from the site.
      </p>
    </LegalPage>
  );
}
