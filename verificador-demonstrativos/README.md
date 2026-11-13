# Verificador de Demonstrativos com Erro

Aplicação **PowerShell + WinForms** (lançada por `.bat`) que consulta o Oracle **SAUDEP** e gera um arquivo **XLSX** (ou CSV em fallback) com demonstrativos/itens potencialmente com erro.

## Como executar

1. Garanta as dependências (abaixo).
2. Dê duplo clique em `VerificadorDemonstrativos.bat`  
   (ou: `powershell -STA -File VerificadorDemonstrativos.ps1`).
3. Informe **usuário** e **senha** Oracle (sempre solicitados; a senha **não** é gravada).
4. Escolha a **data de pagamento**.
5. Modo:
   - **Arquivo com lista de prestadores** — TXT/CSV com `COD_PRESTADOR` (um por linha ou 1ª coluna).
   - **Verificação completa** — busca `DISTINCT COD_PRESTADOR` em `OW_GLOSA.EXTRATO_PREST_CONTA` na data informada.
6. Defina o arquivo de saída `.xlsx` e clique em **Executar**.

Erros por prestador são registrados no log da janela **sem interromper** o lote.

## Conexão Oracle

Equivalente a:

```text
jdbc:oracle:thin:@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=BDCORP_SAUDE-PRD.SULAMERICA.BR)(PORT=1527))(CONNECT_DATA=(SERVICE_NAME=SAUDEP)))
```

As queries usam parâmetros (`:data`, `:prestador`) — sem concatenação de SQL.

## Dependências (PC corporativo)

| Dependência | Obrigatório? | Como obter |
|---|---|---|
| **Windows PowerShell 5.1+** | Sim | Já incluso no Windows 10/11 |
| **Oracle.ManagedDataAccess.dll** | Sim | Pacote NuGet [Oracle.ManagedDataAccess](https://www.nuget.org/packages/Oracle.ManagedDataAccess/). Coloque a DLL **ao lado do `.ps1`** ou em `lib\`. Não é necessário Oracle Instant Client. |
| **Módulo ImportExcel** | Recomendado (XLSX) | `Install-Module ImportExcel -Scope CurrentUser` |

### Fallback sem ImportExcel

Se o caminho de saída for `.xlsx` e o módulo **ImportExcel** não estiver instalado, o app gera **CSV** (`;`, UTF-8) com o mesmo conteúdo e exibe um aviso na tela.

## Lista de prestadores (modo arquivo)

- Extensões: `.txt` / `.csv`
- Uma linha por prestador; comentários `#` ignorados
- Códigos numéricos curtos são preenchidos à esquerda até 12 caracteres (`char(12)`)

## Observações

- A query detalhada filtra `DAT_PAGAMENTO > :data` (maior que a data informada), serviços `61430013` / `61430056` e situações de item `30` / `40`, conforme o SQL de referência do projeto.
- A coluna `COD_PRESTADOR` entra no resultado exportado.
