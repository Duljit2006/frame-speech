import re

with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find </div\s*<div class="stage-card" and insert the connector
pattern = r'(</div>)(\s*)(<div class="stage-card">\s*<div class="stage-number">Stage (0[2-7])</div>)'
replacement = r'\1\2<div class="stage-connector"><i class="fa-solid fa-arrow-right"></i></div>\2\3'

html = re.sub(pattern, replacement, html)

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
