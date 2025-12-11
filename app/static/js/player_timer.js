/**
 * Player Timer - Timer control and playback functions
 */

function togglePlayPause() {
    if (isPlaying) {
        pause();
    } else {
        play();
    }
}

async function play(skipSongStart = false) {
    isPlaying = true;
    document.getElementById('play-icon').classList.add('hidden');
    document.getElementById('pause-icon').classList.remove('hidden');

    const segment = plan.segments[currentSegmentIndex];

    if (!timerOnlyMode && segment.spotify_uri && spotifyDeviceId) {
        if (skipSongStart || songStartedForSegment === currentSegmentIndex) {
            await spotifyPlayer.resume();
        } else {
            const startMs = (segment.song_start_seconds || 0) * 1000;
            const elapsedInSegment = segment.duration_seconds - segmentTimeRemaining;
            const adjustedStartMs = startMs + (elapsedInSegment * 1000);
            await playSong(segment.spotify_uri, adjustedStartMs);
            songStartedForSegment = currentSegmentIndex;
        }
    }

    startTimer();
}

function pause() {
    isPlaying = false;
    document.getElementById('play-icon').classList.remove('hidden');
    document.getElementById('pause-icon').classList.add('hidden');

    pauseSong();

    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function startTimer() {
    timerInterval = setInterval(() => {
        segmentTimeRemaining--;
        songElapsedTime++;

        const segment = plan.segments[currentSegmentIndex];
        const hasSubSegments = segment.sub_segments && segment.sub_segments.length > 0;

        // Handle sub-segment timing
        if (hasSubSegments && currentSubSegmentIndex >= 0) {
            subSegmentTimeRemaining--;

            updateUpNextCountdown(subSegmentTimeRemaining);

            if (subSegmentTimeRemaining <= 0) {
                if (audioCuesEnabled) {
                    playTransitionChime();
                }

                if (currentSubSegmentIndex < segment.sub_segments.length - 1) {
                    currentSubSegmentIndex++;
                    subSegmentTimeRemaining = segment.sub_segments[currentSubSegmentIndex].duration_seconds;

                    const subSeg = segment.sub_segments[currentSubSegmentIndex];
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

                    updateSegmentsList();
                    updateUpNextPreview();
                }
            }

            document.getElementById('segment-timer').textContent = formatTime(subSegmentTimeRemaining);
        } else {
            updateUpNextCountdown(segmentTimeRemaining);
            document.getElementById('segment-timer').textContent = formatTime(segmentTimeRemaining);
        }

        // Handle song end time and fade out
        if (!timerOnlyMode && spotifyPlayer && currentSongEndTime) {
            const timeUntilSongEnd = currentSongEndTime - songElapsedTime;

            if (currentFadeOut && timeUntilSongEnd <= 3 && timeUntilSongEnd > 0) {
                const fadeVolume = (timeUntilSongEnd / 3) * currentVolume;
                spotifyPlayer.setVolume(fadeVolume);
            } else if (timeUntilSongEnd <= 0) {
                spotifyPlayer.pause();
                spotifyPlayer.setVolume(currentVolume);
            }
        } else if (!timerOnlyMode && spotifyPlayer && !currentSongEndTime && currentFadeOut) {
            if (segmentTimeRemaining <= 3 && segmentTimeRemaining > 0) {
                const fadeVolume = (segmentTimeRemaining / 3) * currentVolume;
                spotifyPlayer.setVolume(fadeVolume);
            }
        }

        // Audio cue warnings
        if (audioCuesEnabled) {
            const timeToCheck = hasSubSegments && currentSubSegmentIndex >= 0 ? subSegmentTimeRemaining : segmentTimeRemaining;
            if (timeToCheck === 10) {
                playWarningBeep();
            } else if (timeToCheck <= 3 && timeToCheck > 0) {
                playCountdownBeep(timeToCheck);
            }
        }

        // Check if segment is done
        if (segmentTimeRemaining <= 0) {
            if (spotifyPlayer) spotifyPlayer.setVolume(currentVolume);

            if (audioCuesEnabled) {
                playTransitionChime();
            }

            if (currentSegmentIndex < plan.segments.length - 1) {
                loadSegment(currentSegmentIndex + 1);
                playCurrentSegmentSong();
            } else {
                pause();
                showToast('Class complete!', 'success');
                return;
            }
        }

        // Update progress bar - show sub-segment progress if active
        let progress;
        if (hasSubSegments && currentSubSegmentIndex >= 0) {
            const subSeg = segment.sub_segments[currentSubSegmentIndex];
            const subSegElapsed = subSeg.duration_seconds - subSegmentTimeRemaining;
            progress = (subSegElapsed / subSeg.duration_seconds) * 100;
        } else {
            progress = ((segment.duration_seconds - segmentTimeRemaining) / segment.duration_seconds) * 100;
        }
        document.getElementById('segment-progress-bar').style.width = `${progress}%`;
    }, 1000);
}

function skipTime(seconds) {
    const segment = plan.segments[currentSegmentIndex];
    const totalDuration = segment.duration_seconds;
    const currentElapsed = totalDuration - segmentTimeRemaining;
    const newElapsed = Math.max(0, Math.min(totalDuration, currentElapsed + seconds));
    seekToElapsed(newElapsed);
}

function seekToPosition(event) {
    const progressBar = document.getElementById('segment-progress');
    const rect = progressBar.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, clickX / rect.width));

    const segment = plan.segments[currentSegmentIndex];
    const newElapsed = Math.floor(segment.duration_seconds * percentage);
    seekToElapsed(newElapsed);
}

function seekToElapsed(newElapsed) {
    const segment = plan.segments[currentSegmentIndex];
    const totalDuration = segment.duration_seconds;
    const newRemaining = totalDuration - newElapsed;

    segmentTimeRemaining = newRemaining;
    songElapsedTime = (segment.song_start_seconds || 0) + newElapsed;

    document.getElementById('segment-timer').textContent = formatTime(segmentTimeRemaining);
    const progress = (newElapsed / totalDuration) * 100;
    document.getElementById('segment-progress-bar').style.width = `${progress}%`;

    if (isPlaying && !timerOnlyMode && segment.spotify_uri && spotifyPlayer) {
        const seekMs = songElapsedTime * 1000;
        spotifyPlayer.seek(seekMs).catch(err => console.error('Seek failed:', err));
    }
}
