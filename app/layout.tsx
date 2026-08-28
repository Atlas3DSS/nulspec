import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://nulspec.com"),
  title: {
    default: "NULSPEC",
    template: "%s · NULSPEC",
  },
  description: "AI enthusiasts doing things.",
  applicationName: "NULSPEC",
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: "website",
    siteName: "NULSPEC",
    title: "NULSPEC",
    description: "AI enthusiasts doing things.",
    url: "https://nulspec.com",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
