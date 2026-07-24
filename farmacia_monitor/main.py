"""
Ponto de entrada principal do agente de monitoramento de preços.

Uso:
    python -m farmacia_monitor.main              # Pesquisa imediata + agendamento diário
    python -m farmacia_monitor.main --once       # Apenas uma pesquisa, sem loop
    python -m farmacia_monitor.main --schedule   # Só agenda (sem pesquisa imediata)
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("farmacia_monitor.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Agente de monitoramento de preços de remédios em farmácias brasileiras."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--once",
        action="store_true",
        help="Executa apenas uma pesquisa e encerra.",
    )
    group.add_argument(
        "--schedule",
        action="store_true",
        help="Agenda execuções diárias sem rodar imediatamente.",
    )
    args = parser.parse_args()

    from farmacia_monitor.config import DRUG_CONFIG, SCHEDULE_TIME
    drug = DRUG_CONFIG

    print(f"\n{'='*60}")
    print(f"  Agente de Monitoramento de Preços de Remédios")
    print(f"  Medicamento : {drug['name']} {drug['dosage']}")
    print(f"  Fabricante  : {drug['manufacturer']}")
    print(f"  Horário     : {SCHEDULE_TIME} (diário)")
    print(f"{'='*60}\n")

    if args.once:
        from farmacia_monitor.scheduler import run_check
        run_check()
    else:
        from farmacia_monitor.scheduler import start_scheduler
        run_now = not args.schedule
        start_scheduler(run_now=run_now)


if __name__ == "__main__":
    main()
