#Requires -Version 5.1
# Verificador de Demonstrativos com Erro — WinForms + Oracle
# Conexão: BDCORP_SAUDE-PRD.SULAMERICA.BR:1527 / SERVICE_NAME=SAUDEP
# Credenciais sempre solicitadas na UI; nunca gravadas.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$script:AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:OracleDllCandidates = @(
    (Join-Path $script:AppDir 'Oracle.ManagedDataAccess.dll'),
    (Join-Path $script:AppDir 'lib\Oracle.ManagedDataAccess.dll'),
    (Join-Path $env:USERPROFILE '.nuget\packages\oracle.manageddataaccess*\*\lib\net462\Oracle.ManagedDataAccess.dll'),
    (Join-Path $env:USERPROFILE '.nuget\packages\oracle.manageddataaccess*\*\lib\net40\Oracle.ManagedDataAccess.dll')
)

function Get-OracleConnectionString {
    param(
        [Parameter(Mandatory)][string]$User,
        [Parameter(Mandatory)][string]$Password
    )
    # Equivalente ao JDBC thin DESCRIPTION SAUDEP
    $dataSource = @(
        '(DESCRIPTION='
        '(ADDRESS=(PROTOCOL=TCP)(HOST=BDCORP_SAUDE-PRD.SULAMERICA.BR)(PORT=1527))'
        '(CONNECT_DATA=(SERVICE_NAME=SAUDEP))'
        ')'
    ) -join ''
    return "User Id=$User;Password=$Password;Data Source=$dataSource"
}

function Import-OracleManagedDataAccess {
    if ([AppDomain]::CurrentDomain.GetAssemblies() | Where-Object { $_.GetName().Name -eq 'Oracle.ManagedDataAccess' }) {
        return
    }
    $resolved = @()
    foreach ($pattern in $script:OracleDllCandidates) {
        $resolved += @(Get-Item -Path $pattern -ErrorAction SilentlyContinue)
    }
    $dll = $resolved | Select-Object -First 1
    if (-not $dll) {
        throw @"
Oracle.ManagedDataAccess.dll não encontrado.

Coloque a DLL ao lado deste script (ou em lib\) ou instale o pacote NuGet Oracle.ManagedDataAccess.
Download NuGet: https://www.nuget.org/packages/Oracle.ManagedDataAccess/
"@
    }
    [void][System.Reflection.Assembly]::LoadFrom($dll.FullName)
}

function Format-CodPrestador {
    param([Parameter(Mandatory)][string]$Raw)
    $t = $Raw.Trim().TrimStart([char]0xFEFF)
    if ([string]::IsNullOrWhiteSpace($t)) { return $null }
    # COD_PRESTADOR é char(12): preenche à esquerda com zeros se numérico curto
    if ($t -match '^\d+$' -and $t.Length -lt 12) {
        return $t.PadLeft(12, '0')
    }
    if ($t.Length -gt 12) {
        return $t.Substring(0, 12)
    }
    return $t.PadRight(12, ' ')
}

function Read-ListaPrestadores {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Arquivo de lista não encontrado: $Path"
    }
    $list = [System.Collections.Generic.List[string]]::new()
    $seen = @{}
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ([string]::IsNullOrWhiteSpace($line)) { return }
        if ($line.StartsWith('#')) { return }
        # CSV: pega primeira coluna
        $cod = ($line -split '[,;\t]')[0]
        $fmt = Format-CodPrestador -Raw $cod
        if ($null -eq $fmt) { return }
        $key = $fmt.Trim()
        if (-not $seen.ContainsKey($key)) {
            $seen[$key] = $true
            [void]$list.Add($fmt)
        }
    }
    return ,$list.ToArray()
}

function Open-OracleConnection {
    param(
        [Parameter(Mandatory)][string]$User,
        [Parameter(Mandatory)][string]$Password
    )
    Import-OracleManagedDataAccess
    $cs = Get-OracleConnectionString -User $User -Password $Password
    $conn = New-Object Oracle.ManagedDataAccess.Client.OracleConnection($cs)
    $conn.Open()
    return $conn
}

