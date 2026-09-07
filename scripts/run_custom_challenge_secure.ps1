Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = 'FSO Custom Runtime - ONE Frozen Challenge Run'
$form.Size = New-Object System.Drawing.Size(590, 205)
$form.StartPosition = 'CenterScreen'
$form.TopMost = $true
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

$label = New-Object System.Windows.Forms.Label
$label.Text = 'Enter the Alibaba Model Studio API Key. This starts the single frozen Challenge run:'
$label.Location = New-Object System.Drawing.Point(20, 18)
$label.Size = New-Object System.Drawing.Size(540, 25)
$form.Controls.Add($label)

$warning = New-Object System.Windows.Forms.Label
$warning.Text = 'After the run ledger is created, this experiment must not be rerun.'
$warning.Location = New-Object System.Drawing.Point(20, 43)
$warning.Size = New-Object System.Drawing.Size(540, 22)
$form.Controls.Add($warning)

$keyBox = New-Object System.Windows.Forms.TextBox
$keyBox.Location = New-Object System.Drawing.Point(20, 72)
$keyBox.Size = New-Object System.Drawing.Size(540, 25)
$keyBox.UseSystemPasswordChar = $true
$form.Controls.Add($keyBox)

$okButton = New-Object System.Windows.Forms.Button
$okButton.Text = 'Run once'
$okButton.Location = New-Object System.Drawing.Point(320, 112)
$okButton.Size = New-Object System.Drawing.Size(110, 32)
$okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.AcceptButton = $okButton
$form.Controls.Add($okButton)

$cancelButton = New-Object System.Windows.Forms.Button
$cancelButton.Text = 'Cancel'
$cancelButton.Location = New-Object System.Drawing.Point(450, 112)
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

$env:FSO_MODEL_PROVIDER = 'AlibabaCloud-ModelStudio-Beijing'
$env:FSO_MODEL_BASE_URL = 'https://ws-jiq52ldhidcs83sm.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'
$env:FSO_MODEL_ID = 'qwen3.7-plus-2026-05-26'
$env:FSO_CUSTOM_RUNTIME_CHALLENGE_APPROVAL = 'custom-runtime-challenge-v1-final-once'
$env:FSO_MODEL_API_KEY = $keyBox.Text
$keyBox.Clear()
$form.Dispose()

try {
    & '.\.venv\Scripts\python.exe' 'scripts\run_custom_runtime_challenge_once.py'
    $challengeExitCode = $LASTEXITCODE
}
finally {
    $env:FSO_MODEL_API_KEY = $null
    $env:FSO_CUSTOM_RUNTIME_CHALLENGE_APPROVAL = $null
}
exit $challengeExitCode
