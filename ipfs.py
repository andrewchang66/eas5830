import json
import requests

# ---- Pinata Configuration ----
PINATA_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySW5mb3JtYXRpb24iOnsiaWQiOiJjZjNjOTA0Ny04YjY2LTRiOWQtYTVlYS1iOTBkMmExZjcyMWMiLCJlbWFpbCI6ImFuZHJldy5jaGFuZ3RpbmdrYW5nQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJwaW5fcG9saWN5Ijp7InJlZ2lvbnMiOlt7ImRlc2lyZWRSZXBsaWNhdGlvbkNvdW50IjoxLCJpZCI6IkZSQTEifSx7ImRlc2lyZWRSZXBsaWNhdGlvbkNvdW50IjoxLCJpZCI6Ik5ZQzEifV0sInZlcnNpb24iOjF9LCJtZmFfZW5hYmxlZCI6ZmFsc2UsInN0YXR1cyI6IkFDVElWRSJ9LCJhdXRoZW50aWNhdGlvblR5cGUiOiJzY29wZWRLZXkiLCJzY29wZWRLZXlLZXkiOiJjMzE5YmRhNGMxMDY1ZTVmYzU3YSIsInNjb3BlZEtleVNlY3JldCI6ImI0NGJkNzRiODkzNmMzZmRlOTkxY2Q3OTNmZDJiNDIyYjU1ZTNhODU5MTkxY2YzZGI0ZTU1MmM4YzY1ZGMxMjIiLCJleHAiOjE3OTIyOTgyMzd9.5bAVGfK7HY6iv7gvIidowkDcMi7mfvataYuhiCfrCZ8"
PINATA_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
PINATA_GATEWAY_BASE = "https://gateway.pinata.cloud/ipfs/"

def pin_to_ipfs(data: dict) -> str:
    """Pin a Python dict to IPFS using Pinata. Returns the CID string."""
    assert isinstance(data, dict), "Error pin_to_ipfs expects a dictionary"
    headers = {
        "Authorization": f"Bearer {PINATA_JWT}",
        "Content-Type": "application/json",
    }
    resp = requests.post(PINATA_PIN_JSON_URL, headers=headers, json=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    cid = result.get("IpfsHash")
    if not cid:
        raise RuntimeError(f"Unexpected Pinata response: {result}")
    return cid

def get_from_ipfs(cid: str, content_type: str = "json") -> dict:
    """Retrieve JSON content from Pinata's public gateway for the given CID."""
    assert isinstance(cid, str), "get_from_ipfs accepts a cid in the form of a string"
    url = PINATA_GATEWAY_BASE + cid
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()  # assumes valid JSON
    assert isinstance(data, dict), "get_from_ipfs should return a dict"
    return data
