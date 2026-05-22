import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { OrbProvider } from "./context/OrbContext.jsx";
import { ThemeProvider } from "./context/ThemeContext.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider>
      <OrbProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </OrbProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
