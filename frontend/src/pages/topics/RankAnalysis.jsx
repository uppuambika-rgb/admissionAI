import React, { useState } from 'react';
import { fetchRecommendations } from '../../services/api';

const CATEGORIES = ['General', 'OBC', 'SC', 'ST', 'EWS', 'General-PwD', 'OBC-PwD', 'SC-PwD', 'ST-PwD'];

const TIER_INFO = [
  { label: 'Aspirational', color: '#7c3aed', bg: '#faf5ff', border: '#e9d5ff', desc: 'Top institutes where admission is competitive. Worth trying!' },
  { label: 'Likely', color: '#1e40af', bg: '#eff6ff', border: '#bfdbfe', desc: 'Good chances of admission based on historical cutoffs.' },
  { label: 'Safe', color: '#065f46', bg: '#ecfdf5', border: '#a7f3d0', desc: 'High probability of admission. Solid backup choices.' },
];

export default function RankAnalysis() {
  const [rank, setRank] = useState('');
  const [category, setCategory] = useState('General');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyse = async () => {
    const parsedRank = parseInt(rank);
    if (!parsedRank || parsedRank <= 0) {
      setError('Please enter a valid rank.');
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const profile = {
        rank: parsedRank,
        category,
        academic_strengths: [],
        interests: [],
        career_goals: [],
        preferred_locations: [],
      };
      const data = await fetchRecommendations(profile);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to analyse rank. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const tierCounts = result?.tier_summary || null;

  return (
    <div className="topic-content">
      {/* Form */}
      <div className="predictor-form-card">
        <h3 className="predictor-form-title">📊 Analyse Your Rank</h3>
        <div className="predictor-form-row">
          <div className="predictor-field">
            <label htmlFor="ra-rank" className="predictor-label">Your Rank</label>
            <input
              id="ra-rank"
              type="number"
              className="predictor-input"
              placeholder="e.g. 5000"
              value={rank}
              onChange={(e) => setRank(e.target.value)}
              min="1"
              aria-label="Enter your rank"
            />
          </div>
          <div className="predictor-field">
            <label htmlFor="ra-category" className="predictor-label">Category</label>
            <select
              id="ra-category"
              className="predictor-input predictor-select"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              aria-label="Select category"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <button
            className="predictor-btn"
            onClick={handleAnalyse}
            disabled={loading}
            aria-label="Analyse rank"
          >
            {loading ? '⏳ Analysing...' : '📊 Analyse Rank'}
          </button>
        </div>
        {error && <div className="predictor-error" role="alert">⚠️ {error}</div>}
      </div>

      {/* Tier breakdown */}
      {result && (
        <div className="rank-analysis-results">
          <div className="rank-summary-card">
            <h3 className="rank-summary-title">
              Rank <span style={{ color: 'var(--primary)' }}>#{result.student_profile?.rank?.toLocaleString()}</span> — {result.student_profile?.category}
            </h3>
            <p className="rank-summary-sub">
              Based on historical cutoff data, here's how your rank stacks up across tiers.
            </p>
            <div className="tier-breakdown-grid" role="list">
              {TIER_INFO.map((t) => (
                <div
                  key={t.label}
                  className="tier-breakdown-card"
                  role="listitem"
                  style={{ background: t.bg, borderColor: t.border }}
                >
                  <div className="tier-bd-count" style={{ color: t.color }}>
                    {tierCounts?.[t.label] ?? 0}
                  </div>
                  <div className="tier-bd-label" style={{ color: t.color }}>{t.label}</div>
                  <div className="tier-bd-desc">{t.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rank-advice-card">
            <h4 className="rank-advice-title">💡 Strategy Advice</h4>
            <ul className="rank-advice-list">
              <li>Fill at least <strong>5 Safe</strong> choices to secure a seat.</li>
              <li>Add <strong>3–5 Likely</strong> choices matching your preferred branches.</li>
              <li>Include <strong>2–3 Aspirational</strong> picks — they sometimes open up in later rounds.</li>
              <li>Verify cutoffs via the official JoSAA / CSAB portal before submission.</li>
            </ul>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="topic-empty-state">
          <div className="topic-empty-icon">📊</div>
          <h3>Enter your rank above to see your analysis</h3>
          <p>We'll show you tier-wise college opportunities and a personalised strategy.</p>
        </div>
      )}
    </div>
  );
}
