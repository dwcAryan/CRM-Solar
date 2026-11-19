import React, { useState, useEffect, useRef } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AppShell,
  Burger,
  Group,
  NavLink,
  Title,
  Text,
  Badge,
  ActionIcon,
  Menu,
  Avatar,
  Indicator,
  ScrollArea,
  Divider,
  Button,
  Stack,
  Box,
  rem,
  ThemeIcon,
  TextInput,
  Kbd,
  Select,
  useMantineColorScheme,
  Alert,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconSun,
  IconMoon,
  IconDashboard,
  IconCalendarEvent,
  IconUsers,
  IconClipboardCheck,
  IconFileText,
  IconFileSpreadsheet,
  IconSettings,
  IconBell,
  IconLogout,
  IconHeartbeat,
  IconSearch,
  IconWorld,
  IconAlertCircle,
  IconShieldCheck,
  IconCompass,
} from '@tabler/icons-react';
import { useAuth } from '../../context/AuthContext';
import { useRegion } from '../../context/RegionContext';
import {
  fetchNotifications,
  fetchUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
  fetchTourState,
} from '../../api/client';
import { InstallAppButton } from '../pwa/InstallAppButton';
import { NotificationPermissionModal } from '../notifications/NotificationPermissionModal';
import { NotificationSettingsModal } from '../notifications/NotificationSettingsModal';
import { TourCenterDrawer } from '../tour/TourCenterDrawer';
import { HelpbotFab } from '../helpbot/HelpbotFab';
import { startTour, isTourActive } from '../tour/ProductTourService';
import { LanguageSelector } from '../common/LanguageSelector';
import { changeAppLanguage } from '../../i18n/i18n';
import { useTranslation } from 'react-i18next';
import type { Notification } from '../../api/types';

