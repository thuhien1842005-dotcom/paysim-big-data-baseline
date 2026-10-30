$ErrorActionPreference = 'Stop'
$buildTask = Split-Path -Parent $MyInvocation.MyCommand.Path
$reportTask = Split-Path -Parent $buildTask
$rootTask = [IO.Path]::GetFullPath((Join-Path $buildTask '../../..'))
$outTask = Join-Path $reportTask 'output'
$specTask = Get-Content -LiteralPath (Join-Path $buildTask 'report_content.json') -Raw -Encoding utf8 | ConvertFrom-Json
$docxTask = Join-Path $outTask 'Bao_cao_toi_uu_dashboard_PaySim_xem_truoc.docx'
$pdfTask = Join-Path $buildTask 'Bao_cao_toi_uu_dashboard_PaySim_xem_truoc.pdf'
$htmlTask = Join-Path $buildTask 'report_source.html'
function Escape-Text([string]$textTask) { return [Net.WebUtility]::HtmlEncode($textTask) }
function Image-Tag([string]$relativeTask, [int]$widthTask) {
    $pathTask = [IO.Path]::GetFullPath((Join-Path $rootTask $relativeTask))
    if (-not (Test-Path -LiteralPath $pathTask)) { throw "Missing image: $pathTask" }
    $bytesTask = [IO.File]::ReadAllBytes($pathTask)
    $widthBytesTask = [byte[]]$bytesTask[16..19]
    $heightBytesTask = [byte[]]$bytesTask[20..23]
    [Array]::Reverse($widthBytesTask)
    [Array]::Reverse($heightBytesTask)
    $imageWidthTask = [BitConverter]::ToInt32($widthBytesTask, 0)
    $imageHeightTask = [BitConverter]::ToInt32($heightBytesTask, 0)
    $heightTask = $widthTask * $imageHeightTask / $imageWidthTask
    return '<img src="' + ([Uri]$pathTask).AbsoluteUri + '" width="' + [int]($widthTask * 96 / 72) + '" height="' + [int]($heightTask * 96 / 72) + '" style="width:' + $widthTask + 'pt;height:' + $heightTask.ToString([Globalization.CultureInfo]::InvariantCulture) + 'pt">'
}
$partsTask = New-Object 'Collections.Generic.List[string]'
$partsTask.Add(@'
<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page{size:8.5in 11in;margin:0.78in 0.85in}
body{font-family:"Times New Roman";font-size:13pt;color:#000;line-height:1.15}
p{margin:0 0 7pt;text-align:justify;text-indent:18pt}
.doc-title{font-size:18pt;font-weight:bold;text-align:center;text-indent:0;margin-bottom:10pt}
.subtitle{text-align:center;text-indent:0;font-size:13pt;margin-bottom:6pt}
.date{text-align:center;text-indent:0;font-size:11pt;margin-bottom:18pt}
h1{font-size:15pt;color:#000;margin:16pt 0 8pt;page-break-after:avoid}
h2{font-size:13pt;color:#000;margin:12pt 0 6pt;page-break-after:avoid}
.figure{text-align:center;text-indent:0;margin:10pt 0 5pt;page-break-after:avoid}
.caption{text-align:center;text-indent:0;font-size:11pt;font-style:italic;margin:3pt 0 4pt;page-break-after:avoid}
.source{font-size:10pt;text-indent:0;margin:0 0 12pt;text-align:left}
.reference{font-size:11pt;text-indent:0;text-align:left;margin-bottom:7pt}
table{border-collapse:collapse;width:100%;margin:8pt 0 12pt;table-layout:fixed}
td,th{border:1pt solid #d9d9d9;padding:6pt;font-size:11pt;vertical-align:middle;text-align:left}
th{background:#30465d;color:#fff;font-weight:bold}tr{page-break-inside:avoid}
.image-pair td{text-align:center}.image-pair{page-break-inside:avoid}
</style></head><body>
'@)
$partsTask.Add('<p class="doc-title">' + (Escape-Text $specTask.title) + '</p>')
$partsTask.Add('<p class="subtitle">' + (Escape-Text $specTask.subtitle) + '</p>')
$partsTask.Add('<p class="date">Ng&#224;y l&#7853;p 29/10/2026</p>')
foreach ($blockTask in $specTask.blocks) {
    switch ($blockTask.type) {
        'p' { $partsTask.Add('<p>' + (Escape-Text $blockTask.text) + '</p>') }
        'h1' { $partsTask.Add('<h1>' + (Escape-Text $blockTask.text) + '</h1>') }
        'h2' { $partsTask.Add('<h2>' + (Escape-Text $blockTask.text) + '</h2>') }
        'ref' { $partsTask.Add('<p class="reference">' + (Escape-Text $blockTask.text) + '</p>') }
        'figure' {
            $partsTask.Add('<p class="figure">' + (Image-Tag $blockTask.path $blockTask.width) + '</p>')
            $partsTask.Add('<p class="caption">' + (Escape-Text $blockTask.caption) + '</p>')
            $partsTask.Add('<p class="source">' + (Escape-Text $blockTask.source) + '</p>')
        }
        'figure_pair' {
            $partsTask.Add('<table class="image-pair"><tr><th width="50%">' + (Escape-Text $blockTask.left_label) + '</th><th width="50%">' + (Escape-Text $blockTask.right_label) + '</th></tr><tr><td>' + (Image-Tag $blockTask.left 220) + '</td><td>' + (Image-Tag $blockTask.right 220) + '</td></tr></table>')
            $partsTask.Add('<p class="caption">' + (Escape-Text $blockTask.caption) + '</p>')
            $partsTask.Add('<p class="source">' + (Escape-Text $blockTask.source) + '</p>')
        }
        'table' {
            $partsTask.Add('<table><thead><tr>')
            for ($cTask = 0; $cTask -lt $blockTask.headers.Count; $cTask++) {
                $partsTask.Add('<th width="' + $blockTask.widths[$cTask] + '%">' + (Escape-Text $blockTask.headers[$cTask]) + '</th>')
            }
            $partsTask.Add('</tr></thead><tbody>')
            foreach ($rowTask in $blockTask.rows) {
                $partsTask.Add('<tr>')
                foreach ($cellTask in $rowTask) { $partsTask.Add('<td>' + (Escape-Text $cellTask) + '</td>') }
                $partsTask.Add('</tr>')
            }
            $partsTask.Add('</tbody></table>')
        }
        default { throw "Unknown block type: $($blockTask.type)" }
    }
}
$partsTask.Add('</body></html>')
[IO.File]::WriteAllText($htmlTask, ($partsTask -join "`r`n"), (New-Object Text.UTF8Encoding($true)))

$wordTask = $null
$documentTask = $null
try {
    $wordTask = New-Object -ComObject Word.Application
    $wordTask.Visible = $false
    $wordTask.DisplayAlerts = 0
    $wordTask.ScreenUpdating = $false
    $documentTask = $wordTask.Documents.Open($htmlTask, $false, $false)
    Write-Output 'Opened report content.'
    $documentTask.PageSetup.PageWidth = 612
    $documentTask.PageSetup.PageHeight = 792
    $documentTask.PageSetup.TopMargin = 56.16
    $documentTask.PageSetup.BottomMargin = 56.16
    $documentTask.PageSetup.LeftMargin = 61.2
    $documentTask.PageSetup.RightMargin = 61.2
    $documentTask.Styles.Item(-1).Font.Name = 'Times New Roman'
    $documentTask.Styles.Item(-1).Font.Size = 13
    $documentTask.Styles.Item(-1).Font.Color = 0
    foreach ($styleTask in @(-63,-2,-3)) {
        $documentTask.Styles.Item($styleTask).Font.Name = 'Times New Roman'
        $documentTask.Styles.Item($styleTask).Font.Color = 0
        $documentTask.Styles.Item($styleTask).Font.Bold = $true
        $documentTask.Styles.Item($styleTask).ParagraphFormat.FirstLineIndent = 0
        $documentTask.Styles.Item($styleTask).ParagraphFormat.KeepWithNext = $true
    }
    $documentTask.Styles.Item(-63).Font.Size = 18
    $documentTask.Styles.Item(-2).Font.Size = 15
    $documentTask.Styles.Item(-3).Font.Size = 13
    $documentTask.Paragraphs.Item(1).Range.Style = -63
    $documentTask.Paragraphs.Item(1).Range.Font.Color = 0
    $documentTask.Paragraphs.Item(1).Range.ParagraphFormat.Alignment = 1
    $documentTask.Paragraphs.Item(1).Range.ParagraphFormat.Borders.Enable = 0

    for ($tableIndexTask = 1; $tableIndexTask -le $documentTask.Tables.Count; $tableIndexTask++) {
        $tableTask = $documentTask.Tables.Item($tableIndexTask)
        $tableTask.Rows.AllowBreakAcrossPages = $false
        $tableTask.Rows.Item(1).HeadingFormat = $true
        $tableTask.Rows.Item(1).Range.ParagraphFormat.KeepWithNext = $true
        Write-Output "Formatted table $tableIndexTask."
    }
    $footerTask = $documentTask.Sections.Item(1).Footers.Item(1).Range
    $footerTask.Font.Name = 'Times New Roman'
    $footerTask.Font.Size = 10
    [void]$footerTask.Fields.Add($footerTask, 33)
    $footerTask.ParagraphFormat.FirstLineIndent = 0
    $footerTask.ParagraphFormat.Alignment = 1
    $documentTask.Repaginate()
    $documentTask.SaveAs2($docxTask, 12)
    $pageCountTask = $documentTask.ComputeStatistics(2)
    $documentTask.ExportAsFixedFormat($pdfTask, 17)
    Write-Output "Created DOCX: $docxTask"
    Write-Output "Pages: $pageCountTask; tables: $($documentTask.Tables.Count); images: $($documentTask.InlineShapes.Count)"
} finally {
    if ($null -ne $documentTask) { $documentTask.Close(0); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($documentTask) }
    if ($null -ne $wordTask) { $wordTask.Quit(0); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordTask) }
}
