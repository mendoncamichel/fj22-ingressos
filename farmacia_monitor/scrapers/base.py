"""
Classe base para scrapers de farmácias.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from farmacia_monitor.config import DEFAULT_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class PriceResult:
    """Resultado de preço encontrado em uma farmácia."""

    pharmacy: str
    product_name: str
    price: float
    url: str
    in_stock: bool = True
    extra: dict = field(default_factory=dict)

    def price_str(self) -> str:
        return f"R$ {self.price:.2f}".replace(".", ",")

    def __str__(self) -> str:
        stock = "" if self.in_stock else " [SEM ESTOQUE]"
        return f"{self.pharmacy}: {self.product_name} — {self.price_str()}{stock}"


class BaseScraper:
    """Classe base com lógica compartilhada de scraping."""

    pharmacy_name: str = "Farmácia"
    base_url: str = ""
    search_url: str = ""
    search_param: str = "q"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # Método principal — deve ser sobrescrito
    # ------------------------------------------------------------------

    def search(self, query: str) -> List[PriceResult]:
        """
        Pesquisa o produto na farmácia e retorna uma lista de resultados.
        Tenta primeiro via HTTP direto e cai para Playwright se necessário.
        """
        logger.info("[%s] Pesquisando: %s", self.pharmacy_name, query)

        results = self._search_http(query)
        if results is not None:
            return results

        logger.info("[%s] HTTP bloqueado, tentando Playwright...", self.pharmacy_name)
        results = self._search_playwright(query)
        if results is not None:
            return results

        logger.warning("[%s] Não foi possível obter resultados.", self.pharmacy_name)
        return []

    # ------------------------------------------------------------------
    # HTTP direto
    # ------------------------------------------------------------------

    def _search_http(self, query: str) -> Optional[List[PriceResult]]:
        """Tenta buscar via HTTP simples. Retorna None se bloqueado."""
        try:
            results = self._try_api(query)
            if results is not None:
                return results

            resp = self.session.get(
                self.search_url,
                params={self.search_param: query},
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            if resp.status_code in (403, 503):
                logger.debug("[%s] HTTP bloqueado (status %d).", self.pharmacy_name, resp.status_code)
                return None
            resp.raise_for_status()
            return self._parse_html(resp.text, query)
        except requests.RequestException as exc:
            logger.debug("[%s] Erro HTTP: %s", self.pharmacy_name, exc)
            return None

    def _try_api(self, query: str) -> Optional[List[PriceResult]]:
        """Tenta endpoint de API VTEX/JSON. Subclasses podem sobrescrever."""
        return None

    def _parse_html(self, html: str, query: str) -> List[PriceResult]:
        """Extrai preços do HTML. Subclasses devem implementar."""
        return []

    # ------------------------------------------------------------------
    # Playwright (headless browser)
    # ------------------------------------------------------------------

    def _search_playwright(self, query: str) -> Optional[List[PriceResult]]:
        """Usa Playwright com stealth para contornar proteção anti-bot."""
        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=DEFAULT_HEADERS["User-Agent"],
                    locale="pt-BR",
                    viewport={"width": 1280, "height": 720},
                )
                Stealth().use_sync(context)
                page = context.new_page()

                try:
                    url = f"{self.search_url}?{self.search_param}={requests.utils.quote(query)}"
                    page.goto(url, timeout=30_000)
                    page.wait_for_timeout(4_000)
                    html = page.content()
                    results = self._parse_html(html, query)
                    if not results:
                        results = self._parse_playwright_page(page, query)
                    return results if results is not None else []
                finally:
                    browser.close()
        except ImportError:
            logger.warning("Playwright não instalado. pip install playwright playwright-stealth")
            return None
        except Exception as exc:
            logger.debug("[%s] Erro Playwright: %s", self.pharmacy_name, exc)
            return None

    def _parse_playwright_page(self, page, query: str) -> List[PriceResult]:
        """
        Extrai resultados a partir do objeto page do Playwright.
        Subclasses podem sobrescrever para lógica específica.
        """
        return self._extract_prices_from_page(page, query)

    def _extract_prices_from_page(self, page, query: str) -> List[PriceResult]:
        """Extração genérica de preços usando seletores CSS comuns."""
        results = []
        query_lower = query.lower()

        selectors = [
            "[class*='product-summary']",
            "[class*='productCard']",
            "[class*='product-card']",
            "[data-testid*='product']",
            ".shelf .product",
        ]

        for selector in selectors:
            try:
                cards = page.query_selector_all(selector)
                if cards:
                    for card in cards[:10]:
                        result = self._parse_product_card(card, query_lower)
                        if result:
                            results.append(result)
                    if results:
                        break
            except Exception:
                continue

        return results

    def _parse_product_card(self, card, query_lower: str) -> Optional[PriceResult]:
        """Tenta extrair nome e preço de um elemento HTML de produto."""
        try:
            text = card.inner_text() or ""
            if query_lower.split()[0] not in text.lower():
                return None

            price_match = re.search(r"R\$\s*([\d.,]+)", text)
            if not price_match:
                return None

            price = _parse_price(price_match.group(1))
            if price <= 0:
                return None

            name_el = (
                card.query_selector("[class*='name']")
                or card.query_selector("[class*='title']")
                or card.query_selector("h2, h3, h4")
            )
            product_name = name_el.inner_text().strip() if name_el else text[:80].strip()

            link = card.query_selector("a")
            url = link.get_attribute("href") if link else self.base_url
            if url and not url.startswith("http"):
                url = self.base_url + url

            return PriceResult(
                pharmacy=self.pharmacy_name,
                product_name=product_name,
                price=price,
                url=url or self.base_url,
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def retry(self, func, retries: int = 3, delay: float = 2.0):
        """Executa func com retry exponencial."""
        for attempt in range(retries):
            try:
                return func()
            except Exception as exc:
                if attempt < retries - 1:
                    wait = delay * (2 ** attempt)
                    logger.debug("Tentativa %d falhou (%s). Aguardando %.1fs...", attempt + 1, exc, wait)
                    time.sleep(wait)
                else:
                    raise


def _parse_price(price_str: str) -> float:
    """Converte string de preço BR (ex: '45,90' ou '1.234,56') para float."""
    clean = price_str.strip().replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return 0.0
