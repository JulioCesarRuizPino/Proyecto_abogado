(function () {
    const body = document.body;
    const unreadCount = Number(body.dataset.unreadCount || '0');
    const notificationsUrl = body.dataset.notificationsUrl;
    const homeUrl = body.dataset.homeUrl || '/';
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

    const updateNotificationCounter = (count) => {
        const link = document.querySelector('.notification-link');
        const counter = document.querySelector('.notification-counter');
        if (!link || !counter) return;
        counter.textContent = count;
        link.classList.toggle('has-alert', count > 0);
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

    // Revisa nuevos avisos sin interrumpir el trabajo del usuario con una recarga completa.
    if (notificationsUrl) {
        let currentUnreadCount = unreadCount;
        window.setInterval(async () => {
            try {
                const response = await fetch(notificationsUrl, { credentials: 'same-origin' });
                if (!response.ok) return;
                const data = await response.json();
                const nextUnreadCount = Number(data.total || 0);
                if (nextUnreadCount > currentUnreadCount) {
                    showToast();
                    if (localStorage.getItem(storageKey) === 'true') playNotificationSound();
                }
                currentUnreadCount = nextUnreadCount;
                updateNotificationCounter(nextUnreadCount);
                localStorage.setItem(unreadKey, String(nextUnreadCount));
            } catch (error) {
                // Si se corta la red, se conserva el contador que ya estaba visible.
            }
        }, 30000);
    }

    const backButton = document.querySelector('[data-go-back]');
    if (backButton) {
        backButton.addEventListener('click', () => {
            if (window.history.length > 1) {
                window.history.back();
            } else {
                window.location.assign(homeUrl);
            }
        });
    }
})();
