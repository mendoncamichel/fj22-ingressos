# Verificador de Demonstrativos com Erro

Aplicação **PowerShell + WinForms** (lançada por `.bat`) que consulta o Oracle **SAUDEP** e gera um **CSV** seguro para Excel PT-BR com demonstrativos/itens potencialmente com erro.

## Como executar

1. Coloque `Oracle.ManagedDataAccess.dll` em `lib\` (veja Dependências).
2. Dê duplo clique em `VerificadorDemonstrativos.bat`  
   (ou: `powershell -STA -File VerificadorDemonstrativos.ps1`).
3. Informe **usuário** e **senha** Oracle (sempre solicitados; a senha **não** é gravada).
4. Escolha a **data de pagamento**.
5. Modo:
   - **Arquivo com lista de prestadores** — TXT/CSV com `COD_PRESTADOR` (um por linha ou 1ª coluna).
   - **Verificação completa** — busca `DISTINCT COD_PRESTADOR` em `OW_GLOSA.EXTRATO_PREST_CONTA` na data informada.
6. Defina o arquivo de saída `.csv` e clique em **Executar**.

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
| **Oracle.ManagedDataAccess.dll** | Sim | Pacote NuGet [Oracle.ManagedDataAccess](https://www.nuget.org/packages/Oracle.ManagedDataAccess/). **Caminho padrão:** `lib\Oracle.ManagedDataAccess.dll` (pasta `lib` ao lado do `.ps1`). Fallback: DLL na mesma pasta do script. Não é necessário Oracle Instant Client. |

Estrutura esperada:

```text
verificador-demonstrativos/
  VerificadorDemonstrativos.bat
  VerificadorDemonstrativos.ps1
  README.md
  lib/
    Oracle.ManagedDataAccess.dll   ← colocar aqui
```

## Formato do CSV (Excel PT-BR)

O app **não depende de ImportExcel / XLSX**. A saída é CSV pensada para não “desconfigurar” colunas no Excel brasileiro:

| Regra | Detalhe |
|---|---|
| Delimitador | `;` |
| Encoding | **UTF-8 com BOM** |
| Hint Excel | primeira linha `sep=;` |
| Aspas | **todos** os campos entre aspas (`"..."`); `"` interno vira `""` |
| Células vazias | `""` — mantém o número de colunas |
| `COD_PRESTADOR` | sempre presente (1ª coluna) |
| Datas | `yyyy-MM-dd HH:mm:ss` (invariant) |
| Decimais | formato **pt-BR** (vírgula), ex.: `1234,56` — seguro porque o delimitador é `;` e os campos estão entre aspas |

Abra o `.csv` com duplo clique no Excel ou via **Dados → De texto/CSV**.

## Lista de prestadores (modo arquivo)

- Extensões: `.txt` / `.csv`
- Uma linha por prestador; comentários `#` ignorados
- Códigos numéricos curtos são preenchidos à esquerda até 12 caracteres (`char(12)`)

## Observações

- A query detalhada filtra `DAT_PAGAMENTO > :data` (maior que a data informada), serviços `61430013` / `61430056` e situações de item `30` / `40`, conforme o SQL de referência do projeto.
- Colunas fixas do resultado incluem sempre `COD_PRESTADOR`, mesmo quando não há linhas.
