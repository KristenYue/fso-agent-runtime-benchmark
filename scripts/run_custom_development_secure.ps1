Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = 'FSO Custom Runtime - Model Authentication'
$form.Size = New-Object System.Drawing.Size(560, 190)
$form.StartPosition = 'CenterScreen'
$form.TopMost = $true
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

$label = New-Object System.Windows.Forms.Label
$label.Text = 'Enter the Alibaba Model Studio API Key (used for this run only; not saved):'
$label.Location = New-Object System.Drawing.Point(20, 20)
$label.Size = New-Object System.Drawing.Size(510, 25)
$form.Controls.Add($label)

$keyBox = New-Object System.Windows.Forms.TextBox
$keyBox.Location = New-Object System.Drawing.Point(20, 52)
$keyBox.Size = New-Object System.Drawing.Size(510, 25)
$keyBox.UseSystemPasswordChar = $true
$form.Controls.Add($keyBox)

$okButton = New-Object System.Windows.Forms.Button
$okButton.Text = 'Start development'
$okButton.Location = New-Object System.Drawing.Point(270, 95)
$okButton.Size = New-Object System.Drawing.Size(125, 32)
$okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.AcceptButton = $okButton
$form.Controls.Add($okButton)

$cancelButton = New-Object System.Windows.Forms.Button
$cancelButton.Text = 'Cancel'
$cancelButton.Location = New-Object System.Drawing.Point(405, 95)
$cancelButton.Size = New-Object System.Drawing.Size(125, 32)
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
$env:FSO_MODEL_API_KEY = $keyBox.Text
$keyBox.Clear()
$form.Dispose()

try {
    & '.\.venv\Scripts\python.exe' 'scripts\run_custom_runtime_development.py'
    $developmentExitCode = $LASTEXITCODE
}
finally {
    $env:FSO_MODEL_API_KEY = $null
}
exit $developmentExitCode
