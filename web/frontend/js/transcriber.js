document.addEventListener('DOMContentLoaded', () => {
    const submitBtn = document.getElementById('tx-submit-url');
    const urlInput = document.getElementById('tx-url-input');
    const dropZone = document.getElementById('tx-drop-zone');
    const fileInput = document.getElementById('tx-file-input');
    const modelSelect = document.getElementById('tx-model-size');

    const inputZone = document.querySelector('#workspace-transcriber .input-zone');
    const statusZone = document.getElementById('tx-status');
    const resultsZone = document.getElementById('tx-results');

    const jobIdSpan = document.getElementById('tx-job-id');
    const statusText = statusZone.querySelector('.status-text');

    const chartColors = ['#81B29A', '#E07A5F', '#F2CC8F', '#3D2C2E', '#8B7E74', '#E8DDD3',
                         '#B5838D', '#6D6875', '#FFB4A2', '#457B9D'];

    // Track selected task
    let selectedTask = 'transcribe';
    const toggleBtns = document.querySelectorAll('#workspace-transcriber .toggle-btn[data-task]');
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            toggleBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedTask = btn.dataset.task;
        });
    });

    // Track hinting toggle
    let useLidHints = true;
    const btnHintLid = document.getElementById('btn-hint-lid');
    const btnHintAuto = document.getElementById('btn-hint-auto');
    if (btnHintLid && btnHintAuto) {
        btnHintLid.addEventListener('click', () => {
            btnHintLid.classList.add('active');
            btnHintAuto.classList.remove('active');
            useLidHints = true;
        });
        btnHintAuto.addEventListener('click', () => {
            btnHintAuto.classList.add('active');
            btnHintLid.classList.remove('active');
            useLidHints = false;
        });
    }

    function showStatus(jobId) {
        inputZone.classList.add('hidden');
        resultsZone.classList.add('hidden');
        statusZone.classList.remove('hidden');
        jobIdSpan.textContent = jobId;
        statusText.textContent = 'Transcribing audio with AI...';

        App.subscribeToJob(jobId,
            (data) => {},
            (result) => { showResults(result); },
            (err) => {
                statusText.textContent = `Error: ${err}`;
                document.querySelector('#workspace-transcriber .loader').classList.add('hidden');
            }
        );
    }

    function showResults(result) {
        statusZone.classList.add('hidden');
        resultsZone.classList.remove('hidden');

        App.embedVideo('tx-video-container', result.video_embed_url);
        renderTranscript(result.segments);
        renderSummaryChart('tx-lid-chart', 'tx-lid-legend', result.lid_summary, false);

        // Set download links
        document.getElementById('tx-download-srt').href = result.srt_download;
        document.getElementById('tx-download-txt').href = result.txt_download;
    }

    function renderTranscript(segments) {
        const body = document.getElementById('tx-transcript-body');
        body.innerHTML = '';

        if (!segments || segments.length === 0) {
            body.innerHTML = '<p style="color:var(--secondary-text)">No speech detected.</p>';
            return;
        }

        segments.forEach(seg => {
            const div = document.createElement('div');
            div.className = 'transcript-segment';

            const timeDiv = document.createElement('div');
            timeDiv.className = 'transcript-time';
            timeDiv.textContent = App.formatTime(seg.start);

            const contentDiv = document.createElement('div');
            contentDiv.className = 'transcript-content';

            const langTag = document.createElement('span');
            langTag.className = 'transcript-lang-tag';
            langTag.textContent = seg.language;

            const textP = document.createElement('p');
            textP.className = 'transcript-text';
            textP.textContent = seg.text;

            contentDiv.appendChild(langTag);
            contentDiv.appendChild(textP);

            div.appendChild(timeDiv);
            div.appendChild(contentDiv);
            body.appendChild(div);
        });
    }

    function renderSummaryChart(chartId, legendId, summary, isWordLevel) {
        const chart = document.getElementById(chartId);
        const legend = document.getElementById(legendId);

        chart.innerHTML = '';
        legend.innerHTML = '';

        if (!summary || summary.length === 0) return;

        summary.forEach((item, index) => {
            const color = chartColors[index % chartColors.length];

            // Chart segment
            const segment = document.createElement('div');
            segment.className = 'summary-segment';
            segment.style.width = '0%';
            segment.style.backgroundColor = color;
            const pct = item.percentage.toFixed(1);
            segment.title = `${item.language}: ${pct}%`;
            chart.appendChild(segment);

            setTimeout(() => {
                segment.style.width = `${item.percentage}%`;
            }, 100);

            // Legend
            const legItem = document.createElement('div');
            legItem.className = 'legend-item';
            const detail = isWordLevel
                ? `${item.word_count} words`
                : `${item.duration_seconds}s`;
            legItem.innerHTML = `
                <div class="legend-color" style="background-color: ${color}"></div>
                <span><strong>${item.language}</strong> (${pct}%) — ${detail}</span>
            `;
            legend.appendChild(legItem);
        });
    }

    // Submit URL
    submitBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) return;

        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Starting...';

            const res = await fetch('/api/transcribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url,
                    model_size: modelSelect.value,
                    task: selectedTask,
                    use_lid_hints: useLidHints
                })
            });

            const data = await res.json();
            if (data.job_id) showStatus(data.job_id);

        } catch (e) {
            alert('Failed to start transcription job');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Transcribe';
        }
    });

    // Drag and Drop
    dropZone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, e => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener('change', function() {
        if (this.files.length) uploadFile(this.files[0]);
    });

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('model_size', modelSelect.value);
        formData.append('task', selectedTask);
        formData.append('use_lid_hints', useLidHints);

        try {
            const p = dropZone.querySelector('p');
            const originalText = p.innerHTML;
            p.textContent = 'Uploading...';

            const res = await fetch('/api/transcribe/upload', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (data.job_id) showStatus(data.job_id);

            p.innerHTML = originalText;
        } catch (e) {
            alert('Failed to upload file');
        }
    }
});
