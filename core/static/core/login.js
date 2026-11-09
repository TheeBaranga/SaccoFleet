const passwordToggle = document.querySelector('[data-password-toggle]');
const passwordInput = document.getElementById(passwordToggle.getAttribute('aria-controls'));

passwordToggle.hidden = false;
passwordToggle.setAttribute('aria-label', 'Show password');
passwordToggle.addEventListener('click', () => {
  const show = passwordInput.type === 'password';
  passwordInput.type = show ? 'text' : 'password';
  passwordToggle.textContent = show ? 'Hide' : 'Show';
  passwordToggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
});

const adControls = document.querySelector('[data-account-controls]');
if (adControls) {
  const ads = [...document.querySelectorAll('[data-account-ad]')];
  const buttons = [...adControls.querySelectorAll('[data-account-slide]')];
  const rotation = adControls.querySelector('[data-account-rotation]');
  let active = 0;
  let timer;

  function showAd(index) {
    active = index;
    ads.forEach((ad, position) => { ad.hidden = position !== index; });
    buttons.forEach((button, position) => {
      button.setAttribute('aria-pressed', String(position === index));
    });
  }

  function setRotation(enabled) {
    clearInterval(timer);
    timer = enabled ? setInterval(() => showAd((active + 1) % ads.length), 7000) : undefined;
    rotation.textContent = enabled ? 'Pause' : 'Play';
  }

  buttons.forEach((button, index) => button.addEventListener('click', () => {
    showAd(index);
    setRotation(false);
  }));
  rotation.addEventListener('click', () => setRotation(!timer));
  adControls.hidden = false;
  setRotation(!matchMedia('(prefers-reduced-motion: reduce)').matches);
}
