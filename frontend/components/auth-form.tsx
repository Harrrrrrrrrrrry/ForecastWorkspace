"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { signIn, signUp } from "@/lib/api";
import { storeAuthSession } from "@/lib/auth";


type AuthFormProps = {
  mode: "sign-in" | "sign-up";
};

export function AuthForm({ mode }: AuthFormProps) {
  const isSignUp = mode === "sign-up";
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [accessReason, setAccessReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      if (isSignUp) {
        await signUp({
          email,
          password,
          fullName,
          accessReason,
        });
        const response = await signIn({ email, password });
        storeAuthSession(response.token, response.user);
        router.push("/");
        router.refresh();
      } else {
        const response = await signIn({ email, password });
        storeAuthSession(response.token, response.user);
        router.push("/");
        router.refresh();
      }
    } catch (submitError) {
      const message =
        submitError instanceof Error ? submitError.message : "The request could not be completed.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-header">
          <span className="scene-kicker">Access Control</span>
          <h1>{isSignUp ? "Create your account" : "Sign in to your account"}</h1>
          <p>
            {isSignUp
              ? "Create an account to start using forecasts and explanations immediately."
              : "Sign in to run forecasts and use GPT-backed explanation endpoints."}
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {isSignUp ? (
            <label className="field-block">
              <span className="field-label">Full name</span>
              <input
                className="parameter-input"
                maxLength={120}
                name="fullName"
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Jane Doe"
                type="text"
                value={fullName}
              />
            </label>
          ) : null}

          <label className="field-block">
            <span className="field-label">Email</span>
            <input
              autoComplete="email"
              className="parameter-input"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="jane@example.com"
              type="email"
              value={email}
            />
          </label>

          <label className="field-block">
            <span className="field-label">Password</span>
            <input
              autoComplete={isSignUp ? "new-password" : "current-password"}
              className="parameter-input"
              minLength={8}
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 8 characters"
              type="password"
              value={password}
            />
          </label>

          {isSignUp ? (
            <label className="field-block">
              <span className="field-label">How will you use it?</span>
              <textarea
                className="parameter-input auth-textarea"
                maxLength={500}
                name="accessReason"
                onChange={(event) => setAccessReason(event.target.value)}
                placeholder="How will you use the forecasting and explanation features?"
                rows={4}
                value={accessReason}
              />
            </label>
          ) : null}

          {error ? <div className="auth-status auth-status-error">{error}</div> : null}
          {success ? <div className="auth-status auth-status-success">{success}</div> : null}

          <button className="ghost-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Submitting..." : isSignUp ? "Sign Up" : "Sign In"}
          </button>
        </form>

        <div className="auth-footer">
          <Link href="/">Back to dashboard</Link>
          <Link href={isSignUp ? "/sign-in" : "/sign-up"}>
            {isSignUp ? "Already have an account? Sign in" : "Need an account? Sign up"}
          </Link>
        </div>
      </section>
    </main>
  );
}
