"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AuthUser, fetchCurrentUser } from "@/lib/api";
import {
  AUTH_STATE_EVENT,
  clearStoredAuthSession,
  getStoredAuthToken,
  updateStoredAuthUser,
} from "@/lib/auth";

export function HomePageShell() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

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

  function handleSignOut() {
    clearStoredAuthSession();
    setCurrentUser(null);
  }

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
              {!currentUser ? (
                <>
                  <Link className="forecast-secondary-link" href="/sign-in">
                    Sign in
                    <span aria-hidden="true" className="forecast-dashboard-link-arrow" />
                  </Link>
                  <Link className="forecast-secondary-link" href="/sign-up">
                    Sign up
                    <span aria-hidden="true" className="forecast-dashboard-link-arrow" />
                  </Link>
                </>
              ) : null}
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