function Get-PrestadoresCompleto {
    param(
        [Parameter(Mandatory)]$Connection,
        [Parameter(Mandatory)][datetime]$DataPagamento
    )
    $sql = @"
SELECT DISTINCT COD_PRESTADOR
  FROM OW_GLOSA.EXTRATO_PREST_CONTA epc
 WHERE epc.DAT_PAGAMENTO = :data
"@
    $cmd = $Connection.CreateCommand()
    $cmd.BindByName = $true
    $cmd.CommandText = $sql
    $p = $cmd.Parameters.Add('data', [Oracle.ManagedDataAccess.Client.OracleDbType]::Date)
    $p.Value = $DataPagamento.Date
    $list = [System.Collections.Generic.List[string]]::new()
    $reader = $cmd.ExecuteReader()
    try {
        while ($reader.Read()) {
            $raw = [string]$reader.GetValue(0)
            $fmt = Format-CodPrestador -Raw $raw
            if ($null -ne $fmt) { [void]$list.Add($fmt) }
        }
    }
    finally {
        $reader.Dispose()
        $cmd.Dispose()
    }
    return ,$list.ToArray()
}

function Invoke-DetalhePrestador {
    param(
        [Parameter(Mandatory)]$Connection,
        [Parameter(Mandatory)][string]$CodPrestador,
        [Parameter(Mandatory)][datetime]$DataPagamento
    )
    $sql = @"
SELECT
       A.COD_PRESTADOR,
       A.IDT_DOCUMENTO,
       A.COD_ORIGEM,
       A.DAT_PAGAMENTO,
       A.COD_SITUACAO_DOC,
       B.IDT_ANEXO,
       B.IDT_ITEM,
       B.COD_SERVICO,
       B.COD_GLOSA_BLOQUEIO,
       B.COD_SITUACAO_ITEM,
       B.DAT_INCLUSAO,
       B.COD_NIV_LIBERACAO AS COD_NIV_LIBERACAO_ITEM,
       B.COD_REG_RESP AS COD_REG_RESP_ITEM,
       B.VAL_ITEM,
       (B.VAL_EMPR_ADM + B.VAL_EMPR_PRE + B.VAL_EMPR_SEG + B.VAL_FUNC_ADM) AS VAL_TOTAL_COPART,
       A.COD_NIV_LIBERACAO AS COD_NIV_LIBERACAO_DOC,
       A.COD_REG_RESP AS COD_REG_RESP_DOC,
       (SELECT SUM(C.VAL_GLOSADO)
          FROM OW_REP_SAUDE.ITEM_PROC_MAT_MED C
         WHERE C.IDT_DOCUMENTO   = B.IDT_DOCUMENTO
           AND C.IDT_COMPLEMENTO = B.IDT_COMPLEMENTO
           AND C.IDT_SEQ_PAGTO   = B.IDT_SEQ_PAGTO
           AND C.COD_ORIGEM      = B.COD_ORIGEM
           AND C.IDT_ANEXO       = B.IDT_ANEXO
           AND C.IDT_ITEM        = B.IDT_ITEM) AS VAL_GLOSADO
  FROM OW_REP_SAUDE.CONTA_PROCESSAMENT A
 INNER JOIN OW_REP_SAUDE.ITEM_PROCESSAMENTO B
    ON A.IDT_DOCUMENTO   = B.IDT_DOCUMENTO
   AND A.IDT_COMPLEMENTO = B.IDT_COMPLEMENTO
   AND A.IDT_SEQ_PAGTO   = B.IDT_SEQ_PAGTO
   AND A.COD_ORIGEM      = B.COD_ORIGEM
 WHERE A.COD_PRESTADOR      = :prestador
   AND A.IDT_COMPLEMENTO    = '01'
   AND A.IDT_SEQ_PAGTO      = '0'
   AND A.COD_SITUACAO_DOC  >= 50
   AND A.DAT_PAGAMENTO      > :data
   AND B.COD_SERVICO       IN (61430013, 61430056)
   AND B.COD_SITUACAO_ITEM IN (30, 40)
"@
    $cmd = $Connection.CreateCommand()
    $cmd.BindByName = $true
    $cmd.CommandText = $sql
    $pPrest = $cmd.Parameters.Add('prestador', [Oracle.ManagedDataAccess.Client.OracleDbType]::Varchar2)
    $pPrest.Value = $CodPrestador
    $pData = $cmd.Parameters.Add('data', [Oracle.ManagedDataAccess.Client.OracleDbType]::Date)
    $pData.Value = $DataPagamento.Date

    $table = New-Object System.Data.DataTable
    $adapter = New-Object Oracle.ManagedDataAccess.Client.OracleDataAdapter($cmd)
    try {
        [void]$adapter.Fill($table)
    }
    finally {
        $adapter.Dispose()
        $cmd.Dispose()
    }
    return $table
}

function Test-ImportExcelAvailable {
    return $null -ne (Get-Module -ListAvailable -Name ImportExcel | Select-Object -First 1)
}

