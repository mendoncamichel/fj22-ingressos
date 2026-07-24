from .base import BaseScraper, PriceResult
from .drogasil import DrogasilScraper
from .drogaraia import DrogaRaiaScraper
from .drogaria_sp import DrogariaSPScraper

__all__ = [
    "BaseScraper",
    "PriceResult",
    "DrogasilScraper",
    "DrogaRaiaScraper",
    "DrogariaSPScraper",
]
