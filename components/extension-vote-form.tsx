"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import type { ExtensionCallToAction } from "@/lib/study";

type SubmissionState =
  | { phase: "idle" }
  | { phase: "sending" }
  | { phase: "success"; reference: string; duplicate: boolean }
  | { phase: "error"; message: string };

const PRODUCTION_ENDPOINT = "https://nulspec.com/api/extension-votes";

function extensionVoteEndpoint() {
  if (
    typeof window !== "undefined" &&
    window.location.hostname.endsWith(".chatgpt.site")
  ) {
    return PRODUCTION_ENDPOINT;
  }
  return "/api/extension-votes";
}

export function ExtensionVoteForm({
  callToAction,
  studyId,
}: {
  callToAction: ExtensionCallToAction;
  studyId: string;
}) {
  const [submission, setSubmission] = useState<SubmissionState>({ phase: "idle" });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 12_000);
    setSubmission({ phase: "sending" });

    try {
      const response = await fetch(extensionVoteEndpoint(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          study_id: studyId,
          option_id: formData.get("extension-option"),
          company: formData.get("company"),
        }),
        signal: controller.signal,
      });
      const payload = (await response.json().catch(() => null)) as {
        duplicate?: boolean;
        reference?: string;
      } | null;

      if (!response.ok) {
        if (response.status === 400 || response.status === 404 || response.status === 422) {
          throw new Error("That extension option is no longer available. Refresh and try again.");
        }
        if (response.status === 429) {
          throw new Error("A vote from this network was recently recorded. Try again later.");
        }
        throw new Error("The vote relay is unavailable. Try again soon.");
      }

      form.reset();
      setSubmission({
        phase: "success",
        reference: payload?.reference ?? "received",
        duplicate: payload?.duplicate ?? false,
      });
    } catch (error) {
      setSubmission({
        phase: "error",
        message:
          error instanceof Error && error.name !== "AbortError"
            ? error.message
            : "The vote relay timed out. Try again soon.",
      });
    } finally {
      window.clearTimeout(timeout);
    }
  }

  return (
    <form className="extension-vote" onSubmit={handleSubmit}>
      <fieldset>
        <legend>{callToAction.prompt}</legend>
        <div className="extension-vote__options">
          {[...callToAction.options]
            .sort((left, right) => left.priority - right.priority)
            .map((option) => (
              <label className="extension-vote__option" key={option.id}>
                <input
                  name="extension-option"
                  required
                  type="radio"
                  value={option.id}
                />
                <span className="extension-vote__rank">
                  {String(option.priority).padStart(2, "0")}
                </span>
                <span>
                  <strong>{option.label}</strong>
                  <small>{option.summary}</small>
                  <code>{option.role.replaceAll("_", " ")}</code>
                </span>
              </label>
            ))}
        </div>
      </fieldset>

      <div className="extension-vote__trap" aria-hidden="true">
        <label htmlFor={`extension-company-${studyId}`}>Company</label>
        <input
          autoComplete="off"
          id={`extension-company-${studyId}`}
          name="company"
          tabIndex={-1}
          type="text"
        />
      </div>

      <div className="extension-vote__action">
        <button
          className="button button--primary"
          disabled={submission.phase === "sending"}
          type="submit"
        >
          {submission.phase === "sending" ? "Relaying…" : callToAction.button_label}
        </button>
        <p
          className={`extension-vote__status extension-vote__status--${submission.phase}`}
          role="status"
        >
          {submission.phase === "success" &&
            (submission.duplicate
              ? `Already recorded. Reference ${submission.reference}.`
              : `Vote recorded. Reference ${submission.reference}.`)}
          {submission.phase === "error" && submission.message}
          {(submission.phase === "idle" || submission.phase === "sending") &&
            "No account or email. Your network address is used transiently for abuse prevention and is not sent to Discord."}
        </p>
      </div>
    </form>
  );
}