function Export-Resultados {
    param(
        [Parameter(Mandatory)][System.Data.DataTable]$Table,
        [Parameter(Mandatory)][string]$OutputPath,
        [Parameter(Mandatory)][System.Windows.Forms.Label]$StatusLabel
    )
    $dir = Split-Path -Parent $OutputPath
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $useXlsx = $OutputPath.ToLowerInvariant().EndsWith('.xlsx')
    if ($useXlsx -and (Test-ImportExcelAvailable)) {
        Import-Module ImportExcel -ErrorAction Stop
        if (Test-Path -LiteralPath $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }
        $Table | Export-Excel -Path $OutputPath -WorksheetName 'Demonstrativos' -AutoSize -TableName 'Resultados' -FreezeTopRow
        $StatusLabel.Text = "Exportado XLSX: $OutputPath"
        return @{ Path = $OutputPath; Format = 'xlsx' }
    }

    if ($useXlsx) {
        $csvPath = [System.IO.Path]::ChangeExtension($OutputPath, '.csv')
        $StatusLabel.Text = 'ImportExcel não instalado — gerando CSV...'
        $Table | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8 -Delimiter ';'
        [System.Windows.Forms.MessageBox]::Show(
            "O módulo ImportExcel não está instalado.`n`nArquivo gerado em CSV:`n$csvPath`n`nPara XLSX, instale no PowerShell:`nInstall-Module ImportExcel -Scope CurrentUser",
            'Exportação CSV (fallback)',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        ) | Out-Null
        return @{ Path = $csvPath; Format = 'csv' }
    }

    $Table | Export-Csv -LiteralPath $OutputPath -NoTypeInformation -Encoding UTF8 -Delimiter ';'
    $StatusLabel.Text = "Exportado CSV: $OutputPath"
    return @{ Path = $OutputPath; Format = 'csv' }
}

function Merge-DataTables {
    param([System.Data.DataTable[]]$Tables)
    $merged = New-Object System.Data.DataTable
    foreach ($t in $Tables) {
        if ($null -eq $t) { continue }
        if ($merged.Columns.Count -eq 0) {
            $merged = $t.Clone()
        }
        foreach ($row in $t.Rows) {
            [void]$merged.ImportRow($row)
        }
    }
    if ($merged.Columns.Count -eq 0) {
        # Schema mínimo se nenhum prestador retornou linhas
        [void]$merged.Columns.Add('COD_PRESTADOR')
        [void]$merged.Columns.Add('IDT_DOCUMENTO')
        [void]$merged.Columns.Add('MENSAGEM')
    }
    return $merged
}

# --- UI ---
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Verificador de Demonstrativos com Erro'
$form.Size = New-Object System.Drawing.Size(640, 520)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.Font = New-Object System.Drawing.Font('Segoe UI', 9)

function Add-LabeledControl {
    param($Form, [string]$LabelText, [int]$Y, $Control, [int]$LabelWidth = 160, [int]$ControlWidth = 420)
    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = $LabelText
    $lbl.Location = New-Object System.Drawing.Point(20, ($Y + 3))
    $lbl.Size = New-Object System.Drawing.Size($LabelWidth, 22)
    $Form.Controls.Add($lbl)
    $Control.Location = New-Object System.Drawing.Point(($LabelWidth + 30), $Y)
    $Control.Size = New-Object System.Drawing.Size($ControlWidth, 24)
    $Form.Controls.Add($Control)
}

$txtUser = New-Object System.Windows.Forms.TextBox
Add-LabeledControl -Form $form -LabelText 'Usuário Oracle' -Y 20 -Control $txtUser

$txtPass = New-Object System.Windows.Forms.TextBox
$txtPass.UseSystemPasswordChar = $true
Add-LabeledControl -Form $form -LabelText 'Senha' -Y 55 -Control $txtPass

$dtPagamento = New-Object System.Windows.Forms.DateTimePicker
$dtPagamento.Format = [System.Windows.Forms.DateTimePickerFormat]::Short
$dtPagamento.Value = (Get-Date).Date
Add-LabeledControl -Form $form -LabelText 'Data de pagamento' -Y 90 -Control $dtPagamento -ControlWidth 160

$grpModo = New-Object System.Windows.Forms.GroupBox
$grpModo.Text = 'Modo'
$grpModo.Location = New-Object System.Drawing.Point(20, 125)
$grpModo.Size = New-Object System.Drawing.Size(580, 70)
$form.Controls.Add($grpModo)

