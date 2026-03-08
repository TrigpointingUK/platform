import Card from "../ui/Card";
import AdvertCarousel from "../adverts/AdvertCarousel";

export default function Sidebar() {
  return (
    <aside className="w-full lg:w-96 flex-shrink-0 space-y-4 mb-6 lg:mb-0">
      {/* Advertisement Carousel */}
      <AdvertCarousel />

      {/* Quick Links */}
      <Card>
        <h3 className="font-bold text-lg mb-3 text-gray-800 dark:text-gray-100">Quick Links</h3>
        <nav className="space-y-2">
        <a
            href="/experiment"
            className="block text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 hover:underline"
          >
            🧪 TrigpointingUK Experiments page
          </a>
        <a
            href="https://www.ordnancesurvey.co.uk"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 hover:underline"
          >
            🗺️ Ordnance Survey
          </a>
          <a
            href="https://www.bench-marks.org.uk/"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 hover:underline"
          >
            📖 Bench Mark Database
          </a>
          <a
            href="https://interactivemaps.uk/os-benchmark-archive"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 hover:underline"
          >
            🗺️ OS Benchmark Archive
          </a>          
          <a
            href="https://www.haroldstreet.org.uk/"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 hover:underline"
          >
            🗺️ Harold Street
          </a>
        </nav>
      </Card>
    </aside>
  );
}

