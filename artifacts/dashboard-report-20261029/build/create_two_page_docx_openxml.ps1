$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$buildTask = $PSScriptRoot
$rootTask = (Resolve-Path (Join-Path $buildTask '../../..')).Path
$outTask = (Resolve-Path (Join-Path $buildTask '../output')).Path
$docxTask = Join-Path $outTask 'Tom_tat_toi_uu_dashboard_PaySim_2_trang.docx'
$imagesTask = @(
    (Join-Path $rootTask 'docs/evidence/dashboard-english/baseline-4-desktop.png'),
    (Join-Path $rootTask 'docs/evidence/dashboard-english/workspace-4-desktop.png'),
    (Join-Path $rootTask 'artifacts/dashboard-report-20261029/build/images/transaction-detail.png')
)
foreach ($imageTask in $imagesTask) { if (-not (Test-Path -LiteralPath $imageTask)) { throw "Missing image: $imageTask" } }

function X([string]$s) { [Security.SecurityElement]::Escape($s) }
function Run([string]$text, [bool]$bold = $false, [string]$color = '', [int]$size = 0) {
    $props = ''
    if ($bold) { $props += '<w:b/>' }
    if ($color) { $props += '<w:color w:val="' + $color + '"/>' }
    if ($size -gt 0) { $props += '<w:sz w:val="' + $size + '"/><w:szCs w:val="' + $size + '"/>' }
    return '<w:r><w:rPr>' + $props + '</w:rPr><w:t xml:space="preserve">' + (X $text) + '</w:t></w:r>'
}
function P([string]$text, [string]$style = 'Normal', [bool]$bold = $false) {
    return '<w:p><w:pPr><w:pStyle w:val="' + $style + '"/></w:pPr>' + (Run $text $bold) + '</w:p>'
}
function Rich-P([string]$lead, [string]$rest, [string]$style = 'Normal') {
    return '<w:p><w:pPr><w:pStyle w:val="' + $style + '"/></w:pPr>' + (Run $lead $true '30465D') + (Run $rest) + '</w:p>'
}
function Page-Break { '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' }
function Cell([string]$text, [int]$width, [bool]$header = $false) {
    $fill = if ($header) { '<w:shd w:fill="30465D"/>' } else { '' }
    $color = if ($header) { 'FFFFFF' } else { '' }
    $bold = if ($header) { $true } else { $false }
    $sz = if ($header) { 18 } else { 17 }
    return '<w:tc><w:tcPr><w:tcW w:w="' + $width + '" w:type="dxa"/>' + $fill + '<w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:pStyle w:val="CellText"/></w:pPr>' + (Run $text $bold $color $sz) + '</w:p></w:tc>'
}
function Table([string[]]$widths, [string[][]]$rows) {
    $grid = ''; foreach ($w in $widths) { $grid += '<w:gridCol w:w="' + $w + '"/>' }
    $tr = ''; $rIndex = 0
    foreach ($row in $rows) {
        $tr += '<w:tr><w:trPr><w:cantSplit/></w:trPr>'
        for ($i=0; $i -lt $row.Length; $i++) { $tr += Cell $row[$i] ([int]$widths[$i]) ($rIndex -eq 0) }
        $tr += '</w:tr>'; $rIndex++
    }
    $borders = '<w:tblBorders><w:top w:val="single" w:sz="5" w:color="D9D9D9"/><w:left w:val="single" w:sz="5" w:color="D9D9D9"/><w:bottom w:val="single" w:sz="5" w:color="D9D9D9"/><w:right w:val="single" w:sz="5" w:color="D9D9D9"/><w:insideH w:val="single" w:sz="5" w:color="D9D9D9"/><w:insideV w:val="single" w:sz="5" w:color="D9D9D9"/></w:tblBorders>'
    return '<w:tbl><w:tblPr><w:tblW w:w="10454" w:type="dxa"/><w:tblLayout w:type="fixed"/>' + $borders + '<w:tblCellMar><w:top w:w="70" w:type="dxa"/><w:start w:w="85" w:type="dxa"/><w:bottom w:w="70" w:type="dxa"/><w:end w:w="85" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>' + $grid + '</w:tblGrid>' + $tr + '</w:tbl>'
}
function Png-Dimensions([string]$path) {
    $b = [IO.File]::ReadAllBytes($path); $w = [byte[]]$b[16..19]; $h = [byte[]]$b[20..23]
    [Array]::Reverse($w); [Array]::Reverse($h)
    return @([BitConverter]::ToInt32($w,0), [BitConverter]::ToInt32($h,0))
}
function Picture([int]$imageIndex, [string]$name, [int]$widthPt) {
    $dim = Png-Dimensions $imagesTask[$imageIndex]
    $cx = [long]($widthPt * 12700)
    $cy = [long]($cx * $dim[1] / $dim[0])
    $rid = 'rId' + ($imageIndex + 1)
    $id = $imageIndex + 1
    return '<w:p><w:pPr><w:pStyle w:val="ImagePara"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="' + $cx + '" cy="' + $cy + '"/><wp:docPr id="' + $id + '" name="' + $name + '"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="' + $id + '" name="' + $name + '"/><pic:cNvPicPr><a:picLocks noChangeAspect="1"/></pic:cNvPicPr></pic:nvPicPr><pic:blipFill><a:blip r:embed="' + $rid + '"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="' + $cx + '" cy="' + $cy + '"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
}
function Image-Cell([int]$index, [string]$name, [int]$widthPt) {
    $pict = Picture $index $name $widthPt
    return '<w:tc><w:tcPr><w:tcW w:w="5227" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>' + $pict + '</w:tc>'
}

