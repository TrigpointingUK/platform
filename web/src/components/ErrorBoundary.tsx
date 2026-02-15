import { Component, ErrorInfo, ReactNode } from 'react';
import Button from './ui/Button';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error to console for debugging
    console.error('Uncaught error:', error, errorInfo);
    
    // Check if it's a chunk loading error (common in production after deployments)
    if (error.message.includes('Failed to fetch dynamically imported module')) {
      console.error('Chunk loading error detected. This usually means the app was updated. Reloading...');
    }
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  public render() {
    if (this.state.hasError) {
      const isChunkError = this.state.error?.message.includes('Failed to fetch dynamically imported module');
      
      return (
        <div className="min-h-dvh flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
          <div className="max-w-md w-full text-center">
            <div className="text-6xl mb-4">⚠️</div>
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-4">
              {isChunkError ? 'App Update Available' : 'Something went wrong'}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {isChunkError 
                ? 'The application has been updated. Please reload the page to get the latest version.'
                : 'An unexpected error occurred. Please try reloading the page.'}
            </p>
            {import.meta.env.DEV && this.state.error && (
              <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded text-left">
                <p className="text-sm font-mono text-red-800 dark:text-red-300 break-all">
                  {this.state.error.message}
                </p>
              </div>
            )}
            <div className="flex gap-4 justify-center">
              <Button onClick={this.handleReload} variant="primary">
                Reload Page
              </Button>
              <Button onClick={this.handleGoHome} variant="secondary">
                Go to Home
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

