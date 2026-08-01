import type { Metadata } from "next";
import { ReviewLogin } from "@/components/review-login";

export const metadata: Metadata = {
  title: "Reviewer login",
  description: "Private NULSPEC human-review workspace.",
  robots: { index: false, follow: false, noarchive: true },
};

export default function ReviewLoginPage() {
  return <ReviewLogin />;
}
