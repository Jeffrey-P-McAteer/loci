/**
 * This JS sets up the PWA and is responsible for
 * installing the serviceworker sw.js,
 * which gives foreign clients the ability to
 * talk to fragments of systems (remote map servers, radios operating over HTTP/websockets)
 * without requiring any local clients to be up (aka clients connected to radios with local storage.)
 */

function install_pwa_sw() {
  if (location.protocol === 'https:' || location.protocol === 'https') {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/pwa_sw.js');
    }
  }
}

install_pwa_sw();
document.addEventListener('DOMContentLoaded', install_pwa_sw);

