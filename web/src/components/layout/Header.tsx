import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { GlobalSearch } from "./GlobalSearch";
import ThemeToggle from "../ui/ThemeToggle";

export default function Header() {
  const { isAuthenticated, user, loginWithRedirect, logout } = useAuth0();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // Check if user has api-admin role (from ID token custom claim)
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  const handleLogout = () => {
    logout({
      logoutParams: {
        returnTo: window.location.origin + "/",
        federated: true,
      },
    });
  };

  const handleSearchComplete = () => {
    setMobileMenuOpen(false);
  };

  return (
    <header className="bg-trig-green-600 text-white shadow-md sticky top-0 z-[1200]">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 mr-6">
            <img src="/TUK-Logo.svg" alt="TrigpointingUK" className="h-10 w-10" />
            <span className="text-xl font-bold hidden sm:inline">TrigpointingUK</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <a
              href="https://wiki.trigpointing.uk/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-trig-green-100 transition-colors"
            >
              Wiki
            </a>
            <a
              href="https://forum.trigpointing.uk/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-trig-green-100 transition-colors"
            >
              Forum
            </a>
          </nav>

          {/* Search Bar - Desktop */}
          <div className="hidden md:flex flex-1 max-w-md mx-4">
            <GlobalSearch
              placeholder="Search trigs, places, users..."
              onSearch={handleSearchComplete}
            />
          </div>

          {/* User Menu */}
          <div className="flex items-center gap-2">
            {/* Theme Toggle */}
            <ThemeToggle />
            
            {isAuthenticated && user ? (
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 hover:bg-trig-green-700 px-3 py-2 rounded-md transition-colors"
                >
                  {user.picture && (
                    <img
                      src={user.picture}
                      alt={user.name || "User"}
                      className="h-8 w-8 rounded-full"
                    />
                  )}
                  <span className="hidden md:inline text-sm font-medium">
                    {user.name || user.email}
                  </span>
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg py-1 text-gray-700 dark:text-gray-200 z-[1300]">
                    <Link
                      to="/profile"
                      className="block px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      Profile
                    </Link>
                    <Link
                      to="/preferences"
                      className="block px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      Preferences
                    </Link>
                    {hasAdminRole && (
                      <Link
                        to="/admin"
                        className="block px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        Admin
                      </Link>
                    )}
                    <hr className="my-1 border-gray-200 dark:border-gray-600" />
                    <button
                      onClick={() => {
                        setUserMenuOpen(false);
                        handleLogout();
                      }}
                      className="block w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => loginWithRedirect({
                  appState: { returnTo: window.location.pathname }
                })}
                className="bg-white text-trig-green-600 px-4 py-2 rounded-md font-medium hover:bg-trig-green-50 transition-colors"
              >
                Login
              </button>
            )}

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 hover:bg-trig-green-700 rounded-md"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                {mobileMenuOpen ? (
                  <path d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden pb-4 border-t border-trig-green-500 mt-2 pt-2">
            <nav className="flex flex-col gap-2">
              <div className="mb-2">
                <GlobalSearch
                  placeholder="Search trigs, places, users..."
                  onSearch={handleSearchComplete}
                />
              </div>
              <a
                href="https://wiki.trigpointing.uk"
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 hover:bg-trig-green-700 rounded-md"
              >
                Wiki
              </a>
              <a
                href="https://forum.trigpointing.uk"
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 hover:bg-trig-green-700 rounded-md"
              >
                Forum
              </a>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}

