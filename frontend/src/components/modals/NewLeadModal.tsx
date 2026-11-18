import React, { useState, useEffect } from 'react';
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
  SegmentedControl,
} from '@mantine/core';
import { IconAlertTriangle, IconPlus } from '@tabler/icons-react';
import {
  createLead,
  fetchLeadSources,
  fetchUsers,
  fetchStates,
  fetchRoofTypes,
  fetchPropertyTypes,
} from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { useRegion } from '../../context/RegionContext';
import type { LeadSource, User, State, RoofType, PropertyType } from '../../api/types';

interface NewLeadModalProps {
  opened: boolean;
  onClose: () => void;
  onLeadCreated?: (leadId: number) => void;
}

export const NewLeadModal: React.FC<NewLeadModalProps> = ({ opened, onClose, onLeadCreated }) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, isAdminOrManager } = useAuth();
  const { selectedRegion } = useRegion();

  const [region, setRegion] = useState<string>('IN');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [altPhone, setAltPhone] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [suburb, setSuburb] = useState('');
  const [stateVal, setStateVal] = useState<string | null>(null);
  const [pincode, setPincode] = useState('');
  const [postcode, setPostcode] = useState('');
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [propertyType, setPropertyType] = useState<string | null>('residential');
  const [billAmount, setBillAmount] = useState<number | string>('');
  const [billPeriod, setBillPeriod] = useState<string>('monthly');
  const [electricityProvider, setElectricityProvider] = useState('');
  const [roofType, setRoofType] = useState<string | null>(null);
  const [ownerOrTenant, setOwnerOrTenant] = useState<string | null>('owner');
  const [assignedToId, setAssignedToId] = useState<string | null>(null);
  const [consentStatus, setConsentStatus] = useState<string>('consented');
  const [consentSource, setConsentSource] = useState<string>('Website Form');
  const [remark, setRemark] = useState('');

  const [duplicateLead, setDuplicateLead] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Set default region whenever modal opens
  useEffect(() => {
    if (opened) {
      const def = selectedRegion || user?.default_region || 'IN';
      setRegion(def);
      setCity(def === 'AU' ? 'Melbourne' : 'Ahmedabad');
      setBillPeriod(def === 'AU' ? 'quarterly' : 'monthly');
    }
  }, [opened, selectedRegion, user]);

  // Queries
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

  const { data: states = [] } = useQuery<State[]>({
    queryKey: ['states', region],
    queryFn: () => fetchStates(region),
    enabled: opened,
  });

  const { data: roofTypes = [] } = useQuery<RoofType[]>({
    queryKey: ['roof-types', region],
    queryFn: () => fetchRoofTypes(region),
    enabled: opened,
  });

  const { data: propertyTypes = [] } = useQuery<PropertyType[]>({
    queryKey: ['property-types', region],
    queryFn: () => fetchPropertyTypes(region),
    enabled: opened,
  });

  const isAU = region === 'AU';
  const currencySymbol = isAU ? 'A$' : '₹';

  const resetForm = () => {
    setName('');
    setPhone('');
    setAltPhone('');
    setEmail('');
    setAddress('');
    setCity(region === 'AU' ? 'Melbourne' : 'Ahmedabad');
    setSuburb('');
    setStateVal(null);
    setPincode('');
    setPostcode('');
    setSourceId(null);
    setPropertyType('residential');
    setBillAmount('');
    setBillPeriod(region === 'AU' ? 'quarterly' : 'monthly');
    setElectricityProvider('');
    setRoofType(null);
    setOwnerOrTenant('owner');
    setAssignedToId(null);
    setConsentStatus('consented');
    setConsentSource('Website Form');
    setRemark('');
    setDuplicateLead(null);
    setErrorMsg(null);
  };

  const createMutation = useMutation({
    mutationFn: (force: boolean = false) => {
      const payload: any = {
        region,
        name: name.trim(),
        phone: phone.trim(),
        alt_phone: altPhone.trim() || undefined,
        email: email.trim() || undefined,
        address: address.trim() || undefined,
        city: city.trim() || (isAU ? 'Melbourne' : 'Ahmedabad'),
        suburb: isAU ? suburb.trim() || undefined : undefined,
        state: stateVal || undefined,
        pincode: !isAU ? pincode.trim() || undefined : undefined,
        postcode: isAU ? postcode.trim() || undefined : undefined,
        source: sourceId ? Number(sourceId) : undefined,
        property_type: propertyType || 'residential',
        bill_amount: billAmount ? Number(billAmount) : undefined,
        bill_period: billPeriod || (isAU ? 'quarterly' : 'monthly'),
        monthly_bill: billAmount ? Number(billAmount) : undefined,
        electricity_provider: electricityProvider.trim() || undefined,
        roof_type: roofType || (isAU ? 'Colorbond / Metal' : 'RCC flat'),
        owner_or_tenant: ownerOrTenant || 'owner',
        consent_status: consentStatus,
        consent_source: consentSource,
        remark: remark.trim() || undefined,
      };
      if (assignedToId) {
        payload.assigned_to = Number(assignedToId);
      }
      return createLead(payload, force);
    },
    onSuccess: (newLead) => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['today-leads'] });
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
        setErrorMsg('Duplicate lead detected with this phone number (or matching E.164 number).');
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

          {/* Country / Region selector */}
          <div>
            <Text size="xs" fw={600} mb={4}>
              Target Country / Market
            </Text>
            <SegmentedControl
              fullWidth
              color={isAU ? 'teal' : 'yellow'}
              value={region}
              onChange={(val) => {
                setRegion(val);
                setCity(val === 'AU' ? 'Melbourne' : 'Ahmedabad');
                setBillPeriod(val === 'AU' ? 'quarterly' : 'monthly');
                setStateVal(null);
                setRoofType(null);
              }}
              data={[
                { label: '🇮🇳 India (IN)', value: 'IN' },
                { label: '🇦🇺 Australia (AU)', value: 'AU' },
              ]}
            />
          </div>

          <Group grow>
            <TextInput
              label="Customer Name"
              placeholder={isAU ? 'e.g. Lachlan Smith' : 'e.g. Ramesh Patel'}
              value={name}
              onChange={(e) => setName(e.currentTarget.value)}
              required
            />
            <TextInput
              label={`Phone Number (${isAU ? '+61' : '+91'})`}
              placeholder={isAU ? 'e.g. 0412 345 678' : 'e.g. 98250 12345'}
              description={isAU ? 'Australian 10-digit mobile or landline' : 'Indian 10-digit mobile number'}
              value={phone}
              onChange={(e) => setPhone(e.currentTarget.value)}
              required
            />
          </Group>

          <Group grow>
            <TextInput
              label="Alt Phone (Optional)"
              placeholder={isAU ? 'e.g. 03 9876 5432' : 'e.g. 98250 98765'}
              value={altPhone}
              onChange={(e) => setAltPhone(e.currentTarget.value)}
            />
            <TextInput
              label="Email (Optional)"
              placeholder={isAU ? 'e.g. lachlan@example.com.au' : 'e.g. ramesh@example.com'}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
            />
          </Group>

          <Group grow>
            <Select
              label="State / Territory"
              placeholder="Select state"
              data={states.map((s) => ({ value: s.code, label: `${s.name} (${s.code})` }))}
              value={stateVal}
              onChange={setStateVal}
              searchable
              clearable
            />
            <TextInput
              label={isAU ? 'City / Town' : 'City'}
              placeholder={isAU ? 'e.g. Melbourne, Geelong' : 'e.g. Ahmedabad, Surat'}
              value={city}
              onChange={(e) => setCity(e.currentTarget.value)}
              required
            />
          </Group>

          <Group grow>
            {isAU ? (
              <>
                <TextInput
                  label="Suburb"
                  placeholder="e.g. Richmond, Hawthorn"
                  value={suburb}
                  onChange={(e) => setSuburb(e.currentTarget.value)}
                />
                <TextInput
                  label="Postcode (4 digits)"
                  placeholder="e.g. 3121"
                  maxLength={4}
                  value={postcode}
                  onChange={(e) => setPostcode(e.currentTarget.value)}
                />
              </>
            ) : (
              <TextInput
                label="Pincode (6 digits)"
                placeholder="e.g. 380015"
                maxLength={6}
                value={pincode}
                onChange={(e) => setPincode(e.currentTarget.value)}
              />
            )}
          </Group>

          <TextInput
            label="Street Address / Building"
            placeholder={isAU ? 'e.g. 42 Bridge Road' : 'e.g. 12 Shantivan Bungalows, Bodakdev'}
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
              data={
                propertyTypes.length > 0
                  ? propertyTypes.map((p) => ({ value: p.name.toLowerCase(), label: p.name }))
                  : [
                      { value: 'residential', label: 'Residential' },
                      { value: 'commercial', label: 'Commercial' },
                      { value: 'industrial', label: 'Industrial' },
                      { value: 'agricultural', label: 'Agricultural' },
                      { value: 'other', label: 'Other' },
                    ]
              }
              value={propertyType}
              onChange={setPropertyType}
            />
          </Group>

          <Group grow>
            <NumberInput
              label={`Bill Amount (${currencySymbol})`}
              placeholder={isAU ? 'e.g. 650' : 'e.g. 4500'}
              value={billAmount}
              onChange={setBillAmount}
              min={0}
            />
            <Select
              label="Billing Cycle"
              data={[
                { value: 'monthly', label: 'Monthly' },
                { value: 'two_monthly', label: 'Bi-Monthly (2 months)' },
                { value: 'quarterly', label: 'Quarterly (3 months - standard AU)' },
                { value: 'annual', label: 'Annual' },
              ]}
              value={billPeriod}
              onChange={(val) => setBillPeriod(val || 'monthly')}
            />
          </Group>

          <Group grow>
            <TextInput
              label={isAU ? 'Electricity Retailer' : 'DISCOM / Power Provider'}
              placeholder={isAU ? 'e.g. AGL, Origin, EnergyAustralia' : 'e.g. Torrent Power, UGVCL, BESCOM'}
              value={electricityProvider}
              onChange={(e) => setElectricityProvider(e.currentTarget.value)}
            />
            <Select
              label="Roof Type"
              placeholder="Select roof profile"
              data={
                roofTypes.length > 0
                  ? roofTypes.map((r) => ({ value: r.name, label: r.name }))
                  : isAU
                  ? [
                      { value: 'Colorbond / Metal', label: 'Colorbond / Corrugated Iron' },
                      { value: 'Terracotta Tile', label: 'Terracotta Tile' },
                      { value: 'Concrete Tile', label: 'Concrete Tile' },
                      { value: 'Klip-Lok', label: 'Klip-Lok' },
                      { value: 'Slate', label: 'Slate' },
                    ]
                  : [
                      { value: 'RCC flat', label: 'RCC Flat' },
                      { value: 'tin shade', label: 'Tin / Metal Shade' },
                      { value: 'tiled', label: 'Tiled / Slanted' },
                      { value: 'other', label: 'Other' },
                    ]
              }
              value={roofType}
              onChange={setRoofType}
              searchable
              clearable
            />
            <Select
              label="Occupancy"
              data={[
                { value: 'owner', label: 'Owner-Occupier' },
                { value: 'tenant', label: 'Tenant' },
                { value: 'landlord', label: 'Landlord / Investor' },
                { value: 'other', label: 'Other' },
              ]}
              value={ownerOrTenant}
              onChange={setOwnerOrTenant}
            />
          </Group>

          {/* Privacy & Consent */}
          <Group grow>
            <Select
              label="Consent Status"
              data={[
                { value: 'consented', label: 'Consented (Express / Direct Opt-in)' },
                { value: 'unknown', label: 'Inferred / Public Inquiry' },
              ]}
              value={consentStatus}
              onChange={(val) => setConsentStatus(val || 'consented')}
            />
            <Select
              label="Consent Channel / Source"
              data={[
                { value: 'Website Form', label: 'Direct Website Form' },
                { value: 'Phone Inquiry', label: 'Inbound Phone Inquiry' },
                { value: 'Exhibition / Display', label: 'Exhibition / Mall Kiosk' },
                { value: 'Channel Partner', label: 'Approved Referral Partner' },
              ]}
              value={consentSource}
              onChange={(val) => setConsentSource(val || 'Website Form')}
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

          <TextInput
            label="Initial Remark / Note (max 500 chars)"
            placeholder={isAU ? 'e.g. Customer inquired about 6.6 kW system with 10 kWh battery' : 'e.g. Lead generated at mall solar canopy display'}
            maxLength={500}
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" color={isAU ? 'teal' : 'yellow'} loading={createMutation.isPending}>
              Create Lead
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
