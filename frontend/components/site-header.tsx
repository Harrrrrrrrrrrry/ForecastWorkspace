import Image from "next/image";
import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="mission-nav landing-nav site-header">
      <Link className="nav-mark landing-brand" href="/">
        <Image
          alt=""
          aria-hidden="true"
          className="landing-brand-logo"
          height={32}
          src="/images/no_background_logo.svg"
          width={32}
        />
        <span>PrismForecast</span>
      </Link>

      <nav className="nav-links landing-links" aria-label="Primary navigation">
        <Link href="/">Home</Link>
        <Link href="/dashboard">Dashboard</Link>
      </nav>
    </header>
  );
}
