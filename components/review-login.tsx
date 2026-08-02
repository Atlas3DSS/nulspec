"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { NulspecMark } from "@/components/nulspec-mark";

type LoginState = "checking" | "ready" | "submitting" | "unavailable";

const messages: Record<string, string> = {
  invalid_credentials: "The username or password was not accepted.",
  rate_limited: "Too many attempts were received. Wait briefly, then try again.",
  forbidden_origin: "This login request did not originate from the review site.",
  review_unavailable: "The private review service is not available right now.",
};

export function ReviewLogin() {
  const [state, setState] = useState<LoginState>("checking");
  const [message, setMessage] = useState("Checking for an existing session…");

  useEffect(() => {
    let current = true;
    async function checkSession() {
      try {
        const response = await fetch("/api/review/session", {
          cache: "no-store",
          credentials: "same-origin",
        });
        if (!current) return;
        if (response.ok) {
          window.location.replace("/review");
          return;
        }
        if (response.status === 503) {
          setState("unavailable");
          setMessage(messages.review_unavailable);
          return;
        }
        setState("ready");
        setMessage("");
      } catch {
        if (!current) return;
        setState("unavailable");
        setMessage("The private review service could not be reached.");
      }
    }
    void checkSession();
    return () => {
      current = false;
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setState("submitting");
    setMessage("Verifying credentials…");
    try {
      const response = await fetch("/api/review/login", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: data.get("username"),
          password: data.get("password"),
        }),
      });
      const payload = (await response.json().catch(() => ({}))) as {
        error?: string;
      };
      if (response.ok) {
        setMessage("Access confirmed. Opening the review inbox…");
        window.location.replace("/review");
        return;
      }
      setState(response.status === 503 ? "unavailable" : "ready");
      setMessage(
        (payload.error && messages[payload.error]) ||
          "The login request could not be completed.",
      );
    } catch {
      setState("ready");
      setMessage("The private review service could not be reached.");
    } finally {
      form.querySelector<HTMLInputElement>('input[name="password"]')?.select();
    }
  }

  const disabled = state !== "ready";

  return (
    <div className="review-auth-layout">
      <header className="review-auth-header">
        <div className="review-auth-header__inner">
          <Link className="wordmark" href="/" aria-label="NULSPEC home">
            <NulspecMark className="wordmark__mark" />
            <span>NUL</span>
            <span className="wordmark__accent">SPEC</span>
          </Link>
          <span>Private review workspace</span>
        </div>
      </header>

      <main className="review-auth-main" id="main-content">
        <section className="review-login-card" aria-labelledby="review-login-title">
          <p className="section-kicker">Human release gate</p>
          <h1 id="review-login-title">Reviewer login</h1>
          <p className="review-login-card__intro">
            Review publication blocks, inspect bound evidence, and approve exact
            author-email drafts from one private inbox.
          </p>

          <form className="review-login-form" onSubmit={submit}>
            <label htmlFor="review-username">Username</label>
            <input
              autoCapitalize="none"
              autoComplete="username"
              autoCorrect="off"
              disabled={disabled}
              id="review-username"
              maxLength={32}
              name="username"
              required
              spellCheck={false}
              type="text"
            />
            <label htmlFor="review-password">Password</label>
            <input
              autoComplete="current-password"
              disabled={disabled}
              id="review-password"
              maxLength={1024}
              name="password"
              required
              type="password"
            />
            <button
              className="button button--primary review-login-form__submit"
              disabled={disabled}
              type="submit"
            >
              {state === "submitting" ? "Verifying…" : "Open review inbox"}
            </button>
          </form>

          <p
            className={`review-auth-status${message ? " has-message" : ""}`}
            role="status"
          >
            {message}
          </p>
          <p className="review-login-card__provisioning">
            Access is provisioned manually by the lab operator. This surface does
            not create, recover, or discover accounts.
          </p>
        </section>
      </main>
    </div>
  );
}
