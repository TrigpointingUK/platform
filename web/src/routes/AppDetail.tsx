import { useParams } from "react-router-dom";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";

export default function AppDetail() {
  const { id } = useParams<{ id: string }>();

  return (
    <Layout>
      <title>Trig #{id} | TrigpointingUK</title>
      <div className="max-w-4xl mx-auto">
        <Card>
          <h1 className="text-3xl font-bold text-trig-green-600 mb-4">
            Trig Point Details
          </h1>
          <p className="text-gray-700">
            This is your friendly /app/ page, giving you full details of trig point{" "}
            <strong>#{id}</strong>
          </p>
          <p className="text-sm text-gray-500 mt-4">
            Note: Full trig point detail page coming soon!
          </p>
        </Card>
      </div>
    </Layout>
  );
}

