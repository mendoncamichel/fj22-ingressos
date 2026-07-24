"""
Módulo de notificação — e-mail e console.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List

from farmacia_monitor.config import DRUG_CONFIG, EMAIL_CONFIG
from farmacia_monitor.scrapers import PriceResult

logger = logging.getLogger(__name__)


def send_email_notification(report: str, all_results: Dict[str, List[PriceResult]]):
    """Envia o relatório por e-mail se configurado."""
    if not EMAIL_CONFIG.get("enabled"):
        return

    sender = EMAIL_CONFIG.get("sender_email", "")
    password = EMAIL_CONFIG.get("sender_password", "")
    recipient = EMAIL_CONFIG.get("recipient_email", "")

    if not all([sender, password, recipient]):
        logger.warning("Configuração de e-mail incompleta. Verifique config.py.")
        return

    all_prices = [r for results in all_results.values() for r in results]
    subject_price = ""
    if all_prices:
        cheapest = min(all_prices, key=lambda r: r.price)
        subject_price = f" | Menor preço: {cheapest.price_str()} ({cheapest.pharmacy})"

    drug = DRUG_CONFIG
    subject = f"[Monitor Farmácia] {drug['name']} {drug['dosage']}{subject_price}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    # Texto simples
    msg.attach(MIMEText(report, "plain", "utf-8"))

    # HTML formatado
    html_body = _build_html_report(report, all_results)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        logger.info("E-mail enviado para %s", recipient)
    except Exception as exc:
        logger.error("Falha ao enviar e-mail: %s", exc)


def _build_html_report(text_report: str, all_results: Dict[str, List[PriceResult]]) -> str:
    """Gera versão HTML do relatório."""
    drug = DRUG_CONFIG
    all_prices = [r for results in all_results.values() for r in results]
    cheapest = min(all_prices, key=lambda r: r.price) if all_prices else None

    rows = ""
    for pharmacy, results in all_results.items():
        for r in results[:3]:
            stock_badge = (
                '<span style="color:green">✓ Em estoque</span>'
                if r.in_stock
                else '<span style="color:red">✗ Sem estoque</span>'
            )
            highlight = ""
            if cheapest and r.pharmacy == cheapest.pharmacy and r.price == cheapest.price:
                highlight = 'style="background-color: #e8f5e9;"'
            rows += f"""
            <tr {highlight}>
                <td>{r.pharmacy}</td>
                <td>{r.product_name}</td>
                <td><strong>{r.price_str()}</strong></td>
                <td>{stock_badge}</td>
                <td><a href="{r.url}" target="_blank">Ver produto</a></td>
            </tr>"""

    cheapest_html = ""
    if cheapest:
        cheapest_html = f"""
        <div style="background-color:#e8f5e9; padding:15px; border-radius:5px; margin-top:20px;">
            <h3 style="color:#2e7d32; margin:0;">🏆 Melhor Preço: {cheapest.price_str()}</h3>
            <p style="margin:5px 0;">{cheapest.pharmacy} — {cheapest.product_name}</p>
            <a href="{cheapest.url}" style="color:#1565c0;">Ver produto →</a>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th {{ background-color: #1565c0; color: white; padding: 8px 12px; text-align: left; }}
            td {{ padding: 8px 12px; border-bottom: 1px solid #ddd; }}
            tr:hover {{ background-color: #f5f5f5; }}
        </style>
    </head>
    <body>
        <h2>Monitor de Preços — {drug['name']} {drug['dosage']} ({drug['manufacturer']})</h2>
        <table>
            <thead>
                <tr>
                    <th>Farmácia</th>
                    <th>Produto</th>
                    <th>Preço</th>
                    <th>Estoque</th>
                    <th>Link</th>
                </tr>
            </thead>
            <tbody>
                {rows if rows else '<tr><td colspan="5">Nenhum resultado encontrado.</td></tr>'}
            </tbody>
        </table>
        {cheapest_html}
        <hr>
        <pre style="font-size:12px; color:#666;">{text_report}</pre>
    </body>
    </html>
    """
