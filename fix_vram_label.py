with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update JS
js_old = '''      if(step === 1) { bar.style.width = '3%'; bar.dataset.label = 'OS/Idle'; text.innerText = '120 MB / 4096 MB'; }'''
js_new = '''      if(step === 1 || step === 3 || step === 5) { bar.classList.add('small-bar'); } else { bar.classList.remove('small-bar'); }
      if(step === 1) { bar.style.width = '3%'; bar.dataset.label = 'OS/Idle'; text.innerText = '120 MB / 4096 MB'; }'''

if js_old in html:
    html = html.replace(js_old, js_new)
    print('JS updated.')
else:
    print('JS not found.')

# 2. Update CSS
css_old = '''    .vram-fill::after {
      content: attr(data-label);
      position: absolute;
      right: 15px;
      top: 50%;
      transform: translateY(-50%);
      color: #fff;
      font-weight: 600;
      font-size: 0.85rem;
      font-family: var(--font-mono);
    }'''

css_new = '''    .vram-fill::after {
      content: attr(data-label);
      position: absolute;
      right: 15px;
      top: 50%;
      transform: translateY(-50%);
      color: #fff;
      font-weight: 600;
      font-size: 0.85rem;
      font-family: var(--font-mono);
      white-space: nowrap;
    }
    .vram-fill.small-bar::after {
      right: auto;
      left: 100%;
      margin-left: 12px;
      color: var(--text-main);
    }'''

if css_old in html:
    html = html.replace(css_old, css_new)
    print('CSS updated.')
else:
    print('CSS not found.')

# 3. Add small-bar to initial HTML
html = html.replace('<div class="vram-fill" id="vram-bar" data-label="Idle" style="width: 2%;"></div>', '<div class="vram-fill small-bar" id="vram-bar" data-label="Idle" style="width: 3%;"></div>')

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
