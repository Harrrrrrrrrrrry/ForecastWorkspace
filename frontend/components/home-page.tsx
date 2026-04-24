"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  AuthUser,
  StockHistoryPoint,
  StockHistoryResponse,
  fetchCurrentUser,
  fetchStockHistory,
} from "@/lib/api";
import {
  AUTH_STATE_EVENT,
  clearStoredAuthSession,
  getStoredAuthToken,
  updateStoredAuthUser,
} from "@/lib/auth";

const DEFAULT_TICKER = "AAPL";
const LOOKBACK_DAYS = 90;
const PRESET_TICKERS = ["AAPL", "MSFT", "NVDA", "SPY"];
const FEATURE_TABS = [
  {
    id: "forecast",
    title: "Forecast boards",
    eyebrow: "Model workspace",
    description:
      "Generate a dedicated board for each ticker with ensemble output, benchmarks, diagnostics, and warning states in one place.",
    points: [
      "Batch ticker submission with per-stock cards",
      "Forecast horizon and analysis window controls",
      "Benchmark correlation and model diagnostics",
    ],
  },
  {
    id: "explain",
    title: "Plain-language explanations",
    eyebrow: "GPT layer",
    description:
      "Once a forecast loads, the explanation panel translates the model signal, reliability profile, and limitations into readable language.",
    points: [
      "Narrative signal summary per forecast",
      "Reliability and limitation breakdowns",
      "Fast follow-up context for non-quant users",
    ],
  },
  {
    id: "access",
    title: "Access-aware entry flow",
    eyebrow: "Account system",
    description:
      "The frontend already supports sign-in, sign-up, session storage, and authenticated calls, so the landing page can route users cleanly by state.",
    points: [
      "Local session persistence in the browser",
      "Approved and pending account states",
      "Clear split between public preview and protected tools",
    ],
  },
] as const;

const MODEL_STACK = [
  {
    name: "Market Influence",
    keywords: ["benchmark link", "beta projection", "core path"],
  },
  {
    name: "Fourier",
    keywords: ["cyclical signal", "price rhythm", "pattern fit"],
  },
  {
    name: "ARIMA",
    keywords: ["time series", "local fit", "trend memory"],
  },
  {
    name: "XGBoost",
    keywords: ["lag features", "return learning", "ml curve"],
  },
  {
    name: "GPT-5.4-mini",
    keywords: ["explanation layer", "plain language", "not prediction"],
  },
] as const;

type FeatureTabId = (typeof FEATURE_TABS)[number]["id"];

