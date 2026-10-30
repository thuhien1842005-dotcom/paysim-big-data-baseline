param([Parameter(Mandatory=$true)][string]$DocxPath,[Parameter(Mandatory=$true)][string]$PdfPath)
$ErrorActionPreference='Stop'
$wordTask = $null
$docTask = $null
try {
    $wordTask = New-Object -ComObject Word.Application
    $wordTask.Visible = $false
    $wordTask.DisplayAlerts = 0
    $docTask = $wordTask.Documents.Open($DocxPath, $false, $true)
    $docTask.Repaginate()
    $pageCountTask = $docTask.ComputeStatistics(2)
    $docTask.ExportAsFixedFormat($PdfPath, 17)
    Write-Output "Word pages: $pageCountTask"
    Write-Output "Exported PDF: $PdfPath"
} finally {
    if ($null -ne $docTask) { $docTask.Close(0); [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($docTask) }
    if ($null -ne $wordTask) { $wordTask.Quit(0); [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordTask) }
}
