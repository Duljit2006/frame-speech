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
    
    // Simple color palette for chart (can match theme or just be diverse)
    const chartColors = ['#81B29A', '#E07A5F', '#F2CC8F', '#3D2C2E', '#8B7E74', '#E8DDD3'];

    function showStatus(jobId) {
        inputZone.classList.add('hidden');
        resultsZone.classList.add('hidden');
        statusZone.classList.remove('hidden');
        jobIdSpan.textContent = jobId;
        statusText.textContent = "Analyzing audio with AI...";
        
        App.subscribeToJob(jobId, 
            (data) => {},
            (result) => { showResults(result); },
            (err) => {
                statusText.textContent = `Error: ${err}`;
                document.querySelector('#workspace-lid .loader').classList.add('hidden');
            }
        );
    }

    function showResults(result) {
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
            span.style.backgroundColor = 'rgba(0,0,0,0.05)';
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
            const color = chartColors[index % chartColors.length];
            
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
                body: JSON.stringify({ url })
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
