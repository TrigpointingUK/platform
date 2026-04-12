/**
 * Experiment Index Page
 *
 * Landing page for the /experiment section, listing all available
 * experimental features and data exploration tools.
 */

import { Link } from "react-router-dom";
import {
  FlaskConical,
  Map,
  Calendar,
  ChevronRight,
  Sparkles,
  Filter,
  Box,
  Users,
} from "lucide-react";

import Card from "../components/ui/Card";

interface ExperimentCardProps {
  to: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  tags?: string[];
}

function ExperimentCard({
  to,
  icon,
  title,
  description,
  tags = [],
}: ExperimentCardProps) {
  return (
    <Link
      to={to}
      className="group block p-6 bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-trig-green-500 dark:hover:border-trig-green-400 transition-all duration-200 hover:shadow-lg hover:shadow-trig-green-500/10"
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 p-3 bg-gradient-to-br from-trig-green-500 to-trig-green-600 rounded-lg text-white shadow-md group-hover:scale-110 transition-transform duration-200">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 group-hover:text-trig-green-600 dark:group-hover:text-trig-green-400 transition-colors">
              {title}
            </h3>
            <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-trig-green-500 group-hover:translate-x-1 transition-all" />
          </div>
          <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">
            {description}
          </p>
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

export default function ExperimentIndex() {
  const experiments = [
    {
      to: "/experiment/coop",
      icon: <Users className="w-6 h-6" />,
      title: "Co-op Trigpointing",
      description:
        "Compare trigpoint visits across members. Find trigs that others have visited but you haven't, or discover trigs that are new for everyone.",
      tags: ["Social", "Planning", "New"],
    },
    {
      to: "/experiment/3d-model",
      icon: <Box className="w-6 h-6" />,
      title: "3D Trig Pillar",
      description:
        "An interactive 3D model of a Hotine pillar. Rotate, zoom and pan to explore every detail.",
      tags: ["3D", "Visualisation", "New"],
    },
    {
      to: "/experiment/trigs-v2",
      icon: <Filter className="w-6 h-6" />,
      title: "Trigs Browser v2 (Filter Chips)",
      description:
        "An experimental redesign of the trigpoints browser using a filter chips UI pattern. Adds new filters for historic use, condition, physical type, and improved area selection.",
      tags: ["UX Experiment", "Filters", "New"],
    },
    {
      to: "/experiment/survey-timeline",
      icon: <Calendar className="w-6 h-6" />,
      title: "Survey Timeline",
      description:
        "An animated visualisation showing when trigpoints were triangulated and levelled by the Ordnance Survey. Watch the retriangulation of Great Britain unfold across the decades.",
      tags: ["Visualisation", "Animation", "Historical"],
    },
    {
      to: "/experiment/coordinates",
      icon: <Map className="w-6 h-6" />,
      title: "Coordinate Discrepancy Monitor",
      description:
        "Monitor coordinate consistency between WGS84, OSGB36, and legacy data sources. Useful for identifying trigpoints with location data that may need attention.",
      tags: ["Data Quality", "Admin Tool"],
    },
  ];

  return (
    <>
      <title>Experiments | TrigpointingUK</title>
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="p-8">
            {/* Header */}
            <div className="flex items-center gap-4 mb-2">
              <div className="p-3 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl shadow-lg">
                <FlaskConical className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                  Experiments
                </h1>
                <p className="text-gray-500 dark:text-gray-400 text-sm">
                  Data exploration &amp; visualisation tools
                </p>
              </div>
            </div>

            {/* Description */}
            <div className="mt-6 mb-8 p-4 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 rounded-lg border border-amber-200 dark:border-amber-800/50">
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-amber-800 dark:text-amber-200 leading-relaxed">
                  These experimental pages showcase new features and data
                  exploration tools that are still in development. They may
                  change or be removed at any time, but we hope you find them
                  interesting!
                </p>
              </div>
            </div>

            {/* Experiment Cards */}
            <div className="space-y-4">
              {experiments.map((experiment) => (
                <ExperimentCard key={experiment.to} {...experiment} />
              ))}
            </div>

            {/* Footer */}
            <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
                Have an idea for a new experiment?{" "}
                <Link
                  to="/contact"
                  className="text-trig-green-600 dark:text-trig-green-400 hover:underline"
                >
                  Let us know!
                </Link>
              </p>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}

