"""
Scraper para Drogasil (drogasil.com.br).
Usa VTEX Intelligent Search API ou Playwright como fallback.
"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from farmacia_monitor.config import REQUEST_TIMEOUT
from .base import BaseScraper, PriceResult, _parse_price

logger = logging.getLogger(__name__)


class DrogasilScraper(BaseScraper):
    pharmacy_name = "Drogasil"
    base_url = "https://www.drogasil.com.br"
    search_url = "https://www.drogasil.com.br/pesquisa"
    search_param = "q"

    # Rotas diretas (podem ser bloqueadas por Akamai em IPs de datacenter)
    _VTEX_API = "https://www.drogasil.com.br/api/intelligent-search/product_search"
    _VTEX_CATALOG = (
        "https://www.drogasil.com.br/api/catalog_system/pub/products/search"
        "?ft={query}&_from=0&_to=9"
    )
    # Rota backend VTEX (bypassa Akamai; requer VTEX account correto)
    _VTEX_BACKEND_CATALOG = (
        "https://drogasil.myvtex.com/api/catalog_system/pub/products/search"
        "?ft={query}&_from=0&_to=9"
    )

    def _try_api(self, query: str) -> Optional[List[PriceResult]]:
        """Tenta a API VTEX em múltiplas rotas."""

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
            logger.debug("[Drogasil] Catalog (main) falhou: %s", exc)
            return None

    def _vtex_catalog_via_backend(self, query: str) -> Optional[List[PriceResult]]:
        """Tenta a API de catálogo via backend VTEX (bypassa Akamai)."""
        headers = {**self.session.headers, "Accept": "application/json"}
        try:
            url = self._VTEX_BACKEND_CATALOG.format(query=query.replace(" ", "+"))
            resp = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (400, 403, 404, 503):
                return None
            resp.raise_for_status()
            return _parse_vtex_catalog(resp.json(), self.pharmacy_name, self.base_url)
        except Exception as exc:
            logger.debug("[Drogasil] Catalog (backend) falhou: %s", exc)
            return None

    def _vtex_intelligent_search(self, query: str) -> Optional[List[PriceResult]]:
        headers = {
            **self.session.headers,
            "Accept": "application/json",
            "X-VTEX-Use-Https": "true",
        }
        try:
            resp = self.session.get(
                self._VTEX_API,
                params={"query": query, "count": 10, "sort": "price:asc"},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code in (403, 503):
                return None
            resp.raise_for_status()
            return _parse_vtex_intelligent_search(resp.json(), self.pharmacy_name, self.base_url)
        except Exception as exc:
            logger.debug("[Drogasil] Intelligent Search falhou: %s", exc)
            return None

    def _parse_html(self, html: str, query: str) -> List[PriceResult]:
        return _parse_vtex_html(html, query, self.pharmacy_name, self.base_url)

    def _parse_playwright_page(self, page, query: str) -> List[PriceResult]:
        """Extrai dados via JSON embutido no HTML (window.__STATE__)."""
        try:
            state = page.evaluate("() => window.__STATE__ || window.__STORES__ || null")
            if state:
                results = _extract_from_state(state, self.pharmacy_name, self.base_url)
                if results:
                    return results
        except Exception:
            pass
        return self._extract_prices_from_page(page, query)


# ---------------------------------------------------------------------------
# Funções de parse compartilhadas VTEX
# ---------------------------------------------------------------------------

def _parse_vtex_intelligent_search(data: dict, pharmacy: str, base_url: str) -> List[PriceResult]:
    results = []
    products = (
        data.get("products", [])
        or data.get("data", {}).get("productSearch", {}).get("products", [])
        or []
    )
    for product in products:
        try:
            name = product.get("productName") or product.get("name", "")
            link = product.get("link") or product.get("linkText", "")
            if link and not link.startswith("http"):
                link = base_url + "/" + link.lstrip("/")

            items = product.get("items", [])
            for item in items:
                sellers = item.get("sellers", [])
                for seller in sellers:
                    offer = seller.get("commertialOffer", {})
                    price = offer.get("Price") or offer.get("price") or 0
                    available = offer.get("IsAvailable", True)
                    if price > 0:
                        results.append(
                            PriceResult(
                                pharmacy=pharmacy,
                                product_name=name,
                                price=float(price),
                                url=link or base_url,
                                in_stock=bool(available),
                            )
                        )
        except Exception:
            continue
    return results


def _parse_vtex_catalog(data: list, pharmacy: str, base_url: str) -> List[PriceResult]:
    results = []
    if not isinstance(data, list):
        return results
    for product in data:
        try:
            name = product.get("productName", "")
            link = product.get("link", "")
            items = product.get("items", [])
            for item in items:
                sellers = item.get("sellers", [])
                for seller in sellers:
                    offer = seller.get("commertialOffer", {})
                    price = offer.get("Price") or offer.get("price") or 0
                    if price > 0:
                        results.append(
                            PriceResult(
                                pharmacy=pharmacy,
                                product_name=name,
                                price=float(price),
                                url=link or base_url,
                                in_stock=offer.get("IsAvailable", True),
                            )
                        )
        except Exception:
            continue
    return results


def _parse_vtex_html(html: str, query: str, pharmacy: str, base_url: str) -> List[PriceResult]:
    """Tenta extrair __STATE__ ou dados JSON do HTML de página VTEX."""
    results = []
    try:
        match = re.search(r"window\.__STATE__\s*=\s*(\{.+?\});?\s*</script>", html, re.DOTALL)
        if match:
            state = json.loads(match.group(1))
            results = _extract_from_state(state, pharmacy, base_url)
    except Exception:
        pass

    if not results:
        prices = re.findall(r'"[Pp]rice"\s*:\s*([\d.]+)', html)
        names = re.findall(r'"productName"\s*:\s*"([^"]+)"', html)
        for i, price_str in enumerate(prices[:5]):
            try:
                price = float(price_str)
                name = names[i] if i < len(names) else query
                if price > 0 and query.lower().split()[0] in name.lower():
                    results.append(PriceResult(pharmacy=pharmacy, product_name=name, price=price, url=base_url))
            except ValueError:
                continue

    return results


def _extract_from_state(state: dict, pharmacy: str, base_url: str) -> List[PriceResult]:
    results = []
    try:
        for key, value in state.items():
            if not isinstance(value, dict):
                continue
            if "Product" not in key and "product" not in key:
                continue
            for sub_key, sub_val in value.items():
                if isinstance(sub_val, dict) and "items" in sub_val:
                    items = sub_val.get("items", [])
                    name = sub_val.get("productName", "")
                    link = sub_val.get("link", base_url)
                    for item in items:
                        for seller in item.get("sellers", []):
                            offer = seller.get("commertialOffer", {})
                            price = offer.get("Price") or offer.get("price") or 0
                            if price > 0:
                                results.append(
                                    PriceResult(
                                        pharmacy=pharmacy,
                                        product_name=name,
                                        price=float(price),
                                        url=link,
                                        in_stock=offer.get("IsAvailable", True),
                                    )
                                )
    except Exception:
        pass
    return results
