/**
 * Player Spotify - Spotify Web Playback SDK integration
 */

// Auto-refresh Spotify token
async function refreshSpotifyToken() {
    try {
        const response = await fetch('/api/spotify/refresh', { method: 'POST' });
        if (response.ok) {
            const data = await response.json();
            spotifyAccessToken = data.access_token;
            return true;
        }
    } catch (error) {
        console.error('Failed to refresh token:', error);
    }
    return false;
}

// Spotify API fetch with auto-refresh
async function spotifyApiFetch(url, options = {}, retried = false) {
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${spotifyAccessToken}`,
        'Content-Type': 'application/json'
    };

    const response = await fetch(url, options);

    if (response.status === 401 && !retried) {
        console.log('Spotify token expired, refreshing...');
        const refreshed = await refreshSpotifyToken();
        if (refreshed) {
            options.headers['Authorization'] = `Bearer ${spotifyAccessToken}`;
            return spotifyApiFetch(url, options, true);
        }
    }

    return response;
}

function initSpotifyPlayer() {
    console.log('Initializing Spotify player...');
    if (window.Spotify) {
        console.log('Spotify SDK already loaded');
        window.onSpotifyWebPlaybackSDKReady();
    } else {
        console.log('Waiting for Spotify SDK to load...');
    }
}

// Spotify Web Playback SDK ready callback
window.onSpotifyWebPlaybackSDKReady = () => {
    console.log('Spotify SDK ready callback fired');
    if (!spotifyAccessToken) {
        console.log('No access token, skipping player init');
        return;
    }

    console.log('Creating Spotify player...');
    spotifyPlayer = new Spotify.Player({
        name: 'Cycle Planner',
        getOAuthToken: async cb => {
            if (!spotifyAccessToken) {
                await refreshSpotifyToken();
            }
            cb(spotifyAccessToken);
        },
        volume: 0.7
    });

    spotifyPlayer.addListener('ready', ({ device_id }) => {
        console.log('Spotify player ready, device_id:', device_id);
        spotifyDeviceId = device_id;
        document.getElementById('loading-state').classList.add('hidden');
        document.getElementById('player-ui').classList.remove('hidden');
        document.getElementById('mode-switcher').classList.remove('hidden');
        loadSegment(0);
    });

    spotifyPlayer.addListener('not_ready', ({ device_id }) => {
        console.log('Device has gone offline', device_id);
    });

    spotifyPlayer.addListener('player_state_changed', state => {
        if (!state) return;
        const track = state.track_window.current_track;
        if (track) {
            document.getElementById('now-playing-inline').classList.remove('hidden');
            document.getElementById('track-name-inline').textContent = track.name;
            document.getElementById('track-artist-inline').textContent = track.artists.map(a => a.name).join(', ');
            if (track.album.images[0]) {
                document.getElementById('track-image-inline').innerHTML = `<img src="${track.album.images[0].url}" class="w-10 h-10 rounded">`;
            }

            currentTrackDurationMs = track.duration_ms;
            currentSongPositionMs = state.position;

            if (!timerOnlyMode) {
                document.getElementById('song-position-container').classList.remove('hidden');
                updateSongPositionDisplay();
            }
        }
    });

    // Poll for song position updates
    setInterval(async () => {
        if (spotifyPlayer && isPlaying && !timerOnlyMode) {
            const state = await spotifyPlayer.getCurrentState();
            if (state) {
                currentSongPositionMs = state.position;
                updateSongPositionDisplay();
            }
        }
    }, 500);

    spotifyPlayer.addListener('initialization_error', ({ message }) => {
        console.error('Spotify init error:', message);
        showToast('Spotify player failed to initialize: ' + message, 'error');
    });

    spotifyPlayer.addListener('authentication_error', async ({ message }) => {
        console.error('Spotify auth error:', message);
        const refreshed = await refreshSpotifyToken();
        if (refreshed) {
            console.log('Token refreshed, reconnecting player...');
            spotifyPlayer.connect();
        } else {
            showToast('Spotify authentication failed. Please reconnect.', 'error');
        }
    });

    spotifyPlayer.addListener('account_error', ({ message }) => {
        console.error('Spotify account error:', message);
        showToast('Spotify Premium required for playback', 'error');
        document.getElementById('loading-state').innerHTML = `
            <div class="text-center">
                <p class="text-red-600 mb-4">Spotify Premium is required for playback.</p>
                <button onclick="startTimerOnly()" class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
                    Continue without music
                </button>
            </div>
        `;
    });

    console.log('Connecting Spotify player...');
    spotifyPlayer.connect().then(success => {
        console.log('Spotify connect result:', success);
        if (!success) {
            console.error('Failed to connect to Spotify');
        }
    });
};

async function playSong(uri, positionMs = 0) {
    if (!spotifyDeviceId) {
        console.error('No Spotify device ID available');
        return false;
    }

    try {
        await spotifyApiFetch('https://api.spotify.com/v1/me/player', {
            method: 'PUT',
            body: JSON.stringify({
                device_ids: [spotifyDeviceId],
                play: false
            })
        });

        await new Promise(resolve => setTimeout(resolve, 500));

        const playResponse = await spotifyApiFetch(`https://api.spotify.com/v1/me/player/play?device_id=${spotifyDeviceId}`, {
            method: 'PUT',
            body: JSON.stringify({
                uris: [uri],
                position_ms: positionMs
            })
        });

        if (!playResponse.ok && playResponse.status !== 204) {
            const errorText = await playResponse.text();
            console.error('Spotify play failed:', playResponse.status, errorText);
            showToast('Spotify playback failed: ' + playResponse.status, 'error');
            return false;
        }
        return true;
    } catch (error) {
        console.error('Failed to play song:', error);
        showToast('Failed to play song: ' + error.message, 'error');
        return false;
    }
}