export const AppLayout: React.FC = () => {
  const { t, i18n } = useTranslation('common');
  const [opened, { toggle, close }] = useDisclosure();
  const { user, logout, isAdminOrManager, can } = useAuth();
  const { selectedRegion, setSelectedRegion, activeRegion } = useRegion();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();

  // Global search state
  const [searchTerm, setSearchTerm] = useState('');
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [settingsOpened, setSettingsOpened] = useState(false);
  const [tourCenterOpened, setTourCenterOpened] = useState(false);
  const [showLangSuggestion, setShowLangSuggestion] = useState(false);
  const shownNotifIds = useRef<Set<number>>(new Set());
  const tourTriggeredRef = useRef(false);

  useEffect(() => {
    const prompted = localStorage.getItem('solar_crm_lang_prompted');
    if (!prompted && navigator.language && navigator.language.startsWith('hi')) {
      const current = i18n.language || 'en';
      if (!current.startsWith('hi')) {
        setShowLangSuggestion(true);
      }
    }
  }, [i18n.language]);

  // Automatic product tour: only runs on very first visit to the application
  useEffect(() => {
    // If user already saw or dismissed the tour, do not launch automatically
    const localSeen = localStorage.getItem('solar_crm_has_seen_tour');
    if (localSeen === 'true' || tourTriggeredRef.current || isTourActive()) {
      return;
    }

    tourTriggeredRef.current = true;

    fetchTourState()
      .then((state) => {
        if (!state.has_seen_tour) {
          if (localStorage.getItem('solar_crm_has_seen_tour') !== 'true' && !isTourActive()) {
            setTimeout(() => {
              if (!isTourActive() && localStorage.getItem('solar_crm_has_seen_tour') !== 'true') {
                startTour('complete');
              }
            }, 800);
          }
        } else {
          // Sync server state to localStorage so future reloads skip check immediately
          localStorage.setItem('solar_crm_has_seen_tour', 'true');
        }
      })
      .catch(() => {});
  }, []);

  // Keyboard shortcut: '/' focuses global search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInput = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || (activeEl as HTMLElement).isContentEditable);
      if (e.key === '/' && !isInput) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/leads?search=${encodeURIComponent(searchTerm.trim())}`);
    }
  };

  // Notifications queries (refreshed every 60s and on window focus)
  const { data: unreadCount = 0 } = useQuery<number>({
    queryKey: ['notifications-unread-count'],
    queryFn: fetchUnreadNotificationCount,
    refetchInterval: 60000,
    refetchOnWindowFocus: true,
  });

  const { data: notifications = [] } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: fetchNotifications,
    refetchInterval: 60000,
    refetchOnWindowFocus: true,
  });

  // Trigger browser notification for unread notifications while app is open (no duplicates)
  useEffect(() => {
    if (notifications.length > 0 && typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
      notifications.forEach((notif) => {
        if (!notif.is_read && !shownNotifIds.current.has(notif.id)) {
          shownNotifIds.current.add(notif.id);
          try {
            if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
              navigator.serviceWorker.ready.then((reg) => {
                reg.showNotification('Solar CRM', {
                  body: notif.message,
                  icon: '/icon-192x192.png',
                  tag: `solar-notif-${notif.id}`,
                  data: { url: notif.link || '/' },
                });
              });
            } else {
              const n = new window.Notification('Solar CRM', {
                body: notif.message,
                icon: '/icon-192x192.png',
                tag: `solar-notif-${notif.id}`,
              });
              n.onclick = () => {
                window.focus();
                if (notif.link) navigate(notif.link);
              };
            }
          } catch (e) {
            console.warn('Failed to display browser notification:', e);
          }
        }
      });
    }
  }, [notifications, navigate]);

  const markReadMutation = useMutation({
    mutationFn: (id: number) => markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
    },
  });

  const handleNav = (path: string) => {
    navigate(path);
    close();
  };

  const navItems = [
    { label: t('nav.dashboard', 'Dashboard'), icon: IconDashboard, path: '/' },
    ...(can('lead.view') ? [{ label: t('nav.today_followups', "Today's Follow-ups"), icon: IconCalendarEvent, path: '/today' }] : []),
    ...(can('lead.view') ? [{ label: t('nav.leads', 'All Leads'), icon: IconUsers, path: '/leads', dataTour: 'sidebar-leads' }] : []),
    ...(can('lead.unassigned_queue') || can('lead.lost_approval')
      ? [{ label: 'Manager Attention', icon: IconAlertCircle, path: '/manager-attention' }]
      : []),
    ...(user?.role === 'surveyor'
      ? [{ label: 'My Site Surveys', icon: IconClipboardCheck, path: '/my-surveys', dataTour: 'sidebar-surveys' }]
      : can('survey.view')
      ? [{ label: t('nav.surveys', 'Site Surveys'), icon: IconClipboardCheck, path: '/surveys', dataTour: 'sidebar-surveys' }]
      : []),
    ...(can('quote.view') ? [{ label: t('nav.quotes', 'Quotations'), icon: IconFileText, path: '/quotes', dataTour: 'sidebar-quotes' }] : []),
    ...(can('lead.import') ? [{ label: 'Import Leads', icon: IconFileSpreadsheet, path: '/import-leads' }] : []),
    ...(can('user.view_team') ? [{ label: 'Roles Matrix', icon: IconShieldCheck, path: '/roles-matrix' }] : []),
    ...(can('masters.manage') || user?.role === 'admin'
      ? [{ label: t('nav.admin', 'Admin Hub'), icon: IconSettings, path: '/admin', dataTour: 'sidebar-admin' }]
      : []),
    ...(user?.role === 'admin' || user?.role === 'manager'
      ? [{ label: 'System Health', icon: IconHeartbeat, path: '/health' }]
      : []),
  ];

  const isDark = colorScheme === 'dark';

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: 250,
        breakpoint: 'sm',
        collapsed: { mobile: !opened },
      }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Group gap="xs" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
              <ThemeIcon size="lg" radius="md" color="yellow" variant="filled">
                <IconSun size={22} />
              </ThemeIcon>
              <div>
                <Title order={4} style={{ lineHeight: 1.1 }}>
                  Solar CRM
                </Title>
                <Text size="10px" c="dimmed">
                  Residential & Commercial
                </Text>
              </div>
            </Group>
          </Group>

          {/* Global Search Box (name, phone, city) */}
          <Box style={{ flex: 1, maxWidth: 450 }} mx="md" visibleFrom="xs" data-tour="header-search">
            <form onSubmit={handleSearchSubmit}>
              <TextInput
                ref={searchInputRef}
                placeholder="Search leads by name, phone, city... (Press '/' to focus)"
                leftSection={<IconSearch size={16} />}
                rightSection={<Kbd size="xs">/</Kbd>}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.currentTarget.value)}
                size="sm"
                radius="md"
              />
            </form>
          </Box>

          <Group gap="xs">
            {/* Multi-Country Region Filter / Badge */}
            <Box data-tour="header-region">
              {isAdminOrManager ? (
                <Select
                  size="xs"
                  radius="md"
                  w={145}
                  leftSection={<IconWorld size={14} />}
                  value={selectedRegion}
                  onChange={(val) => {
                    setSelectedRegion(val || '');
                    queryClient.invalidateQueries();
                  }}
                  data={[
                    { value: '', label: '🌐 All Regions' },
                    { value: 'IN', label: '🇮🇳 India (IN)' },
                    { value: 'AU', label: '🇦🇺 Australia (AU)' },
                  ]}
                />
              ) : (
                <Badge
                  size="md"
                  variant="light"
                  color={activeRegion === 'AU' ? 'blue' : 'green'}
                  leftSection={<IconWorld size={12} />}
                >
                  {activeRegion === 'AU' ? '🇦🇺 Australia' : '🇮🇳 India'}
                </Badge>
              )}
            </Box>

            {/* Product Tour Center Button */}
            <ActionIcon
              variant="light"
              size="lg"
              radius="md"
              color="blue"
              onClick={() => setTourCenterOpened(true)}
              title="Product Tour Center & Guided Walkthroughs"
              data-tour="header-help"
            >
              <IconCompass size={20} />
            </ActionIcon>

            {/* Dark Mode Toggle */}
            <ActionIcon
              variant="light"
              size="lg"
              radius="md"
              color={isDark ? 'yellow' : 'gray'}
              onClick={() => toggleColorScheme()}
              title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? <IconSun size={20} /> : <IconMoon size={20} />}
            </ActionIcon>

            {/* Language Selector */}
            <LanguageSelector size="xs" variant="light" />

            {/* Notification Bell Menu */}
            <Box data-tour="header-notifications">
              <Menu position="bottom-end" shadow="md" width={320}>
                <Menu.Target>
                  <Indicator
                    disabled={unreadCount === 0}
                    color="red"
                    size={14}
                    label={unreadCount > 9 ? '9+' : unreadCount}
                    offset={4}
                  >
                    <ActionIcon variant="light" size="lg" radius="md">
                      <IconBell size={20} />
                    </ActionIcon>
                  </Indicator>
                </Menu.Target>

              <Menu.Dropdown>
                <Group justify="space-between" p="xs">
                  <Text size="sm" fw={600}>
                    Notifications
                  </Text>
                  {unreadCount > 0 && (
                    <Button
                      variant="subtle"
                      size="xs"
                      onClick={() => markAllReadMutation.mutate()}
                      loading={markAllReadMutation.isPending}
                    >
                      Mark all read
                    </Button>
                  )}
                </Group>
                <Divider />

                <ScrollArea.Autosize mah={320}>
                  {notifications.length === 0 ? (
                    <Text size="xs" c="dimmed" p="md" ta="center">
                      No notifications yet
                    </Text>
                  ) : (
                    notifications.map((notif) => (
                      <Menu.Item
                        key={notif.id}
                        p="xs"
                        style={{
                          backgroundColor: notif.is_read ? 'transparent' : 'var(--mantine-color-yellow-0)',
                          borderBottom: '1px solid var(--mantine-color-gray-1)',
                        }}
                        onClick={() => {
                          if (!notif.is_read) markReadMutation.mutate(notif.id);
                          if (notif.link) navigate(notif.link);
                        }}
                      >
                        <Stack gap={2}>
                          <Group justify="space-between" wrap="nowrap">
                            <Text size="xs" fw={notif.is_read ? 400 : 600} lineClamp={2}>
                              {notif.message}
                            </Text>
                            {!notif.is_read && (
                              <Badge size="xs" color="yellow" variant="dot">
                                New
                              </Badge>
                            )}
                          </Group>
                          <Text size="10px" c="dimmed">
                            {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </Text>
                        </Stack>
                      </Menu.Item>
                    ))
                  )}
                </ScrollArea.Autosize>
              </Menu.Dropdown>
            </Menu>
          </Box>

            {/* User Profile Menu */}
            <Menu position="bottom-end" shadow="md">
              <Menu.Target>
                <Group gap="xs" style={{ cursor: 'pointer' }} data-tour="header-user-menu">
                  <Avatar color="yellow" radius="xl">
                    {user?.first_name ? user.first_name[0] : (user?.username ? user.username[0].toUpperCase() : 'U')}
                  </Avatar>
                  <Box visibleFrom="sm">
                    <Text size="xs" fw={600} lineClamp={1}>
                      {user?.first_name ? `${user.first_name} ${user.last_name}` : user?.username}
                    </Text>
                    <Badge size="xs" variant="light" color={user?.role === 'admin' ? 'red' : (user?.role === 'manager' ? 'blue' : 'green')}>
                      {user?.role}
                    </Badge>
                  </Box>
                </Group>
              </Menu.Target>

              <Menu.Dropdown>
                <Menu.Label>Signed in as {user?.username}</Menu.Label>
                <Menu.Item leftSection={<IconCompass size={14} />} onClick={() => setTourCenterOpened(true)}>
                  Product Tour Center
                </Menu.Item>
                <Menu.Item leftSection={<IconBell size={14} />} onClick={() => setSettingsOpened(true)}>
                  Notification Settings
                </Menu.Item>
                <Menu.Item leftSection={<IconHeartbeat size={14} />} onClick={() => navigate('/health')}>
                  System Health
                </Menu.Item>
                <Divider />
                <Menu.Item color="red" leftSection={<IconLogout size={14} />} onClick={logout}>
                  Logout
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <Stack justify="space-between" h="100%">
          <ScrollArea style={{ flex: 1 }}>
            <Stack gap={4} data-tour="sidebar-nav">
              {navItems.map((item) => {
                const active = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.path}
                    label={item.label}
                    leftSection={<item.icon size={18} stroke={1.5} />}
                    active={active}
                    onClick={() => handleNav(item.path)}
                    variant="light"
                    color="yellow"
                    style={{ borderRadius: rem(8) }}
                    data-tour={(item as any).dataTour}
                  />
                );
              })}
            </Stack>
          </ScrollArea>

          {/* Desktop PWA Install Button at the bottom of the sidebar */}
          <Box p="xs" style={{ borderTop: '1px solid var(--mantine-color-default-border)' }}>
            <InstallAppButton isMobile={false} />
          </Box>
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>
        {showLangSuggestion && (
          <Box mb="md">
            <Alert
              color="blue"
              withCloseButton
              onClose={() => {
                localStorage.setItem('solar_crm_lang_prompted', 'true');
                setShowLangSuggestion(false);
              }}
              title={t('language.selector_label', 'Language Suggestion')}
            >
              <Group justify="space-between" wrap="wrap">
                <Text size="sm">
                  {t('language.switch_prompt', { language: 'हिन्दी (Hindi)', defaultValue: 'Switch interface language to हिन्दी (Hindi)?' })}
                </Text>
                <Group gap="xs">
                  <Button
                    size="xs"
                    color="blue"
                    onClick={async () => {
                      await changeAppLanguage('hi');
                      localStorage.setItem('solar_crm_lang_prompted', 'true');
                      setShowLangSuggestion(false);
                    }}
                  >
                    {t('language.switch_confirm', 'Switch to हिन्दी')}
                  </Button>
                  <Button
                    size="xs"
                    variant="subtle"
                    color="gray"
                    onClick={() => {
                      localStorage.setItem('solar_crm_lang_prompted', 'true');
                      setShowLangSuggestion(false);
                    }}
                  >
                    {t('language.switch_dismiss', 'Keep English')}
                  </Button>
                </Group>
              </Group>
            </Alert>
          </Box>
        )}
        <Outlet />
      </AppShell.Main>

      {/* PWA & Push Notification Modals */}
      <NotificationPermissionModal />
      <NotificationSettingsModal opened={settingsOpened} onClose={() => setSettingsOpened(false)} />

      {/* Phase 13 Product Tour & Helpbot Components */}
      <TourCenterDrawer
        opened={tourCenterOpened}
        onClose={() => setTourCenterOpened(false)}
        userRole={user?.role}
      />
      <HelpbotFab userRole={user?.role} />
    </AppShell>
  );
};
