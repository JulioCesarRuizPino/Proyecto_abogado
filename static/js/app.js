(function () {
    const body = document.body;
    const unreadCount = Number(body.dataset.unreadCount || '0');
    const toast = document.querySelector('[data-notification-toast]');
    const toggle = document.querySelector('[data-sound-toggle]');
    const storageKey = 'lexora_sound_enabled';
    const unreadKey = 'lexora_last_unread_count';

    const updateToggleState = () => {
        if (!toggle) return;
        const enabled = localStorage.getItem(storageKey) === 'true';
        toggle.classList.toggle('enabled', enabled);
        toggle.textContent = enabled ? 'Sonido activo' : 'Activar sonido';
    };

    const playNotificationSound = () => {
        try {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (!AudioContextClass) return;
            const context = new AudioContextClass();
            const oscillator = context.createOscillator();
            const gain = context.createGain();

            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(740, context.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(1040, context.currentTime + 0.18);
            gain.gain.setValueAtTime(0.0001, context.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.12, context.currentTime + 0.03);
            gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.35);

            oscillator.connect(gain);
            gain.connect(context.destination);
            oscillator.start();
            oscillator.stop(context.currentTime + 0.36);
        } catch (error) {
            // Ignora navegadores que bloqueen audio sin gesto de usuario.
        }
    };

    const showToast = () => {
        if (!toast) return;
        toast.hidden = false;
        window.setTimeout(() => {
            toast.hidden = true;
        }, 4500);
    };

    updateToggleState();

    if (toggle) {
        toggle.addEventListener('click', () => {
            const enabled = localStorage.getItem(storageKey) === 'true';
            localStorage.setItem(storageKey, String(!enabled));
            updateToggleState();
            if (!enabled) {
                playNotificationSound();
            }
        });
    }

    const previousUnreadCount = Number(localStorage.getItem(unreadKey) || '0');
    const hasNewNotification = unreadCount > previousUnreadCount;

    if (hasNewNotification) {
        showToast();
        if (localStorage.getItem(storageKey) === 'true') {
            playNotificationSound();
        }
    }

    localStorage.setItem(unreadKey, String(unreadCount));
})();
