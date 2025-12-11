/**
 * Player UI - UI helpers, display updates, and mode switching
 */

function startTimerOnly() {
    timerOnlyMode = true;
    document.getElementById('spotify-required').classList.add('hidden');
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('player-ui').classList.remove('hidden');
    document.getElementById('mode-switcher').classList.add('hidden');
    document.getElementById('spotify-icon-inline').classList.add('hidden');
    document.getElementById('song-position-container').classList.add('hidden');
    loadSegment(0);
}

function switchToTimerMode() {
    if (spotifyPlayer && isPlaying) {
        spotifyPlayer.pause();
    }
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    isPlaying = false;
    document.getElementById('play-icon').classList.remove('hidden');
    document.getElementById('pause-icon').classList.add('hidden');
    timerOnlyMode = true;
    document.getElementById('spotify-icon-inline').classList.add('hidden');
    document.getElementById('song-position-container').classList.add('hidden');
    updateModeSwitcherUI();
    showToast('Switched to timer-only mode', 'success');
}

function switchToSpotifyMode() {
    if (!spotifyDeviceId) {
        showToast('Spotify not connected', 'error');
        return;
    }
    timerOnlyMode = false;
    document.getElementById('spotify-icon-inline').classList.remove('hidden');
    document.getElementById('song-position-container').classList.remove('hidden');
    const segment = plan.segments[currentSegmentIndex];
    if (segment && segment.spotify_uri) {
        document.getElementById('now-playing-inline').classList.remove('hidden');
        const songParts = (segment.song || '').split(' - ');
        document.getElementById('track-name-inline').textContent = songParts[0] || '';
        document.getElementById('track-artist-inline').textContent = songParts[1] || '';
    }
    updateModeSwitcherUI();
    showToast('Switched to Spotify mode', 'success');
}

function updateModeSwitcherUI() {
    const spotifyBtn = document.getElementById('spotify-mode-btn');
    const timerBtn = document.getElementById('timer-mode-btn');

    if (timerOnlyMode) {
        spotifyBtn.className = 'px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-600 flex items-center gap-1 hover:bg-gray-200';
        timerBtn.className = 'px-3 py-1.5 text-xs font-medium bg-indigo-500 text-white flex items-center gap-1';
    } else {
        spotifyBtn.className = 'px-3 py-1.5 text-xs font-medium bg-green-500 text-white flex items-center gap-1';
        timerBtn.className = 'px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-600 flex items-center gap-1 hover:bg-gray-200';
    }
}

function updateUpNextPreview() {
    const upNextEl = document.getElementById('up-next');
    const next = getNextActivity();

    if (!next) {
        upNextEl.classList.add('hidden');
        return;
    }

    upNextEl.classList.remove('hidden');
    document.getElementById('up-next-name').textContent = next.name;
    document.getElementById('up-next-duration').textContent = formatTime(next.duration_seconds);
    document.getElementById('up-next-cues').textContent = next.description || '';

    const intensityEl = document.getElementById('up-next-intensity');
    intensityEl.textContent = next.intensity;
    intensityEl.className = `px-2 py-0.5 rounded text-xs font-medium ${getIntensityClasses(next.intensity)}`;

    const positionEl = document.getElementById('up-next-position');
    positionEl.textContent = next.position;
    positionEl.className = 'px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800';

    const bpmEl = document.getElementById('up-next-bpm');
    if (next.suggested_bpm_range) {
        bpmEl.textContent = next.suggested_bpm_range;
        bpmEl.className = 'px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800';
        bpmEl.classList.remove('hidden');
    } else {
        bpmEl.classList.add('hidden');
    }
}

function updateUpNextCountdown(timeRemaining) {
    const countdownEl = document.getElementById('up-next-countdown');
    if (timeRemaining <= 30) {
        countdownEl.textContent = `(in ${formatTime(timeRemaining)})`;
    } else {
        countdownEl.textContent = '';
    }
}

