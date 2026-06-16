"""Seed the demo user accounts for the contract_verify API.

Creates three accounts (operator / attorney / admin) in the JSON user store at
``USERS_DB_PATH`` (default ``./var/users.json``), with bcrypt-hashed passwords.
Run from the repo root:

    python backend/scripts/seed_demo.py            # create/update demo users
    python backend/scripts/seed_demo.py --reset    # wipe the store first

Requires backend/requirements-3month.txt (passlib[bcrypt]).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.auth_store import DEMO_USERS, seed_demo_users  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed contract_verify demo accounts.")
    parser.add_argument("--reset", action="store_true", help="clear existing users first")
    args = parser.parse_args()

    users = seed_demo_users(reset=args.reset)
    print(f"Seeded {len(users)} demo accounts:")
    print(f"{'username':<12} {'password':<14} role")
    print("-" * 34)
    for u in DEMO_USERS:
        print(f"{u['username']:<12} {u['password']:<14} {u['role']}")
    print("\nLog in at the SPA (http://localhost:5173) with any of the above.")


if __name__ == "__main__":
    main()
