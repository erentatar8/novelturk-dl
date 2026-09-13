from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Chapter:
    id: int
    novel_slug: str
    order_index: int
    title: str
    url: str
    content_html: Optional[str] = None
    is_downloaded: bool = False

@dataclass
class Novel:
    slug: str
    title: str
    novel_id: str
    author: Optional[str] = "Bilinmiyor"
    description: Optional[str] = ""
    cover_url: Optional[str] = None
    total_chapters: int = 0
    chapters: List[Chapter] = field(default_factory=list)
