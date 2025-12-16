// Theme persistence and system preference detection
(function() {
    // Get stored theme or default to dark (matching the app's dark-mode-only design)
    const storedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Default to dark mode for this zen meditation app
    const theme = storedTheme || 'dark';

    // Apply theme immediately to prevent flash
    document.documentElement.setAttribute('data-theme', theme);

    // Listen for system theme changes (only if no stored preference)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', newTheme);
        }
    });
})();
