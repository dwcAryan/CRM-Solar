import React, { useState } from 'react';
import {
  Modal,
  Stack,
  Text,
  TextInput,
  Textarea,
  Button,
  Group,
  Alert,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconShieldCheck } from '@tabler/icons-react';
import { anonymizeLead, correctLeadData } from '../../api/client';
import type { Lead } from '../../api/types';

interface AnonymizeLeadModalProps {
  opened: boolean;
  onClose: () => void;
  lead: Lead;
  onSuccess: () => void;
}

export const AnonymizeLeadModal: React.FC<AnonymizeLeadModalProps> = ({
  opened,
  onClose,
  lead,
  onSuccess,
}) => {
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAnonymize = async () => {
    if (!reason.trim() || reason.trim().length < 3) {
      notifications.show({
        title: 'Validation Error',
        message: 'A justification reason of at least 3 characters is mandatory.',
        color: 'red',
      });
      return;
    }

    setLoading(true);
    try {
      await anonymizeLead(lead.id, reason.trim());
      notifications.show({
        title: 'Lead Anonymized',
        message: `Personal identifiers for Lead #${lead.id} have been permanently erased and audited.`,
        color: 'green',
        icon: <IconShieldCheck size={16} />,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      notifications.show({
        title: 'Anonymization Failed',
        message: err.response?.data?.error || err.message || 'Operation failed',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Text fw={700} c="red.8">Right to be Forgotten — Anonymize Lead #{lead.id}</Text>}
      centered
    >
      <Stack gap="md">
        <Alert icon={<IconAlertTriangle size={18} />} color="red" variant="light" title="Irreversible Action">
          Permanently redacts customer name, phone number, alternate phone, email, and street address.
          Aggregate transactional, survey, and quote statistics remain preserved for business reporting.
        </Alert>

        <Text size="sm">
          <strong>Customer:</strong> {lead.name} ({lead.region || 'IN'})
        </Text>

        <Textarea
          label="Justification Reason (Mandatory for Audit Trail)"
          placeholder="e.g. Customer requested complete erasure under DPDP Act / Privacy Act APP 2."
          required
          minRows={3}
          value={reason}
          onChange={(e) => setReason(e.currentTarget.value)}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button color="red" onClick={handleAnonymize} loading={loading} disabled={reason.trim().length < 3}>
            Confirm Irreversible Anonymization
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

interface PrivacyCorrectModalProps {
  opened: boolean;
  onClose: () => void;
  lead: Lead;
  onSuccess: () => void;
}

export const PrivacyCorrectModal: React.FC<PrivacyCorrectModalProps> = ({
  opened,
  onClose,
  lead,
  onSuccess,
}) => {
  const [name, setName] = useState(lead.name || '');
  const [phone, setPhone] = useState(lead.phone || '');
  const [email, setEmail] = useState(lead.email || '');
  const [city, setCity] = useState(lead.city || '');
  const [suburb, setSuburb] = useState(lead.suburb || '');
  const [state, setState] = useState(lead.state || '');
  const [postcode, setPostcode] = useState(lead.postcode || lead.pincode || '');
  const [address, setAddress] = useState(lead.address || '');
  const [electricityProvider, setElectricityProvider] = useState(lead.electricity_provider || '');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCorrect = async () => {
    if (!reason.trim() || reason.trim().length < 3) {
      notifications.show({
        title: 'Validation Error',
        message: 'A justification reason of at least 3 characters is mandatory.',
        color: 'red',
      });
      return;
    }

    setLoading(true);
    const updates: Record<string, any> = {
      name,
      phone,
      email,
      city,
      suburb,
      state,
      address,
      electricity_provider: electricityProvider,
    };
    if (lead.region === 'AU') {
      updates.postcode = postcode;
    } else {
      updates.pincode = postcode;
    }

    try {
      await correctLeadData(lead.id, updates, reason.trim());
      notifications.show({
        title: 'Data Rectified',
        message: `Lead #${lead.id} personal records corrected and logged in compliance AuditLog.`,
        color: 'green',
        icon: <IconShieldCheck size={16} />,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      notifications.show({
        title: 'Correction Failed',
        message: err.response?.data?.error || err.message || 'Operation failed',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Text fw={700}>Data Rectification / Correction — Lead #{lead.id}</Text>}
      size="lg"
      centered
    >
      <Stack gap="sm">
        <Text size="xs" c="dimmed">
          Pursuant to statutory access & correction principles (DPDP Act Sec 12 / Privacy Act APP 13).
          All updates require a typed justification and are recorded in the immutable AuditLog.
        </Text>

        <TextInput label="Full Name" required value={name} onChange={(e) => setName(e.currentTarget.value)} />

        <Group grow>
          <TextInput label="Primary Phone" required value={phone} onChange={(e) => setPhone(e.currentTarget.value)} />
          <TextInput label="Email Address" value={email} onChange={(e) => setEmail(e.currentTarget.value)} />
        </Group>

        <Group grow>
          <TextInput label="City" value={city} onChange={(e) => setCity(e.currentTarget.value)} />
          <TextInput label="Suburb / Locality" value={suburb} onChange={(e) => setSuburb(e.currentTarget.value)} />
        </Group>

        <Group grow>
          <TextInput label="State / Territory" value={state} onChange={(e) => setState(e.currentTarget.value)} />
          <TextInput
            label={lead.region === 'AU' ? 'Postcode (4 digits)' : 'Pincode (6 digits)'}
            value={postcode}
            onChange={(e) => setPostcode(e.currentTarget.value)}
          />
        </Group>

        <TextInput label="Street Address" value={address} onChange={(e) => setAddress(e.currentTarget.value)} />
        <TextInput
          label={lead.region === 'AU' ? 'Electricity Retailer' : 'DISCOM Provider'}
          value={electricityProvider}
          onChange={(e) => setElectricityProvider(e.currentTarget.value)}
        />

        <Textarea
          label="Justification Reason for Rectification (Required)"
          placeholder="e.g. Customer provided corrected spelling and updated postal address via telephone request."
          required
          minRows={2}
          value={reason}
          onChange={(e) => setReason(e.currentTarget.value)}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button color="blue" onClick={handleCorrect} loading={loading} disabled={reason.trim().length < 3}>
            Apply Rectification & Record Audit Trail
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};
