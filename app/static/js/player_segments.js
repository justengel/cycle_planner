/**
 * Player Segments - Segment and sub-segment loading/navigation
 */

function loadSegment(index, subIndex = -1) {
    if (index < 0 || index >= plan.segments.length) return;

    currentSegmentIndex = index;
    const segment = plan.segments[index];
    segmentTimeRemaining = segment.duration_seconds;

    const hasSubSegments = segment.sub_segments && segment.sub_segments.length > 0;

    // Validate sub-segment durations match segment duration
    if (hasSubSegments) {
        const subSegmentsTotal = segment.sub_segments.reduce((sum, sub) => sum + sub.duration_seconds, 0);
        if (subSegmentsTotal !== segment.duration_seconds) {
            console.warn(`Sub-segments total (${subSegmentsTotal}s) doesn't match segment duration (${segment.duration_seconds}s)`);
            segmentTimeRemaining = subSegmentsTotal;
        }
    }

    if (hasSubSegments && subIndex === -1) {
        currentSubSegmentIndex = 0;
    } else {
        currentSubSegmentIndex = subIndex;
    }

    // Initialize sub-segment timer if applicable
    if (hasSubSegments && currentSubSegmentIndex >= 0) {
        subSegmentTimeRemaining = segment.sub_segments[currentSubSegmentIndex].duration_seconds;

        let remainingTime = 0;
        for (let i = currentSubSegmentIndex; i < segment.sub_segments.length; i++) {
            remainingTime += segment.sub_segments[i].duration_seconds;
        }
        segmentTimeRemaining = remainingTime;
    } else {
        subSegmentTimeRemaining = 0;
    }

    // Update UI
    document.getElementById('segment-title').textContent = segment.name;
    document.getElementById('segment-cues').textContent = segment.description || '';
    document.getElementById('segment-timer').textContent = formatTime(hasSubSegments && currentSubSegmentIndex >= 0 ? subSegmentTimeRemaining : segmentTimeRemaining);
    document.getElementById('segment-progress-bar').style.width = '0%';

    // Show/hide sub-segment info and segment badges
    const subSegmentInfoEl = document.getElementById('sub-segment-info');
    const segmentBadgesEl = document.getElementById('segment-badges');

    if (hasSubSegments && currentSubSegmentIndex >= 0) {
        const subSeg = segment.sub_segments[currentSubSegmentIndex];
        subSegmentInfoEl.classList.remove('hidden');
        segmentBadgesEl.classList.add('hidden');
        document.getElementById('sub-segment-name').textContent = subSeg.name;
        setSubBadge('sub-segment-intensity', subSeg.intensity, getIntensityClasses(subSeg.intensity));
        setSubBadge('sub-segment-position', subSeg.position, 'bg-blue-100 text-blue-800');
        document.getElementById('sub-segment-cues').textContent = subSeg.description || '';
        const subBpmEl = document.getElementById('sub-segment-bpm');
        if (subSeg.suggested_bpm_range) {
            subBpmEl.textContent = subSeg.suggested_bpm_range;
            subBpmEl.classList.remove('hidden');
        } else {
            subBpmEl.classList.add('hidden');
        }
    } else {
        subSegmentInfoEl.classList.add('hidden');
        segmentBadgesEl.classList.remove('hidden');
        setBadge('segment-intensity', segment.intensity, getIntensityClasses(segment.intensity));
        setBadge('segment-position', segment.position, 'bg-blue-100 text-blue-800');
        setBadge('segment-bpm', segment.suggested_bpm_range || '', 'bg-purple-100 text-purple-800');
    }

    updateSegmentsList();
    updateUpNextPreview();

    // Set up song timing
    songElapsedTime = segment.song_start_seconds || 0;
    currentSongEndTime = segment.song_end_seconds || null;
    currentFadeOut = segment.fade_out === true;

    // Update Now Playing display
    if (segment.spotify_uri || segment.song) {
        document.getElementById('now-playing-inline').classList.remove('hidden');
        const songParts = (segment.song || 'Loading...').split(' - ');
        document.getElementById('track-name-inline').textContent = songParts[0] || 'Loading...';
        document.getElementById('track-artist-inline').textContent = songParts[1] || '';
        document.getElementById('track-image-inline').innerHTML = '';
    } else {
        document.getElementById('now-playing-inline').classList.add('hidden');
    }
}

function getCurrentActivity() {
    const segment = plan.segments[currentSegmentIndex];
    const hasSubSegments = segment.sub_segments && segment.sub_segments.length > 0;

    if (hasSubSegments && currentSubSegmentIndex >= 0 && currentSubSegmentIndex < segment.sub_segments.length) {
        const subSeg = segment.sub_segments[currentSubSegmentIndex];
        return {
            name: subSeg.name,
            intensity: subSeg.intensity,
            position: subSeg.position,
            suggested_bpm_range: subSeg.suggested_bpm_range,
            description: subSeg.description,
            timeRemaining: subSegmentTimeRemaining || subSeg.duration_seconds,
            isSubSegment: true
        };
    }

    return {
        name: segment.name,
        intensity: segment.intensity,
        position: segment.position,
        suggested_bpm_range: segment.suggested_bpm_range,
        description: segment.description,
        timeRemaining: segmentTimeRemaining,
        isSubSegment: false
    };
}

