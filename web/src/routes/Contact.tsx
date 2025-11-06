import { useState, useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import toast from "react-hot-toast";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Spinner from "../components/ui/Spinner";
import { useUserProfile } from "../hooks/useUserProfile";
import { submitContact } from "../lib/api";

interface ContactFormData {
  name: string;
  email: string;
  subject: string;
  message: string;
}

export default function Contact() {
  const { isAuthenticated, user: auth0User, getAccessTokenSilently } = useAuth0();
  // Fetch profile if authenticated (will fail gracefully if not authenticated)
  const { data: userProfile, error: profileError } = useUserProfile("me");
  
  const [formData, setFormData] = useState<ContactFormData>({
    name: "",
    email: "",
    subject: "",
    message: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Pre-populate form for logged-in users
  useEffect(() => {
    if (isAuthenticated && auth0User) {
      if (userProfile && !profileError) {
        // Use profile data if available
        const fullName = [userProfile.firstname, userProfile.surname]
          .filter(Boolean)
          .join(" ");
        const displayName = fullName || userProfile.name || auth0User.name || "";
        const email = userProfile.prefs?.email || auth0User.email || "";

        setFormData((prev) => ({
          ...prev,
          name: displayName,
          email: email,
        }));
      } else {
        // Fallback to Auth0 user data if profile not loaded or errored
        const displayName = auth0User.name || auth0User.nickname || "";
        const email = auth0User.email || "";

        setFormData((prev) => ({
          ...prev,
          name: displayName,
          email: email,
        }));
      }
    }
  }, [isAuthenticated, userProfile, auth0User, profileError]);

  const validateForm = (): boolean => {
    if (!formData.name.trim()) {
      return false;
    }
    if (!formData.email.trim()) {
      return false;
    }
    // Basic email validation
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailPattern.test(formData.email.trim())) {
      return false;
    }
    if (!formData.subject.trim()) {
      return false;
    }
    if (!formData.message.trim()) {
      return false;
    }
    return true;
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      toast.error("Please fill in all fields with valid information");
      return;
    }

    setIsSubmitting(true);

    try {
      // Get token if authenticated (optional - endpoint works without auth)
      let token: string | undefined;
      if (isAuthenticated) {
        try {
          token = await getAccessTokenSilently();
        } catch (error) {
          // If token retrieval fails, continue without token
          console.warn("Failed to get access token for contact form:", error);
        }
      }

      await submitContact(
        {
          name: formData.name.trim(),
          email: formData.email.trim(),
          subject: formData.subject.trim(),
          message: formData.message.trim(),
        },
        token
      );

      toast.success("Your message has been sent successfully!");
      
      // Reset form after successful submission
      setFormData({
        name: isAuthenticated && userProfile 
          ? [userProfile.firstname, userProfile.surname].filter(Boolean).join(" ") || userProfile.name || ""
          : "",
        email: isAuthenticated && userProfile
          ? userProfile.prefs?.email || ""
          : "",
        subject: "",
        message: "",
      });
    } catch (error) {
      let errorMessage = "Failed to send message. Please try again later.";
      
      if (error instanceof Error) {
        const errorText = error.message;
        if (errorText.includes("400")) {
          errorMessage = "Invalid request. Please check all fields are correctly filled.";
        } else if (errorText.includes("500")) {
          errorMessage = "A server error occurred. Please try again later.";
        }
      }

      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormValid = validateForm();

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Contact Us</h1>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name */}
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Name <span className="text-red-600">*</span>
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                maxLength={100}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                placeholder="Enter your name"
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
                placeholder="your.email@example.com"
                disabled={isSubmitting}
              />
            </div>

            {/* Subject */}
            <div>
              <label
                htmlFor="subject"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Subject <span className="text-red-600">*</span>
              </label>
              <input
                type="text"
                id="subject"
                name="subject"
                value={formData.subject}
                onChange={handleChange}
                required
                maxLength={200}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                placeholder="What is this regarding?"
                disabled={isSubmitting}
              />
            </div>

            {/* Message */}
            <div>
              <label
                htmlFor="message"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Message <span className="text-red-600">*</span>
              </label>
              <textarea
                id="message"
                name="message"
                value={formData.message}
                onChange={handleChange}
                required
                rows={6}
                maxLength={5000}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                placeholder="Enter your message..."
                disabled={isSubmitting}
              />
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
                    <span className="ml-2">Sending...</span>
                  </>
                ) : (
                  "Send"
                )}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </Layout>
  );
}

