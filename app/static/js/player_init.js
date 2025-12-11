/**
 * Player Init - Initialization and keyboard controls
 */

async function init() {
    planId = window.location.pathname.split('/').pop();
    document.getElementById('back-link').href = `/plan/${planId}`;

    try {
        const response = await fetch(`/api/plans/${planId}`, {
            headers: { 'Authorization': 'Bearer placeholder' }
        });
        if (!response.ok) throw new Error('Plan not found');

        const data = await response.json();
        plan = data.plan_json;

        document.getElementById('class-theme').textContent = plan.theme;
        document.getElementById('class-duration').textContent = `${plan.total_duration_minutes} minutes`;

        // Check Spotify connection
        const tokenResponse = await fetch('/api/spotify/token');
        const tokenData = await tokenResponse.json();

        if (tokenData.connected) {
            spotifyAccessToken = tokenData.access_token;
            initSpotifyPlayer();

            // Timeout - if Spotify doesn't connect in 10 seconds, offer timer-only mode
            setTimeout(() => {
                if (!spotifyDeviceId) {
                    document.getElementById('loading-state').innerHTML = `
                        <div class="text-center">
                            <p class="text-gray-600 mb-4">Spotify player is taking too long to connect.</p>
                            <p class="text-sm text-gray-500 mb-4">Make sure you have Spotify Premium and the Spotify app is open somewhere.</p>
                            <button onclick="startTimerOnly()" class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
                                Continue without music
                            </button>
                        </div>
                    `;
                }
            }, 10000);
        } else {
            document.getElementById('loading-state').classList.add('hidden');
            document.getElementById('spotify-required').classList.remove('hidden');
        }

    } catch (error) {
        showToast('Failed to load class', 'error');
        setTimeout(() => window.location.href = '/plans', 1500);
    }
}

// Keyboard controls
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
        e.preventDefault();
        togglePlayPause();
    } else if (e.code === 'ArrowRight') {
        if (e.shiftKey) {
            nextSegment();
        } else {
            skipTime(10);
        }
    } else if (e.code === 'ArrowLeft') {
        if (e.shiftKey) {
            previousSegment();
        } else {
            skipTime(-10);
        }
    }
});

// Start initialization
init();
