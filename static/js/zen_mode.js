/**
 * Zen Mode & Distraction Pad Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // === DOM ELEMENTS ===
    const body = document.body;
    const zenOverlay = document.getElementById('zen-mode-overlay');
    const exitBtn = document.getElementById('exit-zen-btn');
    const clockElem = document.getElementById('zen-clock');
    const quoteElem = document.getElementById('zen-quote');
    const soundToggleBtn = document.getElementById('zen-sound-toggle');
    const soundSelect = document.getElementById('zen-sound-select');
    const distractionToggleBtn = document.getElementById('distraction-pad-toggle');
    const distractionPad = document.getElementById('distraction-pad-container');
    const distractionInput = document.getElementById('distraction-input');
    const zenQuotes = [
        "Focus on the process, not the outcome.",
        "The best way to get things done is to simply begin.",
        "Simplicity is the ultimate sophistication.",
        "Inhale focus, exhale distraction.",
        "Do one thing at a time.",
        "Quiet the mind, and the soul will speak."
    ];

    let audioContext = null;
    let noiseSource = null;
    let gainNode = null;
    let isPlayingInfo = false;

    // === FUNCTIONS ===

    // 1. Toggle Zen Mode
    window.toggleZenMode = function () {
        if (!zenOverlay) return;

        const isActive = zenOverlay.classList.contains('active');

        if (!isActive) {
            // Enter Zen Mode
            zenOverlay.classList.add('active');
            requestFullScreen(document.documentElement);
            updateZenClock();

            // Random Quote
            if (quoteElem) {
                quoteElem.textContent = zenQuotes[Math.floor(Math.random() * zenQuotes.length)];
            }
        } else {
            // Exit Zen Mode
            zenOverlay.classList.remove('active');
            exitFullScreen();
            stopAudio();
        }
    };

    if (exitBtn) {
        exitBtn.addEventListener('click', window.toggleZenMode);
    }

    // 2. Full Screen Helpers
    function requestFullScreen(element) {
        if (element.requestFullscreen) {
            element.requestFullscreen();
        } else if (element.mozRequestFullScreen) {
            element.mozRequestFullScreen();
        } else if (element.webkitRequestFullscreen) {
            element.webkitRequestFullscreen();
        } else if (element.msRequestFullscreen) {
            element.msRequestFullscreen();
        }
    }

    function exitFullScreen() {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        }
    }

    // 3. Clock
    function updateZenClock() {
        if (!zenOverlay.classList.contains('active')) return;

        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        if (clockElem) clockElem.textContent = timeString;

        requestAnimationFrame(updateZenClock);
        // Using requestAnimationFrame for smoother updates if we added seconds later, 
        // but for minutes, standard timeout is fine. 
        // Actually, let's just use a setTimeout loop to lower CPU usage.
    }
    setInterval(() => {
        if (zenOverlay && zenOverlay.classList.contains('active')) {
            const now = new Date();
            if (clockElem) clockElem.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    }, 1000);


    // 4. White Noise / Audio (Web Audio API)
    // Simple White Noise Generator
    function createWhiteNoise() {
        const bufferSize = 2 * audioContext.sampleRate;
        const noiseBuffer = audioContext.createBuffer(1, bufferSize, audioContext.sampleRate);
        const output = noiseBuffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            output[i] = Math.random() * 2 - 1;
        }

        const whiteNoise = audioContext.createBufferSource();
        whiteNoise.buffer = noiseBuffer;
        whiteNoise.loop = true;
        whiteNoise.start(0);
        return whiteNoise;
    }

    // Pink Noise (Softer) - approximation
    function createPinkNoise() {
        const bufferSize = 4096;
        var b0, b1, b2, b3, b4, b5, b6;
        b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0;
        const node = audioContext.createScriptProcessor(bufferSize, 1, 1);
        node.onaudioprocess = function (e) {
            var output = e.outputBuffer.getChannelData(0);
            for (var i = 0; i < bufferSize; i++) {
                var white = Math.random() * 2 - 1;
                b0 = 0.99886 * b0 + white * 0.0555179;
                b1 = 0.99332 * b1 + white * 0.0750759;
                b2 = 0.96900 * b2 + white * 0.1538520;
                b3 = 0.86650 * b3 + white * 0.3104856;
                b4 = 0.55000 * b4 + white * 0.5329522;
                b5 = -0.7616 * b5 - white * 0.0168980;
                output[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
                output[i] *= 0.11; // (roughly) compensate for gain
                b6 = white * 0.115926;
            }
        };
        return node;
    }

    // Brown Noise (Deep rumble)
    function createBrownNoise() {
        const bufferSize = 4096;
        const node = audioContext.createScriptProcessor(bufferSize, 1, 1);
        var lastOut = 0;
        node.onaudioprocess = function (e) {
            var output = e.outputBuffer.getChannelData(0);
            for (var i = 0; i < bufferSize; i++) {
                var white = Math.random() * 2 - 1;
                output[i] = (lastOut + (0.02 * white)) / 1.02;
                lastOut = output[i];
                output[i] *= 3.5; // (roughly) compensate for gain
            }
        };
        return node;
    }

    function playAudio(type) {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        // Stop invalid old source
        if (noiseSource) {
            try {
                // ScriptProcessorNodes don't have stop()
                if (noiseSource.stop) noiseSource.stop();
                noiseSource.disconnect();
            } catch (e) { }
        }

        gainNode = audioContext.createGain();
        gainNode.gain.value = 0.1; // Low volume default
        gainNode.connect(audioContext.destination);

        if (type === 'white_noise') {
            noiseSource = createWhiteNoise();
            noiseSource.connect(gainNode);
        } else if (type === 'rain') {
            // Pink noise sounds nice like rain
            noiseSource = createPinkNoise();
            noiseSource.connect(gainNode);
        } else if (type === 'forest') {
            // Brown noise is deeper, somewhat earthy
            noiseSource = createBrownNoise();
            noiseSource.connect(gainNode);
        } else {
            // Binaural beats (Two oscillators)
            // 40Hz (Left) and 44Hz (Right) = 4Hz Theta wave (Focus/Relax)
            const osc1 = audioContext.createOscillator();
            osc1.type = 'sine';
            osc1.frequency.value = 200; // Carrier

            const osc2 = audioContext.createOscillator();
            osc2.type = 'sine';
            osc2.frequency.value = 210; // +10Hz Alpha

            // Create stereo merger
            const merger = audioContext.createChannelMerger(2);
            osc1.connect(merger, 0, 0);
            osc2.connect(merger, 0, 1);

            merger.connect(gainNode);

            osc1.start();
            osc2.start();

            // Wrapper to stop both
            noiseSource = {
                stop: () => { osc1.stop(); osc2.stop(); },
                disconnect: () => { merger.disconnect(); }
            };
        }

        isPlayingInfo = true;
        soundToggleBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
        soundToggleBtn.classList.add('active');
    }

    function stopAudio() {
        if (noiseSource) {
            try {
                if (noiseSource.stop) noiseSource.stop();
                noiseSource.disconnect();
            } catch (e) { }
            noiseSource = null;
        }
        isPlayingInfo = false;
        if (soundToggleBtn) {
            soundToggleBtn.innerHTML = '<i class="fa-solid fa-volume-off"></i>';
            soundToggleBtn.classList.remove('active');
        }
    }

    if (soundToggleBtn && soundSelect) {
        soundToggleBtn.addEventListener('click', () => {
            if (isPlayingInfo) {
                stopAudio();
            } else {
                playAudio(soundSelect.value);
            }
        });

        soundSelect.addEventListener('change', () => {
            if (isPlayingInfo) {
                playAudio(soundSelect.value); // Restart with new sound
            }
        });
    }


    // 5. Distraction Pad (LocalStorage)
    if (distractionToggleBtn && distractionPad && distractionInput) {
        // Load saved
        const saved = localStorage.getItem('distraction_notes');
        if (saved) distractionInput.value = saved;

        distractionToggleBtn.addEventListener('click', () => {
            distractionPad.classList.toggle('open');
            distractionToggleBtn.classList.toggle('active');
        });

        distractionInput.addEventListener('input', () => {
            localStorage.setItem('distraction_notes', distractionInput.value);
        });
    }

});
