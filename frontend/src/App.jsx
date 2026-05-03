import React, { useState, useEffect } from 'react';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8001' : '/api';

function App() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('apiKey') || '');
  const [organization, setOrganization] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [usage, setUsage] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Clear alerts after 5 seconds
  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => {
        setError(null);
        setSuccess(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, success]);

  // Fetch dashboard data
  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Create headers
      const headers = {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      };

      // Since we don't have usage endpoint in current backend, we mock or use existing endpoints
      // Fallback to /status, /model-metrics, /billing/subscription
      
      const statsRes = await fetch(`${API_BASE}/model-metrics`, { headers });
      if (statsRes.status === 401) {
         setError('API Key is invalid or expired. Please login again.');
         setApiKey('');
         localStorage.removeItem('apiKey');
         return;
      }
      
      const statsData = await statsRes.json();
      setUsage({
        total_predictions_all_time: statsData.total || 0,
        average_confidence: statsData.avg_confidence || 0,
        average_inference_time_ms: statsData.avg_inference_time_ms || 0,
        usage_this_month: statsData.total || 0, // Mock usage
        quota_limit: 10000,
        remaining: 10000 - (statsData.total || 0),
        percentage_used: ((statsData.total || 0) / 10000) * 100,
        organization: "My Organization",
        reset_date: new Date(new Date().setMonth(new Date().getMonth() + 1)).toISOString()
      });

      const subRes = await fetch(`${API_BASE}/billing/subscription`, { headers }).catch(() => null);
      if (subRes && subRes.ok) {
        setSubscription(await subRes.json());
      } else {
         setSubscription({ tier: 'free', price_usd: 0, requests_per_month: 10000, status: 'active' });
      }

      const predsRes = await fetch(`${API_BASE}/predictions?limit=20`, { headers }).catch(() => null);
      if (predsRes && predsRes.ok) {
        const predsData = await predsRes.json();
        setPredictions(predsData.predictions || []);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to connect to the API. Is it running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (apiKey) {
      fetchDashboardData();
    }
  }, [apiKey]);

  const handleRegister = async (e) => {
    e.preventDefault();
    const username = e.target.username.value;
    const password = e.target.password.value;

    try {
      const response = await fetch(`${API_BASE}/auth/register?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`, {
        method: 'POST',
      });
      const data = await response.json();

      if (data.api_key) {
        setApiKey(data.api_key);
        localStorage.setItem('apiKey', data.api_key);
        setSuccess(`Welcome! Your account was created successfully.`);
      } else if (data.error) {
        setError(data.error);
      }
    } catch (err) {
      setError("Registration failed. Please try again.");
    }
  };

  const handleMakePrediction = async (e) => {
    e.preventDefault();
    const text = e.target.text.value;
    if (!text) return;

    try {
      const response = await fetch(`${API_BASE}/predict?text=${encodeURIComponent(text)}`, {
        headers: { 'Authorization': `Bearer ${apiKey}` }
      });
      const result = await response.json();

      if (result.prediction) {
        setSuccess(`Predicted: ${result.prediction} (${(result.confidence * 100).toFixed(1)}%)`);
        setPredictions([
          {
            id: Date.now(),
            input_text: text,
            prediction: result.prediction,
            confidence: result.confidence,
            timestamp: new Date().toISOString(),
          },
          ...predictions,
        ].slice(0, 20));
        e.target.reset();
        
        // Refresh usage stats quietly
        fetchDashboardData();
      } else if (result.error) {
         setError(result.error);
      }
    } catch (err) {
      setError("Prediction request failed.");
    }
  };

  const handleUpgradeSubscription = async (tierName) => {
    try {
       const response = await fetch(`${API_BASE}/billing/upgrade?tier_name=${tierName}`, {
         method: 'POST',
         headers: { 'Authorization': `Bearer ${apiKey}` }
       });
       
       if (response.ok) {
          setSuccess(`Successfully upgraded to ${tierName.toUpperCase()} tier!`);
          fetchDashboardData();
       } else {
          const data = await response.json();
          setError(data.error || "Upgrade failed");
       }
    } catch(err) {
       setError("Upgrade failed. API unreachable.");
    }
  };

  // Auth Screen
  if (!apiKey) {
    return (
      <div className="app-container">
        <div className="auth-wrapper">
          <div className="auth-card glass">
            <h1>Nexus ML</h1>
            <p>Enterprise Sentiment Analysis API</p>

            {error && <div className="alert alert-error">{error}</div>}
            {success && <div className="alert alert-success">{success}</div>}

            <form onSubmit={handleRegister} className="auth-form">
              <input
                type="text"
                name="username"
                className="input-field"
                placeholder="Username"
                required
              />
              <input
                type="password"
                name="password"
                className="input-field"
                placeholder="Password"
                required
              />
              <button type="submit" className="btn">Create Account</button>
            </form>

            <div className="divider">OR</div>

            <div className="auth-form">
              <input
                type="text"
                className="input-field"
                placeholder="Paste existing API Key (sk_...)"
                onChange={(e) => {
                  if(e.target.value.length > 20) {
                     setApiKey(e.target.value);
                     localStorage.setItem('apiKey', e.target.value);
                  }
                }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Dashboard Screen
  return (
    <div className="app-container">
      {/* Header */}
      <header className="dashboard-header glass" style={{ borderRadius: 0, borderTop: 0, borderLeft: 0, borderRight: 0 }}>
        <div className="header-brand">
          <h1>Nexus ML</h1>
          <p>{usage?.organization || 'Loading Organization...'}</p>
        </div>
        <div className="header-actions">
          {subscription && <span className="tier-badge">{subscription.tier}</span>}
          <button onClick={() => { setApiKey(''); localStorage.removeItem('apiKey'); }} className="btn-outline">
            Sign Out
          </button>
        </div>
      </header>

      {/* Navigation */}
      <nav className="dashboard-nav">
        {['dashboard', 'predict', 'api-keys', 'billing'].map(tab => (
          <button
            key={tab}
            className={`nav-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1).replace('-', ' ')}
          </button>
        ))}
      </nav>

      <main className="dashboard-main">
         {error && <div className="alert alert-error">{error}</div>}
         {success && <div className="alert alert-success">{success}</div>}

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="fade-in">
            <div className="stats-grid">
              <div className="stat-card glass">
                <span className="stat-label">Total Predictions</span>
                <span className="stat-value">{usage?.total_predictions_all_time || 0}</span>
                <span className="stat-sub">Lifetime usage</span>
              </div>
              <div className="stat-card glass">
                <span className="stat-label">Monthly Quota Used</span>
                <span className="stat-value">{usage?.percentage_used?.toFixed(1) || 0}%</span>
                <span className="stat-sub">{usage?.usage_this_month || 0} / {usage?.quota_limit || 0}</span>
              </div>
              <div className="stat-card glass">
                <span className="stat-label">Model Confidence</span>
                <span className="stat-value">{((usage?.average_confidence || 0) * 100).toFixed(1)}%</span>
                <span className="stat-sub">Average accuracy score</span>
              </div>
              <div className="stat-card glass">
                <span className="stat-label">API Latency</span>
                <span className="stat-value">{usage?.average_inference_time_ms?.toFixed(0) || 0}ms</span>
                <span className="stat-sub">Average response time</span>
              </div>
            </div>

            <div className="section glass">
              <h3>Monthly API Usage</h3>
              <div className="progress-container">
                <div 
                  className="progress-fill" 
                  style={{ width: `${Math.min(usage?.percentage_used || 0, 100)}%` }}
                />
              </div>
              <p className="progress-text">Resets on {new Date(usage?.reset_date || Date.now()).toLocaleDateString()}</p>
            </div>
          </div>
        )}

        {/* Predict Tab */}
        {activeTab === 'predict' && (
          <div className="fade-in">
            <div className="section glass">
              <h3>Test the Model</h3>
              <form onSubmit={handleMakePrediction} className="predict-form">
                <textarea
                  name="text"
                  className="input-field"
                  placeholder="Enter a review or sentence to analyze its sentiment..."
                  required
                />
                <button type="submit" className="btn" disabled={loading}>
                  {loading ? 'Analyzing...' : 'Analyze Sentiment'}
                </button>
              </form>
            </div>

            <div className="section glass">
              <h3>Recent Predictions</h3>
              {predictions.length === 0 ? (
                <p style={{ color: 'var(--text-muted)' }}>No predictions made yet.</p>
              ) : (
                predictions.map((pred) => (
                  <div key={pred.id} className="prediction-item">
                    <div>
                      <div className="pred-text">"{pred.input_text}"</div>
                      <div className="pred-time">{new Date(pred.timestamp).toLocaleString()}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span className={pred.prediction === 'POSITIVE' ? 'badge-positive' : 'badge-negative'}>
                        {pred.prediction}
                      </span>
                      <div style={{ fontSize: '12px', marginTop: '6px', color: 'var(--text-muted)' }}>
                        Conf: {(pred.confidence * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Billing Tab */}
        {activeTab === 'billing' && (
          <div className="fade-in">
            <div className="pricing-grid">
              {[
                { name: 'free', price: 0, reqs: '10,000', features: ['Basic support', 'Standard latency', '10 req/min'] },
                { name: 'pro', price: 29, reqs: '100,000', features: ['Priority support', 'Low latency', '100 req/min'] },
                { name: 'business', price: 299, reqs: '1,000,000', features: ['24/7 Phone support', 'Ultra-low latency', '500 req/min'] }
              ].map(plan => (
                <div key={plan.name} className={`pricing-card glass ${subscription?.tier === plan.name ? 'active-plan' : ''}`}>
                  <div className="pricing-tier">{plan.name}</div>
                  <div className="pricing-price">${plan.price}<span style={{fontSize: '16px', color: 'var(--text-muted)'}}>/mo</span></div>
                  <ul className="pricing-features">
                    <li>✓ {plan.reqs} requests/mo</li>
                    {plan.features.map((f, i) => <li key={i}>✓ {f}</li>)}
                  </ul>
                  {subscription?.tier !== plan.name && (
                    <button onClick={() => handleUpgradeSubscription(plan.name)} className="btn">
                      Upgrade to {plan.name.charAt(0).toUpperCase() + plan.name.slice(1)}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* API Keys Tab */}
        {activeTab === 'api-keys' && (
          <div className="fade-in section glass">
            <h3>Your Secret API Key</h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>
              Use this key to authenticate your requests. Do not share it with anyone.
            </p>
            <div className="api-key-box">
              <code>{apiKey}</code>
              <button 
                onClick={() => { navigator.clipboard.writeText(apiKey); setSuccess('Copied to clipboard!'); }} 
                className="btn-outline"
              >
                Copy
              </button>
            </div>

            <h3 style={{ marginTop: '32px' }}>Integration Example</h3>
            <pre style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '12px', overflowX: 'auto', color: '#60a5fa' }}>
{`curl -X GET "${window.location.hostname === 'localhost' ? 'http://localhost:8001' : 'https://api.yourdomain.com'}/predict?text=This+is+amazing!" \\
  -H "Authorization: Bearer ${apiKey}"`}
            </pre>
          </div>
        )}

      </main>
    </div>
  );
}

export default App;
