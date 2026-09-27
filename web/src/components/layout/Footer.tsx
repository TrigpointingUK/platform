export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-green-700 dark:bg-gray-800 text-gray-300 sticky bottom-0 z-40 border-t border-green-500 dark:border-gray-700 transition-colors duration-200">
      <div className="container mx-auto px-4 py-1">
        {/* Top row: Heading and description */}
        <div className="text-center leading-tight">
          <h3 className="text-white font-bold text-sm inline mr-2">© {currentYear} TrigpointingUK</h3>
        </div>

        {/* Bottom row: Links with dot separators and copyright */}
        <div className="flex flex-wrap items-center justify-center gap-x-3 text-xs leading-tight">
          <a 
            href="https://wiki.trigpointing.uk/TrigpointingUK_Wiki:About" 
            className="hover:text-white"
          >
            About
          </a>
          <span className="text-gray-500 dark:text-gray-600">•</span>
          <a 
            href="https://wiki.trigpointing.uk/TrigpointingUK_Wiki:Privacy_policy" 
            className="hover:text-white"
          >
            Privacy
          </a>
          <span className="text-gray-500 dark:text-gray-600">•</span>
          <a 
            href="https://wiki.trigpointing.uk/TrigpointingUK_Wiki:Terms_Of_Use" 
            className="hover:text-white"
          >
            ToS
          </a>
          <span className="text-gray-500 dark:text-gray-600">•</span>
          <a 
            href="/attributions" 
            className="hover:text-white"
          >
            Floss
          </a>
          <span className="text-gray-500 dark:text-gray-600">•</span>
          <a 
            href="/contact" 
            className="hover:text-white"
          >
            Contact
          </a>
        </div>
      </div>
    </footer>
  );
}

