import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../LoadingSpinner/LoadingSpinner';
import './ProtectedRoute.css';

interface ProtectedRouteProps {
  requireGuest?: boolean;
  requireAuth?: boolean;
  redirectTo?: string;
  children?: React.ReactNode;
  loadingMessage?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  requireGuest = false,
  requireAuth = false,
  redirectTo = '/',
  children,
  loadingMessage = 'Loading...',
}) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="auth-loading-container">
        <LoadingSpinner size="large" />
        <p className="loading-message">{loadingMessage}</p>
      </div>
    );
  }

  // If route requires authentication and user is not logged in
  if (requireAuth && !user) {
    // Redirect to login page, but save the current location to return to after login
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }


  // If route is only for guests and user is logged in
  if (requireGuest && user) {
    return <Navigate to={redirectTo} replace />;
  }

  // If we have children, render them, otherwise render the Outlet
  return children ? <>{children}</> : <Outlet />;
};

export default ProtectedRoute;
