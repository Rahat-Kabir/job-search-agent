"""Test Alembic migration pipeline."""

from dotenv import load_dotenv

load_dotenv()

from alembic import command
from alembic.config import Config

alembic_cfg = Config("alembic.ini")

# 1. Check current revision
print("=== Current revision ===")
command.current(alembic_cfg)

# 2. Run upgrade (should be no-op since we stamped head)
print("\n=== Running upgrade head ===")
command.upgrade(alembic_cfg, "head")
print("Upgrade completed successfully!")

# 3. Check history
print("\n=== Migration history ===")
command.history(alembic_cfg)

# 4. Verify autogenerate detects no drift
print("\n=== Checking for schema drift ===")
command.check(alembic_cfg)
print("No schema drift detected!")
