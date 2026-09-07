Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = 'FSO Custom Runtime - Recovery v1.1'
$form.Size = New-Object System.Drawing.Size(610, 215)
$form.StartPosition = 'CenterScreen'
$form.TopMost = $true
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

$label = New-Object System.Windows.Forms.Label
$label.Text = 'Enter the exact Alibaba Model Studio API Key (ASCII only, no spaces):'
$label.Location = New-Object System.Drawing.Point(20, 18)
$label.Size = New-Object System.Drawing.Size(560, 24)
$form.Controls.Add($label)

$warning = New-Object System.Windows.Forms.Label
$warning.Text = 'A non-Challenge probe runs first. Any failure stops before a new Challenge ledger.'
$warning.Location = New-Object System.Drawing.Point(20, 43)
$warning.Size = New-Object System.Drawing.Size(560, 24)
$form.Controls.Add($warning)

$keyBox = New-Object System.Windows.Forms.TextBox
$keyBox.Location = New-Object System.Drawing.Point(20, 74)
$keyBox.Size = New-Object System.Drawing.Size(560, 25)
$keyBox.UseSystemPasswordChar = $true
$form.Controls.Add($keyBox)

$okButton = New-Object System.Windows.Forms.Button
$okButton.Text = 'Probe, then run'
$okButton.Location = New-Object System.Drawing.Point(330, 118)
$okButton.Size = New-Object System.Drawing.Size(120, 32)
$okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.AcceptButton = $okButton
$form.Controls.Add($okButton)

$cancelButton = New-Object System.Windows.Forms.Button
$cancelButton.Text = 'Cancel'
$cancelButton.Location = New-Object System.Drawing.Point(470, 118)
$cancelButton.Size = New-Object System.Drawing.Size(110, 32)
$cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.CancelButton = $cancelButton
$form.Controls.Add($cancelButton)

$form.Add_Shown({ $keyBox.Focus() })
$dialogResult = $form.ShowDialog()
if ($dialogResult -ne [System.Windows.Forms.DialogResult]::OK -or [string]::IsNullOrWhiteSpace($keyBox.Text)) {
    $form.Dispose()
    exit 2
}

$candidateKey = $keyBox.Text
$keyBox.Clear()
$form.Dispose()
if ($candidateKey -match '[^\x00-\x7F]') {
    Write-Error 'Credential preflight failed: API key contains non-ASCII characters. Stopped before probe and Challenge.'
    $candidateKey = $null
    exit 3
}
if ($candidateKey -match '\s') {
    Write-Error 'Credential preflight failed: API key contains whitespace. Stopped before probe and Challenge.'
    $candidateKey = $null
    exit 3
}

$env:FSO_MODEL_PROVIDER = 'AlibabaCloud-ModelStudio-Beijing'
$env:FSO_MODEL_BASE_URL = 'https://ws-jiq52ldhidcs83sm.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'
$env:FSO_MODEL_ID = 'qwen3.7-plus-2026-05-26'
$env:FSO_CUSTOM_RUNTIME_RECOVERY_APPROVAL = 'custom-runtime-challenge-recovery-v1-1-final-once'
$env:FSO_MODEL_API_KEY = $candidateKey
$candidateKey = $null

try {
    & '.\.venv\Scripts\python.exe' 'scripts\probe_custom_runtime_recovery_v1_1.py'
    if ($LASTEXITCODE -ne 0) {
        Write-Error 'Recovery probe failed. Stopped before the new Challenge ledger.'
        exit $LASTEXITCODE
    }
    & '.\.venv\Scripts\python.exe' 'scripts\run_custom_runtime_challenge_v1_1_once.py'
    $recoveryExitCode = $LASTEXITCODE
}
finally {
    $env:FSO_MODEL_API_KEY = $null
    $env:FSO_CUSTOM_RUNTIME_RECOVERY_APPROVAL = $null
}
exit $recoveryExitCode