$bodyTask = ''
$bodyTask += '<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr>' + (Run 'Tóm tắt tối ưu dashboard PaySim' $true '172B43' 34) + '</w:p>'
$bodyTask += P 'Bản xem trước 2 trang · Đối chiếu Control Room gốc và Workspace hiện tại' 'Subtitle'
$bodyTask += Rich-P 'Kết luận: ' 'Workspace bổ sung một luồng tra cứu rõ hơn quanh bảng vốn đã có: lọc theo điều kiện, chọn Event ID, xem chi tiết và tải tập đang lọc. Đây là cải tiến giao diện; chưa có số đo chứng minh thao tác nhanh hơn hoặc pipeline chạy nhanh hơn.'
$bodyTask += P 'Trước và sau' 'Heading1'
$bodyTask += Rich-P 'Bản gốc: ' 'đã có KPI, biểu đồ vận hành, so sánh mô hình và bảng giao dịch với Event ID, Amount, Risk score, Alert. Điểm còn thiếu là bộ lọc nghiệp vụ kết hợp và inspector theo Event ID do ứng dụng thiết kế. Toolbar mặc định vẫn có thể hỗ trợ tìm kiếm hoặc tải dữ liệu cơ bản.'
$bodyTask += '<w:tbl><w:tblPr><w:tblW w:w="10454" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="30" w:type="dxa"/><w:start w:w="60" w:type="dxa"/><w:bottom w:w="30" w:type="dxa"/><w:end w:w="60" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid><w:gridCol w:w="5227"/><w:gridCol w:w="5227"/></w:tblGrid><w:tr>' + (Cell 'Control Room gốc' 5227 $true) + (Cell 'Workspace hiện tại' 5227 $true) + '</w:tr><w:tr><w:trPr><w:cantSplit/></w:trPr>' + (Image-Cell 0 'Control Room gốc' 244) + (Image-Cell 1 'Workspace hiện tại' 244) + '</w:tr></w:tbl>'
$bodyTask += P 'Cặp ảnh dùng cùng snapshot phát lại. Khác biệt chính nằm ở bộ lọc và luồng xem chi tiết quanh bảng, không phải ở bản thân bảng.' 'Caption'
$bodyTask += P 'Tóm tắt khác biệt' 'Heading1'
$rowsTask = [string[][]]@(
    @('Tiêu chí','Trước','Sau'),
    @('Thông tin','KPI, biểu đồ và bảng đã có.','Giữ KPI lõi; sắp xếp lại thứ tự ưu tiên và nhóm nội dung.'),
    @('Tra cứu','Bảng giao dịch, chưa có bộ lọc kết hợp riêng.','Lọc theo loại, tiền, risk score, dự đoán, Event ID và thời gian.'),
    @('Kiểm tra','Đọc thông tin trong các cột.','Chọn giao dịch để xem inspector theo Event ID.'),
    @('Xuất','Toolbar bảng có thể tải dữ liệu cơ bản.','CSV riêng cho tập đã lọc và thứ tự đang xem.')
)
$bodyTask += Table @('1770','4342','4342') $rowsTask
$bodyTask += P 'Các ảnh minh họa chức năng, không phải phép đo hiệu quả; không dùng dữ liệu từ hai thời điểm chạy khác nhau để kết luận hiệu năng.' 'Small'

