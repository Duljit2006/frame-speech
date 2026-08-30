with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_str = '''    </div>
  </div>
</div>
  <!-- Interactive Engineering Deep Dive -->'''

new_str = '''    </div>
  </div>
  
  <!-- Hover Hint -->
  <div style="grid-column: 1 / -1; grid-row: 8; text-align: center; color: var(--text-muted); font-size: 0.9rem; margin-top: 1rem; opacity: 0.8; font-family: var(--font-mono);">
    <i class="fa-regular fa-hand-pointer" style="margin-right: 0.4rem;"></i> Hover over the stages to reveal technical details
  </div>
</div>
  <!-- Interactive Engineering Deep Dive -->'''

if old_str in html:
    html = html.replace(old_str, new_str)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Added hover hint!")
else:
    print("Failed to find target string. Check exact whitespace.")
