import argparse
from .db import Base, engine, SessionLocal
from .importer import import_csv
from .tasks import reindex_all, celery_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["initdb", "import", "reindex"])
    parser.add_argument("--csv", dest="csv_path")
    args = parser.parse_args()

    if args.cmd == "initdb":
        Base.metadata.create_all(bind=engine)
        print("DB initialized")
    elif args.cmd == "import":
        if not args.csv_path:
            raise SystemExit("--csv required")
        db = SessionLocal()
        try:
            n = import_csv(args.csv_path, db)
            print(f"Imported {n} rows")
        finally:
            db.close()
    elif args.cmd == "reindex":
        if celery_app is None:
            # synchronous fallback
            reindex_all()
            print("Reindex completed (sync fallback)")
        else:
            reindex_all.delay()
            print("Reindex task enqueued")


if __name__ == "__main__":
    main()


