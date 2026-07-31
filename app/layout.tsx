import type { Metadata } from "next";
import "@fontsource-variable/inter/wght.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://nulspec.com"),
  title: {
    default: "NULSPEC — Independent research replication",
    template: "%s — NULSPEC",
  },
  description:
    "A small independent team rerunning published AI research, recording every deviation, and publishing failures and null results with the same care as successes.",
  applicationName: "NULSPEC",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    siteName: "NULSPEC",
    title: "NULSPEC — We rerun the experiments",
    description:
      "Independent AI research replication on hardware we control. Public protocols, live run ledgers, and no conclusions before the work is done.",
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "NULSPEC — We rerun the experiments",
    description:
      "Independent research replication. Null results and deviations included.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        {children}
      </body>
    </html>
  );
}
