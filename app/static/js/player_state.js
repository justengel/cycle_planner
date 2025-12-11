/**
 * Player State - Global state variables for the cycle class player
 */

// Plan data
let plan = null;
let planId = null;

// Segment tracking
let currentSegmentIndex = 0;
let currentSubSegmentIndex = -1;  // -1 means no sub-segments active
let segmentTimeRemaining = 0;
let subSegmentTimeRemaining = 0;

// Playback state
let isPlaying = false;
let timerInterval = null;
let timerOnlyMode = false;

// Spotify state
let spotifyPlayer = null;
let spotifyDeviceId = null;
let spotifyAccessToken = null;
let songStartedForSegment = -1;  // Track which segment has had its song started

// Volume and audio
let currentVolume = 0.7;
let fadeInterval = null;

// Song timing
let songElapsedTime = 0;  // Track song position in seconds
let currentSongEndTime = null;  // When to stop the song (in song seconds)
let currentFadeOut = false;  // Whether to fade out
let currentTrackDurationMs = 0;  // Current track duration in ms
let currentSongPositionMs = 0;  // Current song position in ms

// Audio cues
let audioCuesEnabled = false;
let audioCueVolume = 0.5;
let audioContext = null;
