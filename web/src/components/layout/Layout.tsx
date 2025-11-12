import { ReactNode } from "react";
import Header from "./Header";
import Footer from "./Footer";
import Auth0CallbackHandler from "../Auth0CallbackHandler";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Auth0CallbackHandler />
      <Header />
      <main className="flex-1 container mx-auto px-4 py-6">
        {children}
      </main>
      <Footer />
    </div>
  );
}

