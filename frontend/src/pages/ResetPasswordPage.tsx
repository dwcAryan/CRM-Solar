import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
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
} from '@mantine/core';
import { IconSun, IconMail, IconLock, IconCheck, IconAlertCircle } from '@tabler/icons-react';
import { requestPasswordReset, confirmPasswordReset } from '../api/client';

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  const uid = searchParams.get('uid') || '';
  const token = searchParams.get('token') || '';
  const isResetMode = Boolean(uid && token);

  // Forgot password state
  const [email, setEmail] = useState('');
  const [requestSent, setRequestSent] = useState(false);
  const [requestLoading, setRequestLoading] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);

  // Set new password state
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetSuccess, setResetSuccess] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRequestError(null);
    setRequestLoading(true);

    try {
      await requestPasswordReset(email.trim());
      setRequestSent(true);
    } catch (err: any) {
      setRequestError(err.response?.data?.error || 'Failed to dispatch reset email. Please try again.');
    } finally {
      setRequestLoading(false);
    }
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetError(null);

    if (newPassword.length < 6) {
      setResetError('Password must be at least 6 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setResetError('Passwords do not match. Please re-enter.');
      return;
    }

    setResetLoading(true);
    try {
      await confirmPasswordReset({
        uid,
        token,
        new_password: newPassword,
      });
      setResetSuccess(true);
    } catch (err: any) {
      const msg =
        err.response?.data?.error ||
        'Invalid or expired password reset link. Links are single-use and expire after 1 hour.';
      setResetError(msg);
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <Container size={420} my={50}>
      <Paper withBorder shadow="md" p={30} radius="md">
        <Stack align="center" mb="lg">
          <ThemeIcon size={56} radius="xl" color="yellow" variant="filled">
            <IconSun size={34} />
          </ThemeIcon>
          <Title order={2} ta="center">
            {isResetMode ? 'Set New Password' : 'Reset Password'}
          </Title>
          <Text c="dimmed" size="xs" ta="center">
            {isResetMode
              ? 'Enter your new password below to secure your Solar CRM account'
              : 'Enter your registered email address to receive a 1-hour reset link'}
          </Text>
        </Stack>

        {/* MODE 1: REQUEST RESET LINK */}
        {!isResetMode && (
          <>
            {requestSent ? (
              <Stack gap="md">
                <Alert
                  icon={<IconCheck size={18} />}
                  title="Check Your Email"
                  color="green"
                  radius="md"
                >
                  If an account exists with <strong>{email}</strong>, a secure reset link valid for 1 hour has been sent.
                </Alert>
                <Button component={Link} to="/login" variant="default" fullWidth>
                  Return to Sign In
                </Button>
              </Stack>
            ) : (
              <form onSubmit={handleRequestSubmit}>
                <Stack gap="md">
                  {requestError && (
                    <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red">
                      {requestError}
                    </Alert>
                  )}

                  <TextInput
                    label="Email Address"
                    placeholder="name@example.com"
                    leftSection={<IconMail size={16} />}
                    value={email}
                    onChange={(e) => setEmail(e.currentTarget.value)}
                    required
                    type="email"
                  />

                  <Button type="submit" color="yellow" fullWidth loading={requestLoading}>
                    Send Reset Link
                  </Button>

                  <Group justify="center" mt="xs">
                    <Anchor component={Link} to="/login" size="xs" c="dimmed">
                      Back to Sign In
                    </Anchor>
                  </Group>
                </Stack>
              </form>
            )}
          </>
        )}

        {/* MODE 2: SET NEW PASSWORD WITH TOKEN */}
        {isResetMode && (
          <>
            {resetSuccess ? (
              <Stack gap="md">
                <Alert
                  icon={<IconCheck size={18} />}
                  title="Password Updated Successfully"
                  color="green"
                  radius="md"
                >
                  Your password has been reset. You may now sign in using your new credentials.
                </Alert>
                <Button component={Link} to="/login" color="yellow" fullWidth>
                  Proceed to Sign In
                </Button>
              </Stack>
            ) : (
              <form onSubmit={handleResetSubmit}>
                <Stack gap="md">
                  {resetError && (
                    <Alert icon={<IconAlertCircle size={16} />} title="Reset Failed" color="red">
                      {resetError}
                    </Alert>
                  )}

                  <PasswordInput
                    label="New Password"
                    placeholder="Enter at least 6 characters"
                    leftSection={<IconLock size={16} />}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.currentTarget.value)}
                    required
                  />

                  <PasswordInput
                    label="Confirm New Password"
                    placeholder="Repeat new password"
                    leftSection={<IconLock size={16} />}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.currentTarget.value)}
                    required
                  />

                  <Button type="submit" color="yellow" fullWidth loading={resetLoading}>
                    Update Password
                  </Button>

                  <Group justify="center" mt="xs">
                    <Anchor component={Link} to="/login" size="xs" c="dimmed">
                      Cancel & Return to Sign In
                    </Anchor>
                  </Group>
                </Stack>
              </form>
            )}
          </>
        )}
      </Paper>
    </Container>
  );
};
