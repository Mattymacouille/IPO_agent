const CACHE_NAME = 'ipo-agent-cache-v2'; // change ce numéro à chaque déploiement majeur
const ASSETS = [
  './index.html',
  './app.js',
  './manifest.json'
];

// Installation : mise en cache des fichiers de structure de base
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

// Activation et nettoyage des vieux caches
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
});

// Stratégie Réseau en priorité, repli sur le cache si hors-ligne
self.addEventListener('fetch', (e) => {
  e.respondWith(
    fetch(e.request, { cache: 'no-store' }).catch(() => {
      return caches.match(e.request);
    })
  );
});