function getNextActivity() {
    const segment = plan.segments[currentSegmentIndex];
    const hasSubSegments = segment.sub_segments && segment.sub_segments.length > 0;

    if (hasSubSegments && currentSubSegmentIndex >= 0 && currentSubSegmentIndex < segment.sub_segments.length - 1) {
        return segment.sub_segments[currentSubSegmentIndex + 1];
    }

    if (currentSegmentIndex < plan.segments.length - 1) {
        const nextSegment = plan.segments[currentSegmentIndex + 1];
        if (nextSegment.sub_segments && nextSegment.sub_segments.length > 0) {
            return nextSegment.sub_segments[0];
        }
        return nextSegment;
    }

    return null;
}

async function nextSegment() {
    const segment = plan.segments[currentSegmentIndex];
    const hasSubSegments = segment.sub_segments && segment.sub_segments.length > 0;
    const wasPlaying = isPlaying;

    if (hasSubSegments && currentSubSegmentIndex >= 0 && currentSubSegmentIndex < segment.sub_segments.length - 1) {
        if (isPlaying) {
            clearInterval(timerInterval);
            timerInterval = null;
        }

        currentSubSegmentIndex++;
        subSegmentTimeRemaining = segment.sub_segments[currentSubSegmentIndex].duration_seconds;

        let remainingTime = 0;
        for (let i = currentSubSegmentIndex; i < segment.sub_segments.length; i++) {
            remainingTime += segment.sub_segments[i].duration_seconds;
        }
        segmentTimeRemaining = remainingTime;

        // Seek song to appropriate position
        if (!timerOnlyMode && segment.spotify_uri && spotifyPlayer) {
            const seekMs = calculateSongPositionForSubSegment(currentSegmentIndex, currentSubSegmentIndex);
            spotifyPlayer.seek(seekMs).catch(err => console.error('Sub-segment seek failed:', err));
        }

        const subSeg = segment.sub_segments[currentSubSegmentIndex];
        document.getElementById('sub-segment-name').textContent = subSeg.name;
        setSubBadge('sub-segment-intensity', subSeg.intensity, getIntensityClasses(subSeg.intensity));
        setSubBadge('sub-segment-position', subSeg.position, 'bg-blue-100 text-blue-800');
        document.getElementById('sub-segment-cues').textContent = subSeg.description || '';
        document.getElementById('segment-timer').textContent = formatTime(subSegmentTimeRemaining);
        const subBpmEl = document.getElementById('sub-segment-bpm');
        if (subSeg.suggested_bpm_range) {
            subBpmEl.textContent = subSeg.suggested_bpm_range;
            subBpmEl.classList.remove('hidden');
        } else {
            subBpmEl.classList.add('hidden');
        }

        updateSegmentsList();
        updateUpNextPreview();

        if (wasPlaying) {
            play(true);
        }
    } else if (currentSegmentIndex < plan.segments.length - 1) {
        if (isPlaying) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        loadSegment(currentSegmentIndex + 1);
        if (wasPlaying) {
            await playCurrentSegmentSong();
            play(true);
        }
    }
}

async function previousSegment() {
    const segment = plan.segments[currentSegmentIndex];
    const hasSubSegments = segment.sub_segments && segment.sub_segments.length > 0;
    const wasPlaying = isPlaying;

    if (hasSubSegments && currentSubSegmentIndex > 0) {
        if (isPlaying) {
            clearInterval(timerInterval);
            timerInterval = null;
        }

        currentSubSegmentIndex--;
        subSegmentTimeRemaining = segment.sub_segments[currentSubSegmentIndex].duration_seconds;

        let remainingTime = 0;
        for (let i = currentSubSegmentIndex; i < segment.sub_segments.length; i++) {
            remainingTime += segment.sub_segments[i].duration_seconds;
        }
        segmentTimeRemaining = remainingTime;

        // Seek song to appropriate position
        if (!timerOnlyMode && segment.spotify_uri && spotifyPlayer) {
            const seekMs = calculateSongPositionForSubSegment(currentSegmentIndex, currentSubSegmentIndex);
            spotifyPlayer.seek(seekMs).catch(err => console.error('Sub-segment seek failed:', err));
        }

        const subSeg = segment.sub_segments[currentSubSegmentIndex];
        document.getElementById('sub-segment-name').textContent = subSeg.name;
        setSubBadge('sub-segment-intensity', subSeg.intensity, getIntensityClasses(subSeg.intensity));
        setSubBadge('sub-segment-position', subSeg.position, 'bg-blue-100 text-blue-800');
        document.getElementById('sub-segment-cues').textContent = subSeg.description || '';
        document.getElementById('segment-timer').textContent = formatTime(subSegmentTimeRemaining);
        const subBpmEl = document.getElementById('sub-segment-bpm');
        if (subSeg.suggested_bpm_range) {
            subBpmEl.textContent = subSeg.suggested_bpm_range;
            subBpmEl.classList.remove('hidden');
        } else {
            subBpmEl.classList.add('hidden');
        }

        updateSegmentsList();
        updateUpNextPreview();

        if (wasPlaying) {
            play(true);
        }
    } else if (currentSegmentIndex > 0) {
        if (isPlaying) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        const prevSegment = plan.segments[currentSegmentIndex - 1];
        const prevHasSubSegments = prevSegment.sub_segments && prevSegment.sub_segments.length > 0;
        const startSubIndex = prevHasSubSegments ? prevSegment.sub_segments.length - 1 : -1;
        loadSegment(currentSegmentIndex - 1, startSubIndex);
        if (wasPlaying) {
            await playCurrentSegmentSong();
            play(true);
        }
    }
}

async function jumpToSegment(index) {
    const wasPlaying = isPlaying;
    if (isPlaying) {
        clearInterval(timerInterval);
        timerInterval = null;
        await pauseSong();
    }
    loadSegment(index);
    if (wasPlaying) {
        await playCurrentSegmentSong();
        play(true);
    }
}
