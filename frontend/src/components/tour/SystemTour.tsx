import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Modal,
  Button,
  Group,
  Stack,
  Text,
  Title,
  Badge,
  Progress,
  Paper,
  ThemeIcon,
  Checkbox,
  Box,
  rem,
  Divider,
} from '@mantine/core';
import {
  IconSun,
  IconCalendarEvent,
  IconUsers,
  IconFileSpreadsheet,
  IconClipboardCheck,
  IconBolt,
  IconSearch,
  IconArrowRight,
  IconArrowLeft,
  IconCheck,
  IconBulb,
  IconSparkles,
} from '@tabler/icons-react';

export interface TourStep {
  id: string;
  category: string;
  badgeColor: string;
  title: string;
  headline: string;
  icon: React.ComponentType<{ size: number }>;
  bullets: string[];
  proTip: string;
  route?: string;
  routeLabel?: string;
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: 'welcome',
    category: 'EXECUTIVE OVERVIEW',
    badgeColor: 'yellow',
    title: 'Welcome to Solar CRM',
    headline: 'High-velocity lead management designed specifically for Indian rooftop solar installers.',
    icon: IconSun,
    bullets: [
      'Strict Lifecycle Scope: Tracks enquiries from acquisition to "Won" (customer commits to quotation).',
      'The Golden Business Rule: Every call, visit, or interaction MUST end with an outcome setting Status, Next Action, and Next Follow-up Date.',
      'Active Pipeline Enforcement: Leads cannot exist without a scheduled follow-up date (unless closed in a terminal status).',
    ],
    proTip: 'Follow the triad on every call: Status + Next Action + Next Follow-up Date.',
    route: '/',
    routeLabel: 'View Dashboard',
  },
  {
    id: 'today',
    category: 'DAILY EXECUTION',
    badgeColor: 'orange',
    title: "Today's Follow-up Queue",
    headline: 'Your prioritized daily action center for scheduled and overdue customer calls.',
    icon: IconCalendarEvent,
    bullets: [
      'Urgency Triage: Overdue follow-ups are surfaced with prominent red indicators so zero leads slip away.',
      'One-Click Telephony: Direct "Call" (tel:) launches your phone dialer instantly.',
      'Pre-Filled WhatsApp: Direct "WhatsApp" (wa.me) opens WhatsApp with a personalized bilingual greeting.',
      'Quick Remark & Outcome: Log interaction results or notes directly from each card without leaving the page.',
    ],
    proTip: 'Clear red Overdue cards first each morning before taking on new inbound calls.',
    route: '/today',
    routeLabel: "Go to Today's Follow-ups",
  },
  {
    id: 'leads',
    category: 'PIPELINE MANAGEMENT',
    badgeColor: 'blue',
    title: 'All Leads & Smart Filters',
    headline: 'Comprehensive 360° lead list with instant status badges, bulk management, and saved views.',
    icon: IconUsers,
    bullets: [
      'Saved Filter Tabs: Switch effortlessly between "Due today", "Overdue", "My leads", "Interested", and "Quote sent".',
      'Safety Audit Tab: The "No follow-up date" tab alerts you to active leads needing immediate attention.',
      'Floating Bulk Actions: Select multiple leads to reassign sales reps, update lead source, or export to CSV.',
      'Formula Injection Safe: All CSV exports escape dangerous spreadsheet formula characters (=, +, -, @).',
    ],
    proTip: 'Use checkboxes to bulk-reassign unassigned leads across your sales reps in seconds.',
    route: '/leads',
    routeLabel: 'Open All Leads',
  },
  {
    id: 'import',
    category: 'LEAD INGESTION',
    badgeColor: 'teal',
    title: 'CSV & Excel Lead Import',
    headline: 'Bulk ingest marketing lists with intelligent auto-mapping and 1-click batch undo.',
    icon: IconFileSpreadsheet,
    bullets: [
      'Format & Size Support: Drag-and-drop .csv (with UTF-8 BOM support) or .xlsx files up to 5 MB (5,000 rows).',
      'Synonym Header Matching: Auto-matches name, phone, email, city, address, monthly bill, and roof type.',
      'Phone Normalization: Automatically cleans Indian phone numbers (strips +91, spaces, dashes to 10 digits).',
      'Conflict Handling & Assignment: Choose to skip duplicates or enrich empty fields, and distribute leads via Round-Robin.',
      'Batch Rollback: Made a mistake? Undo the entire import batch with one click to cleanly delete all its leads.',
    ],
    proTip: 'Download our official sample CSV template from the import screen to format your campaigns.',
    route: '/import-leads',
    routeLabel: 'Open Lead Import Wizard',
  },
  {
    id: 'surveys',
    category: 'TECHNICAL ASSESSMENT',
    badgeColor: 'cyan',
    title: 'Site Technical Surveys',
    headline: 'Coordinate rooftop feasibility inspections and verify electrical/structural suitability.',
    icon: IconClipboardCheck,
    bullets: [
      'Appointment Scheduling: Book surveyor slots, specify pre-visit instructions, and track reschedules.',
      'Daily 6:00 PM Reminders: Automated background scheduler notifies surveyors and sends WhatsApp reminders to customers.',
      'Suitability Verdict: Mark Done verifies roof space, unshaded area, and 3-phase meter availability.',
      'Automatic Progression: Suitable roofs automatically advance to "Design pending"; unsuitable roofs move to "Alternative" or "Lost".',
    ],
    proTip: 'Surveyors can access their dedicated "My surveys" view directly from mobile phones.',
    route: '/surveys',
    routeLabel: 'Explore Site Surveys',
  },
  {
    id: 'quotes',
    category: 'COMMERCIAL PROPOSALS',
    badgeColor: 'grape',
    title: 'Versioned Quotations & Won Deals',
    headline: 'Build transparent solar quotes and negotiate until customer acceptance.',
    icon: IconBolt,
    bullets: [
      'Immutable Revision History: Earlier quotes are never overwritten; modifications create v2, v3 preserving audit history.',
      'Dynamic Subsidy Calculation: Enter kW system size, panel brand, gross cost, and central/state subsidy to calculate Net Payable.',
      'One-Click Status Advancement: Move from Draft to "Quote sent" with ready-to-share details.',
      'The "Won" Milestone: Accepting a quote marks the lead as Won, timestamps the win, and successfully closes the sales cycle.',
    ],
    proTip: 'When revising a quote, the customer net payable is recalculated live on screen.',
    route: '/quotes',
    routeLabel: 'View Quotations',
  },
  {
    id: 'shortcuts',
    category: 'PRO-TIPS & AI HELP',
    badgeColor: 'violet',
    title: 'Global Search, Dark Mode & Help Assistant',
    headline: 'High-speed keyboard navigation and instant answers to software questions.',
    icon: IconSearch,
    bullets: [
      'Global Search Hotkey: Press "/" anytime from anywhere in the app to instantly search leads by name, phone, or city.',
      'Dark Mode: Switch comfortably between light and dark themes using the header sun/moon toggle.',
      'Loss Authority Control: Junior sales reps cannot mark leads Lost without Manager or Admin authorization.',
      'In-App Help Assistant: Click the chatbot icon at the bottom-right to ask any question about rules, retry ladders, or procedures.',
    ],
    proTip: 'Press "/" on your keyboard right now to quickly search your lead database.',
    route: '/',
    routeLabel: 'Go to Dashboard',
  },
];

