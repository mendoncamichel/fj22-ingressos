"""
Scraper para Droga Raia (drogaraia.com.br).
Mesma plataforma VTEX que a Drogasil (grupo RaiaDrogasil).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from farmacia_monitor.config import REQUEST_TIMEOUT
from .base import BaseScraper, PriceResult
from .drogasil import (
    _parse_vtex_intelligent_search,
    _parse_vtex_catalog,
    _parse_vtex_html,
    _extract_from_state,
)

logger = logging.getLogger(__name__)


class DrogaRaiaScraper(BaseScraper):
    pharmacy_name = "Droga Raia"
    base_url = "https://www.drogaraia.com.br"
    search_url = "https://www.drogaraia.com.br/pesquisa"
    search_param = "q"

    _VTEX_API = "https://www.drogaraia.com.br/api/intelligent-search/product_search"
    _VTEX_CATALOG = (
        "https://www.drogaraia.com.br/api/catalog_system/pub/products/search"
        "?ft={query}&_from=0&_to=9"
    )
    _VTEX_BACKEND_CATALOG = (
        "https://drogaraia.myvtex.com/api/catalog_system/pub/products/search"
        "?ft={query}&_from=0&_to=9"
    )

    def _try_api(self, query: str) -> Optional[List[PriceResult]]:
        for api_method in [
            self._vtex_catalog_via_main_domain,
            self._vtex_catalog_via_backend,
            self._vtex_intelligent_search,
        ]:
            results = api_method(query)
            if results is not None:
                return results
        return None

    def _vtex_catalog_via_main_domain(self, query: str) -> Optional[List[PriceResult]]:
        headers = {**self.session.headers, "Accept": "application/json"}
        try:
            url = self._VTEX_CATALOG.format(query=query.replace(" ", "+"))
            resp = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (400, 403, 503):
                return None
            resp.raise_for_status()
            return _parse_vtex_catalog(resp.json(), self.pharmacy_name, self.base_url)
        except Exception as exc:
            logger.debug("[Droga Raia] Catalog (main) falhou: %s", exc)
            return None

    def _vtex_catalog_via_backend(self, query: str) -> Optional[List[PriceResult]]:
        headers = {**self.session.headers, "Accept": "application/json"}
        try:
            url = self._VTEX_BACKEND_CATALOG.format(query=query.replace(" ", "+"))
            resp = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (400, 403, 404, 503):
                return None
            resp.raise_for_status()
            return _parse_vtex_catalog(resp.json(), self.pharmacy_name, self.base_url)
        except Exception as exc:
            logger.debug("[Droga Raia] Catalog (backend) falhou: %s", exc)
            return None

    def _vtex_intelligent_search(self, query: str) -> Optional[List[PriceResult]]:
        headers = {**self.session.headers, "Accept": "application/json"}
        try:
            resp = self.session.get(
                self._VTEX_API,
                params={"query": query, "count": 10},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code in (403, 503):
                return None
            resp.raise_for_status()
            return _parse_vtex_intelligent_search(resp.json(), self.pharmacy_name, self.base_url)
        except Exception as exc:
            logger.debug("[Droga Raia] Intelligent Search falhou: %s", exc)
            return None

    def _parse_html(self, html: str, query: str) -> List[PriceResult]:
        return _parse_vtex_html(html, query, self.pharmacy_name, self.base_url)

    def _parse_playwright_page(self, page, query: str) -> List[PriceResult]:
        try:
            state = page.evaluate("() => window.__STATE__ || null")
            if state:
                results = _extract_from_state(state, self.pharmacy_name, self.base_url)
                if results:
                    return results
        except Exception:
            pass
        return self._extract_prices_from_page(page, query)