$bodyTask += Page-Break
$bodyTask += '<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr>' + (Run 'Thay đổi, giới hạn và đánh giá' $true '172B43' 30) + '</w:p>'
$bodyTask += P 'Luồng kiểm tra giao dịch trong Workspace' 'Heading1'
$bodyTask += P 'Người phân tích có thể lọc danh sách bằng nhiều điều kiện, chọn Event ID, xem số tiền, điểm rủi ro, dự đoán và thời điểm chấm, rồi tải CSV của tập đang hiển thị. Lựa chọn được gắn với Event ID để tránh nhầm dòng khi bảng được làm mới.'
$bodyTask += Picture 2 'Inspector theo Event ID' 510
$bodyTask += P 'Ví dụ inspector trong snapshot phát lại. Alert là dự đoán của mô hình, không xác nhận gian lận thực tế.' 'Caption'
$bodyTask += P 'Đánh đổi và giới hạn' 'Heading1'
$bodyTask += Rich-P 'Phạm vi lọc: ' 'chỉ áp dụng cho dữ liệu đã nạp, tối đa 60 giao dịch hoặc 300 cảnh báo; không tra cứu toàn lịch sử và không đổi KPI tổng.' 'Bullet'
$bodyTask += Rich-P 'Bố cục: ' 'hero màu hồng tạo nhận diện nhưng đẩy biểu đồ xuống thấp; nhóm thu gọn giảm nội dung mở cùng lúc nhưng cần thêm lần bấm.' 'Bullet'
$bodyTask += Rich-P 'Hiệu năng: ' 'KPI và luồng dữ liệu lõi được giữ; chưa có benchmark thời gian hiển thị, CPU/RAM hoặc thời gian hoàn thành tác vụ.' 'Bullet'
$bodyTask += Rich-P 'Bằng chứng: ' 'kiểm thử đã lưu ghi nhận 34 passed, 12 skipped, 12 subtests passed. Chưa có nghiên cứu người dùng; lợi ích về tốc độ và khả năng đọc hiện là kỳ vọng. Một lỗi Vega “Unrecognized data set” từng xuất hiện trong một lần rà soát nhưng chưa tái hiện.' 'Bullet'
$bodyTask += P 'Đánh giá tiếp theo' 'Heading1'
$bodyTask += P 'Cho người dùng làm cùng tác vụ trên hai phiên bản, cùng snapshot và thiết bị; đổi thứ tự thử. Ghi thời gian, tỷ lệ hoàn thành đúng, số lần bấm/cuộn và lỗi diễn giải. Đánh giá riêng desktop, mobile và khả năng tiếp cận.'
$bodyTask += P 'Phạm vi: Workspace hiện tại trong mã nguồn, chưa xác nhận triển khai production. Nguồn: dashboard/app.py, dashboard/view_workspace.py, dashboard/ui_transactions.py và docs/evidence/dashboard-english/verification.md.' 'Small'

$stylesTask = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="75" w:line="245" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="0" w:after="35"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:rPr><w:color w:val="596574"/><w:sz w:val="19"/></w:rPr><w:pPr><w:spacing w:after="100"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:keepNext/><w:pPr><w:spacing w:before="110" w:after="45"/></w:pPr><w:rPr><w:b/><w:color w:val="30465D"/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="Caption"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/><w:spacing w:before="20" w:after="65"/></w:pPr><w:rPr><w:color w:val="596574"/><w:sz w:val="16"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Small"><w:name w:val="Small"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="30" w:after="55"/></w:pPr><w:rPr><w:color w:val="596574"/><w:sz w:val="16"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Bullet"><w:name w:val="Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="260" w:hanging="180"/><w:spacing w:after="50" w:line="230"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="CellText"><w:name w:val="CellText"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="220"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="ImagePara"><w:name w:val="ImagePara"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/><w:spacing w:before="10" w:after="10"/></w:pPr></w:style>
</w:styles>
'@
$documentTask = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>' + $bodyTask + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="806" w:right="893" w:bottom="806" w:left="893" w:header="400" w:footer="400" w:gutter="0"/></w:sectPr></w:body></w:document>'
$relsTask = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image3.png"/><Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
$packageRelsTask = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
$typesTask = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'

if (Test-Path -LiteralPath $docxTask) { Remove-Item -LiteralPath $docxTask -Force }
$zipTask = [IO.Compression.ZipFile]::Open($docxTask, [IO.Compression.ZipArchiveMode]::Create)
function Add-TextEntry([string]$nameTask, [string]$valueTask) {
    $entryTask = $zipTask.CreateEntry($nameTask)
    $streamTask = $entryTask.Open()
    $writerTask = New-Object IO.StreamWriter($streamTask, [Text.UTF8Encoding]::new($false))
    try { $writerTask.Write($valueTask) } finally { $writerTask.Dispose() }
}
try {
    Add-TextEntry '[Content_Types].xml' $typesTask
    Add-TextEntry '_rels/.rels' $packageRelsTask
    Add-TextEntry 'word/document.xml' $documentTask
    Add-TextEntry 'word/styles.xml' $stylesTask
    Add-TextEntry 'word/_rels/document.xml.rels' $relsTask
    for ($i=0; $i -lt $imagesTask.Count; $i++) {
        $entryTask = $zipTask.CreateEntry("word/media/image$($i+1).png")
        $streamTask = $entryTask.Open()
        try { $bytesTask = [IO.File]::ReadAllBytes($imagesTask[$i]); $streamTask.Write($bytesTask,0,$bytesTask.Length) } finally { $streamTask.Dispose() }
    }
} finally { $zipTask.Dispose() }
Write-Output "Created $docxTask with 2 explicit pages and $($imagesTask.Count) embedded images."
