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

    // Track region toggle
    let selectedRegion = 'indian';
    const regionBtns = document.querySelectorAll('#workspace-transcriber #tx-region-group .toggle-btn');
    regionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            regionBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedRegion = btn.dataset.region;
        });
    });

    function resetStepper() {
        const stepLid = document.getElementById('step-lid');
        const stepTx = document.getElementById('step-tx');
        const stepGemini = document.getElementById('step-gemini');
        
        if (stepLid) stepLid.className = 'step active theme-sage';
        if (stepTx) stepTx.className = 'step pending theme-gold';
        if (stepGemini) stepGemini.className = 'step pending theme-coral';
        
        const logLid = document.getElementById('log-lid');
        const logTx = document.getElementById('log-tx');
        const logGemini = document.getElementById('log-gemini');
        
        if (logLid) logLid.textContent = 'Waiting to start...';
        if (logTx) logTx.textContent = 'Waiting to start...';
        if (logGemini) logGemini.textContent = 'Waiting to start...';
    }

    function updateStepper(progressText) {
        const stepLid = document.getElementById('step-lid');
        const stepTx = document.getElementById('step-tx');
        const stepGemini = document.getElementById('step-gemini');

        const logLid = document.getElementById('log-lid');
        const logTx = document.getElementById('log-tx');
        const logGemini = document.getElementById('log-gemini');

        function setStepState(step, baseClass, state) {
            step.className = `step ${state} ${baseClass}`;
        }

        if (progressText.includes('Gemini:')) {
            setStepState(stepLid, 'theme-sage', 'completed');
            setStepState(stepTx, 'theme-gold', 'completed');
            setStepState(stepGemini, 'theme-coral', 'active');
            logGemini.textContent = progressText;
            logLid.textContent = "Completed";
            logTx.textContent = "Completed";
        } else if (progressText.includes('Transcribing Block')) {
            setStepState(stepLid, 'theme-sage', 'completed');
            setStepState(stepTx, 'theme-gold', 'active');
            setStepState(stepGemini, 'theme-coral', 'pending');
            logTx.textContent = progressText;
            logLid.textContent = "Completed";
        } else {
            setStepState(stepLid, 'theme-sage', 'active');
            setStepState(stepTx, 'theme-gold', 'pending');
            setStepState(stepGemini, 'theme-coral', 'pending');
            logLid.textContent = progressText;
        }
    }

    let txTimerInterval = null;
    let txStartTime = null;

    function showStatus(jobId) {
        if (inputZone) inputZone.classList.add('hidden');
        if (resultsZone) resultsZone.classList.add('hidden');
        if (statusZone) statusZone.classList.remove('hidden');
        if (jobIdSpan) jobIdSpan.textContent = jobId;
        resetStepper();

        if (txTimerInterval) clearInterval(txTimerInterval);
        txStartTime = Date.now();
        
        // Start the UI update immediately so it doesn't sit on 00:00 for 1s
        const updateTimer = () => {
            const timerEl = document.getElementById('tx-timer');
            if (timerEl && App && typeof App.formatTime === 'function') {
                timerEl.textContent = App.formatTime(Math.floor((Date.now() - txStartTime) / 1000));
            }
        };
        updateTimer();
        txTimerInterval = setInterval(updateTimer, 1000);

        App.subscribeToJob(jobId,
            (data) => {
                if (data.progress) {
                    const stepLid = document.getElementById('step-lid');
                    if (stepLid) {
                        updateStepper(data.progress);
                    } else {
                        // Fallback if index.html is cached
                        const stZone = document.getElementById('tx-status');
                        if (stZone) {
                            let fallbackEl = stZone.querySelector('.fallback-log');
                            if (!fallbackEl) {
                                fallbackEl = document.createElement('p');
                                fallbackEl.className = 'fallback-log step-log';
                                stZone.appendChild(fallbackEl);
                            }
                            fallbackEl.textContent = data.progress;
                        }
                    }
                }
            },
            (result) => { showResults(result); },
            (err) => {
                if (txTimerInterval) clearInterval(txTimerInterval);
                const logLid = document.getElementById('log-lid');
                if (logLid) logLid.textContent = `Error: ${err}`;
                else alert(`Error: ${err}`);
            }
        );
    }

    function showResults(result) {
        if (txTimerInterval) {
            clearInterval(txTimerInterval);
            const totalSeconds = Math.floor((Date.now() - txStartTime) / 1000);
            const totalTimeEl = document.getElementById('tx-total-time');
            if (totalTimeEl && App && typeof App.formatTime === 'function') {
                totalTimeEl.textContent = App.formatTime(totalSeconds);
            }
        }

        if (statusZone) statusZone.classList.add('hidden');
        if (resultsZone) resultsZone.classList.remove('hidden');

        App.embedVideo('tx-video-container', result.video_embed_url);
        renderTranscript(result.segments);
        renderSummaryChart('tx-lid-chart', 'tx-lid-legend', result.lid_summary, false);
        if (result.corrected_summary) {
            renderSummaryChart('tx-corrected-chart', 'tx-corrected-legend', result.corrected_summary, false);
        }

        // Set download links
        document.getElementById('tx-download-srt').href = result.srt_download;
        document.getElementById('tx-download-txt').href = result.txt_download;
    }

    function renderTranscript(segments) {
        const body = document.getElementById('tx-transcript-body');
        if (!body) return;
        body.innerHTML = '';

        if (!segments || segments.length === 0) {
            body.innerHTML = '<p style="color:var(--secondary-text)">No speech detected.</p>';
            return;
        }

        try {
            segments.forEach(seg => {
                const div = document.createElement('div');
                div.className = 'transcript-segment';
                
                // Safe language extraction
                const lang = seg.language || 'Unknown';
                const textStr = seg.text || '';
                const startTime = seg.start || 0;

                let langColor = '#cccccc';
                if (App && typeof App.getLanguageColor === 'function') {
                    langColor = App.getLanguageColor(lang);
                }

                div.style.borderLeft = `4px solid ${langColor}`;
                div.style.backgroundColor = `${langColor}10`; // 10% opacity for subtle background

                const timeDiv = document.createElement('div');
                timeDiv.className = 'transcript-time';
                if (App && typeof App.formatTime === 'function') {
                    timeDiv.textContent = App.formatTime(startTime);
                }

                const contentDiv = document.createElement('div');
                contentDiv.className = 'transcript-content';

                const langTag = document.createElement('span');
                langTag.className = 'transcript-lang-tag';
                langTag.textContent = lang;
                langTag.style.backgroundColor = langColor;
                langTag.style.color = '#fff';

                const textP = document.createElement('p');
                textP.className = 'transcript-text';
                
                // Highlight code-switching: parse English (Latin) words
                let highlightedText = textStr;
                try {
                    const englishRegex = /([a-zA-Z0-9_'-]+)/g;
                    let englishColor = '#457B9D';
                    if (App && typeof App.getLanguageColor === 'function') {
                        englishColor = App.getLanguageColor('English');
                    }
                    highlightedText = textStr.replace(englishRegex, `<span class="code-switch" style="color: ${englishColor}; font-weight: 600;">$1</span>`);
                } catch (err) {
                    console.error("Regex highlight error:", err);
                }
                
                textP.innerHTML = highlightedText;

                contentDiv.appendChild(langTag);
                contentDiv.appendChild(textP);

                div.appendChild(timeDiv);
                div.appendChild(contentDiv);
                body.appendChild(div);
            });
        } catch (error) {
            console.error("Transcript render error:", error);
            const errP = document.createElement('p');
            errP.style.color = 'red';
            errP.textContent = 'Error rendering transcript data.';
            body.appendChild(errP);
        }
    }

    function renderSummaryChart(chartId, legendId, summary, isWordLevel) {
        const chart = document.getElementById(chartId);
        const legend = document.getElementById(legendId);

        if (!chart || !legend) return;

        chart.innerHTML = '';
        legend.innerHTML = '';

        if (!summary || summary.length === 0) return;

        try {
            summary.forEach((item, index) => {
                const lang = item.language || 'Unknown';
                let color = chartColors[index % chartColors.length];
                if (App && typeof App.getLanguageColor === 'function') {
                    color = App.getLanguageColor(lang);
                }

                // Chart segment
                const segment = document.createElement('div');
                segment.className = 'summary-segment';
                segment.style.width = '0%';
                segment.style.backgroundColor = color;
                const pct = (item.percentage || 0).toFixed(1);
                segment.title = `${lang}: ${pct}%`;
                chart.appendChild(segment);

                setTimeout(() => {
                    segment.style.width = `${item.percentage || 0}%`;
                }, 100);

                // Legend item
                const legItem = document.createElement('div');
                legItem.className = 'legend-item';
                legItem.innerHTML = `
                    <div class="legend-color" style="background-color: ${color}"></div>
                    <span><strong>${lang}</strong> (${pct}%)</span>
                `;
                legend.appendChild(legItem);
            });
        } catch (error) {
            console.error("Summary chart render error:", error);
        }
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
                    use_lid_hints: useLidHints,
                    region: selectedRegion
                })
            });

            const data = await res.json();
            if (data.job_id) showStatus(data.job_id);

        } catch (e) {
            alert('Failed to start transcription job: ' + e.stack);
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
        formData.append('region', selectedRegion);

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
            alert('Failed to upload file: ' + e.stack);
        }
    }
});
