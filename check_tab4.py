with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start = html.find('<!-- Interactive Scripts -->')
print(html[start:start+1500])
