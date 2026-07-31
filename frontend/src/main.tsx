import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import App from "@/App";
import { Layout } from "@/components/Layout";
import HeroesPage from "@/pages/HeroesPage";
import ItemsPage from "@/pages/ItemsPage";
import "@/index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

const container = document.getElementById("root");
if (!container) throw new Error("#root missing from index.html");

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<App />} />
            <Route path="heroes" element={<HeroesPage />} />
            <Route path="items" element={<ItemsPage />} />
            {/* Steam bounces back to /?login=… which the index route handles. */}
            <Route path="*" element={<App />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
