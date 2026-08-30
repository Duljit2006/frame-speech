import re

with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start_idx = html.find('<div class="pipeline-staggered">')
end_idx = html.find('<!-- Interactive Engineering Deep Dive -->')
staggered_html = html[start_idx:end_idx]

# Extract cards based on known content
cards = []
for i in range(1, 8):
    stage_num = f'Stage 0{i}'
    idx = staggered_html.find(f'<div class="stage-number">{stage_num}</div>')
    
    # Backtrack to the <div class="stage-card">
    card_start = staggered_html.rfind('<div class="stage-card">', 0, idx)
    
    # Find the end of the stage-details
    details_end = staggered_html.find('</div>', staggered_html.find('</div>', staggered_html.find('<div class="tech-detail">', idx)))
    
    # The card ends after the stage-details closing div, plus one more closing div for the stage-card itself.
    # The structure is:
    # <div class="stage-card">
    #   <div class="stage-number">...</div>
    #   <h4>...</h4>
    #   <div class="stage-details">
    #     <p>...</p>
    #     <div class="tech-detail">...</div>
    #   </div>
    # </div>
    
    # We can just extract it using regex matching the card structure:
    pattern = r'(<div class="stage-card">\s*<div class="stage-number">' + stage_num + r'</div>.*?</div>\s*</div>)'
    match = re.search(pattern, staggered_html, re.DOTALL)
    if match:
        cards.append(match.group(1))

print(f"Extracted {len(cards)} cards")

if len(cards) == 7:
    grid_html = f'''<div class="pipeline-grid-staircase">
      <!-- Row 1 -->
      <div style="grid-column: 1; grid-row: 1;">
        {cards[0].replace('<div class="stage-card">', '<div class="stage-card collapsed">')}
      </div>
      <div class="stage-connector" style="grid-column: 2; grid-row: 1;"><i class="fa-solid fa-arrow-right"></i></div>
      <div style="grid-column: 3; grid-row: 1;">
        {cards[1].replace('<div class="stage-card">', '<div class="stage-card collapsed">')}
      </div>
      <div class="row-connector" style="grid-column: 4; grid-row: 1;"><i class="fa-solid fa-arrow-right" style="transform: rotate(45deg);"></i></div>

      <!-- Row 2 -->
      <div style="grid-column: 3; grid-row: 2;">
        {cards[2].replace('<div class="stage-card">', '<div class="stage-card collapsed">')}
      </div>
      <div class="stage-connector" style="grid-column: 4; grid-row: 2;"><i class="fa-solid fa-arrow-right"></i></div>
      <div style="grid-column: 5; grid-row: 2;">
        {cards[3].replace('<div class="stage-card">', '<div class="stage-card collapsed">')}
      </div>
      <div class="row-connector" style="grid-column: 6; grid-row: 2;"><i class="fa-solid fa-arrow-right" style="transform: rotate(45deg);"></i></div>

      <!-- Row 3 -->
      <div style="grid-column: 5; grid-row: 3;">
        {cards[4].replace('<div class="stage-card">', '<div class="stage-card collapsed">')}
      </div>
      <div class="stage-connector" style="grid-column: 6; grid-row: 3;"><i class="fa-solid fa-arrow-right"></i></div>
      <div style="grid-column: 7; grid-row: 3;">
        {cards[5].replace('<div class="stage-card">', '<div class="stage-card collapsed">')}
      </div>
      <div class="row-connector" style="grid-column: 8; grid-row: 3;"><i class="fa-solid fa-arrow-right" style="transform: rotate(45deg);"></i></div>

      <!-- Row 4 -->
      <div style="grid-column: 7; grid-row: 4;">
        {cards[6].replace('<div class="stage-card">', '<div class="stage-card collapsed">')}
      </div>
    </div>
'''

    # Replace the HTML
    html = html[:start_idx] + grid_html + '\n  <!-- Interactive Engineering Deep Dive -->' + html[end_idx + 44:]
    
    # Replace the CSS
    css_start = html.find('/* Staggered Pipeline Layout */')
    css_end = html.find('/* Interactive Tabs System */')
    
    new_css = '''/* Staggered Pipeline Grid Layout */
    .pipeline-grid-staircase {
      display: grid;
      grid-template-columns: auto 30px auto 30px auto 30px auto 30px;
      gap: 1.25rem;
      margin: 0 0 4rem 0;
      justify-content: start;
    }
    
    .stage-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.25rem;
      transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.2s ease;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      justify-content: center;
      overflow: hidden;
      min-height: 90px;
    }
    
    .stage-card.collapsed {
      width: 230px;
    }
    
    .stage-card:hover {
      width: 380px;
    }
    
    .stage-card h4 {
      white-space: nowrap;
      margin-bottom: 0;
      transition: margin 0.3s ease;
    }
    
    .stage-card:hover h4 {
      margin-bottom: 0.5rem;
    }
    
    .stage-details {
      width: 340px; /* Keep text wrap fixed during animation */
      max-height: 0;
      opacity: 0;
      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stage-card:hover .stage-details {
      max-height: 400px;
      opacity: 1;
      margin-top: 0.5rem;
    }

    .stage-connector, .row-connector {
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--primary);
      font-size: 1.2rem;
      opacity: 0.6;
    }

    @media (max-width: 1050px) {
      .pipeline-grid-staircase {
        display: flex;
        flex-direction: column;
        align-items: center;
      }
      .pipeline-grid-staircase > div { grid-column: auto !important; grid-row: auto !important; }
      .stage-card.collapsed { width: 100%; max-width: 380px; }
      .stage-card:hover { width: 100%; max-width: 380px; }
      .stage-details { width: 100%; }
      .row-connector, .stage-connector { transform: rotate(90deg) !important; height: 2rem; width: 100%; }
    }
'''
    html = html[:css_start] + new_css + '\n    ' + html[css_end:]
    
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Grid applied successfully.")
else:
    print("Failed to extract all 7 cards.")
