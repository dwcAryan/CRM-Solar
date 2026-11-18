import type { DriveStep } from 'driver.js';

export interface TourDefinition {
  id: string;
  title: string;
  description: string;
  duration: string;
  roles: string[];
  steps: DriveStep[];
}

export const TOUR_DEFINITIONS: Record<string, TourDefinition> = {
  complete: {
    id: 'complete',
    title: 'Complete System Tour',
    description: 'A comprehensive 3-minute tour of all primary Solar CRM workspaces and features.',
    duration: '3 mins',
    roles: ['admin', 'manager', 'salesperson', 'surveyor'],
    steps: [
      {
        element: '[data-tour="sidebar-nav"]',
        popover: {
          title: '🧭 Navigation Sidebar',
          description: 'Access all core modules: Dashboard, Leads pipeline, Site Surveys, and Quotes generator.',
          side: 'right',
          align: 'start',
        },
      },
      {
        element: '[data-tour="sidebar-leads"]',
        popover: {
          title: '👥 Leads & Pipeline',
          description: 'Manage active opportunities, log customer calls, and view automated retry ladders.',
          side: 'right',
          align: 'start',
        },
      },
      {
        element: '[data-tour="sidebar-surveys"]',
        popover: {
          title: '📐 Site Surveys',
          description: 'Schedule rooftop inspections, record tilt and shading, and upload inspection photos.',
          side: 'right',
          align: 'start',
        },
      },
      {
        element: '[data-tour="sidebar-quotes"]',
        popover: {
          title: '⚡ Quotes & Proposals',
          description: 'Calculate solar system sizing, apply subsidies/rebates, and download branded proposals.',
          side: 'right',
          align: 'start',
        },
      },
      {
        element: '[data-tour="header-region"]',
        popover: {
          title: '🌏 Multi-Country Region Selector',
          description: 'Switch between India (IN, INR ₹) and Australia (AU, AUD $) configurations with one click.',
          side: 'bottom',
          align: 'end',
        },
      },
      {
        element: '[data-tour="header-notifications"]',
        popover: {
          title: '🔔 Notifications & Alerts',
          description: 'Get real-time updates for newly assigned leads, survey requests, and follow-up reminders.',
          side: 'bottom',
          align: 'end',
        },
      },
      {
        element: '[data-tour="helpbot-fab"]',
        popover: {
          title: '🤖 In-App Help Assistant',
          description: 'Have questions about rules, outcomes, or settings? Click here or press ? anytime to ask Helpbot.',
          side: 'left',
          align: 'end',
        },
      },
    ],
  },

  'getting-started': {
    id: 'getting-started',
    title: 'Getting Started',
    description: 'Learn the essential layout and daily habits to start closing solar deals.',
    duration: '1 min',
    roles: ['salesperson', 'manager', 'admin'],
    steps: [
      {
        element: '[data-tour="sidebar-nav"]',
        popover: {
          title: 'Core Workspaces',
          description: 'Your primary workspaces are organized on the left navigation bar.',
          side: 'right',
        },
      },
      {
        element: '[data-tour="header-user-menu"]',
        popover: {
          title: 'User Profile & Tour Center',
          description: 'Access your account settings, dark mode toggle, and replay any guided walkthrough.',
          side: 'bottom',
          align: 'end',
        },
      },
      {
        element: '[data-tour="helpbot-fab"]',
        popover: {
          title: 'Quick Help (Press ?)',
          description: 'The Help Assistant is always ready to answer questions about CRM features.',
          side: 'left',
        },
      },
    ],
  },

  leads: {
    id: 'leads',
    title: 'Leads & Interaction Logging',
    description: 'Master the CRM Golden Rule, 11 call outcomes, and automated retry ladders.',
    duration: '2 mins',
    roles: ['salesperson', 'manager', 'admin'],
    steps: [
      {
        element: '[data-tour="sidebar-leads"]',
        popover: {
          title: 'Leads Pipeline',
          description: 'View leads grouped by stage or filtered by priority and assigned owner.',
          side: 'right',
        },
      },
      {
        element: '[data-tour="helpbot-fab"]',
        popover: {
          title: 'CRM Golden Rule',
          description: 'Always log an immediate outcome after every call. Ask Helpbot "What are call outcomes?" to learn more.',
          side: 'left',
        },
      },
    ],
  },

  surveys: {
    id: 'surveys',
    title: 'Site Surveys & Inspections',
    description: 'How surveyors inspect rooftops, capture photos, and submit feasibility reports.',
    duration: '1.5 mins',
    roles: ['surveyor', 'manager', 'admin', 'salesperson'],
    steps: [
      {
        element: '[data-tour="sidebar-surveys"]',
        popover: {
          title: 'Surveys Workspace',
          description: 'Track assigned roof inspections with address, map location, and contact numbers.',
          side: 'right',
        },
      },
    ],
  },

  quotes: {
    id: 'quotes',
    title: 'Quotes & Pricing Proposals',
    description: 'Calculate system size, solar incentives (Subsidy/STC), and export customer PDFs.',
    duration: '1.5 mins',
    roles: ['salesperson', 'manager', 'admin'],
    steps: [
      {
        element: '[data-tour="sidebar-quotes"]',
        popover: {
          title: 'Quotes & Proposals',
          description: 'Generate instant estimates with net pricing after government subsidies.',
          side: 'right',
        },
      },
    ],
  },

  import: {
    id: 'import',
    title: 'CSV Lead Import',
    description: 'Bulk upload customer spreadsheets with round-robin salesperson assignment.',
    duration: '1 min',
    roles: ['manager', 'admin'],
    steps: [
      {
        element: '[data-tour="sidebar-leads"]',
        popover: {
          title: 'Bulk Lead Import',
          description: 'Managers and Admins can import CSV lists with automatic phone number de-duplication.',
          side: 'right',
        },
      },
    ],
  },

  'ai-suggestions': {
    id: 'ai-suggestions',
    title: 'AI Lead Recommendations',
    description: 'How the AI suggestions panel analyzes history to recommend smart next actions.',
    duration: '1 min',
    roles: ['salesperson', 'manager', 'admin'],
    steps: [
      {
        element: '[data-tour="sidebar-leads"]',
        popover: {
          title: 'AI Suggestions Panel',
          description: 'Open any lead detail page to view intelligent recommendations for handling objections.',
          side: 'right',
        },
      },
    ],
  },

  regions: {
    id: 'regions',
    title: 'Multi-Country Settings',
    description: 'Switch between India and Australia configurations, taxes, and calling policies.',
    duration: '1 min',
    roles: ['admin', 'manager'],
    steps: [
      {
        element: '[data-tour="header-region"]',
        popover: {
          title: 'Region Controls',
          description: 'Toggle between India (INR) and Australia (AUD) formats, utilities, and tax rules.',
          side: 'bottom',
          align: 'end',
        },
      },
    ],
  },

  notifications: {
    id: 'notifications',
    title: 'Notifications & Alerts',
    description: 'Manage unread notifications, sound alerts, and browser push permissions.',
    duration: '1 min',
    roles: ['admin', 'manager', 'salesperson', 'surveyor'],
    steps: [
      {
        element: '[data-tour="header-notifications"]',
        popover: {
          title: 'Notifications Bell',
          description: 'Click to view unread alerts and click Enable Notifications for desktop push.',
          side: 'bottom',
          align: 'end',
        },
      },
    ],
  },

  admin: {
    id: 'admin',
    title: 'Admin & System Controls',
    description: 'Manage users, policy settings, SMTP email, and Helpbot analytics.',
    duration: '2 mins',
    roles: ['admin'],
    steps: [
      {
        element: '[data-tour="sidebar-admin"]',
        popover: {
          title: 'Admin Console',
          description: 'Configure company-wide policies, email servers, and review Help Assistant insights.',
          side: 'right',
        },
      },
    ],
  },
};
