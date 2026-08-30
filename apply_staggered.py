import re

with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start_idx = html.find('<div class="pipeline-grid">')
end_idx = html.find('<!-- Interactive Engineering Deep Dive -->')
grid_html = html[start_idx:end_idx]

parts = grid_html.split('<div class="stage-card">')
cards = []
for p in parts[1:]:
    idx = p.find('<div class="stage-connector">')
    if idx != -1:
        card = p[:idx].strip()
        cards.append('<div class="stage-card">\n' + card)
    else:
        # Card 7 has trailing section/div ends
        card = p.split('</div>\n    </div>')[0].strip()
        cards.append('<div class="stage-card">\n' + card + '\n      </div>') # Ensure properly closed

css_addition = '''
    /* Staggered Pipeline Layout */
    .pipeline-staggered {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      max-width: 1050px;
      margin: 0 auto 4rem auto;
      align-items: flex-start;
    }
    .stagger-row {
      display: flex;
      align-items: stretch;
      gap: 1.25rem;
      position: relative;
    }
    .row-1 { margin-left: 0; }
    .row-2 { margin-left: 15%; }
    .row-3 { margin-left: 30%; }
    .row-4 { margin-left: 45%; }
    
    .stage-card {
      width: 320px;
      flex-shrink: 0;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 1.5rem;
      transition: all 0.2s ease;
      position: relative;
      display: flex;
      flex-direction: column;
      cursor: pointer;
      justify-content: center;
      min-height: 120px;
    }
    
    .stage-connector {
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--primary);
      font-size: 1.5rem;
      opacity: 0.8;
      width: 30px;
    }
    
    .row-connector {
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--primary);
      font-size: 1.5rem;
      opacity: 0.8;
      width: 30px;
      /* Rotate to point down-right */
      transform: rotate(45deg);
    }

    @media (max-width: 950px) {
      .pipeline-staggered {
        align-items: center;
      }
      .stagger-row {
        flex-direction: column;
        margin-left: 0 !important;
        width: 100%;
        max-width: 350px;
      }
      .stage-card { width: 100%; }
      .row-connector { transform: rotate(90deg); margin: 0.5rem 0; }
      .stage-connector { transform: rotate(90deg); height: 2rem; width: 100%; }
    }
'''

new_grid_html = f'''<div class="pipeline-staggered">
      <!-- Row 1 -->
      <div class="stagger-row row-1">
        {cards[0]}
        <div class="stage-connector"><i class="fa-solid fa-arrow-right"></i></div>
        {cards[1]}
        <div class="row-connector"><i class="fa-solid fa-arrow-right"></i></div>
      </div>
      
      <!-- Row 2 -->
      <div class="stagger-row row-2">
        {cards[2]}
        <div class="stage-connector"><i class="fa-solid fa-arrow-right"></i></div>
        {cards[3]}
        <div class="row-connector"><i class="fa-solid fa-arrow-right"></i></div>
      </div>

      <!-- Row 3 -->
      <div class="stagger-row row-3">
        {cards[4]}
        <div class="stage-connector"><i class="fa-solid fa-arrow-right"></i></div>
        {cards[5]}
        <div class="row-connector"><i class="fa-solid fa-arrow-right"></i></div>
      </div>

      <!-- Row 4 (Output) -->
      <div class="stagger-row row-4">
        {cards[6]}
      </div>
    </div>
    
  </section>
'''

# Replace old grid with new one
html = html[:start_idx] + new_grid_html + '\n  <!-- Interactive Engineering Deep Dive -->' + html.split('<!-- Interactive Engineering Deep Dive -->')[1]

# Remove old .pipeline-grid and .stage-card CSS block
css_pattern = r'\.pipeline-grid\s*\{.*?\.stage-connector\s*\{.*?\}'
# We will just replace it if we can find it.
# Actually, the simplest way is to replace .pipeline-grid { display: flex; ... } and .stage-card { ... } etc.
# But it's easier to just strip out the old block using regex and append the new one.
# Let's find /* Pipeline Architecture Grid */
start_css = html.find('/* Pipeline Architecture Grid */')
end_css = html.find('/* Interactive Tabs System */')
if start_css != -1 and end_css != -1:
    html = html[:start_css] + css_addition + '\n\n    ' + html[end_css:]

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Applied staggered layout successfully!")
