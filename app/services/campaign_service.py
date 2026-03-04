# app/services/campaign_service.py
import pandas as pd
import chardet
import io
from fastapi import UploadFile, HTTPException

MAX_CSV_BYTES = 50 * 1024 * 1024  # 50MB


async def parse_csv(file: UploadFile) -> list[dict]:
    contents = await file.read()
    if len(contents) > MAX_CSV_BYTES:
        raise HTTPException(413, "CSV exceeds 50MB limit")

    encoding = chardet.detect(contents)["encoding"] or "utf-8"
    df = pd.read_csv(io.BytesIO(contents), encoding=encoding, dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "phone_number" not in df.columns:
        raise HTTPException(422, "CSV must contain a 'phone_number' column")

    df = df.dropna(subset=["phone_number"])
    invalid = df[~df["phone_number"].str.match(r"^\+[1-9]\d{7,14}$")]
    if not invalid.empty:
        raise HTTPException(
            422,
            f"{len(invalid)} rows have invalid phone numbers (must be E.164 format e.g. +12025551234)",
        )

    return df.fillna("").to_dict("records")
