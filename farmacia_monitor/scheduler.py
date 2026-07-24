"""
Agendador de execução diária do monitoramento de preços.
"""

from __future__ import annotations

import logging
import time

import schedule

from farmacia_monitor.config import DRUG_CONFIG, SCHEDULE_TIME
from farmacia_monitor.price_tracker import PriceTracker
from farmacia_monitor.notifier import send_email_notification

logger = logging.getLogger(__name__)


def run_check():
    """Executa uma rodada de pesquisa de preços e exibe/salva o relatório."""
    drug = DRUG_CONFIG
    logger.info(
        "Iniciando pesquisa: %s %s (%s)",
        drug["name"], drug["dosage"], drug["manufacturer"],
    )

    tracker = PriceTracker()
    all_results = tracker.run()
    report = tracker.compare_and_report(all_results)

    print(report)
    send_email_notification(report, all_results)


def start_scheduler(run_now: bool = True):
    """
    Agenda a execução diária e (opcionalmente) roda uma vez imediatamente.

    Args:
        run_now: Se True, executa uma pesquisa imediatamente antes de entrar
                 no loop de agendamento.
    """
    if run_now:
        logger.info("Executando pesquisa inicial...")
        run_check()

    schedule.every().day.at(SCHEDULE_TIME).do(run_check)
    logger.info("Agendamento configurado: todos os dias às %s", SCHEDULE_TIME)

    print(f"\nAgente em execução. Próxima pesquisa agendada para as {SCHEDULE_TIME}.")
    print("Pressione Ctrl+C para encerrar.\n")

    while True:
        schedule.run_pending()
        time.sleep(30)
