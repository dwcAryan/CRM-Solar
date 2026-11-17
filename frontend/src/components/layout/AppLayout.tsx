import React from 'react';
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
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconSun,
  IconDashboard,
  IconCalendarEvent,
  IconUsers,
  IconClipboardCheck,
  IconFileText,
  IconSettings,
  IconBell,
  IconLogout,
  IconHeartbeat,
} from '@tabler/icons-react';
import { useAuth } from '../../context/AuthContext';
import {
  fetchNotifications,
  fetchUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
} from '../../api/client';
import type { Notification } from '../../api/types';

export const AppLayout: React.FC = () => {
  const [opened, { toggle, close }] = useDisclosure();
  const { user, logout, isAdminOrManager } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  // Notifications queries
  const { data: unreadCount = 0 } = useQuery<number>({
    queryKey: ['notifications-unread-count'],
    queryFn: fetchUnreadNotificationCount,
    refetchInterval: 20000,
  });

  const { data: notifications = [] } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: fetchNotifications,
    refetchInterval: 30000,
  });

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
    { label: 'Dashboard', icon: IconDashboard, path: '/' },
    { label: "Today's Follow-ups", icon: IconCalendarEvent, path: '/today' },
    { label: 'All Leads', icon: IconUsers, path: '/leads' },
    { label: 'Site Surveys', icon: IconClipboardCheck, path: '/surveys' },
    { label: 'Quotations', icon: IconFileText, path: '/quotes' },
    ...(isAdminOrManager ? [{ label: 'Admin Hub', icon: IconSettings, path: '/admin' }] : []),
    { label: 'System Health', icon: IconHeartbeat, path: '/health' },
  ];

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

          <Group gap="sm">
            {/* Notification Bell Menu */}
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

            {/* User Profile Menu */}
            <Menu position="bottom-end" shadow="md">
              <Menu.Target>
                <Group gap="xs" style={{ cursor: 'pointer' }}>
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
        <ScrollArea>
          <Stack gap={4}>
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
                />
              );
            })}
          </Stack>
        </ScrollArea>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
};
