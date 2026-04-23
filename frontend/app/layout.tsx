import type { ReactNode } from "react";
import type { Metadata } from "next";
import "@fontsource-variable/inter/wght.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Forecast Workspace",
  description: "Web platform for stock forecasting based on the Market Influence Model.",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
