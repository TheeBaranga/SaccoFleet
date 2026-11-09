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
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const duration = 7000;
  let active = 0;
  let elapsed = 0;
  let startedAt;
  let frame;
  let playing = !reducedMotion.matches;

  function drawProgress(time) {
    buttons[active].firstElementChild.style.setProperty('--offer-progress', time / duration);
  }

  function showAd(index) {
    active = index;
    elapsed = 0;
    startedAt = undefined;
    ads.forEach((ad, position) => {
      ad.toggleAttribute('data-active', position === index);
      ad.setAttribute('aria-hidden', String(position !== index));
    });
    buttons.forEach((button, position) => {
      button.setAttribute('aria-pressed', String(position === index));
      button.toggleAttribute('data-complete', position < index);
      button.firstElementChild.style.removeProperty('--offer-progress');
    });
  }

  function tick(now) {
    startedAt ??= now - elapsed;
    elapsed = Math.min(now - startedAt, duration);
    if (!reducedMotion.matches) drawProgress(elapsed);
    if (elapsed === duration) showAd((active + 1) % ads.length);
    frame = requestAnimationFrame(tick);
  }

  function setRotation(enabled) {
    cancelAnimationFrame(frame);
    startedAt = undefined;
    playing = enabled;
    rotation.textContent = enabled ? 'Pause' : 'Play';
    if (enabled) frame = requestAnimationFrame(tick);
  }

  buttons.forEach((button, index) => button.addEventListener('click', () => {
    showAd(index);
    setRotation(false);
  }));
  rotation.addEventListener('click', () => setRotation(!playing));
  reducedMotion.addEventListener('change', () => {
    buttons[active].firstElementChild.style.removeProperty('--offer-progress');
    setRotation(!reducedMotion.matches);
  });
  adControls.hidden = false;
  setRotation(playing);
}
