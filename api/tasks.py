from sqlalchemy.orm import Session
from .config import settings
from .db import SessionLocal
from .models import Card
from .search import ensure_index, index_cards

try:
    from celery import Celery
except Exception:  # pragma: no cover
    Celery = None  # type: ignore


if getattr(settings, "redis_disabled", False) or Celery is None:
    celery_app = None
else:
    celery_app = Celery("zxcard", broker=settings.redis_url, backend=settings.redis_url)


def reindex_all():
    ensure_index()
    db: Session = SessionLocal()
    try:
        batch = 1000
        offset = 0
        while True:
            rows = (
                db.query(Card)
                .order_by(Card.id)
                .offset(offset)
                .limit(batch)
                .all()
            )
            if not rows:
                break
            docs = [
                {
                    "id": r.id,
                    "color": r.color,
                    "card_number": r.card_number,
                    "series": r.series,
                    "rarity": r.rarity,
                    "type": r.type,
                    "jp_name": r.jp_name,
                    "cn_name": r.cn_name,
                    "cost": r.cost,
                    "power": r.power,
                    "race": r.race,
                    "note": r.note,
                    "text_full": r.text_full,
                    "image_url": r.image_url,
                    "detail_url": r.detail_url,
                }
                for r in rows
            ]
            index_cards(docs)
            offset += batch
    finally:
        db.close()


