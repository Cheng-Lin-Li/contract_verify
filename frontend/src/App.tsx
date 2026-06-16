// Top-level routes. Authenticated users get the app shell; others see Login.
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Contracts from "./pages/Contracts";
import Upload from "./pages/Upload";
import Report from "./pages/Report";
import Queue from "./pages/Queue";
import Library from "./pages/Library";
import DocumentViewer from "./pages/DocumentViewer";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/contracts" replace />} />
        <Route path="/contracts" element={<Contracts />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/report/:contractId" element={<Report />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/library" element={<Library />} />
        <Route path="/document/:docId" element={<DocumentViewer />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
