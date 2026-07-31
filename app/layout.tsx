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
    "Independent research replication, beginning with AI and machine learning. Registered protocols, deviations, selected execution records, and reported outcomes are public.",
  applicationName: "NULSPEC",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    siteName: "NULSPEC",
    title: "NULSPEC — Independent research replication",
    description:
      "NULSPEC begins with AI and machine-learning studies using team-operated compute, with a long-term objective of independent replication across research fields.",
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "NULSPEC — Independent research replication",
    description:
      "Independent replication beginning with AI and machine learning, with public protocols, deviations, selected execution records, and reported outcomes.",
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
