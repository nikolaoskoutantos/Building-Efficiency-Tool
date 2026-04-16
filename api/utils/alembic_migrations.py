import subprocess

# --- Alembic migration auto-upgrade on startup ---
def run_alembic_upgrade():
    """Run Alembic upgrade head to apply all migrations."""
    try:
        result = subprocess.run([
            "alembic", "upgrade", "head"
        ], check=True, capture_output=True, text=True)
        print("[main.py] Alembic migration output:\n" + result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[main.py] Alembic migration failed: {e.stderr}")
        raise


def should_run_startup_migrations() -> bool:
    """
    Decide whether schema migrations should run during app startup.

    In development we default to enabled for convenience.
    In non-development environments we default to disabled so CI/CD can run
    migrations as a separate explicit step.
    """
    import os

    dev_mode = os.getenv("DEV", "false").lower() == "true"
    default_value = "true" if dev_mode else "false"
    raw_value = os.getenv("RUN_DB_MIGRATIONS_ON_STARTUP", default_value)
    return raw_value.lower() == "true"
