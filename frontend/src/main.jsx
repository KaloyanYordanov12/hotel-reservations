import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

// Self-hosted fonts (bundled by Vite, no external CDN). Only the weights the app
// actually uses: Fraunces 500 (headings and room nameplates), Inter 400/500/600
// (body, labels, buttons). @fontsource sets font-display: swap by default.
import '@fontsource/fraunces/500.css'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
