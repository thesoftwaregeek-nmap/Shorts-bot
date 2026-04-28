"""
License Key Generator — run this PRIVATELY to create keys
Usage: python keygen.py
"""

import hashlib, secrets, base64, json, datetime, os

SECRET_SALT = "SHORTS_BOT_FYP_2024_PRIVATE_SALT"


def generate_key(expiry_days: int = 30):
    expiry = (datetime.date.today() + datetime.timedelta(days=expiry_days)).isoformat()
    token = secrets.token_hex(8).upper()
    payload = f"{token}|{expiry}"
    checksum = hashlib.sha256(f"{payload}{SECRET_SALT}".encode()).hexdigest()[:8].upper()
    raw = f"{payload}|{checksum}"
    encoded = base64.b64encode(raw.encode()).decode().replace("=", "").upper()[:20].ljust(20, "A")
    key = "-".join([encoded[i:i+5] for i in range(0, 20, 5)])
    return key, expiry, token


def main():
    print("=" * 45)
    print("  SHORTS BOT — Key Generator")
    print("=" * 45)

    label = input("Who is this key for? ").strip()
    print("\n1. 7 days\n2. 30 days\n3. 90 days\n4. 180 days\n5. 365 days\n6. Custom")
    choice = input("Choose [1-6]: ").strip()
    days = {"1":7,"2":30,"3":90,"4":180,"5":365}.get(choice)
    if not days:
        days = int(input("Days: "))

    key, expiry, token = generate_key(days)

    log = []
    if os.path.exists("generated_keys.json"):
        with open("generated_keys.json") as f:
            log = json.load(f)
    log.append({"key": key, "for": label, "expiry": expiry, "token": token, "created": datetime.date.today().isoformat()})
    with open("generated_keys.json", "w") as f:
        json.dump(log, f, indent=2)

    print(f"\n{'='*45}")
    print(f"  KEY:    {key}")
    print(f"  FOR:    {label}")
    print(f"  EXPIRY: {expiry} ({days} days)")
    print(f"{'='*45}")
    print("Send this key to the person. Saved in generated_keys.json")


if __name__ == "__main__":
    main()
