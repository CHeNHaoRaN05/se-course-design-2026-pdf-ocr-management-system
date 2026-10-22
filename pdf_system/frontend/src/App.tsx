import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./app/AuthProvider";
import AppRoutes from "./app/router";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
