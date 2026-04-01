import { Link } from "react-router-dom";

import Button from "../components/ui/Button";
import { useNoIndex } from "../hooks/useNoIndex";

export default function NotFound() {
  useNoIndex(true);

  return (
    <>
      <title>Page Not Found | TrigpointingUK</title>
      <div className="text-center py-12">
        <div className="text-6xl mb-4">🧭</div>
        <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100 mb-4">404 - Not Found</h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          The page you're looking for doesn't exist.
        </p>
        <Link to="/">
          <Button variant="primary">Return Home</Button>
        </Link>
      </div>
    </>
  );
}

