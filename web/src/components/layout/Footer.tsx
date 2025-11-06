export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-green-700 text-gray-300 sticky bottom-0 z-40 border-t border-green-500">
      <div className="container mx-auto px-4 py-2">
        {/* Top row: Heading and description */}
        <div className="text-center mb-1">
          <h3 className="text-white font-bold text-sm inline mr-2">TrigpointingUK</h3>
          <span className="text-xs">
            The UK's premier resource for OS triangulation pillars and survey markers.
          </span>
        </div>

        {/* Bottom row: Links with dot separators and copyright */}
        <div className="flex flex-wrap items-center justify-center gap-x-3 text-xs">
          <a 
            href="https://wiki.trigpointing.uk/TrigpointingUK_Wiki:About" 
            className="hover:text-white"
          >
            About
          </a>
          <span className="text-gray-500">•</span>
          <a 
            href="https://wiki.trigpointing.uk/TrigpointingUK_Wiki:Privacy_policy" 
            className="hover:text-white"
          >
            Privacy Policy
          </a>
          <span className="text-gray-500">•</span>
          <a 
            href="https://wiki.trigpointing.uk/TrigpointingUK_Wiki:Terms_Of_Use" 
            className="hover:text-white"
          >
            Terms of Service
          </a>
          <span className="text-gray-500">•</span>
          <a 
            href="/contact" 
            className="hover:text-white"
          >
            Contact Us
          </a>
          <span className="text-gray-500">•</span>
          <a 
            href="/attributions" 
            className="hover:text-white"
          >
            Floss
          </a>
          <span className="text-gray-500 hidden sm:inline">•</span>
          <span className="w-full sm:w-auto text-center sm:text-left mt-1 sm:mt-0">
            © {currentYear} Trigpointing UK
          </span>
        </div>
      </div>
    </footer>
  );
}

