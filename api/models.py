from sqlalchemy import Column, Integer, String, Text, Index
from .db import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    color = Column(String(16), index=True)
    card_number = Column(String(32), index=True)
    series = Column(String(16), index=True)  # pack prefix
    rarity = Column(String(32), index=True)
    type = Column(String(32), index=True)
    jp_name = Column(String(256), index=True) 
    cn_name = Column(String(256), index=True)
    cost = Column(String(16), index=True)
    power = Column(String(16), index=True)
    race = Column(String(128), index=True)
    note = Column(Text)
    text_full = Column(Text)
    image_url = Column(String(512))
    detail_url = Column(String(512), unique=False, index=True)

    __table_args__ = (
        Index("ix_card_compound", "card_number", "rarity", "cn_name", "jp_name"),
    )


