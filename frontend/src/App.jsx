import React, { useState, useEffect } from 'react';
import { SignedIn, SignedOut, SignIn, UserButton, useAuth, useUser } from '@clerk/clerk-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, CartesianGrid } from 'recharts';
import LandingPage from './LandingPage';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8001' : '/api';

function App() {
  const { getToken } = useAuth();
  const { user } = useUser();
  
  const [apiKey, setApiKey] = useState('');
  const [usage, setUsage] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [driftData, setDriftData] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [flaggedPreds, setFlaggedPreds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const [selectedModel, setSelectedModel] = useState('sentiment');
  const [playgroundResult, setPlaygroundResult] = useState(null);
  const [playgroundCode, setPlaygroundCode] = useState('python');

  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => { setError(null); setSuccess(null); }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, success]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      if (!token) return;
      const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

      const statsRes = await fetch(`${API_BASE}/billing/subscription`, { headers });
      const statsData = await statsRes.json();
      if (statsData.primary_color) document.documentElement.style.setProperty('--accent-blue', statsData.primary_color);
      setUsage(statsData);

      const driftRes = await fetch(`${API_BASE}/analytics/drift`, { headers });
      if (driftRes.ok) setDriftData(await driftRes.json());

      if (activeTab === 'audit') {
         const auditRes = await fetch(`${API_BASE}/admin/audit-logs`, { headers });
         if (auditRes.ok) setAuditLogs(await auditRes.json());
      }

      const predsRes = await fetch(`${API_BASE}/predictions?limit=20`, { headers });
      if (predsRes.ok) {
        const d = await predsRes.json();
        setPredictions(d.predictions || []);
        setFlaggedPreds(d.predictions?.filter(p => p.is_flagged) || []);
      }
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user) fetchDashboardData(); }, [user, activeTab]);

  const runLivePlayground = async (text) => {
    setLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/predict?text=${encodeURIComponent(text)}&model_type=${selectedModel}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setPlaygroundResult(await res.json());
    } catch (err) { setError("Playground execution failed."); } finally { setLoading(false); }
  };

  const handleRetrain = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/retrain`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
      const data = await res.json();
      setSuccess(`Zenith Retraining Complete: ${data.new_version}`);
      fetchDashboardData();
    } catch (err) { setError("Retrain failed."); } finally { setLoading(false); }
  };

  const handleLabel = async (id, label) => {
    try {
      const token = await getToken();
      await fetch(`${API_BASE}/predictions/${id}/label?human_label=${label}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setSuccess(`Human Ground Truth set for #${id}`);
      fetchDashboardData();
    } catch (err) { setError("Labeling failed."); }
  };

  return (
    <div className="app-container">
      <SignedOut><LandingPage /></SignedOut>

      <SignedIn>
        <aside className="sidebar">
          <div>
            <div className="brand" style={{background:'rgba(255,255,255,0.03)', padding:'15px', borderRadius:'12px', marginBottom:'24px', border:'1px solid var(--border-color)'}}>
              <div className="brand-icon" style={{width:32, height:32, background:'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))', borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center', fontWeight:800, color:'#fff'}}>Z</div>
              <div className="brand-text">
                <h1 style={{letterSpacing:'-1px'}}>ZENITH<span style={{color: 'var(--accent-blue)'}}> AI</span></h1>
                <p style={{fontSize:10, textTransform:'uppercase', letterSpacing:1}}>Enterprise ML Ops</p>
              </div>
            </div>

            <nav className="nav-menu">
              {['dashboard', 'predict', 'review', 'playground', 'audit', 'billing'].map(tab => (
                <button key={tab} className={`nav-item ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
                  <span style={{fontSize: 18}}>{tab === 'dashboard' ? '💎' : tab === 'predict' ? '🧠' : tab === 'review' ? '👁️' : tab === 'playground' ? '🧪' : tab === 'audit' ? '📜' : '💳'}</span>
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </nav>
          </div>

          <div className="sidebar-footer">
            <UserButton afterSignOutUrl="/" />
            <div style={{ marginLeft: 12 }}>
               <div style={{ fontSize: 13, fontWeight: 700 }}>{user?.firstName}</div>
               <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Zenith Architect</div>
            </div>
          </div>
        </aside>

        <main className="main-content">
          <div className="top-bar">
            <div className="top-bar-left">
               <h2 style={{fontSize:28, fontWeight:800}}>{activeTab.toUpperCase()}</h2>
               <p style={{color:'var(--text-tertiary)'}}>Full-Stack MLOps with Drift Analytics & Audit Trails</p>
            </div>
            <div className="top-bar-right">
              <span className="badge positive" style={{padding:'8px 16px', borderRadius:'8px'}}>{usage?.model_version || 'v1.0.0'} Stable</span>
              <button onClick={handleRetrain} disabled={loading} className="btn-zenith">
                {loading ? 'Optimizing...' : '🚀 Retrain Model'}
              </button>
            </div>
          </div>

          {activeTab === 'dashboard' && (
            <div className="bento-grid fade-in">
              {/* Drift Analytics Chart */}
              <div className="bento-card span-12" style={{minHeight: 300}}>
                 <div className="card-header"><span className="card-title">📉 Model Drift Analytics (24h Pulse)</span></div>
                 <div style={{height: 250, marginTop: 20}}>
                    <ResponsiveContainer width="100%" height="100%">
                       <LineChart data={driftData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="hour" tickFormatter={(t) => new Date(t).getHours() + ':00'} stroke="var(--text-tertiary)" fontSize={11} />
                          <YAxis domain={[0, 1]} stroke="var(--text-tertiary)" fontSize={11} />
                          <Tooltip contentStyle={{background:'#000', border:'none', borderRadius:12}} />
                          <Line type="monotone" dataKey="confidence" stroke="var(--accent-blue)" strokeWidth={3} dot={{r: 4, fill:'var(--accent-blue)'}} activeDot={{r: 8}} />
                       </LineChart>
                    </ResponsiveContainer>
                 </div>
              </div>

              <div className="bento-card span-4">
                 <span className="card-title">System Confidence</span>
                 <div className="metric-value">{((usage?.average_confidence || 0)*100).toFixed(1)}%</div>
                 <div className="metric-sub">Global average across tenants</div>
              </div>
              <div className="bento-card span-4">
                 <span className="card-title">Latency (P99)</span>
                 <div className="metric-value">{usage?.average_inference_time_ms?.toFixed(0)}ms</div>
                 <div className="metric-sub">Real-time BERT inference</div>
              </div>
              <div className="bento-card span-4">
                 <span className="card-title">HITL Queue</span>
                 <div className="metric-value">{flaggedPreds.length}</div>
                 <div className="metric-sub">Records awaiting review</div>
              </div>
            </div>
          )}

          {activeTab === 'predict' && (
             <div className="bento-grid fade-in">
                <div className="bento-card span-6">
                   <span className="card-title">Predictive Intelligence</span>
                   <div style={{display:'flex', gap: 12, margin: '20px 0'}}>
                      {['sentiment', 'toxicity'].map(m => <button key={m} className={`btn-bento ${selectedModel === m ? 'active-btn' : ''}`} onClick={() => setSelectedModel(m)}>{m.toUpperCase()}</button>)}
                   </div>
                   <form onSubmit={(e) => { e.preventDefault(); runLivePlayground(e.target.text.value); }}>
                      <textarea name="text" className="input-bento" rows="6" placeholder="Enter payload..." required />
                      <button type="submit" className="btn-bento" style={{marginTop: 16, background:'var(--accent-blue)', color:'#fff'}}>Execute</button>
                   </form>
                </div>
                <div className="bento-card span-6">
                   <span className="card-title">XAI & Caching Data</span>
                   {playgroundResult ? (
                      <div className="fade-in" style={{marginTop: 20}}>
                         <div style={{fontSize:24, fontWeight:800}}>{playgroundResult.prediction}</div>
                         <div style={{fontSize:14, color:'var(--text-secondary)', marginBottom:20}}>Confidence: {(playgroundResult.confidence*100).toFixed(1)}%</div>
                         <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
                            {playgroundResult.highlights?.map((h, i) => <span key={i} style={{background:'rgba(59,130,246,0.1)', color:'var(--accent-blue)', padding:'6px 12px', borderRadius:8, fontWeight:700, fontSize:12}}>{h}</span>)}
                         </div>
                         {playgroundResult.cached && <div style={{marginTop:20, color:'var(--accent-green)', fontWeight:700}}>⚡ Served via Redis Cache (0ms)</div>}
                         {playgroundResult.is_flagged && <div style={{marginTop:20, color:'var(--accent-red)'}}>⚠️ Auto-flagged for Human Review</div>}
                      </div>
                   ) : <div style={{textAlign:'center', padding:60, color:'var(--text-tertiary)'}}>Awaiting execution...</div>}
                </div>
             </div>
          )}

          {activeTab === 'audit' && (
             <div className="bento-grid fade-in">
                <div className="bento-card span-12">
                   <span className="card-title">Enterprise Audit Trail</span>
                   <div style={{marginTop: 20}}>
                      <table style={{width:'100%', borderCollapse:'collapse'}}>
                         <thead>
                            <tr style={{textAlign:'left', borderBottom:'1px solid var(--border-color)', color:'var(--text-tertiary)', fontSize:12}}>
                               <th style={{padding:12}}>ACTION</th>
                               <th style={{padding:12}}>DETAILS</th>
                               <th style={{padding:12}}>IP ADDRESS</th>
                               <th style={{padding:12}}>TIMESTAMP</th>
                            </tr>
                         </thead>
                         <tbody>
                            {auditLogs.map(log => (
                               <tr key={log.id} style={{borderBottom:'1px solid var(--border-color)', fontSize:13}}>
                                  <td style={{padding:12, fontWeight:700}}>{log.action}</td>
                                  <td style={{padding:12, color:'var(--text-secondary)'}}>{log.details}</td>
                                  <td style={{padding:12, color:'var(--text-tertiary)'}}>{log.ip_address}</td>
                                  <td style={{padding:12, color:'var(--text-tertiary)'}}>{new Date(log.timestamp).toLocaleString()}</td>
                               </tr>
                            ))}
                         </tbody>
                      </table>
                   </div>
                </div>
             </div>
          )}
        </main>
      </SignedIn>

      <style>{`
        .btn-zenith { background: linear-gradient(135deg, var(--accent-purple), #7c3aed); color: #fff; border: none; padding: 10px 24px; border-radius: 10px; font-weight: 700; cursor: pointer; transition: transform 0.2s; box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3); }
        .btn-zenith:hover { transform: scale(1.05); }
        .active-btn { border: 1px solid var(--accent-blue) !important; color: var(--accent-blue) !important; background: rgba(59,130,246,0.1) !important; }
        .btn-bento { border: 1px solid var(--border-color); background: transparent; color: var(--text-secondary); cursor: pointer; padding: 10px 20px; border-radius: 10px; font-weight: 600; transition: all 0.2s; }
        .btn-bento:hover { color: #fff; border-color: #777; }
        :root { --accent-blue: #3b82f6; --accent-purple: #8b5cf6; }
      `}</style>
    </div>
  );
}

export default App;
