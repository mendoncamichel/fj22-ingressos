# Agente de Monitoramento de Preços — Ozivy EMS 0,25 mg

Pesquisa diariamente o preço do medicamento **Ozivy 0,25 mg (EMS)** nas farmácias:

- **Drogasil** (drogasil.com.br)
- **Droga Raia** (drogaraia.com.br)
- **Drogaria São Paulo** (drogariasaopaulo.com.br)

Compara os preços e exibe qual farmácia está oferecendo o menor valor, salvando o histórico em CSV e JSON.

---

## Requisitos

- Python 3.8+
- pip

## Instalação

```bash
# Instalar dependências Python
pip install -r requirements.txt

# Instalar navegador Chromium para o Playwright (necessário para scraping via browser)
playwright install chromium
```

## Uso

### Pesquisa única (resultado imediato)

```bash
python -m farmacia_monitor.main --once
```

### Agendamento diário automático

Roda uma pesquisa imediatamente e depois agenda para todo dia às 08:00:

```bash
python -m farmacia_monitor.main
```

Apenas agenda (sem pesquisa imediata):

```bash
python -m farmacia_monitor.main --schedule
```

---

## Configuração

Edite o arquivo `farmacia_monitor/config.py` para personalizar:

| Parâmetro | Descrição | Padrão |
|---|---|---|
| `DRUG_CONFIG["name"]` | Nome do medicamento | `Ozivy` |
| `DRUG_CONFIG["dosage"]` | Dosagem | `0,25 mg` |
| `DRUG_CONFIG["manufacturer"]` | Fabricante | `EMS` |
| `SCHEDULE_TIME` | Horário da pesquisa diária | `08:00` |
| `EMAIL_CONFIG["enabled"]` | Ativar notificação por e-mail | `False` |

### Notificação por e-mail (opcional)

Em `config.py`, defina:

```python
EMAIL_CONFIG = {
    "enabled": True,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "seu@gmail.com",
    "sender_password": "sua-app-password",
    "recipient_email": "destinatario@email.com",
}
```

> Para Gmail, use uma [App Password](https://support.google.com/accounts/answer/185833).

---

## Resultados

Os resultados são salvos na pasta `resultados/`:

- `relatorio_YYYYMMDD_HHMMSS.txt` — Relatório legível
- `resultados_YYYYMMDD_HHMMSS.json` — Dados estruturados em JSON
- `historico.csv` — Histórico de todos os preços coletados

---

## Funcionamento técnico

O agente usa duas estratégias em cascata para contornar proteções anti-bot:

1. **Requisição HTTP direta** — Tenta as APIs VTEX dos sites (Intelligent Search e Catalog API). Mais rápido.
2. **Playwright (Chromium headless)** — Simula um navegador real com stealth mode para contornar Akamai/Cloudflare. Usado automaticamente se o HTTP direto for bloqueado.

---

## Estrutura do projeto

```
farmacia_monitor/
├── __init__.py
├── config.py          # Configurações (medicamento, farmácias, agendamento)
├── main.py            # Ponto de entrada (CLI)
├── price_tracker.py   # Orquestração da pesquisa e geração de relatório
├── scheduler.py       # Agendamento diário
├── notifier.py        # Notificação por e-mail
└── scrapers/
    ├── __init__.py
    ├── base.py         # Classe base com estratégias HTTP e Playwright
    ├── drogasil.py     # Scraper Drogasil
    ├── drogaraia.py    # Scraper Droga Raia
    └── drogaria_sp.py  # Scraper Drogaria São Paulo
resultados/            # Gerado automaticamente na primeira execução
requirements.txt
README.md
```
