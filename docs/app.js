'use strict';
const runtimes = {
  host: {title: 'Use your initialized Yocto checkout.', description: 'Source an init script automatically or run from your existing environment. Every target is passed as a quoted argument.', profile: {name: 'host', root: '/work/poky', build_dir: 'build-qemu', mode: 'host', init_script: 'oe-init-build-env'}},
  kas: {title: 'Compose your project with kas.', description: 'Use kas YAML to select repositories, machines and targets. BitBake and devtool actions run through kas shell.', profile: {name: 'kas', root: '/work/project', build_dir: 'build', mode: 'kas', kas_file: 'kas/base.yml:kas/board.yml'}},
  container: {title: 'Keep build dependencies inside a builder image.', description: 'Choose Docker or Podman. New containers mount your project and use your UID/GID. An existing container needs the same mount and an explicit name.', profile: {name: 'podman', root: '/work/poky', build_dir: 'build', mode: 'container', engine: 'podman', image: 'your-builder:scarthgap', init_script: 'oe-init-build-env', container_root: '/work'}},
  'kas-container': {title: 'Use the official containerized kas environment.', description: 'Install kas-container and a container runtime. Keep work on a dedicated Linux filesystem; kas supplies build dependencies inside its image.', profile: {name: 'kas-container', root: '/work/project', build_dir: 'work/build', mode: 'kas-container', kas_file: 'kas.yml', environment: {KAS_CONTAINER_ENGINE: 'docker', KAS_WORK_DIR: '/work/project/work'}}}
};
document.querySelectorAll('[data-runtime]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-runtime]').forEach(item => item.setAttribute('aria-selected', String(item === button)));
  const runtime = runtimes[button.dataset.runtime];
  document.getElementById('runtime-title').textContent = runtime.title;
  document.getElementById('runtime-description').textContent = runtime.description;
  document.getElementById('runtime-code').textContent = JSON.stringify(runtime.profile, null, 2);
}));
document.getElementById('feature-search').addEventListener('input', event => {
  const query = event.target.value.trim().toLowerCase();
  let count = 0;
  document.querySelectorAll('#feature-cards article').forEach(card => {
    const visible = (card.textContent + ' ' + card.dataset.tags).toLowerCase().includes(query);
    card.hidden = !visible;
    if (visible) count++;
  });
  document.getElementById('no-results').hidden = count > 0;
});
document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);
    button.textContent = 'Copied';
    setTimeout(() => {button.textContent = 'Copy';}, 2000);
  } catch (_) {button.textContent = 'Select and copy';}
}));
const lightbox = document.getElementById('lightbox');
document.querySelectorAll('[data-image]').forEach(button => button.addEventListener('click', () => {
  document.getElementById('lightbox-image').src = button.dataset.image;
  document.getElementById('lightbox-image').alt = button.querySelector('img').alt;
  lightbox.showModal();
}));
document.getElementById('lightbox-close').addEventListener('click', () => lightbox.close());
lightbox.addEventListener('click', event => {if (event.target === lightbox) lightbox.close();});
// Hero title: one sentence per thing Bitloom does, word by word. Reduced motion keeps the first one still.
const PHRASES = [
  ['Follow every build', 'from your browser.'],
  ['Find the real cause,', 'not the first error.'],
  ['Pick an image.', 'Watch it build.'],
  ['Know your SBOM', 'before the CRA asks.'],
  ['Your own distro,', 'explained line by line.'],
  ['Close the laptop.', 'The build keeps going.'],
  ['1,300 recipes,', 'sorted by layer.'],
  ['Which recipe put', 'this file here?'],
  ['Right tool for', 'your Yocto release.'],
];
const stage = document.querySelector('.rot-stage');
if (stage) {
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const DURATION = 4200;
  let index = 0, timer = null;
  const build = (pair) => {
    const node = document.createElement('span');
    node.className = 'rot-phrase';
    pair.forEach((text, line) => {
      const row = document.createElement('span');
      row.className = 'rot-line';
      text.split(' ').forEach((word, i, words) => {
        const span = document.createElement('span');
        span.className = 'rot-word';
        span.textContent = word + (i < words.length - 1 ? ' ' : '');
        span.style.transitionDelay = `${(line * words.length + i) * 70}ms`;
        row.append(span);
      });
      node.append(row);
    });
    return node;
  };
  // Reserve the height of the tallest sentence, so the page below never jumps.
  const fit = () => {
    const probe = document.createElement('span');
    probe.style.cssText = 'position:absolute;visibility:hidden;left:0;right:0';
    stage.append(probe);
    let tallest = 0;
    for (const pair of PHRASES) { probe.replaceChildren(build(pair)); tallest = Math.max(tallest, probe.offsetHeight); }
    probe.remove();
    stage.style.minHeight = tallest + 'px';
  };
  const bars = document.createElement('div');
  bars.className = 'rot-progress';
  bars.setAttribute('aria-hidden', 'true');
  stage.parentElement.after(bars);
  PHRASES.forEach((_, i) => { const b = document.createElement('button'); b.tabIndex = -1; b.addEventListener('click', () => show(i)); bars.append(b); });
  bars.style.setProperty('--rot-ms', DURATION + 'ms');
  const show = (next) => {
    clearTimeout(timer);
    index = next;
    const old = stage.querySelector('.rot-phrase');
    const fresh = build(PHRASES[index]);
    fresh.style.position = 'absolute'; fresh.style.inset = '0';
    if (old) { old.classList.remove('rot-in'); old.classList.add('rot-out'); setTimeout(() => old.remove(), 450); }
    stage.append(fresh);
    requestAnimationFrame(() => requestAnimationFrame(() => fresh.classList.add('rot-in')));
    [...bars.children].forEach((b, i) => { b.classList.remove('active'); if (i === index) { void b.offsetWidth; b.classList.add('active'); } });
    if (!still) timer = setTimeout(() => show((index + 1) % PHRASES.length), DURATION);
  };
  fit(); addEventListener('resize', fit);
  show(0);
}
// Hero screenshots: the dashboard first, the terminal one click away.
document.querySelectorAll('[data-screen]').forEach(button => {
  if (button.tagName !== 'BUTTON') return;
  button.addEventListener('click', () => {
    document.querySelectorAll('.screen-tabs button').forEach(b => b.setAttribute('aria-selected', String(b === button)));
    document.querySelectorAll('.screens img').forEach(img => img.classList.toggle('shown', img.dataset.screen === button.dataset.screen));
  });
});
