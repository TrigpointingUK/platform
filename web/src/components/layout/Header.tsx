import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { GlobalSearch } from "./GlobalSearch";

export default function Header() {
  const { isAuthenticated, user, loginWithRedirect, logout } = useAuth0();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

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
    <header className="bg-trig-green-600 text-white shadow-md sticky top-0 z-50">
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
            <a
              href="https://trigpointing.uk/trigtools"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-trig-green-100 transition-colors"
            >
              TrigTools
            </a>
            <Link to="/map" className="hover:text-trig-green-100 transition-colors">
              Map
            </Link>
            {isAuthenticated && (
              <Link to="/mytrigs" className="hover:text-trig-green-100 transition-colors">
                MyTrigs
              </Link>
            )}
          </nav>

          {/* Search Bar - Desktop */}
          <div className="hidden md:flex flex-1 max-w-md mx-4">
            <GlobalSearch
              placeholder="Search trigs, places, users..."
              onSearch={handleSearchComplete}
            />
          </div>

          {/* User Menu */}
          <div className="flex items-center gap-4">
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
                      className="h-8 w-8 rounded-full border-2 border-white"
                    />
                  )}
                  <span className="hidden md:inline text-sm font-medium">
                    {user.name || user.email}
                  </span>
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 text-gray-700">
                    <Link
                      to="/profile"
                      className="block px-4 py-2 hover:bg-gray-100"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      Profile
                    </Link>
                    <Link
                      to="/settings"
                      className="block px-4 py-2 hover:bg-gray-100"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      Settings
                    </Link>
                    <hr className="my-1" />
                    <button
                      onClick={() => {
                        setUserMenuOpen(false);
                        handleLogout();
                      }}
                      className="block w-full text-left px-4 py-2 hover:bg-gray-100"
                    >
                      Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => loginWithRedirect()}
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
                href="https://trigpointing.uk/wiki"
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 hover:bg-trig-green-700 rounded-md"
              >
                Wiki
              </a>
              <a
                href="https://trigpointing.uk/forum"
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 hover:bg-trig-green-700 rounded-md"
              >
                Forum
              </a>
              <a
                href="https://trigpointing.uk/trigtools"
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 hover:bg-trig-green-700 rounded-md"
              >
                TrigTools
              </a>
              <Link
                to="/map"
                className="px-3 py-2 hover:bg-trig-green-700 rounded-md"
                onClick={() => setMobileMenuOpen(false)}
              >
                Map
              </Link>
              {isAuthenticated && (
                <Link
                  to="/mytrigs"
                  className="px-3 py-2 hover:bg-trig-green-700 rounded-md"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  MyTrigs
                </Link>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}

