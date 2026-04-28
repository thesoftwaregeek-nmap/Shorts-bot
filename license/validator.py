import hashlib
import base64
import json
import datetime
import os

SECRET_SALT = "SHORTS_BOT_FYP_2024_PRIVATE_SALT"
LICENSE_DB  = "data/licenses.json"

os.makedirs("data", exist_ok=True)


def _load_db() -> dict:
    if not os.path.exists(LICENSE_DB):
        return {}
    with open(LICENSE_DB) as f:
        return json.load(f)


def _save_db(db: dict):
    with open(LICENSE_DB, "w") as f:
        json.dump(db, f, indent=2)


def decode_key(key: str):
    try:
        flat = key.replace("-", "").upper()
        padded = flat + "=" * ((4 - len(flat) % 4) % 4)
        decoded = base64.b64decode(padded).decode()
        parts = decoded.split("|")
        if len(parts) != 3:
            return None
        random_token, expiry_date, checksum = parts
        payload = f"{random_token}|{expiry_date}"
        expected = hashlib.sha256(
            f"{payload}{SECRET_SALT}".encode()
        ).hexdigest()[:8].upper()
        if checksum != expected:
            return None
        return {"token": random_token, "expiry": expiry_date}
    except Exception:
        return None


def check_expiry(expiry_str: str):
    expiry = datetime.date.fromisoformat(expiry_str)
    days = (expiry - datetime.date.today()).days
    return days >= 0, days


def validate_license(key: str = None, session_id: str = None):
    db = _load_db()

    if session_id and not key:
        record = db.get(session_id)
        if not record:
            return False, "No license found."
        valid, days = check_expiry(record["expiry"])
        if not valid:
            return False, f"License expired on {record['expiry']}."
        return True, f"License valid — {days} day(s) remaining."

    if key:
        decoded = decode_key(key)
        if not decoded:
            return False, "Invalid license key. Please check and try again."
        valid, days = check_expiry(decoded["expiry"])
        if not valid:
            return False, f"This key expired on {decoded['expiry']}."
        used_by = [s for s, r in db.items() if r.get("token") == decoded["token"]]
        if len(used_by) >= 2:
            return False, "This key is already in use on another device."
        if session_id:
            db[session_id] = {
                "token": decoded["token"],
                "expiry": decoded["expiry"],
                "activated_at": datetime.date.today().isoformat()
            }
            _save_db(db)
        return True, f"Activated! License valid for {days} day(s)."

    return False, "No license key provided."
