from pathlib import Path
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import logging
import pickle
import uuid

from src.schemas.schemas import GameStateInput

#PRODUCT VERSION
PRODUCT_VERSION = "0.0.0"

app = FastAPI(title="NBA Draft Optimizer API", version=PRODUCT_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


#API endpoints

@app.get("/health")
def health_check():
    return {"status": "ok"}

#change to get
@app.post("/challenge")
async def initialize_draft(payload: GameStateInput) -> dict:

    #-- Paths ────────────────────────────────────────────────────────────────────
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    WPA_PATH = PROJECT_ROOT / "data" / "wpa_challenge_values.json"
    
    #1 - read the wpa json payload
    with open(WPA_PATH, "r") as f:
        data = json.load(f)

    #2 - based on game state, 
    values = data[str(int(payload.spread))][str(payload.time_elapsed)][str(payload.score_margin)][payload.challenge_type]
    breakeven_save1 = 0 #values["ev1"] / values["wpa"]
    breakeven_save2 = 0 #values["ev2"] / values["wpa"]
    return {"wpa": values["wpa"], "breakeven_save1": breakeven_save1, "breakeven_save2": breakeven_save2}
    