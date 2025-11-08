import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import toast from "react-hot-toast";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Spinner from "../components/ui/Spinner";
import { legacyLogin } from "../lib/api";

interface MigrationFormData {
  username: string;
  password: string;
  email: string;
}

interface MigrationResult {
  success: boolean;
  message: string;
  userId?: number;
  username?: string;
  email?: string;
}

export default function LegacyMigration() {
  const { isAuthenticated, user } = useAuth0();
  const [formData, setFormData] = useState<MigrationFormData>({
    username: "",
    password: "",
    email: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<MigrationResult | null>(null);

  // If user is already logged in, show congratulations message
  if (isAuthenticated) {
    const username = user?.name || user?.nickname || user?.email || "there";
    return (
      <Layout>
        <div className="max-w-2xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">
            Legacy Account Migration
          </h1>
          <Card>
            <div className="bg-green-50 border border-green-200 rounded-lg px-6 py-5">
              <div className="flex items-start gap-3">
                <div className="text-3xl">🎉</div>
                <div className="flex-1">
                  <h2 className="text-xl font-bold text-green-800 mb-2">
                    Congratulations {username}!
                  </h2>
                  <p className="text-green-700 mb-3">
                    Your account has been migrated to the new login system.
                  </p>
                  <p className="text-green-700">
                    Please{" "}
                    <a
                      href="/contact"
                      className="text-trig-green-600 hover:text-trig-green-700 hover:underline font-medium"
                    >
                      contact us
                    </a>{" "}
                    if you are experiencing any unexpected behaviour.
                  </p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  const validateForm = (): boolean => {
    if (!formData.username.trim()) {
      return false;
    }
    if (!formData.password) {
      return false;
    }
    // Basic email validation
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!formData.email.trim() || !emailPattern.test(formData.email.trim())) {
      return false;
    }
    return true;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear result when user changes input
    if (result) {
      setResult(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      toast.error("Please fill in all fields with valid information");
      return;
    }

    setIsSubmitting(true);
    setResult(null);

    try {
      const response = await legacyLogin({
        username: formData.username.trim(),
        password: formData.password,
        email: formData.email.trim(),
      });

      setResult({
        success: true,
        message: "Migration successful! Your account has been migrated to the new login system.",
        userId: response.id,
        username: response.name,
        email: response.email,
      });

      toast.success("Account migration completed successfully!");
      
      // Reset form after successful migration
      setFormData({
        username: "",
        password: "",
        email: "",
      });
    } catch (error) {
      let errorMessage = "Migration failed. Please check your details and try again.";
      
      if (error instanceof Error) {
        // Try to extract meaningful error message from API response
        const errorText = error.message;
        if (errorText.includes("401") || errorText.includes("Incorrect username or password")) {
          errorMessage = "Incorrect username or password. Please check your credentials and try again.";
        } else if (errorText.includes("400") && errorText.includes("already in use")) {
          errorMessage = "This email address is already registered with another account. Please use a different email address.";
        } else if (errorText.includes("400")) {
          errorMessage = "Invalid request. Please check all fields are correctly filled.";
        } else if (errorText.includes("500")) {
          errorMessage = "A server error occurred. Please try again later.";
        }
      }

      setResult({
        success: false,
        message: errorMessage,
      });

      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormValid = validateForm();

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">
          Legacy Account Migration
        </h1>

        {/* Explanatory Text */}
        <Card className="mb-6">
          <div className="prose prose-sm max-w-none">
            <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-4">
              <p className="text-gray-700 mb-2">
                <strong>Important:</strong> This page does not log you into the TrigpointingUK website. 
                Instead, it is a migration tool for users who previously registered without an email address 
                but remember their username and password.
              </p>
              <p className="text-gray-700">
                By providing your username, password, and email address, you can migrate your log history 
                to the new login system, which authenticates users by email address and password.
              </p>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
              <p className="text-gray-700">
                <strong>Note:</strong> If you have already provided an email address with your account, 
                you do not need to use this page. Instead, you can {" "}
                <Link to="https://trigpointing.uk/auth0/login.php" className="text-trig-green-600 hover:text-trig-green-700 hover:underline">
                  login
                </Link>
                {" "} using the link on the TrigpointingUK homepage, follwing the "Can't log in to your account?" link if you need a password reset.
              </p>
            </div>
          </div>
        </Card>

        {/* Migration Form */}
        <Card>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">
            Migration Form
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Username <span className="text-red-600">*</span>
              </label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                maxLength={30}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                placeholder="Enter your username"
                disabled={isSubmitting}
              />
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Password <span className="text-red-600">*</span>
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                placeholder="Enter your password"
                disabled={isSubmitting}
              />
            </div>

            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Email Address <span className="text-red-600">*</span>
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                maxLength={255}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                placeholder="Enter your email address"
                disabled={isSubmitting}
              />
              <p className="mt-1 text-sm text-gray-500">
                This email will be used for your new account login.
              </p>
            </div>

            {/* Submit Button */}
            <div className="pt-4">
              <Button
                type="submit"
                disabled={!isFormValid || isSubmitting}
                className="w-full"
              >
                {isSubmitting ? (
                  <>
                    <Spinner size="sm" />
                    <span className="ml-2">Migrating...</span>
                  </>
                ) : (
                  "Attempt Migration"
                )}
              </Button>
            </div>
          </form>

          {/* Result Display */}
          {result && (
            <div className={`mt-6 p-4 rounded-lg border ${
              result.success
                ? "bg-green-50 border-green-200"
                : "bg-red-50 border-red-200"
            }`}>
              <div className={`font-semibold mb-2 ${
                result.success ? "text-green-800" : "text-red-800"
              }`}>
                {result.success ? "✓ Migration Successful" : "✗ Migration Failed"}
              </div>
              <p className={`text-sm ${
                result.success ? "text-green-700" : "text-red-700"
              }`}>
                {result.message}
              </p>
              {result.success && result.username && (
                <div className="mt-3 pt-3 border-t border-green-200">
                  <p className="text-sm text-green-700">
                    <strong>Username:</strong> {result.username}
                  </p>
                  {result.email && (
                    <p className="text-sm text-green-700">
                      <strong>Email:</strong> {result.email}
                    </p>
                  )}
                  <p className="text-sm text-green-700 mt-2">
                    You can now log in using your email address and password at the{" "}
                    <Link to="/" className="underline font-medium">
                      login page
                    </Link>
                    .
                  </p>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </Layout>
  );
}

