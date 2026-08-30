with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the script block with the simple, standard ESM mermaid
old_script = '''  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    document.addEventListener("DOMContentLoaded", function() {
        mermaid.initialize({ 
            startOnLoad: false, 
            theme: 'base', 
            themeVariables: { 
                primaryColor: '#FFF8F0', 
                primaryTextColor: '#3D2C2E', 
                primaryBorderColor: '#E8DDD3', 
                lineColor: '#E07A5F' 
            } 
        });
        
        let mermaidRendered = false;
        
        document.querySelectorAll('.tab-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            if (btn.dataset.target === 'tab4' && !mermaidRendered) {
              setTimeout(() => {
                try {
                  mermaid.run({ querySelector: '.mermaid' });
                  mermaidRendered = true;
                } catch (e) {
                  console.error(e);
                  mermaid.init(undefined, document.querySelectorAll('.mermaid'));
                }
              }, 100);
            }
          });
        });
    });
  </script>'''

new_script = '''  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({ 
        startOnLoad: true, 
        theme: 'base', 
        themeVariables: { 
            primaryColor: '#FFF8F0', 
            primaryTextColor: '#3D2C2E', 
            primaryBorderColor: '#E8DDD3', 
            lineColor: '#E07A5F' 
        } 
    });
  </script>'''

if old_script in html:
    html = html.replace(old_script, new_script)
    print('Script restored.')
else:
    print('Script not found!')

# Now replace the CSS for tab-content
old_css = '''    .tab-content {
      display: none;
      animation: fadeIn 0.4s ease forwards;
    }
    .tab-content.active {
      display: block;
    }'''

new_css = '''    .tab-content {
      position: absolute;
      left: -9999px;
      visibility: hidden;
      opacity: 0;
    }
    .tab-content.active {
      position: relative;
      left: 0;
      visibility: visible;
      opacity: 1;
      animation: fadeIn 0.4s ease forwards;
    }'''

if old_css in html:
    html = html.replace(old_css, new_css)
    print('CSS fixed.')
else:
    print('CSS not found!')

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
