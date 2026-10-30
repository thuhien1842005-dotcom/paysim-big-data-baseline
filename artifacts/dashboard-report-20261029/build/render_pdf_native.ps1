param([Parameter(Mandatory=$true)][string]$PdfPath,[Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[void][Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
[void][Windows.Storage.StorageFolder, Windows.Storage, ContentType=WindowsRuntime]
[void][Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType=WindowsRuntime]
[void][Windows.Data.Pdf.PdfPageRenderOptions, Windows.Data.Pdf, ContentType=WindowsRuntime]
[void][Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$taskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
$taskAction = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' } | Select-Object -First 1
function Await-Operation($operationTask, [Type]$resultTypeTask) {
    $taskTask = $taskGeneric.MakeGenericMethod($resultTypeTask).Invoke($null, @($operationTask))
    $taskTask.GetAwaiter().GetResult()
}
function Await-Action($operationTask) {
    $taskTask = $taskAction.Invoke($null, @($operationTask))
    [void]$taskTask.GetAwaiter().GetResult()
}
$pdfFileTask = Await-Operation ([Windows.Storage.StorageFile]::GetFileFromPathAsync([IO.Path]::GetFullPath($PdfPath))) ([Windows.Storage.StorageFile])
$pdfTask = Await-Operation ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($pdfFileTask)) ([Windows.Data.Pdf.PdfDocument])
[IO.Directory]::CreateDirectory([IO.Path]::GetFullPath($OutputDir)) | Out-Null
$folderTask = Await-Operation ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync([IO.Path]::GetFullPath($OutputDir))) ([Windows.Storage.StorageFolder])
for ($indexTask=0; $indexTask -lt $pdfTask.PageCount; $indexTask++) {
    $pageTask = $pdfTask.GetPage($indexTask)
    try {
        $fileTask = Await-Operation ($folderTask.CreateFileAsync(('page-{0}.png' -f ($indexTask+1)), [Windows.Storage.CreationCollisionOption]::ReplaceExisting)) ([Windows.Storage.StorageFile])
        $streamTask = Await-Operation ($fileTask.OpenAsync([Windows.Storage.FileAccessMode]::ReadWrite)) ([Windows.Storage.Streams.IRandomAccessStream])
        try {
            $optionsTask = New-Object Windows.Data.Pdf.PdfPageRenderOptions
            $optionsTask.DestinationWidth = 1275
            Await-Action ($pageTask.RenderToStreamAsync($streamTask, $optionsTask))
        } finally { $streamTask.Dispose() }
    } finally { $pageTask.Dispose() }
}
Write-Output "Rendered $($pdfTask.PageCount) pages into $OutputDir"
