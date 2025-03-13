// Update the theme preference detection to set light theme as default

// Theme toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    // Check for saved theme preference but make light the default
    const toggleSwitch = document.getElementById('theme-toggle');
    if (!toggleSwitch) return; // Skip if toggle doesn't exist (login page)
    
    // Changed this line to make light the default, regardless of system preference
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    if (currentTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        toggleSwitch.checked = true;
        updateNavbarClasses(true);
    } else {
        // Explicitly set light theme attributes
        document.documentElement.setAttribute('data-theme', 'light');
        toggleSwitch.checked = false;
        updateNavbarClasses(false);
    }
    
    // Listen for toggle changes
    toggleSwitch.addEventListener('change', switchTheme);
    
    function switchTheme(e) {
        const isDark = e.target.checked;
        
        if (isDark) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
        
        updateNavbarClasses(isDark);
    }
    
    function updateNavbarClasses(isDark) {
        const navbar = document.querySelector('.navbar');
        if (isDark) {
            navbar.classList.remove('navbar-light', 'bg-light');
            navbar.classList.add('navbar-dark', 'bg-dark');
        } else {
            navbar.classList.remove('navbar-dark', 'bg-dark');
            navbar.classList.add('navbar-light', 'bg-light');
        }
    }
});

// Remove the conflicting sidebar toggle code here - it's now handled in base.html