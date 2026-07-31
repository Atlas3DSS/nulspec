"use client";

import { useState } from "react";
import type { FormEvent } from "react";

type SubmissionState =
  | { phase: "idle" }
  | { phase: "sending" }
  | { phase: "success"; reference: string }
  | { phase: "error"; message: string };

const PRODUCTION_ENDPOINT = "https://nulspec.com/api/nominations";

function nominationEndpoint() {
  if (
    typeof window !== "undefined" &&
    window.location.hostname.endsWith(".chatgpt.site")
  ) {
    return PRODUCTION_ENDPOINT;
  }

  return "/api/nominations";
}

export function NominationForm() {
  const [submission, setSubmission] = useState<SubmissionState>({
    phase: "idle",
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 12_000);

    setSubmission({ phase: "sending" });

    try {
      const response = await fetch(nominationEndpoint(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: formData.get("email"),
          paper: formData.get("paper"),
          company: formData.get("company"),
        }),
        signal: controller.signal,
      });
      const payload = (await response.json().catch(() => null)) as {
        reference?: string;
      } | null;

      if (!response.ok) {
        if (response.status === 400 || response.status === 422) {
          throw new Error(
            "Use a valid email address and a complete arxiv.org abstract or PDF URL.",
          );
        }
        if (response.status === 429) {
          throw new Error(
            "The submission limit for this email address or IP address has been reached. Try again later.",
          );
        }
        throw new Error("Submission failed. Try again.");
      }

      form.reset();
      setSubmission({
        phase: "success",
        reference: payload?.reference ?? "received",
      });
    } catch (error) {
      setSubmission({
        phase: "error",
        message:
          error instanceof Error && error.name !== "AbortError"
            ? error.message
            : "The submission timed out. Try again.",
      });
    } finally {
      window.clearTimeout(timeout);
    }
  }

  return (
    <form className="nomination-form" onSubmit={handleSubmit}>
      <div className="nomination-form__topline">
        <span>Paper nomination</span>
        <span>ARXIV URL REQUIRED</span>
      </div>

      <div className="nomination-form__field">
        <label htmlFor="nomination-email">Your email</label>
        <input
          autoComplete="email"
          id="nomination-email"
          inputMode="email"
          maxLength={254}
          name="email"
          placeholder="you@example.com"
          required
          type="email"
        />
        <p>
          If we complete a replication of this paper, we may send one email
          with the result. We do not send marketing email.
        </p>
      </div>

      <div className="nomination-form__field">
        <label htmlFor="nomination-paper">Paper</label>
        <input
          autoComplete="url"
          id="nomination-paper"
          inputMode="url"
          maxLength={300}
          name="paper"
          pattern="https://(www\.)?arxiv\.org/(abs|pdf)/.+"
          placeholder="https://arxiv.org/abs/2607.25091"
          required
          type="url"
        />
        <p>Paste a complete arxiv.org abstract or PDF URL.</p>
      </div>

      <div className="nomination-form__trap" aria-hidden="true">
        <label htmlFor="nomination-company">Company</label>
        <input
          autoComplete="off"
          id="nomination-company"
          name="company"
          tabIndex={-1}
          type="text"
        />
      </div>

      <button
        className="button button--primary nomination-form__submit"
        disabled={submission.phase === "sending"}
        type="submit"
      >
        {submission.phase === "sending" ? "Submitting…" : "Submit nomination"}
      </button>

      <p
        className={`nomination-form__status nomination-form__status--${submission.phase}`}
        role="status"
      >
        {submission.phase === "success" &&
          `Nomination received. Reference: ${submission.reference}.`}
        {submission.phase === "error" && submission.message}
        {(submission.phase === "idle" || submission.phase === "sending") &&
          "Submission does not guarantee that NULSPEC will replicate the paper or respond."}
      </p>
    </form>
  );
}
