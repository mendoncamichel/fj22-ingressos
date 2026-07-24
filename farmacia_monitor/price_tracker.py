"""
Lógica de comparação e rastreamento de preços entre farmácias.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from farmacia_monitor.config import DRUG_CONFIG, PHARMACIES, RESULTS_DIR
from farmacia_monitor.scrapers import (
    DrogasilScraper,
    DrogaRaiaScraper,
    DrogariaSPScraper,
    PriceResult,
)

logger = logging.getLogger(__name__)


class PriceTracker:
    """Pesquisa preços em todas as farmácias e compara os resultados."""

    _SCRAPERS = {
        "drogasil": DrogasilScraper,
        "drogaraia": DrogaRaiaScraper,
        "drogaria_sp": DrogariaSPScraper,
    }

    def __init__(self):
        os.makedirs(RESULTS_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # Método principal
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, List[PriceResult]]:
        """
        Executa a pesquisa em todas as farmácias habilitadas e retorna
        um dicionário {farmácia: [resultados]}.
        """
        all_results: Dict[str, List[PriceResult]] = {}
        search_terms = DRUG_CONFIG["search_terms"]

        for pharmacy_key, config in PHARMACIES.items():
            if not config.get("enabled"):
                continue

            scraper_cls = self._SCRAPERS.get(pharmacy_key)
            if not scraper_cls:
                continue

            scraper = scraper_cls()
            pharmacy_results: List[PriceResult] = []

            for term in search_terms:
                results = scraper.search(term)
                relevant = _filter_relevant(results, DRUG_CONFIG)
                if relevant:
                    pharmacy_results = relevant
                    break

            all_results[config["name"]] = pharmacy_results

        return all_results

    # ------------------------------------------------------------------
    # Análise e relatório
    # ------------------------------------------------------------------

    def compare_and_report(self, all_results: Dict[str, List[PriceResult]]) -> str:
        """Gera relatório de comparação e retorna o texto formatado."""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        drug = DRUG_CONFIG

        lines = [
            "=" * 60,
            f"  MONITORAMENTO DE PREÇOS — {drug['name'].upper()} {drug['dosage']}",
            f"  Fabricante: {drug['manufacturer']}",
            f"  Consulta: {timestamp}",
            "=" * 60,
            "",
        ]

        all_prices: List[PriceResult] = []
        dosage_prices: List[PriceResult] = []

        for pharmacy_name, results in all_results.items():
            if not results:
                lines.append(f"[{pharmacy_name}]  Produto não encontrado ou site indisponível.")
            else:
                lines.append(f"[{pharmacy_name}]")
                for r in results[:3]:
                    is_target_dosage = _is_target_dosage(r.product_name, drug["dosage"])
                    dosage_tag = " ◀ dosagem solicitada" if is_target_dosage else ""
                    lines.append(f"  • {r.product_name}{dosage_tag}")
                    lines.append(f"    Preço: {r.price_str()}")
                    lines.append(f"    Link:  {r.url}")
                    if not r.in_stock:
                        lines.append("    *** SEM ESTOQUE ***")
                    all_prices.append(r)
                    if is_target_dosage:
                        dosage_prices.append(r)
            lines.append("")

        lines.append("-" * 60)

        target_prices = dosage_prices if dosage_prices else all_prices

        if target_prices:
            cheapest = min(target_prices, key=lambda r: r.price)
            available = [r for r in target_prices if r.in_stock]
            cheapest_available = min(available, key=lambda r: r.price) if available else None

            if dosage_prices:
                lines.append(f"MELHOR PREÇO — {drug['name']} {drug['dosage']}:")
            else:
                lines.append("MELHOR PREÇO ENCONTRADO (produto próximo):")

            lines.append(f"  Farmácia : {cheapest.pharmacy}")
            lines.append(f"  Produto  : {cheapest.product_name}")
            lines.append(f"  Preço    : {cheapest.price_str()}")
            lines.append(f"  Link     : {cheapest.url}")
            if not cheapest.in_stock:
                lines.append("  STATUS   : *** SEM ESTOQUE ***")

            if cheapest_available and (
                cheapest_available.pharmacy != cheapest.pharmacy
                or cheapest_available.price != cheapest.price
            ):
                lines.append("")
                lines.append("MELHOR PREÇO EM ESTOQUE:")
                lines.append(f"  Farmácia : {cheapest_available.pharmacy}")
                lines.append(f"  Produto  : {cheapest_available.product_name}")
                lines.append(f"  Preço    : {cheapest_available.price_str()}")
                lines.append(f"  Link     : {cheapest_available.url}")
            elif not cheapest_available:
                lines.append("")
                lines.append("  ⚠  Produto sem estoque em todas as farmácias consultadas.")
        else:
            lines.append("Nenhum produto encontrado nas farmácias pesquisadas.")
            lines.append("Possíveis causas:")
            lines.append("  1. Sites bloqueando requisições de IPs de datacenter")
            lines.append("     → Execute em rede doméstica/corporativa para melhor resultado")
            lines.append("  2. Produto ainda não cadastrado nas lojas online")
            lines.append("  3. Produto disponível apenas nas lojas físicas")

        lines.append("=" * 60)

        report = "\n".join(lines)
        self._save_results(all_results, report)
        return report

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def _save_results(self, all_results: Dict[str, List[PriceResult]], report: str):
        """Salva resultados em JSON e CSV."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Salva relatório de texto
        txt_path = os.path.join(RESULTS_DIR, f"relatorio_{ts}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(report)

        # Salva JSON estruturado
        json_data = {
            "timestamp": datetime.now().isoformat(),
            "drug": DRUG_CONFIG,
            "results": {
                pharmacy: [
                    {
                        "product_name": r.product_name,
                        "price": r.price,
                        "url": r.url,
                        "in_stock": r.in_stock,
                    }
                    for r in results
                ]
                for pharmacy, results in all_results.items()
            },
        }
        json_path = os.path.join(RESULTS_DIR, f"resultados_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        # Salva histórico CSV
        csv_path = os.path.join(RESULTS_DIR, "historico.csv")
        file_exists = os.path.isfile(csv_path)
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["data_hora", "farmacia", "produto", "preco", "em_estoque", "url"])
            for pharmacy, results in all_results.items():
                for r in results:
                    writer.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        pharmacy,
                        r.product_name,
                        r.price,
                        r.in_stock,
                        r.url,
                    ])

        logger.info("Resultados salvos em: %s", RESULTS_DIR)


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _filter_relevant(results: List[PriceResult], drug_config: dict) -> List[PriceResult]:
    """Filtra resultados que correspondem ao medicamento pesquisado."""
    if not results:
        return []

    name_lower = drug_config["name"].lower()
    manufacturer_lower = drug_config["manufacturer"].lower()
    dosage_variants = [drug_config["dosage"].replace(",", "."), drug_config["dosage"]]

    relevant = []
    for r in results:
        product_lower = r.product_name.lower()
        if name_lower in product_lower:
            relevant.append(r)
        elif manufacturer_lower in product_lower and any(d in product_lower for d in dosage_variants):
            relevant.append(r)

    # Se nenhum filtro severo bateu, retorna todos (pode ser nome diferente)
    if not relevant:
        return results

    # Ordena: primeiro os da dosagem correta, depois por preço
    target_dosage = drug_config["dosage"]
    relevant.sort(key=lambda r: (
        not _is_target_dosage(r.product_name, target_dosage),
        not r.in_stock,
        r.price,
    ))
    return relevant


def _is_target_dosage(product_name: str, dosage: str) -> bool:
    """Verifica se o produto tem a dosagem solicitada."""
    name_lower = product_name.lower()
    # Normaliza dosagem: "0,25 mg" → "0,25" e "0.25"
    base = dosage.replace(" mg", "").replace(" MG", "").strip()
    variants = [base, base.replace(",", ".")]
    return any(v in name_lower for v in variants)
