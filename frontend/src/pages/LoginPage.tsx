import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Container,
  Paper,
  Title,
  Text,
  TextInput,
  PasswordInput,
  Button,
  Stack,
  Alert,
  ThemeIcon,
  Anchor,
  Group,
  Modal,
} from '@mantine/core';
import { IconSun, IconAlertCircle, IconLockCheck } from '@tabler/icons-react';
import { useAuth } from '../context/AuthContext';
import { changePassword } from '../api/client';

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Forced password change state
  const [showChangeModal, setShowChangeModal] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changeError, setChangeError] = useState<string | null>(null);
  const [changing, setChanging] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const user = await login({ username, password });
      if (user.must_change_password) {
        setShowChangeModal(true);
      } else {
        navigate(from, { replace: true });
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Invalid username or password. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleForcedPasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setChangeError(null);

    if (newPassword !== confirmPassword) {
      setChangeError('Passwords do not match.');
      return;
    }

    setChanging(true);
    try {
      await changePassword({ old_password: password, new_password: newPassword });
      setShowChangeModal(false);
      navigate(from, { replace: true });
    } catch (err: any) {
      const msg = err.response?.data?.error || 'Password does not meet complexity requirements (min 10 characters, upper, lower, digit, special character).';
      setChangeError(msg);
    } finally {
      setChanging(false);
    }
  };

  return (
    <Container size={420} my={40}>
      <Paper withBorder shadow="md" p={30} radius="md">
        <Stack align="center" mb="lg">
          <ThemeIcon size={56} radius="xl" color="yellow" variant="filled">
            <IconSun size={34} />
          </ThemeIcon>
          <Title order={2} ta="center">
            Solar CRM
          </Title>
          <Text c="dimmed" size="xs" ta="center">
            Sign in to access your leads, surveys, and quotations
          </Text>
        </Stack>

        {error && (
          <Alert icon={<IconAlertCircle size={16} />} title="Authentication Failed" color="red" mb="md">
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              label="Username"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.currentTarget.value)}
              required
            />
            <PasswordInput
              label="Password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
            />
            <Group justify="flex-end" mt={-4}>
              <Anchor component={Link} to="/reset-password" size="xs" c="dimmed">
                Forgot password?
              </Anchor>
            </Group>
            <Button type="submit" color="yellow" fullWidth loading={loading} mt="sm">
              Sign In
            </Button>
          </Stack>
        </form>
      </Paper>

      {/* Mandatory Password Change Modal for new accounts */}
      <Modal
        opened={showChangeModal}
        onClose={() => {}}
        closeOnClickOutside={false}
        closeOnEscape={false}
        withCloseButton={false}
        title={
          <Group gap="xs">
            <ThemeIcon color="blue" size="sm" variant="light">
              <IconLockCheck size={16} />
            </ThemeIcon>
            <Text fw={600} size="sm">
              Password Change Required
            </Text>
          </Group>
        }
      >
        <Text size="xs" c="dimmed" mb="md">
          Your account was provisioned with a temporary password. Please set a new, secure password to continue.
        </Text>

        {changeError && (
          <Alert icon={<IconAlertCircle size={14} />} color="red" mb="sm">
            {changeError}
          </Alert>
        )}

        <form onSubmit={handleForcedPasswordChange}>
          <Stack gap="sm">
            <PasswordInput
              label="New Password"
              placeholder="Min 10 chars, uppercase, lowercase, number, symbol"
              value={newPassword}
              onChange={(e) => setNewPassword(e.currentTarget.value)}
              required
              size="xs"
            />
            <PasswordInput
              label="Confirm New Password"
              placeholder="Re-enter new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.currentTarget.value)}
              required
              size="xs"
            />
            <Button type="submit" color="blue" fullWidth loading={changing} mt="xs" size="xs">
              Save Password & Enter CRM
            </Button>
          </Stack>
        </form>
      </Modal>
    </Container>
  );
};
