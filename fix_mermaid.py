with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_script = '''  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({ startOnLoad: true, theme: 'base', themeVariables: { primaryColor: '#FFF8F0', primaryTextColor: '#3D2C2E', primaryBorderColor: '#E8DDD3', lineColor: '#E07A5F' } });
  </script>'''

new_script = '''  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({ startOnLoad: false, theme: 'base', themeVariables: { primaryColor: '#FFF8F0', primaryTextColor: '#3D2C2E', primaryBorderColor: '#E8DDD3', lineColor: '#E07A5F' } });
    await mermaid.run({ querySelector: '.mermaid' });
  </script>'''

if old_script in html:
    html = html.replace(old_script, new_script)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Mermaid script updated!")
else:
    print("Could not find the script block.")
