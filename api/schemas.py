from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class CardOut(BaseModel):
    id: int
    color: Optional[str] = None
    card_number: Optional[str] = None
    series: Optional[str] = None
    rarity: Optional[str] = None
    type: Optional[str] = None
    jp_name: Optional[str] = None
    cn_name: Optional[str] = None
    cost: Optional[str] = None
    power: Optional[str] = None
    race: Optional[str] = None
    note: Optional[str] = None
    text_full: Optional[str] = None
    image_url: Optional[str] = None
    detail_url: Optional[str] = None

    class Config:
        from_attributes = True


class SearchBody(BaseModel):
    keyword: Optional[str] = None
    colors: Optional[List[str]] = None
    rarities: Optional[List[str]] = None
    types: Optional[List[str]] = None
    marks: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    series: Optional[List[str]] = None
    packs: Optional[List[str]] = None
    cost: Optional[Dict[str, Optional[int]]] = None
    power: Optional[Dict[str, Optional[int]]] = None
    sort: Optional[str] = None
    cursor: Optional[str] = None
    page_size: Optional[int] = 50


class SearchResp(BaseModel):
    items: List[CardOut]
    next_cursor: Optional[str] = None


class ConstantsResp(BaseModel):
    color: List[str]
    rarity: List[List[str]]
    type: List[str]
    mark: List[List[str]]
    tags: List[str]
    series: Any


