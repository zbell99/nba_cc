"""
NBA Challenge Calculator – NiceGUI frontend.

Run:
    python -m src.ui          (from project root)
    python src/ui.py          (also works)
"""

from pathlib import Path
import sys
import httpx

# Ensure project root is on sys.path so `src.*` imports work
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from nicegui import ui

API_URL = "http://localhost:8000"

CHALLENGE_TYPES = [
    "oob_challenge",
    "nofoul2_keepBall",
    "nofoul2_jumpBall",
    "nofoul2_loseBall",
    "nofoul3_keepBall",
    "nofoul3_jumpBall",
    "nofoul3_loseBall",
    "nogoaltend",
    "noand1",
]

# ── Custom CSS (replicates the React dark-brown / orange theme) ─────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after {
    box-sizing: border-box;
}

body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    line-height: 1.6;
    color-scheme: dark;
    color: #f5ebe0;
    background:
        radial-gradient(ellipse at 30% 20%, rgba(200,80,20,0.06) 0%, transparent 60%),
        radial-gradient(ellipse at 70% 80%, rgba(200,80,20,0.04) 0%, transparent 60%),
        #1a120b !important;
    font-synthesis: none;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* NiceGUI resets */
.nicegui-content {
    padding: 0 !important;
}
.q-page {
    background: transparent !important;
    min-height: auto !important;
}

/* ── Shell ── */
.shell {
    width: 100%;
    max-width: 780px;
    padding: 1.5rem 2rem 1.25rem;
    background: #231710;
    border: 1px solid #3a2518;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5),
                inset 0 1px 0 rgba(255,255,255,0.03);
    margin: 1rem auto;
}

/* ── Title ── */
.app-title {
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    text-align: center;
    margin-bottom: 1.25rem;
    color: #f5ebe0;
}
.app-title::after {
    content: '';
    display: block;
    width: 48px;
    height: 3px;
    margin: 0.6rem auto 0;
    border-radius: 2px;
    background: linear-gradient(90deg, #e85d04, #f48c06);
}

/* ── Layout columns ── */
.layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    align-items: start;
}
@media (max-width: 640px) {
    .layout { grid-template-columns: 1fr; }
}

/* ── Form ── */
.form-col {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
}

/* field wrapper */
.field {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    flex: 1;
}
.field-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #b8977a;
}

/* input / select styling through Quasar overrides */
.dark-input {
    width: 100%;
}
.dark-input .q-field__control {
    background: #2c1b10 !important;
    border: 1px solid #3a2518;
    border-radius: 8px;
    color: #f5ebe0 !important;
    height: 36px !important;
    min-height: 36px !important;
    max-height: 36px !important;
    padding: 0 0.75rem !important;
}
.dark-input .q-field__control:before {
    border: none !important;
}
.dark-input .q-field__control:after {
    border: none !important;
}
.dark-input .q-field__native,
.dark-input .q-field__input,
.dark-input .q-select__dropdown-icon {
    color: #f5ebe0 !important;
}
.dark-input .q-field__native,
.dark-input .q-field__input {
    padding: 0 !important;
    min-height: 0 !important;
    font-size: 0.95rem;
}
.dark-input .q-field__control:focus-within {
    border-color: #e85d04 !important;
    box-shadow: 0 0 0 3px rgba(232,93,4,0.2);
}
.dark-input .q-field__bottom {
    display: none !important;
    min-height: 0 !important;
    padding: 0 !important;
}
.dark-input .q-field__label {
    display: none !important;
}
.dark-input .q-field__marginal {
    color: #b8977a !important;
    height: 36px !important;
}
.dark-input .q-field--dense .q-field__control {
    height: 36px !important;
    min-height: 36px !important;
}

/* time row */
.time-row {
    display: flex;
    gap: 1rem;
}

