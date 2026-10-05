import argparse
import json
import random
import string
import sys
import time
from pathlib import Path

import requests

ROBLOX_VALIDATE_URL = "https://auth.roblox.com/v2/usernames/validate"

LETTER_POOL = string.ascii_letters
CHAR_POOL = string.ascii_letters + string.digits


def random_username(kind: str) -> str:
    """Create a random username for the requested format."""
    if kind == "4L":
        return "".join(random.choice(LETTER_POOL) for _ in range(4))
    if kind == "4C":
        return "".join(random.choice(CHAR_POOL) for _ in range(4))
    if kind == "5L":
        return "".join(random.choice(LETTER_POOL) for _ in range(5))
    if kind == "5C":
        return "".join(random.choice(CHAR_POOL) for _ in range(5))
    raise ValueError(f"Unsupported username kind: {kind}")


def validate_username(username: str):
    """Check availability using Roblox's username validate API."""
    try:
        response = requests.post(
            ROBLOX_VALIDATE_URL,
            headers={"Content-Type": "application/json"},
            json={"username": username},
            timeout=15,
        )

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        message = str(payload.get("message", "")).lower()
        code = payload.get("code")

        if response.status_code == 200 and "valid" in message:
            return True, "available"

        if "already in use" in message or "taken" in message or "in use" in message:
            return False, "taken"
        if "invalid" in message or "reserved" in message or "too short" in message or "too long" in message:
            return False, "invalid"
        if "valid" in message:
            return True, "available"
        if response.status_code == 200:
            return True, "likely available"

        return False, f"status={response.status_code} message={message or 'unknown'}"
    except requests.RequestException as exc:
        return False, f"request_error: {exc}"


def generate_available_usernames(kind: str, count: int, delay: float = 0.25, max_attempts: int = 5000):
    """Return a list of available usernames for the requested pattern."""
    results = []
    seen = set()

    for attempt in range(1, max_attempts + 1):
        username = random_username(kind)
        if username in seen:
            continue
        seen.add(username)

        available, reason = validate_username(username)
        if available:
            results.append(username)
            print(f"[✓] {kind}: {username}")
            if len(results) >= count:
                break

        time.sleep(delay)

    if len(results) < count:
        print(f"Warning: found only {len(results)} available {kind} usernames before reaching max attempts.")

    return results


def parse_args():
    parser = argparse.ArgumentParser(description="Generate and check Roblox usernames by category.")
    parser.add_argument("--kind", choices=["4L", "4C", "5L", "5C", "all"], default="all", help="Username pattern to check")
    parser.add_argument("--count", type=int, default=5, help="Number of available usernames to find per category")
    parser.add_argument("--delay", type=float, default=0.25, help="Wait time between checks in seconds")
    parser.add_argument("--save", type=str, default="available_usernames.json", help="Output file path to save results")
    return parser.parse_args()


def main():
    args = parse_args()
    kinds = ["4L", "4C", "5L", "5C"] if args.kind == "all" else [args.kind]

    combined = {}

    print("=" * 50)
    print("ROBLOX USERNAME AVAILABILITY CHECKER")
    print("=" * 50)
    print()

    for kind in kinds:
        print(f"🔍 Searching for {kind} usernames...")
        found = generate_available_usernames(kind, args.count, delay=args.delay)
        combined[kind] = found
        print()

    print("=" * 50)
    print("RESULTS")
    print("=" * 50)
    for kind in kinds:
        names = combined.get(kind, [])
        print(f"{kind}: {names}")
    print()

    # Auto-save to JSON
    output_path = Path(args.save)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)
    print(f"✅ Results saved to {output_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user.")
        sys.exit(0)
