// Top-level routes. Authenticated users get the app shell; others see Login.
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Upload from "./pages/Upload";
import Report from "./pages/Report";
import Queue from "./pages/Queue";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/upload" replace />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/report/:contractId" element={<Report />} />
        <Route path="/queue" element={<Queue />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
