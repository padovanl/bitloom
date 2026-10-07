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
