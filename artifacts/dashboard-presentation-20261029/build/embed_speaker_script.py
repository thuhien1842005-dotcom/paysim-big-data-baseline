"""Put the revised presenter script into its corresponding illustrated slides."""
from pathlib import Path
import html
import re

BUILD = Path(__file__).resolve().parent
OUTPUT = BUILD.parent / 'output'
SCRIPT = OUTPUT / 'Loi_thoai_trinh_bay_dashboard_PaySim.md'
PRESENTATION = OUTPUT / 'Thuyet_trinh_toi_uu_dashboard_PaySim.html'


def inline(text):
    escaped = html.escape(text)
    escaped = re.sub(r'\*\[([^\]]+)\]\*', r'<em class="direction">[\1]</em>', escaped)
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)


def load_slides():
    markdown = SCRIPT.read_text(encoding='utf-8')
    sections = re.split(r'(?=^## Slide \d+ · )', markdown, flags=re.MULTILINE)
    slides = {}
    for section in sections:
        header = re.match(r'^## Slide (\d+) · [^\n]+\n', section)
        if not header:
            continue
        n = int(header.group(1))
        body = re.split(r'^## ', section[header.end():], maxsplit=1, flags=re.MULTILINE)[0].strip()
        ending = re.search(r'^\*\*(Chuyển slide|Kết thúc):\*\*\s*(.+)$', body, re.MULTILINE)
        if not ending:
            raise ValueError(f'Missing transition for slide {n}')
        speech = body[:ending.start()].strip()
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', speech) if p.strip()]
        slides[n] = (paragraphs, ending.group(1), ending.group(2).strip())
    if set(slides) != set(range(1, 9)):
        raise ValueError('Expected scripts for slides 1 through 8')
    return slides


def main():
    slides = load_slides()
    original = PRESENTATION.read_text(encoding='utf-8')
    note_pattern = re.compile(r'<section class="notes">.*?</section>', re.DOTALL)
    existing_notes = note_pattern.findall(original)
    if len(existing_notes) != 8:
        raise ValueError('Expected exactly eight existing presenter note sections')

    new_notes = []
    for n, old in enumerate(existing_notes, start=1):
        status = re.search(r'<p class="status">.*?</p>', old, re.DOTALL)
        source = re.search(r'<p class="source">.*?</p>', old, re.DOTALL)
        if not status or not source:
            raise ValueError(f'Missing evidence or sources for slide {n}')
        paragraphs, ending_label, ending = slides[n]
        lines = ''.join(f'<p class="spoken">{inline(p)}</p>' for p in paragraphs)
        new_notes.append(
            f'<section class="notes"><button class="copy" data-copy="{n}">Sao chép lời nói</button>'
            '<h3>Lời thoại và hướng dẫn chỉ hình</h3>'
            '<p class="status">Chỉ dẫn trong ngoặc vuông giúp luyện nói, không đọc thành lời.</p>'
            f'{lines}<h3>{html.escape(ending_label)}</h3><p class="spoken">{inline(ending)}</p>'
            f'{status.group(0)}{source.group(0)}</section>'
        )

    replacements = iter(new_notes)
    result = note_pattern.sub(lambda _: next(replacements), original)
    if note_pattern.sub('', original) != note_pattern.sub('', result):
        raise ValueError('Unexpected change outside the presenter notes')
    if result.count('<img ') != original.count('<img '):
        raise ValueError('Unexpected change to embedded images')
    PRESENTATION.write_text(result, encoding='utf-8')
    print(f'Updated {len(new_notes)} slide notes; preserved {result.count("<img ")} embedded images.')


if __name__ == '__main__':
    main()
