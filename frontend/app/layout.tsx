import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ConsumerSheildAI - Explainable Consumer Rights Assistant",
  description: "Evidence-backed consumer rights guidance powered by explainable AI.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
