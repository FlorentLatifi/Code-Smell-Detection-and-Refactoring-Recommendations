import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// Fontet vijnë nga paketa e jo nga një CDN: demonstrimi bëhet edhe pa internet,
// dhe një font që nuk ngarkohet e kthen ekranin te fonti i çdo sistemi (VD-119).
import "@fontsource-variable/instrument-sans";
import "@fontsource-variable/jetbrains-mono";
import { App } from "./App";
import { Boundary } from "./Boundary";
import "./design/utilities.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Boundary>
      <App />
    </Boundary>
  </StrictMode>,
);
