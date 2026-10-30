"""Add direct editing for slide text and speaker notes to the offline HTML."""
from pathlib import Path
import re

BUILD = Path(__file__).resolve().parent
PRESENTATION = BUILD.parent / 'output' / 'Thuyet_trinh_toi_uu_dashboard_PaySim.html'


def main():
    original = PRESENTATION.read_text(encoding='utf-8')
    css = (BUILD / 'note_editor.css').read_text(encoding='utf-8')
    js = (BUILD / 'note_editor.js').read_text(encoding='utf-8')
    slide_css = (BUILD / 'slide_editor.css').read_text(encoding='utf-8')
    slide_js = (BUILD / 'slide_editor.js').read_text(encoding='utf-8')
    if '</script' in js.lower():
        raise ValueError('Editor JavaScript must be safe to embed in a script element')
    if '</script' in slide_js.lower():
        raise ValueError('Slide editor JavaScript must be safe to embed in a script element')
    output = re.sub(r'<style id="inline-notes-style">.*?</style>', '', original, flags=re.DOTALL)
    output = re.sub(r'<script id="inline-notes-editor">.*?</script>', '', output, flags=re.DOTALL)
    output = re.sub(r'<style id="inline-slide-editor-style">.*?</style>', '', output, flags=re.DOTALL)
    output = re.sub(r'<script id="inline-slide-editor">.*?</script>', '', output, flags=re.DOTALL)
    old = "document.addEventListener('keydown',e=>{if(modal.classList.contains('open'))"
    new = "document.addEventListener('keydown',e=>{if(e.target && e.target.isContentEditable)return;if(modal.classList.contains('open'))"
    if old in output:
        output = output.replace(old, new, 1)
    elif new not in output:
        raise ValueError('Could not find the presentation keyboard handler')
    if output.count('</head>') != 1 or output.count('</body>') != 1:
        raise ValueError('Unexpected HTML structure')
    output = output.replace('</head>', f'<style id="inline-notes-style">{css}</style></head>', 1)
    output = output.replace('</head>', f'<style id="inline-slide-editor-style">{slide_css}</style></head>', 1)
    output = output.replace('</body>', f'<script id="inline-notes-editor">{js}</script><script id="inline-slide-editor">{slide_js}</script></body>', 1)
    note_pattern = re.compile(r'<section class="notes">.*?</section>', re.DOTALL)
    if note_pattern.findall(original) != note_pattern.findall(output):
        raise ValueError('Presenter notes unexpectedly changed')
    if original.count('<img ') != output.count('<img '):
        raise ValueError('Embedded images unexpectedly changed')
    PRESENTATION.write_text(output, encoding='utf-8')
    print(f'Enabled inline editing for {len(note_pattern.findall(output))} slides; preserved {output.count("<img ")} images.')


if __name__ == '__main__':
    main()
