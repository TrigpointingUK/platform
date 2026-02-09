/**
 * 3D Trig Point Model page.
 *
 * Displays an interactive 3D model of a Hotine pillar (the classic
 * Ordnance Survey triangulation pillar) using React Three Fiber.
 */

import { Link } from "react-router-dom";
import { ArrowLeft, RotateCcw } from "lucide-react";
import Layout from "../../components/layout/Layout";
import Card from "../../components/ui/Card";
import TrigModelViewer from "../../components/experiment/TrigModelViewer";

export default function TrigModel() {
  return (
    <Layout>
      <title>3D Trig Pillar | TrigpointingUK</title>
      <div className="max-w-5xl mx-auto">
        <Card>
          <div className="p-6">
            {/* Back link */}
            <Link
              to="/experiment"
              className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-trig-green-600 dark:hover:text-trig-green-400 transition-colors mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Experiments
            </Link>

            {/* Header */}
            <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2">
              3D Trig Pillar
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              An interactive 3D model of an Ordnance Survey Hotine triangulation
              pillar.  Drag to rotate, scroll to zoom, and right-click to pan.
            </p>

            {/* Hint */}
            <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 mb-4">
              <RotateCcw className="w-3.5 h-3.5" />
              <span>
                The model rotates automatically — grab it to take control
              </span>
            </div>

            {/* 3D Viewer */}
            <div className="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-900 h-[70vh]">
              <TrigModelViewer />
            </div>
          </div>
        </Card>
      </div>
    </Layout>
  );
}

