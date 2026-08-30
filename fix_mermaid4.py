with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('<div class="mermaid"', '<pre class="mermaid"')
html = html.replace('E --> F["Append to Final Timeline"]\n      </div>', 'E --> F["Append to Final Timeline"]\n      </pre>')

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
