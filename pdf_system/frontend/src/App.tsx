import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./app/AuthProvider";
import AppRoutes from "./app/router";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="management-ui">
          <AppRoutes />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
