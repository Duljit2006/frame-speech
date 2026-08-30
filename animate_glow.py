with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_css = '''    .glow-bg {
      position: fixed;
      width: 600px;
      height: 600px;
      border-radius: 50%;
      filter: blur(140px);
      pointer-events: none;
      z-index: -1;
      opacity: 0.4;
    }
    .glow-1 { top: -100px; left: -100px; background: #F2CC8F; }
    .glow-2 { top: 40%; right: -150px; background: #E07A5F; }
    .glow-3 { bottom: -100px; left: 30%; background: #81B29A; }'''

new_css = '''    .glow-bg {
      position: fixed;
      width: 600px;
      height: 600px;
      border-radius: 50%;
      filter: blur(140px);
      pointer-events: none;
      z-index: -1;
      opacity: 0.4;
      will-change: transform;
    }
    .glow-1 { top: -100px; left: -100px; background: #F2CC8F; animation: float-1 25s infinite ease-in-out; }
    .glow-2 { top: 40%; right: -150px; background: #E07A5F; animation: float-2 30s infinite ease-in-out; }
    .glow-3 { bottom: -100px; left: 30%; background: #81B29A; animation: float-3 28s infinite ease-in-out; }

    @keyframes float-1 {
      0%, 100% { transform: translate(0, 0) scale(1); }
      33% { transform: translate(120px, 80px) scale(1.1); }
      66% { transform: translate(-50px, 150px) scale(0.9); }
    }
    @keyframes float-2 {
      0%, 100% { transform: translate(0, 0) scale(1); }
      33% { transform: translate(-150px, -100px) scale(0.95); }
      66% { transform: translate(80px, -150px) scale(1.05); }
    }
    @keyframes float-3 {
      0%, 100% { transform: translate(0, 0) scale(1); }
      33% { transform: translate(150px, -120px) scale(1.1); }
      66% { transform: translate(-100px, -80px) scale(0.85); }
    }'''

if old_css in html:
    html = html.replace(old_css, new_css)
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Glow animations applied!")
else:
    print("Could not find the exact string to replace.")
