import React, { useState, useEffect } from 'react';
import { SignedIn, SignedOut, SignIn, UserButton, useAuth, useUser } from '@clerk/clerk-react';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8001' : '/api';

function App() {
  const { getToken } = useAuth();
  const { user } = useUser();
  
  const [apiKey, setApiKey] = useState('');
  const [subscription, setSubscription] = useState(null);
  const [usage, setUsage] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => {
        setError(null);
        setSuccess(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, success]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      if (!token) return;

      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      if (!apiKey) {
          const keyRes = await fetch(`${API_BASE}/auth/my-key`, { headers }).catch(() => null);
          if (keyRes && keyRes.ok) {
            const keyData = await keyRes.json();
            setApiKey(keyData.api_key);
          }
      }
      
      const statsRes = await fetch(`${API_BASE}/model-metrics`, { headers });
      if (statsRes.status === 401) {
         setError('Session expired. Please login again.');
         return;
      }
      
      const statsData = await statsRes.json();
      setUsage({
        total_predictions_all_time: statsData.total || 0,
        average_confidence: statsData.avg_confidence || 0,
        average_inference_time_ms: statsData.avg_inference_time_ms || 0,
        usage_this_month: statsData.total || 0,
        quota_limit: 10000,
        remaining: 10000 - (statsData.total || 0),
        percentage_used: ((statsData.total || 0) / 10000) * 100,
        organization: user?.fullName || user?.primaryEmailAddress?.emailAddress || "My Organization",
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
    if (user) {
      fetchDashboardData();
    }
  }, [user]);

  const handleMakePrediction = async (e) => {
    e.preventDefault();
    const text = e.target.text.value;
    if (!text) return;

    try {
      const token = await getToken();
      const response = await fetch(`${API_BASE}/predict?text=${encodeURIComponent(text)}`, {
        headers: { 'Authorization': `Bearer ${token}` }
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
       const token = await getToken();
       const response = await fetch(`${API_BASE}/billing/upgrade?tier_name=${tierName}`, {
         method: 'POST',
         headers: { 'Authorization': `Bearer ${token}` }
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

  return (
    <div className="app-container">
      <SignedOut>
        <div className="auth-layout">
          {/* Visual Left Side (Perok.ai style) */}
          <div className="auth-visual">
            <div className="auth-visual-content">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <img src="/logo.png" alt="Monitor Dashboard Logo" style={{ width: '40px', height: '40px', objectFit: 'contain', borderRadius: '10px' }} />
                <h1 style={{ color: '#fff', fontSize: '24px', fontFamily: 'Plus Jakarta Sans', fontWeight: 800 }}>FinSight<span style={{color: '#3b82f6'}}>.</span></h1>
              </div>
              
              <div className="auth-quote fade-in">
                Secure AI Ops <br />
                & Compliance Monitoring.
              </div>
            </div>
          </div>

          {/* Form Right Side */}
          <div className="auth-form-side">
            <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
              <h2 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '8px' }}>Welcome back</h2>
              <p style={{ color: 'var(--text-secondary)' }}>Sign in to access your dashboard</p>
            </div>
            <SignIn routing="hash" />
          </div>
        </div>
      </SignedOut>

      <SignedIn>
        {/* SIDEBAR NAVIGATION */}
        <aside className="sidebar">
          <div>
            <div className="brand">
              <img src="/logo.png" alt="Logo" style={{ width: '32px', height: '32px', objectFit: 'contain', borderRadius: '8px' }} />
              <div className="brand-text">
                <h1>FinSight<span style={{color: '#3b82f6'}}>.</span></h1>
                <p>Monitor Dash</p>
              </div>
            </div>

            <nav className="nav-menu">
              {['dashboard', 'predict', 'api-keys', 'billing'].map(tab => (
                <button
                  key={tab}
                  className={`nav-item ${activeTab === tab ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab)}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    {tab === 'dashboard' && <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>}
                    {tab === 'predict' && <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>}
                    {tab === 'api-keys' && <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path>}
                    {tab === 'billing' && <rect x="2" y="5" width="20" height="14" rx="2"></rect>}
                  </svg>
                  {tab.charAt(0).toUpperCase() + tab.slice(1).replace('-', ' ')}
                </button>
              ))}
            </nav>
          </div>

          <div className="sidebar-footer">
            <div style={{ display: 'flex', flexDirection: 'column' }}>
               <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Logged in as</span>
               <span style={{ fontSize: '14px', fontWeight: 600 }}>{usage?.organization || 'User'}</span>
            </div>
            <UserButton afterSignOutUrl="/" />
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <main className="main-content">
          <div className="top-bar">
            <div className="top-bar-left">
              <h2>Overview</h2>
              <p>System metrics & AI operations compliance</p>
            </div>
            <div className="top-bar-right">
              {subscription && <span className="badge neutral">{subscription.tier} tier</span>}
              <span className="badge positive">System Healthy</span>
            </div>
          </div>

          {error && <div className="bento-card fade-in" style={{ borderLeft: '4px solid var(--accent-red)' }}><p>{error}</p></div>}
          {success && <div className="bento-card fade-in" style={{ borderLeft: '4px solid var(--accent-green)' }}><p>{success}</p></div>}

          {activeTab === 'dashboard' && (
            <div className="bento-grid fade-in">
              {/* Main Metric Cards */}
              <div className="bento-card span-3">
                <div className="card-header">
                  <span className="card-title">Total Inference</span>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                </div>
                <div className="metric-value">{usage?.total_predictions_all_time || 0}</div>
                <div className="metric-sub">Lifetime requests processed</div>
              </div>

              <div className="bento-card span-3">
                <div className="card-header">
                  <span className="card-title">Avg Latency</span>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>
                <div className="metric-value">{usage?.average_inference_time_ms?.toFixed(0) || 0}<span style={{fontSize:'24px', color:'var(--text-secondary)'}}>ms</span></div>
                <div className="metric-sub">P95 Global Latency</div>
              </div>

              <div className="bento-card span-3">
                <div className="card-header">
                  <span className="card-title">Model Confidence</span>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                </div>
                <div className="metric-value">{((usage?.average_confidence || 0) * 100).toFixed(1)}<span style={{fontSize:'24px', color:'var(--text-secondary)'}}>%</span></div>
                <div className="metric-sub">Global average accuracy</div>
              </div>

              <div className="bento-card span-3">
                <div className="card-header">
                  <span className="card-title">Compute Quota</span>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                </div>
                <div className="metric-value">{usage?.percentage_used?.toFixed(1) || 0}<span style={{fontSize:'24px', color:'var(--text-secondary)'}}>%</span></div>
                <div className="metric-sub {usage?.percentage_used > 80 ? 'danger' : ''}">{usage?.usage_this_month} / {usage?.quota_limit} calls</div>
              </div>

              {/* Large Quota Consumption Visual */}
              <div className="bento-card span-8 row-span-2">
                <div className="card-header" style={{ marginBottom: '10px' }}>
                  <span className="card-title" style={{ color: '#fff', fontSize: '18px' }}>Monthly API Consumption</span>
                  <span className="badge neutral">Resets {new Date(usage?.reset_date || Date.now()).toLocaleDateString()}</span>
                </div>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '30px' }}>Real-time usage tracking against your {subscription?.tier} plan limits.</p>
                
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                   <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                     <span style={{ fontSize: '14px', fontWeight: 600 }}>Total Requests</span>
                     <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{usage?.usage_this_month} / {usage?.quota_limit}</span>
                   </div>
                   <div className="data-bar-track" style={{ height: '24px', borderRadius: '12px', background: 'rgba(255,255,255,0.05)', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5)' }}>
                     <div className="data-bar-fill" style={{ width: `${Math.min(usage?.percentage_used || 0, 100)}%`, background: 'linear-gradient(90deg, var(--accent-blue), var(--accent-purple))', boxShadow: '0 0 20px rgba(59, 130, 246, 0.4)' }} />
                   </div>
                </div>
              </div>

              {/* Quick Action / Small List */}
              <div className="bento-card span-4 row-span-2">
                <div className="card-header">
                  <span className="card-title">Live Pipeline Activity</span>
                </div>
                <div className="activity-list">
                  {predictions.slice(0, 5).map((pred) => (
                    <div key={pred.id} className="activity-item">
                      <div>
                        <div className="activity-text">"{pred.input_text}"</div>
                        <div className="activity-time">{new Date(pred.timestamp).toLocaleTimeString()}</div>
                      </div>
                      <span className={`badge ${pred.prediction === 'POSITIVE' ? 'positive' : 'negative'}`}>
                        {pred.prediction.substring(0, 3)}
                      </span>
                    </div>
                  ))}
                  {predictions.length === 0 && <p style={{color: 'var(--text-tertiary)', fontSize: '13px'}}>No recent activity detected.</p>}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'predict' && (
             <div className="bento-grid fade-in">
                <div className="bento-card span-6">
                  <div className="card-header">
                    <span className="card-title">Model Testing Environment</span>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '14px' }}>
                    Run ad-hoc sentiment analysis predictions through the pipeline to test latency and accuracy.
                  </p>
                  <form onSubmit={handleMakePrediction} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <textarea
                      name="text"
                      className="input-bento"
                      rows="6"
                      placeholder="Enter a payload to analyze..."
                      required
                    />
                    <button type="submit" className="btn-bento" disabled={loading} style={{ alignSelf: 'flex-start' }}>
                      {loading ? 'Processing...' : 'Run Inference'}
                    </button>
                  </form>
                </div>

                <div className="bento-card span-6">
                  <div className="card-header">
                    <span className="card-title">Inference Results Log</span>
                  </div>
                  <div className="activity-list">
                    {predictions.map((pred) => (
                      <div key={pred.id} className="activity-item">
                        <div style={{ flex: 1, marginRight: '16px' }}>
                          <div className="activity-text" style={{ maxWidth: '100%' }}>"{pred.input_text}"</div>
                          <div className="activity-time">{new Date(pred.timestamp).toLocaleString()}</div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                          <span className={`badge ${pred.prediction === 'POSITIVE' ? 'positive' : 'negative'}`}>
                            {pred.prediction}
                          </span>
                          <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{(pred.confidence * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    ))}
                    {predictions.length === 0 && <p style={{color: 'var(--text-tertiary)', fontSize: '14px'}}>Awaiting payload...</p>}
                  </div>
                </div>
             </div>
          )}

          {activeTab === 'api-keys' && (
             <div className="bento-grid fade-in">
                <div className="bento-card span-8">
                  <div className="card-header">
                    <span className="card-title">Production API Key</span>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                    This key grants full programmatic access to your allocated pipeline resources. Store it securely in your environment variables.
                  </p>
                  
                  <div className="api-key-code">
                    {apiKey || "Generating secure token..."}
                  </div>
                  
                  <button onClick={() => { navigator.clipboard.writeText(apiKey); setSuccess('Copied to clipboard!'); }} className="btn-bento">
                    Copy to Clipboard
                  </button>
                </div>

                <div className="bento-card span-4">
                  <div className="card-header">
                    <span className="card-title">cURL Example</span>
                  </div>
                  <pre style={{ background: '#000', padding: '16px', borderRadius: '8px', fontSize: '13px', color: 'var(--accent-blue)', overflowX: 'auto', marginTop: '16px' }}>
{`curl -X GET \\
  "${window.location.hostname === 'localhost' ? 'http://localhost:8001' : 'https://api.yourdomain.com'}/predict?text=Awesome" \\
  -H "Authorization: Bearer YOUR_KEY"`}
                  </pre>
                </div>
             </div>
          )}

          {activeTab === 'billing' && (
            <div className="pricing-bento fade-in">
               {[
                  { name: 'free', price: 0, reqs: '10,000', features: ['Standard latency', '10 req/min', 'Community support'] },
                  { name: 'pro', price: 29, reqs: '100,000', features: ['Low latency', '100 req/min', 'Priority support'] },
                  { name: 'business', price: 299, reqs: '1,000,000', features: ['Ultra-low latency', '500 req/min', 'SLA 99.9%'] }
                ].map(plan => (
                  <div key={plan.name} className={`tier-card ${subscription?.tier === plan.name ? 'active' : ''}`}>
                     {subscription?.tier === plan.name && <span className="badge neutral" style={{ position: 'absolute', top: '16px', right: '16px' }}>Current Plan</span>}
                     <span style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{plan.name}</span>
                     <div className="tier-price">${plan.price}<span style={{fontSize: '16px', color: 'var(--text-tertiary)', fontWeight: 500}}>/mo</span></div>
                     
                     <div style={{ flex: 1 }}>
                       <div style={{ fontSize: '15px', fontWeight: 600, marginBottom: '16px', color: 'var(--text-primary)' }}>{plan.reqs} requests/mo</div>
                       <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                         {plan.features.map((f, i) => (
                           <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '14px' }}>
                             <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green)" strokeWidth="3"><polyline points="20 6 9 17 4 12"/></svg>
                             {f}
                           </li>
                         ))}
                       </ul>
                     </div>

                     {subscription?.tier !== plan.name && (
                       <button onClick={() => handleUpgradeSubscription(plan.name)} className="btn-bento" style={{ marginTop: '32px', width: '100%' }}>
                         Select {plan.name.charAt(0).toUpperCase() + plan.name.slice(1)}
                       </button>
                     )}
                  </div>
                ))}
            </div>
          )}

        </main>
      </SignedIn>
    </div>
  );
}

export default App;
