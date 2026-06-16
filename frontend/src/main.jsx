import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Очистка старого service worker (если остался от предыдущей сборки)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(registrations => {
    for (const registration of registrations) {
      registration.unregister()
    }
  })
  if (caches) {
    caches.keys().then(names => names.forEach(name => caches.delete(name)))
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)