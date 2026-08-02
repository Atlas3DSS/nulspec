import type { Metadata } from "next";
import { ReviewDashboard } from "@/components/review-dashboard";

export const metadata: Metadata = {
  title: "Human review inbox",
  description: "Private NULSPEC publication and author-email review inbox.",
  robots: { index: false, follow: false, noarchive: true },
};

export default function ReviewPage() {
  return <ReviewDashboard />;
}
