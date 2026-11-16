"""
Maintenance commands. The API already runs these on a timer, but you can also run them by hand or from a scheduler (cron).

    python jobs.py expire-subscriptions     end Premium plans whose time is up
"""
import sys

from database import SessionLocal
from services.payments.fulfillment import expire_due_subscriptions

if __name__ == "__main__":
    if sys.argv[1:] == ["expire-subscriptions"]:
        with SessionLocal() as db:
            print(f"Expired {expire_due_subscriptions(db)} subscription(s).")
    else:
        sys.exit(__doc__)
