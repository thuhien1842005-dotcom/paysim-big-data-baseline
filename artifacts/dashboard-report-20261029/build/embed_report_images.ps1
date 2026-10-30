$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$buildTask = Split-Path -Parent $MyInvocation.MyCommand.Path
$docxTask = Join-Path (Split-Path -Parent $buildTask) 'output/Bao_cao_toi_uu_dashboard_PaySim_xem_truoc.docx'
$zTask = [IO.Compression.ZipFile]::Open($docxTask, [IO.Compression.ZipArchiveMode]::Update)
function Read-XmlEntry([string]$nameTask) {
    $readerTask = New-Object IO.StreamReader($zTask.GetEntry($nameTask).Open())
    try { [xml]$xmlTask = $readerTask.ReadToEnd(); return ,$xmlTask } finally { $readerTask.Close() }
}
function Write-XmlEntry([string]$nameTask, $xmlTask) {
    $oldTask = $zTask.GetEntry($nameTask)
    if ($null -ne $oldTask) { $oldTask.Delete() }
    $entryTask = $zTask.CreateEntry($nameTask)
    $writerTask = New-Object IO.StreamWriter($entryTask.Open(), (New-Object Text.UTF8Encoding($false)))
    try { $xmlTask.Save($writerTask) } finally { $writerTask.Close() }
}
try {
    $relsTask = Read-XmlEntry 'word/_rels/document.xml.rels'
    $docTask = Read-XmlEntry 'word/document.xml'
    $typesTask = Read-XmlEntry '[Content_Types].xml'
    $nsTask = New-Object Xml.XmlNamespaceManager($docTask.NameTable)
    $nsTask.AddNamespace('a','http://schemas.openxmlformats.org/drawingml/2006/main')
    $nsTask.AddNamespace('r','http://schemas.openxmlformats.org/officeDocument/2006/relationships')
    $nsTask.AddNamespace('wp','http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing')
    $nsTask.AddNamespace('pic','http://schemas.openxmlformats.org/drawingml/2006/picture')
    $indexTask = 0
    foreach ($relationshipTask in @($relsTask.DocumentElement.ChildNodes)) {
        if ($relationshipTask.Type -notlike '*/image' -or $relationshipTask.TargetMode -ne 'External') { continue }
        $indexTask++
        $imagePathTask = ([Uri]$relationshipTask.Target).LocalPath
        $croppedTask = $imagePathTask -like '*workspace-transaction-result-and-details.png'
        if ($croppedTask) { $imagePathTask = Join-Path $buildTask 'images/transaction-detail.png' }
        $targetTask = "media/report-image-$indexTask.png"
        $imageEntryTask = $zTask.CreateEntry('word/' + $targetTask)
        $streamTask = $imageEntryTask.Open()
        try { $bytesTask = [IO.File]::ReadAllBytes($imagePathTask); $streamTask.Write($bytesTask,0,$bytesTask.Length) } finally { $streamTask.Close() }
        $relationshipTask.SetAttribute('Target',$targetTask)
        $relationshipTask.RemoveAttribute('TargetMode')
        $idTask = $relationshipTask.Id
        foreach ($blipTask in $docTask.SelectNodes("//a:blip[@r:link='$idTask']",$nsTask)) {
            $blipTask.RemoveAttribute('link','http://schemas.openxmlformats.org/officeDocument/2006/relationships')
            $blipTask.SetAttribute('embed','http://schemas.openxmlformats.org/officeDocument/2006/relationships',$idTask)
            if ($croppedTask) {
                $widthBytesTask = [byte[]]$bytesTask[16..19]; [Array]::Reverse($widthBytesTask)
                $heightBytesTask = [byte[]]$bytesTask[20..23]; [Array]::Reverse($heightBytesTask)
                $imageWidthTask = [BitConverter]::ToInt32($widthBytesTask,0)
                $imageHeightTask = [BitConverter]::ToInt32($heightBytesTask,0)
                $inlineTask = $blipTask.SelectSingleNode('ancestor::wp:inline',$nsTask)
                $extentTask = $inlineTask.SelectSingleNode('wp:extent',$nsTask)
                $cyTask = [long]([long]$extentTask.cx * $imageHeightTask / $imageWidthTask)
                $extentTask.SetAttribute('cy',[string]$cyTask)
                $shapeExtentTask = $inlineTask.SelectSingleNode('.//pic:spPr/a:xfrm/a:ext',$nsTask)
                if ($null -ne $shapeExtentTask) { $shapeExtentTask.SetAttribute('cy',[string]$cyTask) }
            }
        }
    }
    if (-not ($typesTask.DocumentElement.ChildNodes | Where-Object Extension -eq 'png')) {
        $pngTask = $typesTask.CreateElement('Default','http://schemas.openxmlformats.org/package/2006/content-types')
        $pngTask.SetAttribute('Extension','png'); $pngTask.SetAttribute('ContentType','image/png')
        [void]$typesTask.DocumentElement.AppendChild($pngTask)
    }
    Write-XmlEntry 'word/_rels/document.xml.rels' $relsTask
    Write-XmlEntry 'word/document.xml' $docTask
    Write-XmlEntry '[Content_Types].xml' $typesTask
    Write-Output "Embedded $indexTask images. The DOCX no longer depends on linked image files."
} finally { $zTask.Dispose() }
