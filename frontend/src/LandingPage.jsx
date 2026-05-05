import React from 'react';
import { SignInButton } from '@clerk/clerk-react';

const LandingPage = () => {
  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className="landing-nav fade-in">
        <div className="brand">
          <div className="brand-icon">F</div>
          <span className="brand-name">FinSight<span className="dot">.</span></span>
        </div>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#status">System Status</a>
          <SignInButton mode="modal">
            <button className="btn-primary">Get Started</button>
          </SignInButton>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="hero-section">
        <div className="hero-content fade-in">
          <span className="hero-badge">A Better Way to Monitor AI</span>
          <h1 className="hero-title">
            Enterprise <span className="gradient-text">BERT</span> Sentiment <br />
            Analysis as a Service
          </h1>
          <p className="hero-subtitle">
            A complete MLOps platform for analyzing text at scale. Monitor performance, 
            detect drift, and manage multi-tenant billing with zero infra overhead.
          </p>
          <div className="hero-actions">
            <SignInButton mode="modal">
              <button className="btn-large">Launch Dashboard</button>
            </SignInButton>
            <button className="btn-outline">View Docs</button>
          </div>
        </div>

        {/* Floating UI Elements */}
        <div className="hero-visual">
          <div className="floating-card c1">
            <div className="card-top">
              <span className="label">Live Latency</span>
              <span className="value">142ms</span>
            </div>
            <div className="mini-chart"></div>
          </div>
          <div className="floating-card c2">
             <div className="label">Accuracy</div>
             <div className="value">99.2%</div>
          </div>
          <div className="hero-glow"></div>
        </div>
      </header>

      {/* Features Grid */}
      <section id="features" className="features-section">
        <h2 className="section-title">Built for Production MLOps</h2>
        <div className="features-grid">
          {[
            {
              title: "Multi-Tenant API",
              desc: "Isolated keys and quotas for every organization out of the box.",
              icon: "🔑"
            },
            {
              title: "Real-time Observability",
              desc: "Grafana, Loki, and Jaeger integration for deep pipeline visibility.",
              icon: "📊"
            },
            {
              title: "Automated Drift Detection",
              desc: "Background tasks monitor model confidence and alert on performance drop.",
              icon: "🧠"
            },
            {
              title: "SaaS Billing Ready",
              desc: "Built-in Stripe webhooks and subscription tier management.",
              icon: "💳"
            }
          ].map((f, i) => (
            <div key={i} className="feature-card">
              <div className="feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Live Status Section */}
      <section id="status" className="status-section">
        <div className="status-container">
          <div className="status-left">
            <h2>Reliability by Design</h2>
            <p>Our distributed architecture ensures high availability and low latency globally.</p>
            <div className="status-pill">
              <span className="status-dot green"></span>
              All Systems Operational
            </div>
          </div>
          <div className="status-stats">
            <div className="stat-item">
              <span className="stat-val">99.9%</span>
              <span className="stat-lab">Uptime</span>
            </div>
            <div className="stat-item">
              <span className="stat-val">{"<"}200ms</span>
              <span className="stat-lab">P95 Latency</span>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>© 2026 FinSight MLOps Dashboard. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default LandingPage;
