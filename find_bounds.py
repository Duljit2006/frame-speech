with open('docs/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start = -1
end = -1
for i, line in enumerate(lines):
    if '<div class="pipeline-grid">' in line:
        start = i
    elif '<!-- Interactive Engineering Deep Dive -->' in line:
        end = i
        break

print(f"Start: {start}, End: {end}")
