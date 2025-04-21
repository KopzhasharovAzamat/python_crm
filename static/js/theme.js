document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.getElementById('theme-body');
    const icon = themeToggle.querySelector('i');

    // Загрузка сохраненной темы
    if (localStorage.getItem('theme') === 'dark') {
        body.classList.add('dark-theme');
        icon.classList.replace('fa-moon', 'fa-sun');
        themeToggle.classList.replace('btn-outline-primary', 'btn-outline-warning');
    }

    themeToggle.addEventListener('click', () => {
        body.classList.toggle('dark-theme');
        if (body.classList.contains('dark-theme')) {
            localStorage.setItem('theme', 'dark');
            icon.classList.replace('fa-moon', 'fa-sun');
            themeToggle.classList.replace('btn-outline-primary', 'btn-outline-warning');
        } else {
            localStorage.setItem('theme', 'light');
            icon.classList.replace('fa-sun', 'fa-moon');
            themeToggle.classList.replace('btn-outline-warning', 'btn-outline-primary');
        }
    });
});