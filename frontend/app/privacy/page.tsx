import { LegalPage } from "@/components/legal-page";

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy" updated="April 30, 2026">
      <p>
        PrismForecast is an academic stock-forecasting project. The app does not currently provide
        user accounts, subscriptions, checkout, newsletters, or profile pages.
      </p>
      <p>
        When you use the dashboard, the frontend sends the ticker symbols, forecast horizon,
        analysis-window length, and optional analysis end date needed to generate a forecast. The
        backend may also receive standard technical request information, such as IP address,
        browser details, timestamps, and error logs, through hosting or API infrastructure.
      </p>
      <p>
        Historical market data is requested from Yahoo Finance through the backend. If you generate
        an explanation, the structured forecast result is sent to the explanation service so it can
        produce a plain-language summary. Do not enter personal, confidential, or sensitive
        information into ticker or forecast fields.
      </p>
      <p>
        PrismForecast does not sell personal information. Any collected technical information is
        used to operate, debug, secure, and improve the project.
      </p>
    </LegalPage>
  );
}
