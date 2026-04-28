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
            Market Forecast Workspace
          </Link>

          <div className="nav-links landing-links">
            <Link href="/">Home</Link>
            <Link href="/dashboard">Dashboard</Link>
          </div>
        </header>

        <div className="forecast-hero-layout landing-reveal">
          <Image
            alt="Forecast architecture diagram"
            className="forecast-diagram-image"
            height={941}
            priority
            src="/images/forecast-architecture-reference.png"
            width={1672}
          />

          <aside className="forecast-side-panel">
            <div className="forecast-side-copy">
              <h1>Start forecasting.</h1>
              <p>
                Combine market influence, statistical signals, machine learning, and language
                interpretation in one flow.
              </p>
            </div>

            <div className="forecast-link-row">
              <Link className="forecast-dashboard-link" href="/dashboard">
                Open dashboard
                <span aria-hidden="true" className="forecast-dashboard-link-arrow" />
              </Link>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
