import requests
import json
import os

# ---- Configuration (Pinata) ----
PINATA_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
PINATA_GATEWAY_BASE = "https://gateway.pinata.cloud/ipfs/"

# Auth: prefer JWT if provided; otherwise API key + secret headers
PINATA_JWT = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySW5mb3JtYXRpb24iOnsiaWQiOiJjZjNjOTA0Ny04YjY2LTRiOWQtYTVlYS1iOTBkMmExZjcyMWMiLCJlbWFpbCI6ImFuZHJldy5jaGFuZ3RpbmdrYW5nQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJwaW5fcG9saWN5Ijp7InJlZ2lvbnMiOlt7ImRlc2lyZWRSZXBsaWNhdGlvbkNvdW50IjoxLCJpZCI6IkZSQTEifSx7ImRlc2lyZWRSZXBsaWNhdGlvbkNvdW50IjoxLCJpZCI6Ik5ZQzEifV0sInZlcnNpb24iOjF9LCJtZmFfZW5hYmxlZCI6ZmFsc2UsInN0YXR1cyI6IkFDVElWRSJ9LCJhdXRoZW50aWNhdGlvblR5cGUiOiJzY29wZWRLZXkiLCJzY29wZWRLZXlLZXkiOiJjMzE5YmRhNGMxMDY1ZTVmYzU3YSIsInNjb3BlZEtleVNlY3JldCI6ImI0NGJkNzRiODkzNmMzZmRlOTkxY2Q3OTNmZDJiNDIyYjU1ZTNhODU5MTkxY2YzZGI0ZTU1MmM4YzY1ZGMxMjIiLCJleHAiOjE3OTIyOTgyMzd9.5bAVGfK7HY6iv7gvIidowkDcMi7mfvataYuhiCfrCZ8")  # raw token (no 'Bearer ' prefix needed)
PINATA_API_KEY = os.environ.get("c319bda4c1065e5fc57a")
PINATA_SECRET_API_KEY = os.environ.get("b44bd74b8936c3fde991cd793fd2b422b55e3a859191cf3db4e552c8c65dc122")

def _pinata_headers(json_mode: bool = False) -> dict:
    """Build Pinata headers for either JWT or key/secret auth."""
    headers = {}
    if PINATA_JWT:
        headers["Authorization"] = f"Bearer {PINATA_JWT}"
        if json_mode:
            headers["Content-Type"] = "application/json"
        return headers
    if PINATA_API_KEY and PINATA_SECRET_API_KEY:
        headers["pinata_api_key"] = PINATA_API_KEY
        headers["pinata_secret_api_key"] = PINATA_SECRET_API_KEY
        if json_mode:
            headers["Content-Type"] = "application/json"
        return headers
    raise RuntimeError("Pinata credentials missing. Set PINATA_JWT or PINATA_API_KEY and PINATA_SECRET_API_KEY.")

def pin_to_ipfs(data: dict) -> str:
    """Pin a Python dict to IPFS using Pinata. Returns the CID string."""
    assert isinstance(data, dict), "Error pin_to_ipfs expects a dictionary"
    headers = _pinata_headers(json_mode=True)
    resp = requests.post(PINATA_PIN_JSON_URL, headers=headers, json=data, timeout=30)
    resp.raise_for_status()
    out = resp.json()
    cid = out.get("IpfsHash")
    if not cid:
        raise RuntimeError(f"Unexpected Pinata response: {out}")
    return cid

def get_from_ipfs(cid: str, content_type: str = "json") -> dict:
    """Retrieve JSON content from Pinata's public gateway for the given CID."""
    assert isinstance(cid, str), "get_from_ipfs accepts a cid in the form of a string"
    url = PINATA_GATEWAY_BASE + cid
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()  # assumes valid JSON per assignment
    assert isinstance(data, dict), "get_from_ipfs should return a dict"
    return data
