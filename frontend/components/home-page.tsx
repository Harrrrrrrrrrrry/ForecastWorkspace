"use client";

import Image from "next/image";
import Link from "next/link";

export function HomePageShell() {
  return (
    <main className="landing-shell forecast-home">
      <section className="scene landing-hero forecast-home-hero">
        <div className="scene-overlay landing-overlay" />

        <header className="mission-nav landing-nav">
          <Link className="nav-mark landing-brand" href="/">
            <Image
              alt=""
              aria-hidden="true"
              className="landing-brand-logo"
              height={32}
              src="/images/no_background_logo.svg"
              width={32}
            />
            <span>PrismForecast</span>
          </Link>

          <div className="nav-links landing-links">
            <Link href="/">Home</Link>
            <Link href="/dashboard">Dashboard</Link>
          </div>
        </header>

        <div className="forecast-hero-layout landing-reveal">
          <div className="forecast-side-panel">
            <div className="forecast-side-copy">
              <h1>Start forecasting.</h1>
              <p>Five models, one clear forecast.</p>
            </div>

            <div className="forecast-link-row">
              <Link className="forecast-dashboard-link" href="/dashboard">
                Get started
                <span aria-hidden="true" className="forecast-dashboard-link-arrow" />
              </Link>
            </div>
          </div>

          <Image
            alt="Forecast architecture diagram"
            className="forecast-diagram-image"
            height={941}
            priority
            src="/images/forecast-architecture-reference.png"
            width={1672}
          />
        </div>
      </section>

      <section className="how-it-works-section">
        <div className="how-it-works-head">
          <h2>How it works ?</h2>
          <p>
            PrismForecast combines market relationships, statistical models, and reliability
            checks to turn historical price data into a clearer forecast.
          </p>
        </div>

        <div className="how-it-works-grid">
          <article className="how-it-works-card">
            <span className="how-it-works-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img">
                <path d="M5 7c0-1.7 3.1-3 7-3s7 1.3 7 3-3.1 3-7 3-7-1.3-7-3Z" />
                <path d="M5 7v5c0 1.7 3.1 3 7 3s7-1.3 7-3V7" />
                <path d="M5 12v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5" />
              </svg>
            </span>
            <h3>Find market context</h3>
            <p>
              The system reads historical prices and compares each stock with broad market
              benchmarks to find the strongest relationship.
            </p>
          </article>

          <article className="how-it-works-card">
            <span className="how-it-works-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img">
                <path d="M4 18h16" />
                <path d="M5 15l4-4 3 3 6-7" />
                <path d="M15 7h3v3" />
              </svg>
            </span>
            <h3>Blend model signals</h3>
            <p>
              Market Influence, ARIMA, and XGBoost each produce a signal, then the app blends them
              into one forecast with reliability checks.
            </p>
          </article>

          <article className="how-it-works-card">
            <span className="how-it-works-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img">
                <path d="M5 6.5h14v9H9l-4 3v-12Z" />
                <path d="M9 10h6" />
                <path d="M9 13h4" />
              </svg>
            </span>
            <h3>Explain the result</h3>
            <p>
              The AI layer explains the structured forecast in plain language. It does not invent
              prices or replace the quantitative model.
            </p>
          </article>
        </div>

        <div className="model-source-grid">
          <article className="model-source-card model-source-card-openai">
            <div className="model-source-content">
              <span>GPT 5.4 integrated</span>
            </div>
          </article>

          <article className="model-source-card model-source-card-yahoo">
            <div className="model-source-content">
              <span>Yahoo Finance</span>
            </div>
          </article>

          <article className="model-source-card model-source-card-more-model">
            <div className="model-source-content">
              <span>Native AI-generated chart data is currently under development.</span>
            </div>
          </article>
        </div>
      </section>
    </main>
  );
}