function formatCurrency(value: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function getLatestPoint(history: StockHistoryResponse | null): StockHistoryPoint | null {
  return history?.points.at(-1) ?? null;
}

function getRange(history: StockHistoryResponse | null): { low: number | null; high: number | null } {
  if (!history || history.points.length === 0) {
    return { low: null, high: null };
  }

  let low = history.points[0].close;
  let high = history.points[0].close;

  for (const point of history.points) {
    low = Math.min(low, point.close);
    high = Math.max(high, point.close);
  }

  return { low, high };
}

function getReturnPercent(history: StockHistoryResponse | null): number | null {
  if (!history || history.points.length < 2) {
    return null;
  }

  const first = history.points[0].close;
  const last = history.points.at(-1)?.close ?? null;

  if (!last || first === 0) {
    return null;
  }

  return ((last - first) / first) * 100;
}

function buildSparklinePath(points: StockHistoryPoint[]): string {
  if (points.length === 0) {
    return "";
  }

  const width = 320;
  const height = 120;
  const closes = points.map((point) => point.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;

  return points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - ((point.close - min) / range) * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export function HomePageShell() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [history, setHistory] = useState<StockHistoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<FeatureTabId>("forecast");

  useEffect(() => {
    let isActive = true;

    async function hydrateAuthState() {
      const token = getStoredAuthToken();

      if (!token) {
        if (isActive) {
          setCurrentUser(null);
        }
        return;
      }

      try {
        const user = await fetchCurrentUser(token);
        if (!isActive) {
          return;
        }

        updateStoredAuthUser(user);
        setCurrentUser(user);
      } catch {
        if (!isActive) {
          return;
        }

        clearStoredAuthSession();
        setCurrentUser(null);
      }
    }

    void hydrateAuthState();

    function handleAuthStateChange() {
      void hydrateAuthState();
    }

    window.addEventListener(AUTH_STATE_EVENT, handleAuthStateChange);

    return () => {
      isActive = false;
      window.removeEventListener(AUTH_STATE_EVENT, handleAuthStateChange);
    };
  }, []);

  useEffect(() => {
    void runLookup(DEFAULT_TICKER);
  }, []);

  async function runLookup(nextTicker: string) {
    const normalizedTicker = nextTicker.trim().toUpperCase();

    if (!normalizedTicker) {
      setError("Enter a stock ticker to preview recent market behavior.");
      setHistory(null);
      return;
    }

    setTicker(normalizedTicker);
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchStockHistory(normalizedTicker, LOOKBACK_DAYS);
      setHistory(response);
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "Failed to load market preview.";
      setError(message);
      setHistory(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runLookup(ticker);
  }

  function handleSignOut() {
    clearStoredAuthSession();
    setCurrentUser(null);
  }

  const latestPoint = getLatestPoint(history);
  const range = getRange(history);
  const returnPercent = getReturnPercent(history);
  const activeFeature = FEATURE_TABS.find((feature) => feature.id === activeTab) ?? FEATURE_TABS[0];
  const sparklinePath = buildSparklinePath(history?.points ?? []);

  return (
    <main className="landing-shell">
      <section className="scene landing-hero">
        <div className="scene-overlay landing-overlay" />
        <header className="mission-nav landing-nav">
          <Link className="nav-mark landing-brand" href="/">
            Market Forecast Workspace
          </Link>

          <div className="nav-links landing-links">
            <Link href="/">Home</Link>
            <Link href="/dashboard">Dashboard</Link>
            {currentUser ? (
              <>
                <span className="nav-user">
                  {currentUser.full_name?.trim() || currentUser.email}
                  <span className="nav-user-role">{currentUser.role}</span>
                </span>
                <button className="nav-link-button" onClick={handleSignOut} type="button">
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link href="/sign-in">Sign In</Link>
                <Link href="/sign-up">Sign Up</Link>
              </>
            )}
          </div>
        </header>

        <div className="landing-image-stage landing-reveal">
          <div className="landing-image-frame">
            <Image
              alt="Soft abstract homepage hero artwork"
              className="landing-hero-image"
              height={941}
              priority
              src="/images/home-hero-soft.png"
              width={1672}
            />
            <div className="landing-image-overlay">
              <div className="landing-image-copy">
                <h2>Start Forecasting.</h2>
              </div>
              <Link className="landing-image-button" href="/dashboard">
                Open Dashboard
                <span aria-hidden="true" className="landing-image-button-arrow" />
              </Link>
            </div>
          </div>
        </div>
      </section>
      <section className="landing-section landing-section-compact">
        <div className="landing-models-panel landing-models-panel-standalone landing-reveal">
          <div className="landing-section-head landing-models-head">
            <h2 className="landing-section-title">Models behind the forecast</h2>
            <p>
              The platform predicts prices with mathematical and machine-learning models, then uses a
              separate explanation layer to translate the result into readable language.
            </p>
          </div>

          <div className="landing-model-list">
            {MODEL_STACK.map((model) => (
              <article className="landing-model-card" key={model.name}>
                <h3>{model.name}</h3>
                <span aria-hidden="true" className="landing-model-divider" />
                <p>{model.keywords.join(" / ")}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-section-compact">
        <div className="landing-auth-cta landing-reveal">
          <Link className="landing-auth-button landing-auth-button-secondary" href="/sign-in">
            Sign In
          </Link>
          <Link className="landing-auth-button landing-auth-button-primary" href="/sign-up">
            Sign Up
          </Link>
        </div>
      </section>
    </main>
  );
}
