// Common Utilities & App Logic
const App = {
    init() {
        this.bindSmoothScroll();
        this.bindNavigation();
    },

    bindSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    },

    bindNavigation() {
        // Handle Model Card Clicks
        document.querySelectorAll('.model-card:not(.disabled)').forEach(card => {
            card.addEventListener('click', () => {
                const targetId = card.getAttribute('data-target');
                this.showWorkspace(targetId);
            });
        });

        // Close Workspace
        document.getElementById('close-workspace').addEventListener('click', () => {
            document.getElementById('workspace-area').classList.add('hidden');
            document.querySelectorAll('.workspace-content').forEach(ws => ws.classList.add('hidden'));
            // Scroll back to models
            document.getElementById('models').scrollIntoView({ behavior: 'smooth' });
        });
    },

    showWorkspace(workspaceId) {
        // Hide all workspaces
        document.querySelectorAll('.workspace-content').forEach(ws => ws.classList.add('hidden'));
        
        // Show selected workspace and area
        const ws = document.getElementById(workspaceId);
        if (ws) {
            document.getElementById('workspace-area').classList.remove('hidden');
            ws.classList.remove('hidden');
            ws.scrollIntoView({ behavior: 'smooth' });
        }
    },

    formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = (seconds % 60).toFixed(1);
        return `${m.toString().padStart(2, '0')}:${s.padStart(4, '0')}`;
    },

    embedVideo(containerId, url) {
        const container = document.getElementById(containerId);
        if (url) {
            container.innerHTML = `<iframe src="${url}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
            container.classList.remove('hidden');
        } else {
            container.innerHTML = '';
            container.classList.add('hidden');
        }
    },
    
    // Poll for SSE job updates
    subscribeToJob(jobId, onUpdate, onComplete, onError) {
        const source = new EventSource(`/api/jobs/${jobId}/stream`);
        
        source.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.status === 'not_found') {
                source.close();
                onError('Job not found or expired.');
                return;
            }
            
            onUpdate(data);
            
            if (data.status === 'completed') {
                source.close();
                onComplete(data.result);
            } else if (data.status === 'failed') {
                source.close();
                onError(data.error);
            }
        };
        
        source.onerror = function(err) {
            source.close();
            onError("Connection lost while waiting for results.");
        };
        
        return source; // return so caller can close if needed
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
