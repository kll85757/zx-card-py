from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .db import get_db
from .models import Card
from .schemas import CardOut, SearchBody, SearchResp

router = APIRouter()


@router.get("/cards/{card_id}", response_model=CardOut)
def get_card(card_id: int, db: Session = Depends(get_db)):
    obj = db.query(Card).get(card_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return obj


@router.post("/cards/search", response_model=SearchResp)
def search_cards(body: SearchBody, db: Session = Depends(get_db)):
    # MVP: simple SQL fallback; Meilisearch will be added in next step
    q = db.query(Card)
    if body.keyword:
        kw = f"%{body.keyword}%"
        q = q.filter(
            (Card.cn_name.like(kw)) | (Card.jp_name.like(kw)) | (Card.card_number.like(kw))
        )
    if body.colors:
        q = q.filter(Card.color.in_(body.colors))
    if body.rarities:
        q = q.filter(Card.rarity.in_(body.rarities))
    if body.types:
        q = q.filter(Card.type.in_(body.types))
    if body.series:
        q = q.filter(Card.series.in_(body.series))

    page_size = min(max(body.page_size or 50, 1), 200)
    items = q.limit(page_size).all()
    return {"items": items, "next_cursor": None}


