import csv
from sqlalchemy.orm import Session
from .models import Card


def normalize_int(value: str) -> str:
    v = (value or "").strip()
    if v in ("-", "", "—"):
        return ""
    return v


def import_csv(path: str, db: Session) -> int:
    count = 0
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            obj = Card(
                color=row.get("color") or "",
                card_number=row.get("card_number") or "",
                series=row.get("series") or "",
                rarity=row.get("rarity") or "",
                type=row.get("type") or "",
                jp_name=row.get("jp_name") or "",
                cn_name=row.get("cn_name") or "",
                cost=normalize_int(row.get("cost")),
                power=normalize_int(row.get("power")),
                race=row.get("race") or "",
                note=row.get("note") or "",
                text_full=row.get("text_full") or "",
                image_url=row.get("image_url") or "",
                detail_url=row.get("detail_url") or "",
            )
            db.add(obj)
            count += 1
            if count % 1000 == 0:
                db.commit()
        db.commit()
    return count


