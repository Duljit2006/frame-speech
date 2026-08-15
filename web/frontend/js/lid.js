document.addEventListener('DOMContentLoaded', () => {
    const submitBtn = document.getElementById('lid-submit-url');
    const urlInput = document.getElementById('lid-url-input');
    const dropZone = document.getElementById('lid-drop-zone');
    const fileInput = document.getElementById('lid-file-input');
    
    const inputZone = document.querySelector('#workspace-lid .input-zone');
    const statusZone = document.getElementById('lid-status');
    const resultsZone = document.getElementById('lid-results');
    
    const jobIdSpan = document.getElementById('lid-job-id');
    const statusText = statusZone.querySelector('.status-text');
    
    const chartColors = ['#81B29A', '#E07A5F', '#F2CC8F', '#3D2C2E', '#8B7E74', '#E8DDD3'];

    // Track region toggle
    let selectedRegion = 'indian';
    const regionBtns = document.querySelectorAll('#workspace-lid #lid-region-group .toggle-btn');
    regionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            regionBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedRegion = btn.dataset.region;
        });
    });

    function resetStepper() {
        const stepExt = document.getElementById('step-lid-ext');
        const stepProc = document.getElementById('step-lid-proc');
        const stepSmooth = document.getElementById('step-lid-smooth');
        
        if (stepExt) stepExt.className = 'step active theme-sage';
        if (stepProc) stepProc.className = 'step pending theme-gold';
        if (stepSmooth) stepSmooth.className = 'step pending theme-coral';
        
        const logExt = document.getElementById('log-lid-ext');
        const logProc = document.getElementById('log-lid-proc');
        const logSmooth = document.getElementById('log-lid-smooth');
        
        if (logExt) logExt.textContent = 'Waiting to start...';
        if (logProc) logProc.textContent = 'Waiting to start...';
        if (logSmooth) logSmooth.textContent = 'Waiting to start...';
    }

    function updateStepper(progressText) {
        const stepExt = document.getElementById('step-lid-ext');
        const stepProc = document.getElementById('step-lid-proc');
        const stepSmooth = document.getElementById('step-lid-smooth');

        const logExt = document.getElementById('log-lid-ext');
        const logProc = document.getElementById('log-lid-proc');
        const logSmooth = document.getElementById('log-lid-smooth');

        function setStepState(step, baseClass, state) {
            if (step) step.className = `step ${state} ${baseClass}`;
        }

        if (progressText.includes('Applying Temporal Smoothing')) {
            setStepState(stepExt, 'theme-sage', 'completed');
            setStepState(stepProc, 'theme-gold', 'completed');
            setStepState(stepSmooth, 'theme-coral', 'active');
            if (logSmooth) logSmooth.textContent = progressText;
            if (logExt) logExt.textContent = "Completed";
            if (logProc) logProc.textContent = "Completed";
        } else if (progressText.includes('Initializing LID') || progressText.includes('LID: Processing')) {
            setStepState(stepExt, 'theme-sage', 'completed');
            setStepState(stepProc, 'theme-gold', 'active');
            setStepState(stepSmooth, 'theme-coral', 'pending');
            if (logProc) logProc.textContent = progressText;
            if (logExt) logExt.textContent = "Completed";
        } else {
            setStepState(stepExt, 'theme-sage', 'active');
            setStepState(stepProc, 'theme-gold', 'pending');
            setStepState(stepSmooth, 'theme-coral', 'pending');
            if (logExt) logExt.textContent = progressText;
        }
    }

    let lidTimerInterval = null;
    let lidStartTime = null;

    function showStatus(jobId) {
        inputZone.classList.add('hidden');
        resultsZone.classList.add('hidden');
        statusZone.classList.remove('hidden');
        jobIdSpan.textContent = jobId;
        resetStepper();
        
        if (lidTimerInterval) clearInterval(lidTimerInterval);
        lidStartTime = Date.now();
        lidTimerInterval = setInterval(() => {
            const timerEl = document.getElementById('lid-timer');
            if (timerEl) {
                timerEl.textContent = App.formatTime(Math.floor((Date.now() - lidStartTime) / 1000));
            }
        }, 1000);

        App.subscribeToJob(jobId, 
            (data) => {
                if (data.progress) {
                    updateStepper(data.progress);
                }
            },
            (result) => { showResults(result); },
            (err) => {
                if (lidTimerInterval) clearInterval(lidTimerInterval);
                const logExt = document.getElementById('log-lid-ext');
                if (logExt) logExt.textContent = `Error: ${err}`;
                else alert(`Error: ${err}`);
            }
        );
    }

    function showResults(result) {
        if (lidTimerInterval) {
            clearInterval(lidTimerInterval);
            const totalSeconds = Math.floor((Date.now() - lidStartTime) / 1000);
            document.getElementById('lid-total-time').textContent = App.formatTime(totalSeconds);
        }

        statusZone.classList.add('hidden');
        resultsZone.classList.remove('hidden');
        
        App.embedVideo('lid-video-container', result.video_embed_url);
        renderTimeline(result.timeline);
        renderSummaryChart(result.summary);
    }
    
    function renderTimeline(timeline) {
        const tbody = document.getElementById('lid-timeline-body');
        tbody.innerHTML = '';
        
        timeline.forEach(block => {
            const tr = document.createElement('tr');
            
            // Time range
            const timeTd = document.createElement('td');
            timeTd.textContent = `${App.formatTime(block.start)} → ${App.formatTime(block.end)}`;
            
            // Duration
            const durationTd = document.createElement('td');
            const durationSecs = block.end - block.start;
            durationTd.textContent = `${durationSecs.toFixed(1)}s`;
            durationTd.style.color = 'var(--secondary-text)';
            
            // Language
            const langTd = document.createElement('td');
            const span = document.createElement('span');
            span.className = 'lang-badge';
            span.textContent = block.language;
            
            // Use App.getLanguageColor
            span.style.backgroundColor = App.getLanguageColor(block.language);
            span.style.color = '#fff';
            langTd.appendChild(span);
            
            // Confidence
            const confTd = document.createElement('td');
            confTd.textContent = (block.confidence * 100).toFixed(1) + '%';
            
            tr.appendChild(timeTd);
            tr.appendChild(durationTd);
            tr.appendChild(langTd);
            tr.appendChild(confTd);
            tbody.appendChild(tr);
        });
    }
    
    function renderSummaryChart(summary) {
        const chart = document.getElementById('lid-summary-chart');
        const legend = document.getElementById('lid-summary-legend');
        
        chart.innerHTML = '';
        legend.innerHTML = '';
        
        summary.forEach((item, index) => {
            const color = App.getLanguageColor(item.language);
            
            // Chart bar
            const segment = document.createElement('div');
            segment.className = 'summary-segment';
            segment.style.width = '0%';
            segment.style.backgroundColor = color;
            segment.title = `${item.language}: ${item.percentage.toFixed(1)}%`;
            chart.appendChild(segment);
            
            // Animate width shortly after adding to DOM
            setTimeout(() => {
                segment.style.width = `${item.percentage}%`;
            }, 100);
            
            // Legend item
            const legItem = document.createElement('div');
            legItem.className = 'legend-item';
            legItem.innerHTML = `
                <div class="legend-color" style="background-color: ${color}"></div>
                <span><strong>${item.language}</strong> (${item.percentage.toFixed(1)}%)</span>
            `;
            legend.appendChild(legItem);
        });
    }

    submitBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) return;
        
        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Starting...';
            
            const res = await fetch('/api/detect-language', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, region: selectedRegion })
            });
            
            const data = await res.json();
            if (data.job_id) showStatus(data.job_id);
            
        } catch (e) {
            alert('Failed to start job');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Detect';
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
        formData.append('region', selectedRegion);
        
        try {
            const p = dropZone.querySelector('p');
            const originalText = p.innerHTML;
            p.textContent = 'Uploading...';
            
            const res = await fetch('/api/detect-language/upload', {
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
