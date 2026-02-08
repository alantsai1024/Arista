#!/usr/bin/env python3
"""
Deprecated: this project no longer uses fake 30-device seeding as main validation flow.
"""
import sys


def main() -> int:
    print("seed_30_devices.py is deprecated.")
    print("Use real vEOS bootstrap instead:")
    print("  docker compose exec backend python scripts/bootstrap_real_veos.py")
    print("or")
    print("  cd backend && python scripts/bootstrap_real_veos.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
