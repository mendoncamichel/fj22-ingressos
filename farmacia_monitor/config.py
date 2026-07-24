"""
Configuração do agente de monitoramento de preços de remédios.
"""

# Medicamento a ser pesquisado
DRUG_CONFIG = {
    "name": "Ozivy",
    "manufacturer": "EMS",
    "dosage": "0,25 mg",
    "search_terms": ["ozivy 0.25", "ozivy ems", "ozivy"],
    # Termos alternativos (princípio ativo: semaglutida)
    "alternative_terms": ["semaglutida 0.25", "semaglutida ems"],
}

# Farmácias monitoradas
PHARMACIES = {
    "drogasil": {
        "name": "Drogasil",
        "base_url": "https://www.drogasil.com.br",
        "search_url": "https://www.drogasil.com.br/pesquisa",
        "search_param": "q",
        "api_url": "https://www.drogasil.com.br/api/intelligent-search/product_search",
        "vtex_account": "drogasil",
        "enabled": True,
    },
    "drogaraia": {
        "name": "Droga Raia",
        "base_url": "https://www.drogaraia.com.br",
        "search_url": "https://www.drogaraia.com.br/pesquisa",
        "search_param": "q",
        "api_url": "https://www.drogaraia.com.br/api/intelligent-search/product_search",
        "vtex_account": "drogaraia",
        "enabled": True,
    },
    "drogaria_sp": {
        "name": "Drogaria São Paulo",
        "base_url": "https://www.drogariasaopaulo.com.br",
        "search_url": "https://www.drogariasaopaulo.com.br/pesquisa",
        "search_param": "q",
        "api_url": "https://www.drogariasaopaulo.com.br/api/intelligent-search/product_search",
        "vtex_account": "drogariasaopaulo",
        "enabled": True,
    },
}

# Configuração do agendamento (horário diário de execução)
SCHEDULE_TIME = "08:00"  # 08:00 da manhã

# Configuração de notificação por e-mail (opcional)
EMAIL_CONFIG = {
    "enabled": False,          # Mude para True para ativar notificação por e-mail
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "",        # Seu e-mail
    "sender_password": "",     # Sua senha ou App Password
    "recipient_email": "",     # E-mail para receber alertas
}

# Diretório para salvar os resultados
RESULTS_DIR = "resultados"

# Timeout das requisições (segundos)
REQUEST_TIMEOUT = 20

# Headers padrão para requisições HTTP
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
