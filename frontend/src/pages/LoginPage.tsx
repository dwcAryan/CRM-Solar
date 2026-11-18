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
  Divider,
  SimpleGrid,
  Anchor,
  Group,
} from '@mantine/core';
import { IconSun, IconAlertCircle } from '@tabler/icons-react';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('demo_sales1');
  const [password, setPassword] = useState('Sales1@Demo2026!');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login({ username, password });
      navigate(from, { replace: true });
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Invalid username or password. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDemoSelect = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
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
              placeholder="e.g. demo_sales1"
              value={username}
              onChange={(e) => setUsername(e.currentTarget.value)}
              required
            />
            <PasswordInput
              label="Password"
              placeholder="Your password"
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

        <Divider label="Or 1-Click Demo Accounts" labelPosition="center" my="lg" />

        <SimpleGrid cols={2} spacing="xs">
          <Button
            variant="light"
            color="green"
            size="xs"
            onClick={() => handleDemoSelect('demo_sales1', 'Sales1@Demo2026!')}
          >
            Salesperson 1
          </Button>
          <Button
            variant="light"
            color="green"
            size="xs"
            onClick={() => handleDemoSelect('demo_sales2', 'Sales2@Demo2026!')}
          >
            Salesperson 2
          </Button>
          <Button
            variant="light"
            color="blue"
            size="xs"
            onClick={() => handleDemoSelect('demo_manager', 'Manager@Demo2026!')}
          >
            Manager
          </Button>
          <Button
            variant="light"
            color="red"
            size="xs"
            onClick={() => handleDemoSelect('demo_admin', 'Admin@Demo2026!')}
          >
            Admin
          </Button>
        </SimpleGrid>
      </Paper>
    </Container>
  );
};
