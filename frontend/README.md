# NBA Challenge Calculator — Frontend

A lightweight React UI for evaluating the expected value of an NBA coach's challenge in real time.

## Purpose

During an NBA game, coaches have a limited number of challenges they can use to contest referee calls. This tool helps answer the question: **"Is it worth using a challenge right now?"**

Given the current game state, the UI calls a backend API that returns:

- **WPA (Win Probability Added)** — how much win probability swings if the challenge succeeds.
- **Breakeven Save 1 / Save 2** — the minimum success probability needed for the challenge to be +EV, factoring in the value of saving the challenge for later.

## Inputs

| Field | Description |
|-------|-------------|
| **Spread** | Pre-game point spread (half-point increments) |
| **Period** | Current game period (1–10, accounting for OT) |
| **Minute / Second** | Time remaining in the current period |
| **Score Margin** | Current point differential (positive = leading) |
| **Challenge Type** | The type of call being challenged (e.g. out-of-bounds, no-foul, goaltending, and-one) |

## Tech Stack

- **React + TypeScript** via Vite
- Calls a **FastAPI** backend (`POST /challenge`) running on `localhost:8000`

## Running

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173`. Make sure the FastAPI backend is running separately.