async function pauseSong() {
    if (timerOnlyMode || !spotifyPlayer) return;
    await spotifyPlayer.pause();
}

async function resumeSong() {
    if (timerOnlyMode || !spotifyPlayer) return;
    await spotifyPlayer.resume();
}

async function playCurrentSegmentSong() {
    const segment = plan.segments[currentSegmentIndex];
    if (!timerOnlyMode && segment.spotify_uri && spotifyDeviceId) {
        const startMs = (segment.song_start_seconds || 0) * 1000;
        await playSong(segment.spotify_uri, startMs);
        songStartedForSegment = currentSegmentIndex;
    }
}

function setVolume(value) {
    currentVolume = value / 100;
    if (spotifyPlayer) {
        spotifyPlayer.setVolume(currentVolume);
    }
}

function updateSongPositionDisplay() {
    if (currentTrackDurationMs <= 0) return;

    const currentSec = Math.floor(currentSongPositionMs / 1000);
    const totalSec = Math.floor(currentTrackDurationMs / 1000);
    const progress = (currentSongPositionMs / currentTrackDurationMs) * 100;

    document.getElementById('song-current-time').textContent = formatTime(currentSec);
    document.getElementById('song-total-time').textContent = formatTime(totalSec);
    document.getElementById('song-position-bar').style.width = `${progress}%`;
}

function seekSongPosition(event) {
    if (!spotifyPlayer || timerOnlyMode || currentTrackDurationMs <= 0) return;

    const container = event.currentTarget;
    const rect = container.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, clickX / rect.width));
    const seekMs = Math.floor(currentTrackDurationMs * percentage);

    spotifyPlayer.seek(seekMs).catch(err => console.error('Song seek failed:', err));
}

function calculateSongPositionForSubSegment(segmentIndex, subSegmentIndex) {
    const segment = plan.segments[segmentIndex];
    if (!segment.sub_segments || subSegmentIndex < 0) {
        return (segment.song_start_seconds || 0) * 1000;
    }

    let elapsedSeconds = segment.song_start_seconds || 0;
    for (let i = 0; i < subSegmentIndex; i++) {
        elapsedSeconds += segment.sub_segments[i].duration_seconds;
    }
    return elapsedSeconds * 1000;
}
