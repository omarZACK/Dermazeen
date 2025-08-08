// Sidebar toggle
document.querySelector('.toggle-nav-sidebar').addEventListener('click', function () {
  document.querySelector('.main').classList.toggle('shifted');
  const icon = this.querySelector('i');
  icon.classList.toggle('fa-bars');
  icon.classList.toggle('fa-times');
});

document.addEventListener('click', function (e) {
  const sidebar = document.querySelector('#nav-sidebar');
  const toggle = document.querySelector('.toggle-nav-sidebar');
  const main = document.querySelector('.main');
  if (window.innerWidth <= 1024 && main.classList.contains('shifted') &&
      !sidebar.contains(e.target) && !toggle.contains(e.target)) {
    main.classList.remove('shifted');
    const icon = toggle.querySelector('i');
    icon.classList.add('fa-bars'); icon.classList.remove('fa-times');
  }
});

// Smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) target.scrollIntoView({ behavior: 'smooth' });
  });
});

// Light/Dark mode toggle
const modeToggle = document.getElementById('mode-toggle');
const body = document.body;
function setMode(mode) {
  body.classList.toggle('dark-mode', mode === 'dark');
  body.classList.toggle('light-mode', mode !== 'dark');
  modeToggle.innerHTML = mode === 'dark'
    ? '<i class="fas fa-sun"></i>'
    : '<i class="fas fa-moon"></i>';
  localStorage.setItem('theme', mode);
}
const savedTheme = localStorage.getItem('theme') || 'light';
setMode(savedTheme);
modeToggle.addEventListener('click', () => setMode(body.classList.contains('dark-mode') ? 'light' : 'dark'));