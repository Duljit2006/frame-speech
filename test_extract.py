import re

with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start_idx = html.find('<div class="pipeline-grid">')
end_idx = html.find('<!-- Interactive Engineering Deep Dive -->')

grid_html = html[start_idx:end_idx]

# Split grid_html by '<div class="stage-card">'
parts = grid_html.split('<div class="stage-card">')

cards = []
for p in parts[1:]: # Skip the first part which is just the opening tag and whitespace
    # Find where the card ends. It ends before '<div class="stage-connector">' or the end of the grid.
    idx = p.find('<div class="stage-connector">')
    if idx != -1:
        card = p[:idx].strip()
    else:
        # Last card. Strip the closing tags of the grid container.
        card = p.strip()
        if card.endswith('</div>\n    </div>'):
            card = card[:-14].strip()
        elif card.endswith('</div></div>'):
            card = card[:-12].strip()
        # Just to be safe, find the last </div> and we might have one too many.
        # It's better to just trim from the end until the closing </div> of the stage-details.
        # Actually, let's just use the known structure.
        
    cards.append('<div class="stage-card">\n' + card)

print(f"Found {len(cards)} cards")
for i, c in enumerate(cards):
    print(f"Card {i+1} length: {len(c)}")
    print(c[-50:])
