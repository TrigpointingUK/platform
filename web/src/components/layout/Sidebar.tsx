import Card from "../ui/Card";
import AdvertCarousel from "../adverts/AdvertCarousel";

export default function Sidebar() {
  return (
    <aside className="w-full lg:w-96 flex-shrink-0 space-y-4 mb-6 lg:mb-0">
      {/* Advertisement Carousel */}
      <AdvertCarousel />

      {/* Quick Links */}
      <Card>
        <h3 className="font-bold text-lg mb-3 text-gray-800">Quick Links</h3>
        <nav className="space-y-2">
          <a
            href="https://trigpointing.uk/wiki"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-trig-green-600 hover:text-trig-green-700 hover:underline"
          >
            📖 Wiki
          </a>
          <a
            href="https://trigpointing.uk/forum"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-trig-green-600 hover:text-trig-green-700 hover:underline"
          >
            💬 Forum
          </a>
          <a
            href="https://trigpointing.uk/trigtools"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-trig-green-600 hover:text-trig-green-700 hover:underline"
          >
            🔧 TrigTools
          </a>
          <a
            href="https://www.ordnancesurvey.co.uk"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-trig-green-600 hover:text-trig-green-700 hover:underline"
          >
            🗺️ Ordnance Survey
          </a>
        </nav>
      </Card>

      {/* About */}
      <Card>
        <h3 className="font-bold text-lg mb-2 text-gray-800">About</h3>
        <p className="text-sm text-gray-600">
          Trigpointing UK is the largest database of triangulation pillars and survey
          markers in the UK.
        </p>
      </Card>
    </aside>
  );
}

