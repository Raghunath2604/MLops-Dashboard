/**
 * BERT Sentiment Analysis Dashboard
 * Production-grade React UI for SaaS management
 *
 * Features:
 * - Organization management
 * - API key generation & management
 * - Billing & subscription management
 * - Real-time usage analytics
 * - Prediction history with search/filter
 * - Admin controls
 */

import React, { useState, useEffect } from 'react';

// Production React Dashboard Component
const SentimentDashboard = () => {
  const [apiKey, setApiKey] = useState(localStorage.getItem('apiKey') || '');
  const [organization, setOrganization] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [usage, setUsage] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

  // API Helper
  const apiCall = async (endpoint, options = {}) => {
    try {
      const headers = {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        ...options.headers,
      };

      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        if (response.status === 401) {
          setError('API key invalid or expired');
          setApiKey('');
          localStorage.removeItem('apiKey');
          return null;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      setError(err.message);
      return null;
    }
  };

  // Fetch organization data on mount
  useEffect(() => {
    if (apiKey) {
      fetchDashboardData();
    }
  }, [apiKey]);

  const fetchDashboardData = async () => {
    setLoading(true);
    const [sub, use, preds] = await Promise.all([
      apiCall('/billing/subscription'),
      apiCall('/billing/usage'),
      apiCall('/predictions?limit=20'),
    ]);

    if (sub) setSubscription(sub);
    if (use) setUsage(use);
    if (preds) setPredictions(preds.predictions || []);
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    const username = e.target.username.value;
    const password = e.target.password.value;

    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `username=${username}&password=${password}`,
      });
      const data = await response.json();

      if (data.api_key) {
        setApiKey(data.api_key);
        localStorage.setItem('apiKey', data.api_key);
        setSuccess(`Welcome ${data.username}!`);
        e.target.reset();
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleMakePrediction = async (e) => {
    e.preventDefault();
    const text = e.target.text.value;
    const result = await apiCall(`/predict?text=${encodeURIComponent(text)}`);

    if (result) {
      setSuccess(`Prediction: ${result.prediction} (${(result.confidence * 100).toFixed(1)}%)`);
      setPredictions([
        {
          id: predictions.length + 1,
          input_text: text,
          prediction: result.prediction,
          confidence: result.confidence,
          timestamp: new Date().toISOString(),
        },
        ...predictions,
      ].slice(0, 20));
      e.target.reset();
    }
  };

  const handleUpgradeSubscription = async (tierName) => {
    const result = await apiCall(`/billing/upgrade?tier_name=${tierName}`, {
      method: 'POST',
    });

    if (result) {
      setSuccess(`Upgraded to ${tierName} tier!`);
      fetchDashboardData();
    }
  };

  // Login Screen
  if (!apiKey) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <h1 style={styles.title}>🎯 Sentiment Analysis API</h1>
          <p style={styles.subtitle}>Production-Grade SaaS Platform</p>

          <form onSubmit={handleRegister} style={styles.form}>
            <h2>Register or Login</h2>
            <input
              type="text"
              name="username"
              placeholder="Username"
              required
              style={styles.input}
            />
            <input
              type="password"
              name="password"
              placeholder="Password"
              required
              style={styles.input}
            />
            <button type="submit" style={styles.button}>Register</button>
          </form>

          <div style={styles.pasteBox}>
            <p>Or paste your API key:</p>
            <input
              type="text"
              placeholder="sk_test_..."
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                localStorage.setItem('apiKey', e.target.value);
              }}
              style={styles.input}
            />
          </div>

          {error && <div style={styles.error}>{error}</div>}
          {success && <div style={styles.success}>{success}</div>}
        </div>
      </div>
    );
  }

  // Dashboard
  return (
    <div style={styles.dashboardContainer}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.headerTitle}>📊 Dashboard</h1>
          {usage && <p style={styles.org}>{usage.organization}</p>}
        </div>
        <div style={styles.headerRight}>
          <span style={styles.tier}>{subscription?.tier.toUpperCase()}</span>
          <button onClick={() => {
            setApiKey('');
            localStorage.removeItem('apiKey');
          }} style={styles.logoutBtn}>Logout</button>
        </div>
      </header>

      {/* Tabs */}
      <nav style={styles.tabs}>
        {['dashboard', 'predict', 'billing', 'api-keys', 'settings'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              ...styles.tab,
              ...(activeTab === tab ? styles.tabActive : {}),
            }}
          >
            {tab.replace('-', ' ').toUpperCase()}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main style={styles.main}>
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div>
            <h2>Overview</h2>

            {/* Stats */}
            <div style={styles.statsGrid}>
              <div style={styles.stat}>
                <p style={styles.statLabel}>Monthly Usage</p>
                <p style={styles.statValue}>{usage?.usage_this_month || 0}</p>
                <p style={styles.statSmall}>{usage?.percentage_used.toFixed(1)}% of limit</p>
              </div>

              <div style={styles.stat}>
                <p style={styles.statLabel}>Remaining</p>
                <p style={styles.statValue}>{usage?.remaining || 0}</p>
                <p style={styles.statSmall}>Until {new Date(usage?.reset_date).toLocaleDateString()}</p>
              </div>

              <div style={styles.stat}>
                <p style={styles.statLabel}>Avg Confidence</p>
                <p style={styles.statValue}>{(usage?.average_confidence * 100).toFixed(1)}%</p>
                <p style={styles.statSmall}>{usage?.total_predictions_all_time} predictions</p>
              </div>

              <div style={styles.stat}>
                <p style={styles.statLabel}>API Performance</p>
                <p style={styles.statValue}>{usage?.average_inference_time_ms.toFixed(0)}ms</p>
                <p style={styles.statSmall}>Average latency</p>
              </div>
            </div>

            {/* Usage Bar */}
            <div style={styles.section}>
              <h3>Monthly Quota</h3>
              <div style={styles.progressBar}>
                <div
                  style={{
                    ...styles.progressFill,
                    width: `${Math.min(usage?.percentage_used || 0, 100)}%`,
                  }}
                />
              </div>
              <p style={styles.progressText}>
                {usage?.usage_this_month} / {usage?.quota_limit} requests
              </p>
            </div>

            {/* Subscription */}
            <div style={styles.section}>
              <h3>Current Plan</h3>
              <div style={styles.planCard}>
                <h4>{subscription?.tier.toUpperCase()}</h4>
                <p>${subscription?.price_usd / 100}/month</p>
                <p>{subscription?.requests_per_month.toLocaleString()} requests/month</p>
                <p>Status: <span style={styles.badge}>{subscription?.status}</span></p>
              </div>
            </div>
          </div>
        )}

        {/* Predict Tab */}
        {activeTab === 'predict' && (
          <div>
            <h2>Make Prediction</h2>

            <form onSubmit={handleMakePrediction} style={styles.predictForm}>
              <textarea
                name="text"
                placeholder="Enter text to analyze..."
                required
                style={styles.textarea}
                rows="6"
              />
              <button type="submit" style={styles.submitBtn}>Analyze Sentiment</button>
            </form>

            <div style={styles.section}>
              <h3>Recent Predictions</h3>
              <div style={styles.predictionsList}>
                {predictions.length === 0 ? (
                  <p style={styles.empty}>No predictions yet</p>
                ) : (
                  predictions.map((pred, idx) => (
                    <div key={idx} style={styles.predictionItem}>
                      <div>
                        <p>{pred.input_text}</p>
                        <small>{new Date(pred.timestamp).toLocaleString()}</small>
                      </div>
                      <div>
                        <span
                          style={{
                            ...styles.badge,
                            backgroundColor:
                              pred.prediction === 'POSITIVE' ? '#4CAF50' : '#f44336',
                          }}
                        >
                          {pred.prediction}
                        </span>
                        <span style={styles.confidence}>
                          {(pred.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Billing Tab */}
        {activeTab === 'billing' && (
          <div>
            <h2>Billing & Subscriptions</h2>

            {/* Upgrade Options */}
            <div style={styles.plansGrid}>
              {[
                { name: 'free', price: 0, requests: '10,000', rpm: '10' },
                { name: 'pro', price: 29, requests: '100,000', rpm: '100' },
                { name: 'business', price: 299, requests: '1,000,000', rpm: '500' },
                { name: 'enterprise', price: 'custom', requests: 'Unlimited', rpm: '10,000' },
              ].map(plan => (
                <div
                  key={plan.name}
                  style={{
                    ...styles.planOption,
                    ...(plan.name === subscription?.tier ? styles.planOptionActive : {}),
                  }}
                >
                  <h4>{plan.name.toUpperCase()}</h4>
                  <p style={styles.price}>
                    {typeof plan.price === 'number'
                      ? `$${plan.price}/mo`
                      : plan.price}
                  </p>
                  <ul style={styles.features}>
                    <li>📊 {plan.requests} requests/month</li>
                    <li>⚡ {plan.rpm} requests/min</li>
                  </ul>
                  {plan.name !== subscription?.tier && (
                    <button
                      onClick={() => handleUpgradeSubscription(plan.name)}
                      style={styles.upgradeBtn}
                    >
                      Choose Plan
                    </button>
                  )}
                  {plan.name === subscription?.tier && (
                    <span style={styles.currentPlan}>✓ Current Plan</span>
                  )}
                </div>
              ))}
            </div>

            {/* Invoices */}
            <div style={styles.section}>
              <h3>Invoices</h3>
              <div style={styles.invoicesList}>
                <p style={styles.empty}>No invoices yet. Upgrade to a paid plan to start billing.</p>
              </div>
            </div>
          </div>
        )}

        {/* API Keys Tab */}
        {activeTab === 'api-keys' && (
          <div>
            <h2>API Keys</h2>

            <div style={styles.section}>
              <h3>Your API Key</h3>
              <div style={styles.apiKeyDisplay}>
                <code>{apiKey}</code>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(apiKey);
                    setSuccess('Copied!');
                  }}
                  style={styles.copyBtn}
                >
                  Copy
                </button>
              </div>
              <p style={styles.warning}>
                ⚠️ Keep this secret! Don't share in public repositories.
              </p>
            </div>

            <div style={styles.section}>
              <h3>API Usage Guide</h3>
              <pre style={styles.codeBlock}>{`
# Make a prediction
curl -H "Authorization: Bearer ${apiKey}" \\
  "http://localhost:8000/predict?text=Hello"

# Batch predictions
curl -X POST \\
  -H "Authorization: Bearer ${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"texts": ["Great", "Terrible"]}' \\
  http://localhost:8000/batch-predict

# Get predictions
curl -H "Authorization: Bearer ${apiKey}" \\
  http://localhost:8000/predictions

# Check usage
curl -H "Authorization: Bearer ${apiKey}" \\
  http://localhost:8000/billing/usage
              `}</pre>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div>
            <h2>Settings</h2>

            <div style={styles.section}>
              <h3>Account Information</h3>
              {usage && (
                <div style={styles.settingsList}>
                  <div style={styles.settingItem}>
                    <span>Organization:</span>
                    <strong>{usage.organization}</strong>
                  </div>
                  <div style={styles.settingItem}>
                    <span>Current Plan:</span>
                    <strong>{usage.tier}</strong>
                  </div>
                  <div style={styles.settingItem}>
                    <span>Total Predictions:</span>
                    <strong>{usage.total_predictions_all_time.toLocaleString()}</strong>
                  </div>
                </div>
              )}
            </div>

            <div style={styles.section}>
              <h3>Documentation</h3>
              <p>
                <a href="/docs" style={styles.link}>📚 Interactive API Docs</a>
              </p>
              <p>
                <a href="https://github.com" style={styles.link}>💻 GitHub Repository</a>
              </p>
              <p>
                <a href="mailto:support@my-app.com" style={styles.link}>📧 Email Support</a>
              </p>
            </div>

            <div style={styles.section}>
              <button onClick={() => {
                setApiKey('');
                localStorage.removeItem('apiKey');
              }} style={styles.logoutBtn}>Logout</button>
            </div>
          </div>
        )}
      </main>

      {/* Alerts */}
      {error && <div style={styles.alert}>{error}</div>}
      {success && <div style={styles.alertSuccess}>{success}</div>}
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    padding: '20px',
  },
  card: {
    background: 'white',
    borderRadius: '12px',
    padding: '40px',
    boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
    maxWidth: '500px',
    width: '100%',
  },
  title: {
    fontSize: '28px',
    fontWeight: 'bold',
    marginBottom: '8px',
    color: '#333',
  },
  subtitle: {
    color: '#666',
    marginBottom: '30px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    marginBottom: '24px',
  },
  input: {
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    fontSize: '14px',
    fontFamily: 'inherit',
  },
  button: {
    padding: '12px',
    background: '#667eea',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  pasteBox: {
    borderTop: '1px solid #eee',
    paddingTop: '20px',
  },
  error: {
    background: '#ffebee',
    color: '#c62828',
    padding: '12px',
    borderRadius: '6px',
    marginTop: '12px',
  },
  success: {
    background: '#e8f5e9',
    color: '#2e7d32',
    padding: '12px',
    borderRadius: '6px',
    marginTop: '12px',
  },
  // Dashboard
  dashboardContainer: {
    minHeight: '100vh',
    background: '#f5f7fa',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    background: 'white',
    padding: '20px 30px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  headerLeft: { display: 'flex', flexDirection: 'column', gap: '4px' },
  headerTitle: { fontSize: '24px', fontWeight: 'bold', margin: 0, color: '#333' },
  org: { color: '#666', margin: 0, fontSize: '14px' },
  headerRight: { display: 'flex', alignItems: 'center', gap: '16px' },
  tier: {
    background: '#667eea',
    color: 'white',
    padding: '6px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 'bold',
  },
  logoutBtn: {
    padding: '8px 16px',
    background: '#f44336',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '12px',
  },
  tabs: {
    display: 'flex',
    borderBottom: '2px solid #eee',
    background: 'white',
    padding: '0 30px',
  },
  tab: {
    padding: '16px 20px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#666',
    fontSize: '14px',
    fontWeight: '500',
    borderBottom: '3px solid transparent',
  },
  tabActive: {
    color: '#667eea',
    borderBottomColor: '#667eea',
  },
  main: {
    padding: '30px',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '20px',
    marginBottom: '30px',
  },
  stat: {
    background: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
  },
  statLabel: { color: '#666', margin: '0 0 8px 0', fontSize: '12px', fontWeight: '500' },
  statValue: { fontSize: '28px', fontWeight: 'bold', margin: '0 0 4px 0', color: '#333' },
  statSmall: { color: '#999', margin: 0, fontSize: '12px' },
  section: {
    background: 'white',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
  },
  progressBar: {
    height: '8px',
    background: '#eee',
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '8px',
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #667eea, #764ba2)',
    transition: 'width 0.3s ease',
  },
  progressText: { color: '#666', fontSize: '14px', margin: 0 },
  planCard: { background: '#f5f7fa', padding: '16px', borderRadius: '6px' },
  badge: {
    display: 'inline-block',
    background: '#4CAF50',
    color: 'white',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 'bold',
  },
  predictForm: {
    background: 'white',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  textarea: {
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    fontSize: '14px',
    fontFamily: 'inherit',
    resize: 'vertical',
  },
  submitBtn: {
    padding: '12px',
    background: '#667eea',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  predictionsList: { display: 'flex', flexDirection: 'column', gap: '12px' },
  predictionItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    background: '#f5f7fa',
    borderRadius: '6px',
  },
  empty: { color: '#999', textAlign: 'center', margin: '20px 0' },
  confidence: { marginLeft: '8px', fontSize: '12px', fontWeight: 'bold' },
  plansGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '20px',
    marginBottom: '30px',
  },
  planOption: {
    background: 'white',
    padding: '20px',
    borderRadius: '8px',
    border: '2px solid #eee',
    textAlign: 'center',
  },
  planOptionActive: {
    borderColor: '#667eea',
    background: '#f0f4ff',
  },
  price: { fontSize: '24px', fontWeight: 'bold', margin: '8px 0', color: '#667eea' },
  features: {
    listStyle: 'none',
    padding: 0,
    margin: '12px 0',
    textAlign: 'left',
  },
  upgradeBtn: {
    width: '100%',
    padding: '10px',
    background: '#667eea',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    marginTop: '12px',
  },
  currentPlan: {
    display: 'block',
    color: '#4CAF50',
    fontWeight: 'bold',
    marginTop: '12px',
  },
  invoicesList: { minHeight: '100px' },
  apiKeyDisplay: {
    display: 'flex',
    gap: '12px',
    background: '#f5f7fa',
    padding: '12px',
    borderRadius: '6px',
    alignItems: 'center',
  },
  copyBtn: {
    padding: '8px 16px',
    background: '#667eea',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  warning: {
    background: '#fff3e0',
    color: '#e65100',
    padding: '12px',
    borderRadius: '6px',
    marginTop: '12px',
  },
  codeBlock: {
    background: '#f5f7fa',
    padding: '12px',
    borderRadius: '6px',
    overflow: 'auto',
    fontSize: '12px',
  },
  link: {
    color: '#667eea',
    textDecoration: 'none',
  },
  settingsList: { display: 'flex', flexDirection: 'column', gap: '12px' },
  settingItem: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '12px',
    background: '#f5f7fa',
    borderRadius: '6px',
  },
  alert: {
    position: 'fixed',
    bottom: '20px',
    right: '20px',
    background: '#f44336',
    color: 'white',
    padding: '16px',
    borderRadius: '6px',
    zIndex: 1000,
  },
  alertSuccess: {
    position: 'fixed',
    bottom: '20px',
    right: '20px',
    background: '#4CAF50',
    color: 'white',
    padding: '16px',
    borderRadius: '6px',
    zIndex: 1000,
  },
};

export default SentimentDashboard;
