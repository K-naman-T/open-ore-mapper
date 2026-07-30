import { BrowserRouter, Routes, Route } from "react-router-dom"
import { HomePage } from "@/pages/home"
import { ResultPage } from "@/pages/result"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/result/:id" element={<ResultPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
