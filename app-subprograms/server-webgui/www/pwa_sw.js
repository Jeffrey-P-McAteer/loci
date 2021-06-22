/**
 * This script is responsible for responding to HTTP requests when
 * operating offline. You can assume this will only ever happen on a remote client.
 */

// Update the name of the cache with each major revision to invalidate old app fragments
var cacheName = 'app-pwa-v0.0.4';

// Caching only occurs on these hosts b/c development is slow when you have to
// constantly bump a version number.
var activeServerHostsWithCaches = [
  'loci.devil-tech.com', 'jeffrey-p-mcateer.github.io',
];

var filesToCache = [
  './',
  './index.html',

  './style.css',

  './app_gui.js',
  './app_lib.js',
  './app_pwa.js',
  './app_util.js',
  './app_test.js',
  //'./pwa_sw.js',
  //'./manifest.json'

  // Generated resources
  './gen/icon-192.png',
  './gen/icon-512.png',

  // 3rd-party libs
  './lib/split.min.js',
  './lib/worldwind.min.js',

];

var _self = self;
function register_sw_offline_cache() {
  /* Start the service worker and cache all of the app's content */
  _self.addEventListener('install', function(e) {
    e.waitUntil(
      caches.open(cacheName).then(function(cache) {
        http_get_json('./api/additional_offline_files', function(status_code, offline_files_arr) {
          cache.addAll(offline_files_arr);
        });
        return cache.addAll(filesToCache);
      })
    );
    _self.skipWaiting();
  });

  /* Serve cached content when offline */
  _self.addEventListener('fetch', function(e) {
    e.respondWith(
      caches.match(e.request).then(function(response) {
        return response || fetch(e.request);
      })
    );
  });
}

// Start logic

if (activeServerHostsWithCaches.includes(location.hostname)) {
  console.log('Caching version', cacheName);
  register_sw_offline_cache();
}
else {
  console.log('Not registering offline files b/c ', location.hostname, ' not in ', activeServerHostsWithCaches);
}


