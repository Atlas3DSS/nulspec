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
    "Independent replication of computational machine-learning claims, with public selection records, protocols, deviations, execution evidence, and outcomes.",
  applicationName: "NULSPEC",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    siteName: "NULSPEC",
    title: "NULSPEC — Independent research replication",
    description:
      "Independent replication of computational machine-learning claims, with a public selection denominator and staged statistical escalation.",
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "NULSPEC — Independent research replication",
    description:
      "Independent computational ML replication with public selection records, protocols, deviations, execution evidence, and reported outcomes.",
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
