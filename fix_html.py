with open('docs/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

content = '''<div class="pipeline-grid-staircase">
  <!-- Row 1 -->
  <div class="stage-card collapsed" style="grid-column: 1; grid-row: 1;">
    <div class="stage-number">Stage 01</div>
    <h4><i class="fa-solid fa-file-audio" style="color: #E07A5F;"></i> Audio Extractor</h4>
    <div class="stage-details">
      <p>Uses <code>yt-dlp</code> and <code>ffmpeg-python</code>. Resamples input streams to 16kHz, downmixes to mono (<code>ac=1</code>), and forces PCM 16-bit little-endian (<code>pcm_s16le</code>) encoding to normalize mel-spectrogram generation.</p>
      <div class="tech-detail">Sample Rate: 16000Hz | Channels: 1</div>
    </div>
  </div>
  <div class="stage-connector" style="grid-column: 2; grid-row: 1;"><i class="fa-solid fa-arrow-right"></i></div>
  <div class="stage-card collapsed" style="grid-column: 3; grid-row: 1;">
    <div class="stage-number">Stage 02</div>
    <h4><i class="fa-solid fa-microphone-slash" style="color: #F2CC8F;"></i> Silero VAD</h4>
    <div class="stage-details">
      <p>Evaluates <code>float32</code> audio tensors via a lightweight PyTorch neural VAD. Identifies active speech indices against a strict probability threshold to strip compute-heavy silence.</p>
      <div class="tech-detail">Confidence Threshold: &ge; 0.50</div>
    </div>
  </div>

  <!-- Down Arrow 1 -->
  <div class="stage-connector" style="grid-column: 3; grid-row: 2;"><i class="fa-solid fa-arrow-down"></i></div>

  <!-- Row 3 -->
  <div class="stage-card collapsed" style="grid-column: 3; grid-row: 3;">
    <div class="stage-number">Stage 03</div>
    <h4><i class="fa-solid fa-scissors" style="color: #e2e8f0;"></i> Segmentation</h4>
    <div class="stage-details">
      <p>Generates sequential overlapping audio frames using a targeted sliding window algorithm to ensure boundary phonetic transitions are fully captured for the classifier.</p>
      <div class="tech-detail">Window: 3.0s | Stride: 1.0s | Overlap: 66%</div>
    </div>
  </div>
  <div class="stage-connector" style="grid-column: 4; grid-row: 3;"><i class="fa-solid fa-arrow-right"></i></div>
  <div class="stage-card collapsed" style="grid-column: 5; grid-row: 3;">
    <div class="stage-number">Stage 04</div>
    <h4><i class="fa-solid fa-language" style="color: #8B7E74;"></i> SpeechBrain LID</h4>
    <div class="stage-details">
      <p>Executes vectorized inference on 107-class ECAPA-TDNN embeddings. Applies an <code>-inf</code> log-softmax mask to filter out non-Indian language classes prior to activation.</p>
      <div class="tech-detail">Batch Size: 32 | Fallback Threshold: &lt; 0.70</div>
    </div>
  </div>

  <!-- Down Arrow 2 -->
  <div class="stage-connector" style="grid-column: 5; grid-row: 4;"><i class="fa-solid fa-arrow-down"></i></div>

  <!-- Row 5 -->
  <div class="stage-card collapsed" style="grid-column: 5; grid-row: 5;">
    <div class="stage-number">Stage 05</div>
    <h4><i class="fa-solid fa-filter" style="color: #E8DDD3;"></i> Timeline Smoother</h4>
    <div class="stage-details">
      <p>Consolidates raw predictions via non-linear median filtering and confidence-weighted majority voting across 0.5s bins. Applies multi-pass glitch absorption for blocks under 2.5s.</p>
      <div class="tech-detail">Time Bin Resolution: 0.5s</div>
    </div>
  </div>
  <div class="stage-connector" style="grid-column: 6; grid-row: 5;"><i class="fa-solid fa-arrow-right"></i></div>
  <div class="stage-card collapsed" style="grid-column: 7; grid-row: 5;">
    <div class="stage-number">Stage 06</div>
    <h4><i class="fa-solid fa-pen-nib" style="color: #457B9D;"></i> faster-whisper</h4>
    <div class="stage-details">
      <p>Executes CTranslate2 int8 quantized transcription. Disables internal redundant VAD. Applies gated language hinting and drops segments where <code>alpha_count &lt; length * 0.3</code>.</p>
      <div class="tech-detail">Hint Gate: &ge; 0.85 | Quantization: int8</div>
    </div>
  </div>

  <!-- Down Arrow 3 -->
  <div class="stage-connector" style="grid-column: 7; grid-row: 6;"><i class="fa-solid fa-arrow-down"></i></div>

  <!-- Row 7 -->
  <div class="stage-card collapsed" style="grid-column: 7; grid-row: 7;">
    <div class="stage-number">Stage 07</div>
    <h4><i class="fa-solid fa-wand-magic-sparkles" style="color: #B5838D;"></i> Gemini AI Corrector</h4>
    <div class="stage-details">
      <p>Restructures textual fragments into complete sentences while enforcing zero-shot code-switching rules. Utilizes strict JSON schema parsing and dynamic exponential backoff on 429 errors.</p>
      <div class="tech-detail">Batch Size: 100 | Temp: 0.2 | format: JSON</div>
    </div>
  </div>
</div>'''

start = html.find('<div class="pipeline-grid-staircase">')
end = html.find('<!-- Interactive Engineering Deep Dive -->')

html = html[:start] + content + '\n  ' + html[end:]

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Applied downward arrows successfully!')
