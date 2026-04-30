import { ReactNode } from "react";

import { SiteHeader } from "@/components/site-header";

type LegalPageProps = {
  title: string;
  updated: string;
  children: ReactNode;
};

export function LegalPage({ title, updated, children }: LegalPageProps) {
  return (
    <main className="legal-page-shell">
      <SiteHeader />

      <article className="legal-page-content">
        <p className="legal-page-updated">Last updated: {updated}</p>
        <h1>{title}</h1>
        {children}
      </article>
    </main>
  );
}