/* ── Button ── */
.submit-btn {
    margin-top: 0.5rem;
    padding: 0.55rem;
    background: linear-gradient(135deg, #e85d04, #f48c06) !important;
    color: #fff !important;
    border: none;
    border-radius: 8px !important;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    text-transform: none !important;
    letter-spacing: 0;
    width: 100%;
}
.submit-btn:hover { opacity: 0.9; }
.submit-btn .q-btn__content { justify-content: center; }

/* ── Right panel ── */
.right-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

/* placeholder */
.placeholder {
    padding: 2rem 1rem;
    text-align: center;
    color: #7a6252;
    font-size: 0.9rem;
    border: 1px dashed #3a2518;
    border-radius: 12px;
}

/* ── Error ── */
.error-box {
    margin-top: 1rem;
    padding: 0.7rem 0.85rem;
    background: rgba(220,38,38,0.12);
    border: 1px solid rgba(220,38,38,0.35);
    color: #fca5a5;
    border-radius: 8px;
    font-size: 0.85rem;
}

/* ── Results ── */
.results-card {
    padding: 1.25rem;
    background: #2c1b10;
    border: 1px solid #3a2518;
    border-radius: 12px;
}
.results-title {
    margin: 0 0 0.85rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: #f48c06;
}
.results-table {
    width: 100%;
    border-collapse: collapse;
}
.results-table tr + tr {
    border-top: 1px solid #3a2518;
}
.results-table td {
    padding: 0.55rem 0;
    font-size: 0.9rem;
}
.results-table td.label {
    font-weight: 500;
    color: #b8977a;
    width: 55%;
}
.results-table td:last-child {
    text-align: right;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: #f5ebe0;
}

/* Quasar select popup dark theme */
.q-menu {
    background: #2c1b10 !important;
    border: 1px solid #3a2518;
    border-radius: 8px !important;
}
.q-item {
    color: #f5ebe0 !important;
    min-height: 36px !important;
}
.q-item--active, .q-item:hover {
    background: rgba(232,93,4,0.15) !important;
}
"""


# ── Build the page ──────────────────────────────────────────────────────────────
@ui.page("/")
def index():
    # Inject custom CSS
    ui.add_css(CUSTOM_CSS)

    # Reactive state
    spread = {"value": 0.0}
    period = {"value": 1}
    minute = {"value": 12}
    second = {"value": 0}
    score_margin = {"value": 0}
    challenge_type = {"value": CHALLENGE_TYPES[0]}

    # Containers we'll update
    result_container = None
    error_container = None
    placeholder_container = None

    async def compute():
        nonlocal result_container, error_container, placeholder_container
        # Clear previous
        results_panel.clear()

        try:
            payload = {
                "spread": float(spread["value"] or 0),
                "period": int(period["value"] or 1),
                "minute": int(minute["value"] or 0),
                "second": int(second['value'] or 0),
                "score_margin": int(score_margin["value"] or 0),
                "challenge_type": challenge_type["value"],
            }

            async with httpx.AsyncClient() as client:
                res = await client.post(f"{API_URL}/challenge", json=payload)
                res.raise_for_status()
                data = res.json()

            with results_panel:
                with ui.element("div").classes("results-card"):
                    ui.html('<h2 class="results-title">Results</h2>')
                    ui.html(f"""
                        <table class="results-table">
                            <tbody>
                                <tr>
                                    <td class="label">Value of Successful Challenge</td>
                                    <td>{data["wpa"]}%</td>
                                </tr>
                                <tr>
                                    <td class="label">Breakeven Confidence (1 Challenge Rem.)</td>
                                    <td>{"NOT WORTH A CHALLENGE" if data["breakeven_save1"] > 100 else f'{data["breakeven_save1"]}%'} </td>
                                </tr>
                                <tr>
                                    <td class="label">Breakeven Confidence (2 Challenges Rem.)</td>
                                    <td>{"NOT WORTH A CHALLENGE" if data["breakeven_save2"] > 100 else f'{data["breakeven_save2"]}%'} </td>
                                </tr>
                            </tbody>
                        </table>
                    """)

        except Exception as exc:
            with results_panel:
                ui.html(f'<div class="error-box">Error: {exc}</div>')

    # ── UI tree ──
    with ui.element("div").classes("shell"):
        ui.html('<h1 class="app-title">NBA Challenge Calculator</h1>')

        with ui.element("div").classes("layout"):
            # ── Left: Form ──
            with ui.element("div").classes("form-col"):

                # Spread
                with ui.element("div").classes("field"):
                    ui.html('<span class="field-label">SPREAD</span>')
                    ui.number(label="", value=None, format="%.1f",
                              placeholder="e.g. -3.5", step=0.5).classes("dark-input").on(
                        "update:model-value", lambda e: spread.update({"value": e.args})
                    )

                # Period
                with ui.element("div").classes("field"):
                    ui.html('<span class="field-label">PERIOD</span>')
                    ui.number(label="", value=None,
                              placeholder="1-4, 5 for OT", min=1, max=10, step=1).classes("dark-input").on(
                        "update:model-value", lambda e: period.update({"value": e.args})
                    )

                # Minute / Second row
                with ui.element("div").classes("time-row"):
                    with ui.element("div").classes("field"):
                        ui.html('<span class="field-label">MINUTES</span>')
                        ui.number(label="", value=None,
                                  placeholder="0-12", min=0, max=12, step=1).classes("dark-input").on(
                            "update:model-value", lambda e: minute.update({"value": e.args})
                        )
                    with ui.element("div").classes("field"):
                        ui.html('<span class="field-label">SECONDS</span>')
                        ui.number(label="", value=None,
                                  placeholder="0-60", min=0, max=60, step=1).classes("dark-input").on(
                            "update:model-value", lambda e: second.update({"value": e.args})
                        )

                # Score Margin
                with ui.element("div").classes("field"):
                    ui.html('<span class="field-label">SCORE MARGIN</span>')
                    ui.number(label="", value=None,
                              placeholder="e.g. -5", step=1).classes("dark-input").on(
                        "update:model-value", lambda e: score_margin.update({"value": e.args})
                    )

                # Challenge Type
                with ui.element("div").classes("field"):
                    ui.html('<span class="field-label">CHALLENGE TYPE</span>')
                    challenge_select = ui.select(options=CHALLENGE_TYPES, value=CHALLENGE_TYPES[0]).classes("dark-input")
                    challenge_select.on(
                        "update:model-value",
                        lambda e: challenge_type.update({"value": challenge_select.value}),
                    )

                # Submit
                ui.button("Get Challenge Value", on_click=compute).classes("submit-btn")

            # ── Right: Results ──
            results_panel = ui.element("div").classes("right-panel")
            with results_panel:
                ui.html('<div class="placeholder">Submit a game state to see results</div>')


# ── Entry point ─────────────────────────────────────────────────────────────────
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="NBA Challenge Calculator", port=8001)
