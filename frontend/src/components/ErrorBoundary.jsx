import { Component } from 'react';
import { Button } from './ui/Button';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-[calc(100vh-120px)] flex items-center justify-center">
          <div className="text-center p-8">
            <p className="text-4xl mb-4">⚠️</p>
            <h2 className="text-xl font-semibold text-text-primary mb-2">
              Что-то пошло не так
            </h2>
            <p className="text-text-secondary mb-4 text-sm">
              {this.state.error?.message || 'Неизвестная ошибка'}
            </p>
            <Button onClick={this.handleRetry} variant="primary">
              Попробовать снова
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export function withErrorBoundary(WrappedComponent, fallback = null) {
  return function WithErrorBoundary(props) {
    return (
      <ErrorBoundary fallback={fallback}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    );
  };
}

export default ErrorBoundary;
