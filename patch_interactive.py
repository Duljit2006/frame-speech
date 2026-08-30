import re

with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update CSS
css_addition = """
    .stage-card {
      cursor: pointer;
      justify-content: center;
    }
    
    .stage-card h4 {
      margin-bottom: 0;
      transition: margin 0.3s ease;
    }
    
    .stage-card:hover h4 {
      margin-bottom: 0.5rem;
    }

    .stage-details {
      max-height: 0;
      opacity: 0;
      overflow: hidden;
      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .stage-card:hover .stage-details {
      max-height: 400px;
      opacity: 1;
      margin-top: 0.5rem;
    }
"""

if ".stage-details {" not in html:
    html = html.replace('.stage-card:hover {', css_addition + '\n    .stage-card:hover {')

# 2. Wrap content
# We want to find:
# <h4>...</h4>
# <p>...</p>
# <div class="tech-detail">...</div>
# And replace with:
# <h4>...</h4>
# <div class="stage-details">
#   <p>...</p>
#   <div class="tech-detail">...</div>
# </div>

pattern = r'(<h4>.*?</h4>)\s*(<p>.*?</p>)\s*(<div class="tech-detail">.*?</div>)'
replacement = r'\1\n        <div class="stage-details">\n          \2\n          \3\n        </div>'

html = re.sub(pattern, replacement, html, flags=re.DOTALL)

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Patch applied successfully.")
