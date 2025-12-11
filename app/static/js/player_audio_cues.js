/**
 * Player Audio Cues - Web Audio API tone generation for countdown beeps
 */

function getAudioContext() {
    if (!window.AudioContext && !window.webkitAudioContext) {
        console.warn('Web Audio API not supported');
        return null;
    }
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === 'suspended') {
        audioContext.resume().catch(err => console.error('Audio context resume failed:', err));
    }
    return audioContext;
}

function playTone(frequency, duration, type = 'sine') {
    if (!audioCuesEnabled) return;

    const ctx = getAudioContext();
    if (!ctx) return;

    try {
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        oscillator.type = type;
        oscillator.frequency.setValueAtTime(frequency, ctx.currentTime);
        gainNode.gain.setValueAtTime(audioCueVolume, ctx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

        oscillator.start(ctx.currentTime);
        oscillator.stop(ctx.currentTime + duration);
    } catch (e) {
        console.error('Audio cue error:', e);
    }
}

function playWarningBeep() {
    // Single low beep at 10 seconds
    playTone(440, 0.2);
}

function playCountdownBeep(secondsRemaining) {
    // Ascending beeps for 3-2-1 countdown
    const frequencies = { 3: 440, 2: 550, 1: 660 };
    const freq = frequencies[secondsRemaining];
    if (freq) {
        playTone(freq, 0.15);
    }
}

function playTransitionChime() {
    // Success chime for segment/sub-segment transition
    playTone(880, 0.3);
    setTimeout(() => playTone(1100, 0.2), 100);
}

function toggleAudioCues() {
    audioCuesEnabled = document.getElementById('audio-cues-toggle').checked;
    if (audioCuesEnabled) {
        // Play a test beep when enabling
        playTone(660, 0.1);
    }
}
