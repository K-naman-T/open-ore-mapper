import { BrowserRouter, Routes, Route } from "react-router-dom"
import { ToastProvider } from "./components/ui/Toast"
import { Home } from "./pages/Home"
import { MapViewPage } from "./pages/MapView"

export function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/maps/:uuid" element={<MapViewPage />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
