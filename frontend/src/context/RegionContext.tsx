import React, { createContext, useContext, useState } from 'react';
import { useAuth } from './AuthContext';

interface RegionContextType {
  selectedRegion: string; // '' for All, 'IN', 'AU'
  setSelectedRegion: (region: string) => void;
  activeRegion: string;   // resolved active region for formatting ('IN' or 'AU')
  currencySymbol: string; // '₹' or 'A$'
  currencyCode: string;   // 'INR' or 'AUD'
  taxLabel: string;       // 'GST'
  incentiveLabel: string; // 'Subsidy' or 'Government incentive (STCs and rebates)'
  electricityProviderLabel: string; // 'DISCOM' or 'Electricity retailer'
  postcodeLabel: string;  // 'Pincode' or 'Postcode'
  formatMoney: (amount: number | null | undefined, currency?: string) => string;
}

const RegionContext = createContext<RegionContextType | undefined>(undefined);

export const RegionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();

  const [selectedRegion, setSelectedRegionState] = useState<string>(() => {
    return localStorage.getItem('solar_crm_selected_region') || '';
  });

  const setSelectedRegion = (reg: string) => {
    setSelectedRegionState(reg);
    if (reg) {
      localStorage.setItem('solar_crm_selected_region', reg);
    } else {
      localStorage.removeItem('solar_crm_selected_region');
    }
  };

  // Determine effective region for single-region restricted users vs managers
  const userAllowed = Array.isArray(user?.allowed_regions) ? user.allowed_regions : [];
  const isRestrictedSingleRegion = userAllowed.length === 1;
  const singleRegionCode = isRestrictedSingleRegion
    ? (typeof userAllowed[0] === 'string' ? userAllowed[0] : (userAllowed[0] as any).code)
    : '';

  const effectiveRegion = (isRestrictedSingleRegion ? singleRegionCode : (selectedRegion || user?.default_region || 'IN')).toUpperCase();

  const isAU = effectiveRegion === 'AU';

  const currencySymbol = isAU ? 'A$' : '₹';
  const currencyCode = isAU ? 'AUD' : 'INR';
  const taxLabel = 'GST';
  const incentiveLabel = isAU ? 'Government incentive (STCs and rebates)' : 'Subsidy';
  const electricityProviderLabel = isAU ? 'Electricity retailer' : 'DISCOM';
  const postcodeLabel = isAU ? 'Postcode' : 'Pincode';

  const formatMoney = (amount: number | null | undefined, customCurrency?: string): string => {
    if (amount === null || amount === undefined) return '-';
    const curr = (customCurrency || currencyCode).toUpperCase();
    const symbol = curr === 'AUD' ? 'A$' : (curr === 'INR' ? '₹' : curr + ' ');

    try {
      if (curr === 'INR') {
        return `${symbol}${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(amount)}`;
      } else {
        return `${symbol}${new Intl.NumberFormat('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount)}`;
      }
    } catch {
      return `${symbol}${amount.toLocaleString()}`;
    }
  };

  return (
    <RegionContext.Provider
      value={{
        selectedRegion,
        setSelectedRegion,
        activeRegion: effectiveRegion,
        currencySymbol,
        currencyCode,
        taxLabel,
        incentiveLabel,
        electricityProviderLabel,
        postcodeLabel,
        formatMoney,
      }}
    >
      {children}
    </RegionContext.Provider>
  );
};

export const useRegion = (): RegionContextType => {
  const context = useContext(RegionContext);
  if (!context) {
    throw new Error('useRegion must be used within a RegionProvider');
  }
  return context;
};