interface SystemTourProps {
  opened: boolean;
  onClose: () => void;
}

export const SystemTour: React.FC<SystemTourProps> = ({ opened, onClose }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const totalSteps = TOUR_STEPS.length;
  const current = TOUR_STEPS[activeStep];
  const progressPercent = ((activeStep + 1) / totalSteps) * 100;

  const handleFinish = () => {
    if (dontShowAgain) {
      localStorage.setItem('solar_crm_has_seen_tour', 'true');
    }
    onClose();
  };

  const handleNext = () => {
    if (activeStep < totalSteps - 1) {
      setActiveStep((prev) => prev + 1);
    } else {
      handleFinish();
    }
  };

  const handlePrev = () => {
    if (activeStep > 0) {
      setActiveStep((prev) => prev - 1);
    }
  };

  // Keyboard navigation
  useEffect(() => {
    if (!opened) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNext();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlePrev();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [opened, activeStep, totalSteps, dontShowAgain]);

  const handleNavigateStepRoute = (route?: string) => {
    if (route && location.pathname !== route) {
      navigate(route);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={handleFinish}
      size="lg"
      radius="lg"
      padding="xl"
      withCloseButton
      centered
      overlayProps={{
        backgroundOpacity: 0.65,
        blur: 4,
      }}
      title={
        <Group justify="space-between" style={{ width: '100%' }}>
          <Group gap="xs">
            <ThemeIcon size="md" radius="md" color="yellow" variant="light">
              <IconSparkles size={16} />
            </ThemeIcon>
            <Text fw={700} size="sm" tt="uppercase" style={{ letterSpacing: '0.5px' }}>
              Solar CRM Guided Tour
            </Text>
          </Group>
          <Badge variant="light" color={current.badgeColor} size="sm">
            Step {activeStep + 1} of {totalSteps}
          </Badge>
        </Group>
      }
    >
      <Stack gap="md">
        {/* Progress bar */}
        <Progress value={progressPercent} color="yellow" size="xs" radius="xl" striped animated />

        {/* Hero Card */}
        <Paper
          p="lg"
          radius="md"
          withBorder
          style={{
            background: 'var(--mantine-color-default-hover)',
          }}
        >
          <Group align="flex-start" gap="md" wrap="nowrap">
            <ThemeIcon size={56} radius="xl" color={current.badgeColor} variant="light" style={{ flexShrink: 0 }}>
              <current.icon size={30} />
            </ThemeIcon>
            <div style={{ flex: 1 }}>
              <Badge size="xs" color={current.badgeColor} variant="dot" mb={4}>
                {current.category}
              </Badge>
              <Title order={3} style={{ lineHeight: 1.2 }}>
                {current.title}
              </Title>
              <Text size="sm" c="dimmed" mt={4}>
                {current.headline}
              </Text>
            </div>
          </Group>
        </Paper>

        {/* Key Features Bullet List */}
        <Stack gap="xs" my="xs">
          {current.bullets.map((point, idx) => (
            <Group key={idx} align="flex-start" gap="xs" wrap="nowrap">
              <ThemeIcon size={20} radius="xl" color="green" variant="light" mt={2} style={{ flexShrink: 0 }}>
                <IconCheck size={12} stroke={3} />
              </ThemeIcon>
              <Text size="xs" style={{ lineHeight: 1.45 }}>
                {point}
              </Text>
            </Group>
          ))}
        </Stack>

        {/* Pro-Tip Box */}
        <Paper p="xs" radius="md" withBorder bg="var(--mantine-color-yellow-0)">
          <Group gap="xs" wrap="nowrap">
            <ThemeIcon size="sm" radius="xl" color="yellow" variant="filled">
              <IconBulb size={12} />
            </ThemeIcon>
            <Text size="xs" fw={500} c="yellow.9">
              <strong>Pro-Tip:</strong> {current.proTip}
            </Text>
          </Group>
        </Paper>

        {/* Optional Page Preview Action */}
        {current.route && (
          <Group justify="flex-start">
            <Button
              size="xs"
              variant="subtle"
              color={current.badgeColor}
              leftSection={<IconArrowRight size={12} />}
              onClick={() => handleNavigateStepRoute(current.route)}
            >
              Jump to {current.routeLabel || current.title}
            </Button>
          </Group>
        )}

        <Divider my="xs" />

        {/* Footer controls */}
        <Group justify="space-between" align="center">
          <Checkbox
            size="xs"
            label="Don't show tour automatically"
            checked={dontShowAgain}
            onChange={(e) => setDontShowAgain(e.currentTarget.checked)}
          />

          <Group gap="xs">
            {/* Step navigation dots */}
            <Group gap={4} visibleFrom="xs" mr="xs">
              {TOUR_STEPS.map((_, i) => (
                <Box
                  key={i}
                  onClick={() => setActiveStep(i)}
                  style={{
                    width: i === activeStep ? rem(20) : rem(8),
                    height: rem(8),
                    borderRadius: rem(4),
                    backgroundColor: i === activeStep ? 'var(--mantine-color-yellow-6)' : 'var(--mantine-color-gray-4)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                />
              ))}
            </Group>

            {activeStep > 0 && (
              <Button
                variant="default"
                size="xs"
                leftSection={<IconArrowLeft size={14} />}
                onClick={handlePrev}
              >
                Back
              </Button>
            )}

            <Button
              color="yellow"
              size="xs"
              rightSection={activeStep < totalSteps - 1 ? <IconArrowRight size={14} /> : <IconCheck size={14} />}
              onClick={handleNext}
            >
              {activeStep < totalSteps - 1 ? 'Next' : 'Got it, let’s begin!'}
            </Button>
          </Group>
        </Group>
      </Stack>
    </Modal>
  );
};
