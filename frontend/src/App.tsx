import { useState, type ChangeEvent, type SubmitEvent } from "react";
import "./App.css";

const CHALLENGE_TYPES = [
  "oob_challenge",
  "nofoul2_keepBall",
  "nofoul2_jumpBall",
  "nofoul2_loseBall",
  "nofoul3_keepBall",
  "nofoul3_jumpBall",
  "nofoul3_loseBall",
  "nogoaltend",
  "noand1",
] as const;

type ChallengeType = (typeof CHALLENGE_TYPES)[number];

interface GameForm {
  spread: string;
  period: string;
  minute: string;
  second: string;
  score_margin: string;
  challenge_type: ChallengeType;
}

interface ChallengeResult {
  wpa: number;
  breakeven_save1: number;
  breakeven_save2: number;
}

const API_URL = "http://localhost:8000";

function App() {
  const [form, setForm] = useState<GameForm>({
    spread: "",
    period: "",
    minute: "",
    second: "",
    score_margin: "",
    challenge_type: CHALLENGE_TYPES[0],
  });

  const [result, setResult] = useState<ChallengeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (
    e: ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_URL}/challenge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          spread: Number(form.spread) || 0,
          period: Number(form.period) || 1,
          minute: Number(form.minute) || 0,
          second: Number(form.second) || 0,
          score_margin: Number(form.score_margin) || 0,
          challenge_type: form.challenge_type,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="shell">
      <h1>NBA Challenge Calculator</h1>

      <div className="layout">
        {/* ── Left: Form ── */}
        <form onSubmit={handleSubmit} className="form">
        <div className="field">
          <label htmlFor="spread">Spread</label>
          <input
            id="spread"
            name="spread"
            type="number"
            step="0.5"
            placeholder="e.g. -3.5"
            value={form.spread}
            onChange={handleChange}
          />
        </div>

        <div className="field">
          <label htmlFor="period">Period</label>
          <input
            id="period"
            name="period"
            type="number"
            min={1}
            max={10}
            placeholder="1-4, 5 for OT"
            value={form.period}
            onChange={handleChange}
          />
        </div>

        <div className="row">
          <div className="field">
            <label htmlFor="minute">Minute</label>
            <input
              id="minute"
              name="minute"
              type="number"
              min={0}
              max={12}
              placeholder="0-12"
              value={form.minute}
              onChange={handleChange}
            />
          </div>

          <div className="field">
            <label htmlFor="second">Second</label>
            <input
              id="second"
              name="second"
              type="number"
              min={0}
              max={60}
              step="1"
              placeholder="0-60"
              value={form.second}
              onChange={handleChange}
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="score_margin">Score Margin</label>
          <input
            id="score_margin"
            name="score_margin"
            type="number"
            placeholder="e.g. -5"
            value={form.score_margin}
            onChange={handleChange}
          />
        </div>

        <div className="field">
          <label htmlFor="challenge_type">Challenge Type</label>
          <select
            id="challenge_type"
            name="challenge_type"
            value={form.challenge_type}
            onChange={handleChange}
          >
            {CHALLENGE_TYPES.map((ct) => (
              <option key={ct} value={ct}>
                {ct}
              </option>
            ))}
          </select>
        </div>

        <button type="submit" className="submit-btn" disabled={loading}>
          {loading ? "Loading…" : "Get Challenge Value"}
        </button>
      </form>

        {/* ── Right: Results ── */}
        <div className="right-panel">
          {error && <div className="error">Error: {error}</div>}

          {result ? (
            <div className="results">
              <h2>Results</h2>
              <table>
                <tbody>
                  <tr>
                    <td className="label">WPA</td>
                    <td>{result.wpa}</td>
                  </tr>
                  <tr>
                    <td className="label">Breakeven Save 1</td>
                    <td>{result.breakeven_save1}</td>
                  </tr>
                  <tr>
                    <td className="label">Breakeven Save 2</td>
                    <td>{result.breakeven_save2}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="placeholder">
              Submit a game state to see results
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