$rbLista = New-Object System.Windows.Forms.RadioButton
$rbLista.Text = 'Arquivo com lista de prestadores'
$rbLista.Location = New-Object System.Drawing.Point(15, 25)
$rbLista.Size = New-Object System.Drawing.Size(280, 24)
$rbLista.Checked = $true
$grpModo.Controls.Add($rbLista)

$rbCompleta = New-Object System.Windows.Forms.RadioButton
$rbCompleta.Text = 'Verificação completa'
$rbCompleta.Location = New-Object System.Drawing.Point(310, 25)
$rbCompleta.Size = New-Object System.Drawing.Size(240, 24)
$grpModo.Controls.Add($rbCompleta)

$txtLista = New-Object System.Windows.Forms.TextBox
$txtLista.ReadOnly = $true
Add-LabeledControl -Form $form -LabelText 'Arquivo de lista' -Y 210 -Control $txtLista -ControlWidth 340

$btnLista = New-Object System.Windows.Forms.Button
$btnLista.Text = 'Procurar...'
$btnLista.Location = New-Object System.Drawing.Point(530, 208)
$btnLista.Size = New-Object System.Drawing.Size(70, 26)
$form.Controls.Add($btnLista)

$txtSaida = New-Object System.Windows.Forms.TextBox
$defaultOut = Join-Path ([Environment]::GetFolderPath('MyDocuments')) ("demonstrativos_{0:yyyyMMdd_HHmmss}.xlsx" -f (Get-Date))
$txtSaida.Text = $defaultOut
Add-LabeledControl -Form $form -LabelText 'Arquivo de saída' -Y 245 -Control $txtSaida -ControlWidth 340

$btnSaida = New-Object System.Windows.Forms.Button
$btnSaida.Text = 'Procurar...'
$btnSaida.Location = New-Object System.Drawing.Point(530, 243)
$btnSaida.Size = New-Object System.Drawing.Size(70, 26)
$form.Controls.Add($btnSaida)

$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(20, 290)
$progress.Size = New-Object System.Drawing.Size(580, 22)
$progress.Minimum = 0
$progress.Maximum = 100
$form.Controls.Add($progress)

$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Text = 'Pronto.'
$lblStatus.Location = New-Object System.Drawing.Point(20, 318)
$lblStatus.Size = New-Object System.Drawing.Size(580, 22)
$form.Controls.Add($lblStatus)

$txtLog = New-Object System.Windows.Forms.TextBox
$txtLog.Multiline = $true
$txtLog.ScrollBars = 'Vertical'
$txtLog.ReadOnly = $true
$txtLog.Location = New-Object System.Drawing.Point(20, 345)
$txtLog.Size = New-Object System.Drawing.Size(580, 80)
$form.Controls.Add($txtLog)

$btnExecutar = New-Object System.Windows.Forms.Button
$btnExecutar.Text = 'Executar'
$btnExecutar.Location = New-Object System.Drawing.Point(420, 440)
$btnExecutar.Size = New-Object System.Drawing.Size(90, 30)
$form.Controls.Add($btnExecutar)

$btnFechar = New-Object System.Windows.Forms.Button
$btnFechar.Text = 'Fechar'
$btnFechar.Location = New-Object System.Drawing.Point(520, 440)
$btnFechar.Size = New-Object System.Drawing.Size(80, 30)
$form.Controls.Add($btnFechar)

function Write-UiLog {
    param([string]$Message)
    $ts = Get-Date -Format 'HH:mm:ss'
    $txtLog.AppendText("[$ts] $Message`r`n")
}

function Update-ListaEnabled {
    $on = $rbLista.Checked
    $txtLista.Enabled = $on
    $btnLista.Enabled = $on
}

$rbLista.Add_CheckedChanged({ Update-ListaEnabled })
$rbCompleta.Add_CheckedChanged({ Update-ListaEnabled })
Update-ListaEnabled

$btnLista.Add_Click({
    $ofd = New-Object System.Windows.Forms.OpenFileDialog
    $ofd.Filter = 'Lista (*.txt;*.csv)|*.txt;*.csv|Todos (*.*)|*.*'
    $ofd.Title = 'Selecione a lista de COD_PRESTADOR'
    if ($ofd.ShowDialog() -eq 'OK') {
        $txtLista.Text = $ofd.FileName
    }
})

