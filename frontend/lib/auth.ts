"use client";

import { AuthUser } from "@/lib/api";


export const AUTH_TOKEN_STORAGE_KEY = "market-influence-auth-token";
export const AUTH_USER_STORAGE_KEY = "market-influence-auth-user";
export const AUTH_STATE_EVENT = "market-influence-auth-state-change";

export function getStoredAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

export function getStoredAuthUser(): AuthUser | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawUser = window.localStorage.getItem(AUTH_USER_STORAGE_KEY);
  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as AuthUser;
  } catch {
    clearStoredAuthSession();
    return null;
  }
}

export function storeAuthSession(token: string, user: AuthUser): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  window.localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event(AUTH_STATE_EVENT));
}

export function updateStoredAuthUser(user: AuthUser): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearStoredAuthSession(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);
  window.dispatchEvent(new Event(AUTH_STATE_EVENT));
}
