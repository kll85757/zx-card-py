from typing import List, Dict, Any
from .config import settings

try:
    from meilisearch import Client
except Exception:  # pragma: no cover
    Client = None  # type: ignore


def meili_client():
    if getattr(settings, "meili_disabled", False):
        return None
    if Client is None:
        return None
    return Client(settings.meili_host, settings.meili_api_key)


def ensure_index():
    cl = meili_client()
    if cl is None:
        return
    idx = cl.index(settings.meili_index)
    try:
        idx.get_raw_info()
    except Exception:
        cl.create_index(settings.meili_index, {"primaryKey": "id"})
        idx = cl.index(settings.meili_index)
    idx.update_settings({
        "filterableAttributes": [
            "color", "rarity", "type", "series", "card_number"
        ],
        "sortableAttributes": ["card_number"],
        "searchableAttributes": [
            "cn_name", "jp_name", "card_number", "text_full", "note"
        ],
    })


def index_cards(cards: List[Dict[str, Any]]):
    cl = meili_client()
    if cl is None:
        return
    idx = cl.index(settings.meili_index)
    idx.add_documents(cards)