function updateSegmentsList() {
    const container = document.getElementById('all-segments');

    container.innerHTML = plan.segments.map((seg, i) => {
        const isCurrent = i === currentSegmentIndex;
        const bgClass = isCurrent ? 'bg-indigo-100 border-indigo-300' : 'bg-gray-50';
        const textClass = isCurrent ? 'text-indigo-700 font-semibold' : 'text-gray-700';
        const hasSubSegments = seg.sub_segments && seg.sub_segments.length > 0;
        const intensityClass = getIntensityClasses(seg.intensity);

        let subSegmentsHtml = '';
        if (hasSubSegments) {
            subSegmentsHtml = `
                <div class="mt-2 space-y-1 border-l-2 border-indigo-200 pl-2">
                    ${seg.sub_segments.map((subSeg, j) => {
                        const isCurrentSub = isCurrent && j === currentSubSegmentIndex;
                        const subBgClass = isCurrentSub ? 'bg-indigo-200' : 'bg-gray-100';
                        const subTextClass = isCurrentSub ? 'text-indigo-800 font-medium' : 'text-gray-600';
                        const subIntensityClass = getIntensityClasses(subSeg.intensity);
                        return `
                            <div class="p-1.5 rounded ${subBgClass}">
                                <div class="flex flex-wrap items-center justify-between gap-1">
                                    <div class="flex items-center gap-2">
                                        <span class="${subTextClass} text-xs">${escapeHtml(subSeg.name)}</span>
                                        <span class="text-xs text-gray-500">${formatTime(subSeg.duration_seconds)}</span>
                                        ${isCurrentSub ? '<span class="text-xs text-indigo-600">current</span>' : ''}
                                    </div>
                                    <div class="flex items-center gap-1 flex-wrap">
                                        <span class="text-xs px-1.5 py-0.5 rounded ${subIntensityClass}">${subSeg.intensity}</span>
                                        <span class="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">${subSeg.position}</span>
                                        ${subSeg.suggested_bpm_range ? `<span class="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">${subSeg.suggested_bpm_range}</span>` : ''}
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        return `
            <div class="p-2 rounded border ${bgClass}">
                <div class="flex items-start gap-2">
                    <button onclick="jumpToSegment(${i})" class="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-indigo-600 flex-shrink-0" title="Start from here">
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                    </button>
                    <div class="flex-1 min-w-0">
                        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1">
                            <div class="flex items-center gap-2">
                                <span class="${textClass} text-sm">${escapeHtml(seg.name)}</span>
                                <span class="text-xs text-gray-500">${formatTime(seg.duration_seconds)}</span>
                                ${hasSubSegments ? `<span class="text-xs text-indigo-500">(${seg.sub_segments.length} parts)</span>` : ''}
                                ${isCurrent && !hasSubSegments ? '<span class="text-xs text-indigo-600">current</span>' : ''}
                            </div>
                            <div class="flex items-center gap-1">
                                <span class="text-xs px-2 py-0.5 rounded ${intensityClass}">${seg.intensity}</span>
                                <span class="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800">${seg.position}</span>
                                ${seg.suggested_bpm_range ? `<span class="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-800">${seg.suggested_bpm_range}</span>` : ''}
                            </div>
                        </div>
                        ${seg.song ? `<div class="text-xs text-gray-500 truncate">${escapeHtml(seg.song)}</div>` : ''}
                        ${subSegmentsHtml}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Utility functions
function formatTime(totalSeconds) {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getIntensityClasses(intensity) {
    switch (intensity) {
        case 'high': return 'bg-red-100 text-red-800';
        case 'medium': return 'bg-yellow-100 text-yellow-800';
        default: return 'bg-green-100 text-green-800';
    }
}

function setBadge(elementId, value, colorClasses) {
    const el = document.getElementById(elementId);
    el.textContent = value;
    el.className = `px-3 py-1 rounded-full text-sm font-medium ${colorClasses}`;
}

function setSubBadge(elementId, value, colorClasses) {
    const el = document.getElementById(elementId);
    el.textContent = value;
    el.className = `px-3 py-1 rounded text-sm font-medium ${colorClasses}`;
}
