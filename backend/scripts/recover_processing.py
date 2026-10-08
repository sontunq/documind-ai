"""Run only after stopping every backend instance using this database."""
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.db.processing import SQLProcessingRepository

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--backend-stopped", action="store_true", required=True,
                    help="Confirm all backend instances are stopped; active jobs must not be recovered")

if __name__ == "__main__":
    parser.parse_args()
    engine = create_engine(Settings().database_url.get_secret_value())
    with Session(engine) as session:
        print(f"Marked {SQLProcessingRepository(session).recover_interrupted()} interrupted runs FAILED; manual retry is available.")
    engine.dispose()
