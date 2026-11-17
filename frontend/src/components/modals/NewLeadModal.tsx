import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Modal,
  Button,
  Stack,
  TextInput,
  NumberInput,
  Select,
  Alert,
  Group,
  Text,
  Paper,
  Badge,
} from '@mantine/core';
import { IconAlertTriangle, IconPlus } from '@tabler/icons-react';
import { createLead, fetchLeadSources, fetchUsers } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import type { LeadSource, User } from '../../api/types';

interface NewLeadModalProps {
  opened: boolean;
  onClose: () => void;
  onLeadCreated?: (leadId: number) => void;
}

export const NewLeadModal: React.FC<NewLeadModalProps> = ({ opened, onClose, onLeadCreated }) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAdminOrManager } = useAuth();

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [altPhone, setAltPhone] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [pincode, setPincode] = useState('');
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [propertyType, setPropertyType] = useState<string | null>('residential');
  const [monthlyBill, setMonthlyBill] = useState<number | string>('');
  const [roofType, setRoofType] = useState<string | null>('RCC flat');
  const [ownerOrTenant, setOwnerOrTenant] = useState<string | null>('owner');
  const [assignedToId, setAssignedToId] = useState<string | null>(null);

  const [duplicateLead, setDuplicateLead] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: sources = [] } = useQuery<LeadSource[]>({
    queryKey: ['lead-sources'],
    queryFn: fetchLeadSources,
    enabled: opened,
  });

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: fetchUsers,
    enabled: opened && isAdminOrManager,
  });

  const resetForm = () => {
    setName('');
    setPhone('');
    setAltPhone('');
    setEmail('');
    setAddress('');
    setCity('');
    setPincode('');
    setSourceId(null);
    setPropertyType('residential');
    setMonthlyBill('');
    setRoofType('RCC flat');
    setOwnerOrTenant('owner');
    setAssignedToId(null);
    setDuplicateLead(null);
    setErrorMsg(null);
  };

  const createMutation = useMutation({
    mutationFn: (force: boolean = false) => {
      const payload: any = {
        name: name.trim(),
        phone: phone.trim(),
        alt_phone: altPhone.trim() || undefined,
        email: email.trim() || undefined,
        address: address.trim() || undefined,
        city: city.trim() || 'Ahmedabad',
        pincode: pincode.trim() || undefined,
        source: sourceId ? Number(sourceId) : undefined,
        property_type: propertyType || 'residential',
        monthly_bill: monthlyBill ? Number(monthlyBill) : undefined,
        roof_type: roofType || 'RCC flat',
        owner_or_tenant: ownerOrTenant || 'owner',
      };
      if (assignedToId) {
        payload.assigned_to = Number(assignedToId);
      }
      return createLead(payload, force);
    },
    onSuccess: (newLead) => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      resetForm();
      onClose();
      if (onLeadCreated) {
        onLeadCreated(newLead.id);
      } else {
        navigate(`/leads/${newLead.id}`);
      }
    },
    onError: (err: any) => {
      const resp = err.response?.data;
      if (resp?.duplicate && resp?.existing_lead) {
        setDuplicateLead(resp.existing_lead);
        setErrorMsg('Duplicate lead detected with this phone number.');
      } else if (typeof resp === 'object') {
        const messages = Object.entries(resp)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join('\n');
        setErrorMsg(messages || 'Validation failed.');
      } else {
        setErrorMsg(err.message || 'Failed to create lead.');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setDuplicateLead(null);
    createMutation.mutate(false);
  };

  return (
    <Modal
      opened={opened}
      onClose={() => {
        resetForm();
        onClose();
      }}
      title={
        <Group gap="xs">
          <IconPlus size={18} />
          <Text fw={600}>Add New Solar Lead</Text>
        </Group>
      }
      size="lg"
      radius="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {errorMsg && (
            <Alert icon={<IconAlertTriangle size={16} />} title="Notice" color="orange" variant="light">
              <Text size="xs" style={{ whiteSpace: 'pre-line' }}>
                {errorMsg}
              </Text>
            </Alert>
          )}

          {duplicateLead && (
            <Paper p="sm" withBorder style={{ borderColor: 'var(--mantine-color-orange-5)' }}>
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text size="sm" fw={600} c="orange">
                    Matching Existing Lead Found!
                  </Text>
                  <Badge color="orange">{duplicateLead.status}</Badge>
                </Group>
                <Text size="xs">
                  <strong>Name:</strong> {duplicateLead.name} | <strong>Phone:</strong> {duplicateLead.phone}
                </Text>
                {duplicateLead.assigned_to && (
                  <Text size="xs" c="dimmed">
                    Assigned to: {duplicateLead.assigned_to}
                  </Text>
                )}
                <Group gap="sm" mt="xs">
                  <Button
                    size="xs"
                    variant="light"
                    color="blue"
                    onClick={() => {
                      onClose();
                      navigate(`/leads/${duplicateLead.id}`);
                    }}
                  >
                    View Existing Lead #{duplicateLead.id}
                  </Button>
                  <Button
                    size="xs"
                    variant="filled"
                    color="orange"
                    loading={createMutation.isPending}
                    onClick={() => createMutation.mutate(true)}
                  >
                    Create Anyway (Force)
                  </Button>
                </Group>
              </Stack>
            </Paper>
          )}

          <Group grow>
            <TextInput
              label="Customer Name"
              placeholder="e.g. Ramesh Patel"
              value={name}
              onChange={(e) => setName(e.currentTarget.value)}
              required
            />
            <TextInput
              label="Phone Number"
              placeholder="e.g. 9825012345"
              value={phone}
              onChange={(e) => setPhone(e.currentTarget.value)}
              required
            />
          </Group>

          <Group grow>
            <TextInput
              label="Alt Phone (Optional)"
              placeholder="e.g. 9825098765"
              value={altPhone}
              onChange={(e) => setAltPhone(e.currentTarget.value)}
            />
            <TextInput
              label="Email (Optional)"
              placeholder="e.g. ramesh@example.com"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
            />
          </Group>

          <Group grow>
            <TextInput
              label="City"
              placeholder="e.g. Ahmedabad, Surat"
              value={city}
              onChange={(e) => setCity(e.currentTarget.value)}
              required
            />
            <TextInput
              label="Pincode"
              placeholder="e.g. 380015"
              value={pincode}
              onChange={(e) => setPincode(e.currentTarget.value)}
            />
          </Group>

          <TextInput
            label="Address / Society"
            placeholder="e.g. 12 Shantivan Bunglows, Bodakdev"
            value={address}
            onChange={(e) => setAddress(e.currentTarget.value)}
          />

          <Group grow>
            <Select
              label="Lead Source"
              placeholder="Select source"
              data={sources.map((s) => ({ value: String(s.id), label: s.name }))}
              value={sourceId}
              onChange={setSourceId}
              searchable
              clearable
            />
            <Select
              label="Property Type"
              data={[
                { value: 'residential', label: 'Residential' },
                { value: 'commercial', label: 'Commercial' },
                { value: 'industrial', label: 'Industrial' },
                { value: 'agricultural', label: 'Agricultural' },
                { value: 'other', label: 'Other' },
              ]}
              value={propertyType}
              onChange={setPropertyType}
            />
          </Group>

          <Group grow>
            <NumberInput
              label="Approx Monthly Bill (₹)"
              placeholder="e.g. 4500"
              value={monthlyBill}
              onChange={setMonthlyBill}
              min={0}
            />
            <Select
              label="Roof Type"
              data={[
                { value: 'RCC flat', label: 'RCC Flat' },
                { value: 'tin shade', label: 'Tin / Metal Shade' },
                { value: 'tiled', label: 'Tiled / Slanted' },
                { value: 'other', label: 'Other' },
              ]}
              value={roofType}
              onChange={setRoofType}
            />
            <Select
              label="Occupancy"
              data={[
                { value: 'owner', label: 'Owner' },
                { value: 'tenant', label: 'Tenant' },
                { value: 'other', label: 'Other' },
              ]}
              value={ownerOrTenant}
              onChange={setOwnerOrTenant}
            />
          </Group>

          {isAdminOrManager && (
            <Select
              label="Assign To Salesperson"
              placeholder="Select team member"
              data={users
                .filter((u) => u.role === 'salesperson' || u.role === 'manager')
                .map((u) => ({
                  value: String(u.id),
                  label: `${u.first_name || u.username} (${u.role})`,
                }))}
              value={assignedToId}
              onChange={setAssignedToId}
              searchable
              clearable
            />
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" color="yellow" loading={createMutation.isPending}>
              Create Lead
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
