import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User } from '../api/types';
import { apiLogin, fetchMe, clearTokens, getAccessToken } from '../api/client';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: { username: string; password: string }) => Promise<User>;
  logout: () => void;
  refetchUser: () => Promise<void>;
  isAdminOrManager: boolean;
  isSurveyor: boolean;
  isSalesperson: boolean;
  can: (permissionKey: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refetchUser = async () => {
    try {
      const userData = await fetchMe();
      setUser(userData);
    } catch {
      setUser(null);
      clearTokens();
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const token = getAccessToken();
      if (token) {
        try {
          const userData = await fetchMe();
          setUser(userData);
        } catch {
          clearTokens();
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (credentials: { username: string; password: string }): Promise<User> => {
    await apiLogin(credentials);
    const userData = await fetchMe();
    setUser(userData);
    return userData;
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  const isAdminOrManager = Boolean(user && (user.role === 'admin' || user.role === 'manager'));
  const isSurveyor = Boolean(user && user.role === 'surveyor');
  const isSalesperson = Boolean(user && user.role === 'salesperson');

  const can = (permissionKey: string): boolean => {
    if (!user) return false;
    if (user.role === 'admin') return true;
    if (!user.permissions || !Array.isArray(user.permissions)) return false;
    return user.permissions.includes(permissionKey);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: Boolean(user),
        isLoading,
        login,
        logout,
        refetchUser,
        isAdminOrManager,
        isSurveyor,
        isSalesperson,
        can,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
