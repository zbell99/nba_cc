from pathlib import Path
import pandas as pd
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
    WPA_PATH = PROJECT_ROOT / "data" / "wpa_challenge_values_sim.parquet"
    
    #1 - read the wpa json payload
    data = pd.read_parquet(WPA_PATH)

    #2 - round down time elapsed
    time = (payload.time_elapsed // 45) * 45

    #3 - based on game state, 
    values = data[(data["line"] == int(payload.spread)) & (data["gt"] == time) & (data["m"] == payload.score_margin)].iloc[0]
    breakeven_save1 = (values["ev1"] / values[payload.challenge_type]) * 100
    breakeven_save2 = (values["ev2"] / (values[payload.challenge_type] + values["ev1"])) * 100
    return {
        "wpa": round(values[payload.challenge_type] * 100, 1),
        "breakeven_save1": round(breakeven_save1),
        "breakeven_save2": round(breakeven_save2),
    }    