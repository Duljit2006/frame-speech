import re

with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_block = '''Raw Whisper Output:
          <br>
          <span style="color: #E07A5F;">মোর ঘর গুয়াহাটীত।</span> (Bengali script hallucination)
          <br><br>
          After Gemini Correction:
          <br>
          <span style="color: #81B29A;">মোৰ ঘৰ গুৱাহাটীত।</span> (Assamese script enforced: ৰ, ৱ)'''

# find the exact div content to replace
# Looking for Raw Whisper Output: ... ৰ, ৱ applied
html = re.sub(r'Raw Whisper Output:.*?ৰ, ৱ applied', new_block, html, flags=re.DOTALL)

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Replaced!')
