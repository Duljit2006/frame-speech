import re

with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Extract the 7 stage cards
# Find the start and end of the pipeline grid
start_idx = html.find('<div class="pipeline-grid">')
end_idx = html.find('<!-- Interactive Engineering Deep Dive -->')

grid_html = html[start_idx:end_idx]

# Extract each stage card. We can use a regex that matches <div class="stage-card"> up to the next <div class="stage-card"> or end of string.
# Actually, since we know there are exactly 7, let's just split by '<div class="stage-card">'
parts = grid_html.split('<div class="stage-card">')
cards = []
for p in parts[1:]:
    # find the closing </div> of the card.
    # It's a bit tricky because of nested divs, but we know it ends right before either a stage-connector or the end of pipeline-grid.
    # Let's split by '<div class="stage-connector">'
    card_content = p.split('<div class="stage-connector">')[0].strip()
    # Also strip the final </div> of the pipeline-grid if it's the last card
    if card_content.endswith('</div>\n    </div>'):
        card_content = card_content[:-13].strip()
    elif card_content.endswith('</div>\n  </div>'):
        card_content = card_content[:-13].strip()
    elif card_content.endswith('</div></div>'):
        card_content = card_content[:-6].strip()
    elif card_content.endswith('</div>\n    '):
        card_content = card_content[:-11].strip()
        
    # We will reconstruct it cleanly anyway.
    cards.append('<div class="stage-card">\n' + card_content)

# Safety fallback if parsing was weird (which happens with regex on HTML)
# Let's do it much simpler: just find them using BeautifulSoup? No, we don't have it installed guaranteed.
# Let's just use the known structure!
