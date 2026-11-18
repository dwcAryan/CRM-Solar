import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  Paper,
  Table,
  Badge,
  TextInput,
  Group,
  Loader,
  Center,
} from '@mantine/core';
import { IconSearch, IconShieldCheck } from '@tabler/icons-react';
import { fetchRolesMatrix } from '../api/client';

export const RolesMatrixPage: React.FC = () => {
  const [filter, setFilter] = useState('');

  const { data: matrixData, isLoading, error } = useQuery({
    queryKey: ['roles-matrix'],
    queryFn: fetchRolesMatrix,
  });

  const getScopeBadge = (scope: string) => {
    switch (scope) {
      case 'all':
        return <Badge color="green" variant="filled">All (Full)</Badge>;
      case 'region':
        return <Badge color="blue" variant="filled">Region-Scoped</Badge>;
      case 'own':
        return <Badge color="cyan" variant="light">Own Records</Badge>;
      case 'none':
        return <Badge color="gray" variant="outline">Denied</Badge>;
      case 'read_only':
        return <Badge color="teal" variant="light">Read Only</Badge>;
      case 'pending_only':
        return <Badge color="orange" variant="light">Pending Approval</Badge>;
      case 'remark_only':
        return <Badge color="violet" variant="light">Remark Only</Badge>;
      case 'assigned_survey':
        return <Badge color="indigo" variant="light">Assigned Survey</Badge>;
      default:
        return <Badge color="dark" variant="light">{scope}</Badge>;
    }
  };

  const entries = matrixData ? Object.entries(matrixData) : [];
  const filteredEntries = entries.filter(([key]) =>
    key.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <Container size="xl" py="md">
      <Group justify="space-between" mb="md">
        <div>
          <Group gap="xs">
            <IconShieldCheck size={28} color="var(--mantine-color-blue-6)" />
            <Title order={2}>Roles & Permissions Matrix</Title>
          </Group>
          <Text size="sm" c="dimmed">
            Centralized RBAC authorization rules across all four platform roles.
          </Text>
        </div>
        <TextInput
          placeholder="Filter permissions..."
          leftSection={<IconSearch size={16} />}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </Group>

      <Paper withBorder p="md" radius="md">
        {isLoading ? (
          <Center py="xl"><Loader /></Center>
        ) : error ? (
          <Text c="red" ta="center" py="xl">Failed to load permissions matrix.</Text>
        ) : (
          <Table.ScrollContainer minWidth={700}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Permission Key</Table.Th>
                  <Table.Th>Admin</Table.Th>
                  <Table.Th>Manager</Table.Th>
                  <Table.Th>Salesperson</Table.Th>
                  <Table.Th>Surveyor</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {filteredEntries.map(([permKey, roleMap]) => (
                  <Table.Tr key={permKey}>
                    <Table.Td fw={600} style={{ fontFamily: 'monospace' }}>
                      {permKey}
                    </Table.Td>
                    <Table.Td>{getScopeBadge((roleMap as any).admin)}</Table.Td>
                    <Table.Td>{getScopeBadge((roleMap as any).manager)}</Table.Td>
                    <Table.Td>{getScopeBadge((roleMap as any).salesperson)}</Table.Td>
                    <Table.Td>{getScopeBadge((roleMap as any).surveyor)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Paper>
    </Container>
  );
};
