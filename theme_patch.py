import re

with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update Google Fonts
html = re.sub(
    r'<link href=\"https://fonts.googleapis.com/css2\?family=Plus\+Jakarta.*?rel=\"stylesheet\">',
    '<link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@500;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap\" rel=\"stylesheet\">',
    html
)

# 2. Update Prism Theme to Light
html = html.replace('prism-tomorrow.min.css', 'prism.min.css')

# 3. Update CSS Variables & Styles
css_vars = '''    /* FrameSpeech Light Theme */
    :root {
      --bg-dark: #FFF8F0;
      --bg-card: #FFFDF9;
      --bg-card-hover: #FFFFFF;
      --border-color: #E8DDD3;
      --border-glow: #E07A5F;
      --primary: #E07A5F;
      --primary-gradient: linear-gradient(135deg, #E07A5F 0%, #F2CC8F 100%);
      --accent-cyan: #81B29A;
      --accent-emerald: #81B29A;
      --accent-amber: #F2CC8F;
      --text-main: #3D2C2E;
      --text-muted: #8B7E74;
      --font-sans: 'Inter', sans-serif;
      --font-heading: 'Outfit', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }'''
html = re.sub(r':root\s*\{.*?(?=\* \{)', css_vars + '\n\n    ', html, flags=re.DOTALL)

# Update Typography
html = re.sub(r'(body\s*\{[^}]*?)font-family: var\(--font-sans\);', r'\1font-family: var(--font-sans);', html)
html = html.replace('body {', 'h1, h2, h3, h4 { font-family: var(--font-heading); }\n\n    body {')

# Update Glows
glows = '''    .glow-bg {
      position: fixed;
      width: 600px;
      height: 600px;
      border-radius: 50%;
      filter: blur(140px);
      pointer-events: none;
      z-index: -1;
      opacity: 0.4;
    }
    .glow-1 { top: -100px; left: -100px; background: #F2CC8F; }
    .glow-2 { top: 40%; right: -150px; background: #E07A5F; }
    .glow-3 { bottom: -100px; left: 30%; background: #81B29A; }'''
html = re.sub(r'\.glow-bg\s*\{.*?\.glow-3.*?\}', glows, html, flags=re.DOTALL)

# Update Header & Logo
html = re.sub(r'header\s*\{.*?\}', 'header { position: sticky; top: 0; backdrop-filter: blur(16px); background: rgba(255, 248, 240, 0.85); border-bottom: 1px solid var(--border-color); z-index: 100; padding: 1rem 2rem; }', html, flags=re.DOTALL)
html = re.sub(r'\.logo\s*\{.*?\}', '.logo { display: flex; align-items: center; gap: 0.75rem; font-weight: 800; font-size: 1.3rem; color: var(--text-main); text-decoration: none; font-family: var(--font-heading); }', html, flags=re.DOTALL)
html = re.sub(r'\.logo i\s*\{.*?\}', '.logo i { color: var(--primary); }', html, flags=re.DOTALL)

# Update Buttons
html = re.sub(r'\.btn-primary\s*\{.*?\}', '.btn-primary { display: inline-flex; align-items: center; gap: 0.6rem; padding: 0.85rem 1.8rem; background: var(--text-main); border: none; border-radius: 12px; color: #FFFDF9; text-decoration: none; font-weight: 600; font-size: 1rem; transition: all 0.2s ease; }', html, flags=re.DOTALL)
html = re.sub(r'\.btn-primary:hover\s*\{.*?\}', '.btn-primary:hover { transform: translateY(-2px); background: #2a1e20; box-shadow: 0 10px 15px -3px rgba(61, 44, 46, 0.1); }', html, flags=re.DOTALL)
html = re.sub(r'\.btn-secondary\s*\{.*?\}', '.btn-secondary { display: inline-flex; align-items: center; gap: 0.6rem; padding: 0.85rem 1.8rem; background: transparent; border: 1px solid var(--text-main); border-radius: 12px; color: var(--text-main); text-decoration: none; font-weight: 600; font-size: 1rem; transition: all 0.2s ease; }', html, flags=re.DOTALL)
html = re.sub(r'\.btn-secondary:hover\s*\{.*?\}', '.btn-secondary:hover { background: rgba(61, 44, 46, 0.05); }', html, flags=re.DOTALL)

# Update Badges & Code Sections
html = re.sub(r'\.badge-hero\s*\{.*?\}', '.badge-hero { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem; background: rgba(224, 122, 95, 0.1); border: 1px solid rgba(224, 122, 95, 0.2); border-radius: 9999px; color: var(--primary); font-size: 0.85rem; font-weight: 600; margin-bottom: 1.5rem; text-transform: uppercase; letter-spacing: 0.05em; font-family: var(--font-heading); }', html, flags=re.DOTALL)
html = re.sub(r'\.tech-detail\s*\{.*?\}', '.tech-detail { font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted); background: rgba(61, 44, 46, 0.03); padding: 0.5rem; border-radius: 6px; margin-top: 0.75rem; border-left: 3px solid var(--primary); }', html, flags=re.DOTALL)

html = re.sub(r'\.code-comparison\s*\{.*?\}', '.code-comparison { background: #FFFDF9; border-radius: 8px; padding: 1rem; font-family: var(--font-mono); font-size: 0.9rem; margin-top: 1rem; border: 1px solid var(--border-color); box-shadow: inset 0 2px 4px rgba(0,0,0,0.02); }', html, flags=re.DOTALL)
html = html.replace('.code-bad { color: #f87171; }', '.code-bad { color: #E07A5F; }')
html = html.replace('.code-good { color: #34d399; }', '.code-good { color: #81B29A; }')

html = re.sub(r'\.code-section\s*\{.*?\}', '.code-section { background: #FFFDF9; border: 1px solid var(--border-color); border-radius: 16px; overflow: hidden; margin-bottom: 4rem; box-shadow: 0 4px 6px -1px rgba(61, 44, 46, 0.05); }', html, flags=re.DOTALL)
html = re.sub(r'\.code-section-header\s*\{.*?\}', '.code-section-header { background: rgba(61, 44, 46, 0.02); padding: 1rem 1.5rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }', html, flags=re.DOTALL)
html = re.sub(r'\.code-section-header h3\s*\{.*?\}', '.code-section-header h3 { font-size: 1rem; font-family: var(--font-mono); color: var(--text-main); display: flex; align-items: center; gap: 0.5rem; margin: 0; }', html, flags=re.DOTALL)

# Update Footer
html = re.sub(r'footer\s*\{.*?\}', 'footer { border-top: 1px solid var(--border-color); padding: 3rem 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.9rem; background: var(--bg-card); }', html, flags=re.DOTALL)

# Specific tweaks for icons in boxes
html = html.replace('background: rgba(99, 102, 241, 0.15)', 'background: rgba(224, 122, 95, 0.1)')
html = html.replace('border: 1px solid rgba(99, 102, 241, 0.3)', 'border: 1px solid rgba(224, 122, 95, 0.2)')

# GitHub Button
html = html.replace('background: rgba(255, 255, 255, 0.06);', 'background: transparent;')

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Theme patch applied.')
