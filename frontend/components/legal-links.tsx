import Link from "next/link";

const legalLinks = [
  { href: "/privacy", label: "Privacy Policy" },
  { href: "/terms-of-use", label: "Terms of Use" },
  { href: "/financial-disclaimer", label: "Financial Disclaimer" },
];

export function LegalLinks() {
  return (
    <footer className="legal-link-bar" aria-label="Legal links">
      <nav className="legal-link-list">
        {legalLinks.map((link) => (
          <Link className="legal-link-button" href={link.href} key={link.href}>
            {link.label}
          </Link>
        ))}
      </nav>
      <p className="site-credit">
        Built by Han Zhao ·{" "}
        <a
          href="https://github.com/Harrrrrrrrrrrry/ForecastWorkspace"
          rel="noreferrer"
          target="_blank"
        >
          GitHub
        </a>
      </p>
    </footer>
  );
}