$btnSaida.Add_Click({
    $sfd = New-Object System.Windows.Forms.SaveFileDialog
    $sfd.Filter = 'Excel (*.xlsx)|*.xlsx|CSV (*.csv)|*.csv'
    $sfd.Title = 'Arquivo de saída'
    $sfd.FileName = [System.IO.Path]::GetFileName($txtSaida.Text)
    if ($sfd.ShowDialog() -eq 'OK') {
        $txtSaida.Text = $sfd.FileName
    }
})

$btnFechar.Add_Click({ $form.Close() })

$btnExecutar.Add_Click({
    $btnExecutar.Enabled = $false
    $progress.Value = 0
    $txtLog.Clear()
    $conn = $null
    try {
        if ([string]::IsNullOrWhiteSpace($txtUser.Text)) {
            throw 'Informe o usuário Oracle.'
        }
        if ([string]::IsNullOrWhiteSpace($txtPass.Text)) {
            throw 'Informe a senha Oracle.'
        }
        if ([string]::IsNullOrWhiteSpace($txtSaida.Text)) {
            throw 'Informe o arquivo de saída.'
        }
        if ($rbLista.Checked -and [string]::IsNullOrWhiteSpace($txtLista.Text)) {
            throw 'Selecione o arquivo com a lista de prestadores.'
        }

        $dataPag = $dtPagamento.Value.Date
        $lblStatus.Text = 'Conectando ao Oracle...'
        [System.Windows.Forms.Application]::DoEvents()
        Write-UiLog 'Abrindo conexão Oracle (SAUDEP)...'
        $conn = Open-OracleConnection -User $txtUser.Text.Trim() -Password $txtPass.Text

        $prestadores = @()
        if ($rbLista.Checked) {
            Write-UiLog "Lendo lista: $($txtLista.Text)"
            $prestadores = @(Read-ListaPrestadores -Path $txtLista.Text)
        }
        else {
            Write-UiLog "Buscando prestadores com DAT_PAGAMENTO = $($dataPag.ToString('yyyy-MM-dd'))..."
            $prestadores = @(Get-PrestadoresCompleto -Connection $conn -DataPagamento $dataPag)
        }

        if ($prestadores.Count -eq 0) {
            throw 'Nenhum prestador encontrado para processar.'
        }

        Write-UiLog ("Total de prestadores: {0}" -f $prestadores.Count)
        $progress.Maximum = [Math]::Max(1, $prestadores.Count)
        $progress.Value = 0

        $tables = [System.Collections.Generic.List[System.Data.DataTable]]::new()
        $erros = 0
        $ok = 0
        $i = 0
        foreach ($prest in $prestadores) {
            $i++
            $codShow = $prest.Trim()
            $lblStatus.Text = "Processando prestador $codShow ($i de $($prestadores.Count))..."
            $progress.Value = $i
            [System.Windows.Forms.Application]::DoEvents()
            try {
                $dt = Invoke-DetalhePrestador -Connection $conn -CodPrestador $prest -DataPagamento $dataPag
                [void]$tables.Add($dt)
                $ok++
                Write-UiLog "OK $codShow — $($dt.Rows.Count) linha(s)"
            }
            catch {
                $erros++
                Write-UiLog "ERRO $codShow — $($_.Exception.Message)"
            }
        }

        $lblStatus.Text = 'Agregando e exportando...'
        [System.Windows.Forms.Application]::DoEvents()
        $merged = Merge-DataTables -Tables $tables.ToArray()
        $export = Export-Resultados -Table $merged -OutputPath $txtSaida.Text.Trim() -StatusLabel $lblStatus
        Write-UiLog "Concluído. OK=$ok Erros=$erros Linhas=$($merged.Rows.Count) Arquivo=$($export.Path)"
        $lblStatus.Text = "Concluído: $($merged.Rows.Count) linha(s); $erros erro(s). $($export.Path)"
        [System.Windows.Forms.MessageBox]::Show(
            "Processamento finalizado.`nLinhas: $($merged.Rows.Count)`nPrestadores OK: $ok`nErros: $erros`nArquivo: $($export.Path)",
            'Verificador',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        ) | Out-Null
    }
    catch {
        Write-UiLog "FALHA: $($_.Exception.Message)"
        $lblStatus.Text = 'Falha — veja o log.'
        [System.Windows.Forms.MessageBox]::Show(
            $_.Exception.Message,
            'Erro',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    }
    finally {
        if ($null -ne $conn) {
            try { $conn.Close(); $conn.Dispose() } catch { }
        }
        # Limpa senha da memória da caixa (não grava em disco)
        $txtPass.Clear()
        $btnExecutar.Enabled = $true
    }
})

[void]$form.ShowDialog()
