import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  Group,
  Stack,
  Button,
  Paper,
  Select,
  MultiSelect,
  Radio,
  Table,
  Badge,
  Alert,
  SimpleGrid,
  Card,
  ThemeIcon,
  Loader,
} from '@mantine/core';
import {
  IconFileSpreadsheet,
  IconDownload,
  IconUpload,
  IconAlertTriangle,
  IconArrowRight,
  IconArrowLeft,
  IconRefresh,
} from '@tabler/icons-react';
import {
  previewCsv,
  importCsvLeads,
  downloadSampleCsv,
  fetchImportBatches,
  undoImportBatch,
  downloadFailedRowsCsv,
  fetchUsers,
} from '../api/client';
import { ConfirmActionModal } from '../components/modals/ConfirmActionModal';
import type { User, ImportBatch, CsvPreviewResponse, CsvImportResponse } from '../api/types';

export const ImportLeadsPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Step state: 1 = upload, 2 = mapping & options, 3 = results
  const [activeStep, setActiveStep] = useState<1 | 2 | 3>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<CsvPreviewResponse | null>(null);
  const [importResult, setImportResult] = useState<CsvImportResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Column mapping state
  const [mapping, setMapping] = useState<Record<string, string>>({});

  // Options state
  const [duplicateAction, setDuplicateAction] = useState<string>('skip');
  const [assignmentMode, setAssignmentMode] = useState<string>('unassigned');
  const [singleUserId, setSingleUserId] = useState<string | null>(null);
  const [roundRobinUserIds, setRoundRobinUserIds] = useState<string[]>([]);

  // Undo confirmation state
  const [undoTargetBatch, setUndoTargetBatch] = useState<ImportBatch | null>(null);
  const [undoModalOpen, setUndoModalOpen] = useState(false);

  // Drag and drop ref and state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Queries
  const { data: users = [] } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: fetchUsers,
  });

  const { data: batches = [], refetch: refetchBatches } = useQuery<ImportBatch[]>({
    queryKey: ['import-batches'],
    queryFn: fetchImportBatches,
  });

  const salespeople = users.filter((u) => u.role === 'salesperson' || u.role === 'manager');

  // Preview Mutation
  const previewMutation = useMutation({
    mutationFn: (file: File) => previewCsv(file),
    onSuccess: (data) => {
      setPreviewData(data);
      setMapping(data.suggested_mapping || {});
      setErrorMsg(null);
      setActiveStep(2);
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.error || err.message || 'Failed to parse file.');
    },
  });

  // Import Mutation
  const importMutation = useMutation({
    mutationFn: () => {
      if (!selectedFile) throw new Error('No file selected');
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('mapping', JSON.stringify(mapping));
      formData.append('duplicate_action', duplicateAction);
      formData.append('assignment_mode', assignmentMode);
      if (assignmentMode === 'single' && singleUserId) {
        formData.append('assigned_to_id', singleUserId);
      } else if (assignmentMode === 'round_robin' && roundRobinUserIds.length > 0) {
        formData.append('round_robin_user_ids', roundRobinUserIds.join(','));
      }
      return importCsvLeads(formData);
    },
    onSuccess: (data) => {
      setImportResult(data);
      setErrorMsg(null);
      setActiveStep(3);
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      refetchBatches();
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.error || err.message || 'Import execution failed.');
    },
  });

  // Undo Mutation
  const undoMutation = useMutation({
    mutationFn: (batchId: number) => undoImportBatch(batchId),
    onSuccess: () => {
      setUndoModalOpen(false);
      setUndoTargetBatch(null);
      refetchBatches();
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const handleFileDrop = (files: File[]) => {
    if (files.length > 0) {
      const file = files[0];
      setSelectedFile(file);
      setErrorMsg(null);
      previewMutation.mutate(file);
    }
  };

  const handleMappingChange = (crmField: string, fileCol: string | null) => {
    setMapping((prev) => {
      const next = { ...prev };
      if (!fileCol) {
        delete next[crmField];
      } else {
        next[crmField] = fileCol;
      }
      return next;
    });
  };

  const crmFieldsList = [
    { key: 'name', label: 'Customer Name *', required: true },
    { key: 'phone', label: 'Phone Number *', required: true },
    { key: 'alt_phone', label: 'Alt Phone', required: false },
    { key: 'email', label: 'Email Address', required: false },
    { key: 'city', label: 'City', required: false },
    { key: 'address', label: 'Address / Society', required: false },
    { key: 'pincode', label: 'Pincode', required: false },
    { key: 'source', label: 'Lead Source', required: false },
    { key: 'monthly_bill', label: 'Monthly Electricity Bill (₹)', required: false },
    { key: 'roof_type', label: 'Roof Type', required: false },
    { key: 'property_type', label: 'Property Type', required: false },
    { key: 'owner_or_tenant', label: 'Owner / Tenant', required: false },
    { key: 'remark', label: 'Initial Remark / Note', required: false },
  ];

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="center">
          <Group gap="xs">
            <ThemeIcon size="lg" radius="md" color="yellow" variant="light">
              <IconFileSpreadsheet size={22} />
            </ThemeIcon>
            <div>
              <Title order={3}>CSV & Excel Lead Import</Title>
              <Text size="xs" c="dimmed">
                Upload leads, auto-match headers, handle duplicates, and distribute to your team
              </Text>
            </div>
          </Group>

          <Button
            variant="light"
            color="yellow"
            leftSection={<IconDownload size={16} />}
            onClick={downloadSampleCsv}
          >
            Download Sample CSV Template
          </Button>
        </Group>

        {errorMsg && (
          <Alert icon={<IconAlertTriangle size={16} />} title="Import Error" color="red" variant="light">
            <Text size="xs">{errorMsg}</Text>
          </Alert>
        )}

        {/* STEP 1: FILE UPLOAD */}
        {activeStep === 1 && (
          <Paper p="xl" withBorder radius="md">
            <Stack gap="lg">
              <div>
                <Title order={4}>Step 1: Select or Drop Lead File</Title>
                <Text size="xs" c="dimmed">
                  Supports .csv and .xlsx files up to 5 MB (max 5,000 rows). Indian phone numbers will be automatically cleaned and validated.
                </Text>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFileDrop(Array.from(e.target.files));
                  }
                }}
              />

              <Paper
                p="xl"
                withBorder
                radius="md"
                style={{
                  borderStyle: 'dashed',
                  borderWidth: 2,
                  borderColor: isDragging ? 'var(--mantine-color-yellow-6)' : 'var(--mantine-color-gray-4)',
                  backgroundColor: isDragging ? 'var(--mantine-color-yellow-0)' : 'var(--mantine-color-gray-0)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    handleFileDrop(Array.from(e.dataTransfer.files));
                  }
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <Group justify="center" gap="xl" mih={180}>
                  {previewMutation.isPending ? (
                    <Stack align="center" gap="sm">
                      <Loader color="yellow" size="lg" />
                      <Text size="sm" fw={600}>Analyzing and parsing file...</Text>
                    </Stack>
                  ) : (
                    <>
                      <ThemeIcon size={64} radius="xl" color="yellow" variant="light">
                        <IconUpload size={36} />
                      </ThemeIcon>
                      <div>
                        <Text size="lg" fw={600}>
                          Drag lead file here or click to browse
                        </Text>
                        <Text size="xs" c="dimmed" mt={7}>
                          Upload standard CSV (with or without BOM) or Excel spreadsheet. Max file size 5 MB.
                        </Text>
                      </div>
                    </>
                  )}
                </Group>
              </Paper>
            </Stack>
          </Paper>
        )}

        {/* STEP 2: COLUMN MAPPING, PREVIEW & SETTINGS */}
        {activeStep === 2 && previewData && (
          <Stack gap="lg">
            {/* 5-10 Row Preview */}
            <Paper p="md" withBorder radius="md">
              <Group justify="space-between" mb="sm">
                <div>
                  <Title order={4}>File Data Preview ({previewData.total_rows} total rows)</Title>
                  <Text size="xs" c="dimmed">
                    Showing first {previewData.preview_rows.length} rows from <strong>{selectedFile?.name}</strong>
                  </Text>
                </div>
                <Button
                  size="xs"
                  variant="subtle"
                  leftSection={<IconArrowLeft size={14} />}
                  onClick={() => setActiveStep(1)}
                >
                  Choose Different File
                </Button>
              </Group>

              <div style={{ overflowX: 'auto' }}>
                <Table highlightOnHover verticalSpacing="xs">
                  <Table.Thead bg="var(--mantine-color-gray-0)">
                    <Table.Tr>
                      {previewData.headers.map((h, i) => (
                        <Table.Th key={i} style={{ whiteSpace: 'nowrap' }}>
                          {h}
                        </Table.Th>
                      ))}
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {previewData.preview_rows.map((row, idx) => (
                      <Table.Tr key={idx}>
                        {previewData.headers.map((h, colIdx) => (
                          <Table.Td key={colIdx} style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>
                            {row[h] || '—'}
                          </Table.Td>
                        ))}
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </div>
            </Paper>

            {/* Column Mapping Section */}
            <Paper p="md" withBorder radius="md">
              <Title order={4} mb="xs">
                Step 2: Column Mapping
              </Title>
              <Text size="xs" c="dimmed" mb="md">
                We've auto-matched your headers. Verify or update the mappings below:
              </Text>

              <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
                {crmFieldsList.map((f) => (
                  <Select
                    key={f.key}
                    label={f.label}
                    placeholder="Select matching column"
                    data={previewData.headers.map((h) => ({ value: h, label: h }))}
                    value={mapping[f.key] || null}
                    onChange={(val) => handleMappingChange(f.key, val)}
                    clearable={!f.required}
                    searchable
                  />
                ))}
              </SimpleGrid>
            </Paper>

            {/* Import Options: Duplicates & Assignment */}
            <Paper p="md" withBorder radius="md">
              <Title order={4} mb="xs">
                Step 3: Duplicate Handling & Sales Assignment
              </Title>
              <Text size="xs" c="dimmed" mb="md">
                Configure duplicate phone resolution and salesperson allocation.
              </Text>

              <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
                {/* Duplicate Handling */}
                <Card withBorder padding="sm" radius="md">
                  <Text size="xs" fw={600} mb="xs">
                    Duplicate Phone Policy (in file & database):
                  </Text>
                  <Radio.Group value={duplicateAction} onChange={setDuplicateAction}>
                    <Stack gap="xs">
                      <Radio
                        value="skip"
                        label="Skip duplicates (Recommended)"
                        description="Do not create duplicate leads; existing records remain untouched"
                        color="yellow"
                      />
                      <Radio
                        value="update_empty"
                        label="Update empty fields on existing lead"
                        description="Fill in missing email, city, address, or bill if blank on existing record"
                        color="yellow"
                      />
                      <Radio
                        value="create_anyway"
                        label="Create anyway"
                        description="Allow duplicate leads with same phone number"
                        color="yellow"
                      />
                    </Stack>
                  </Radio.Group>
                </Card>

                {/* Assignment Options */}
                <Card withBorder padding="sm" radius="md">
                  <Text size="xs" fw={600} mb="xs">
                    Assign Leads To:
                  </Text>
                  <Radio.Group value={assignmentMode} onChange={setAssignmentMode}>
                    <Stack gap="xs">
                      <Radio value="unassigned" label="Leave Unassigned" color="yellow" />
                      <Radio value="single" label="Assign All to One Team Member" color="yellow" />
                      {assignmentMode === 'single' && (
                        <Select
                          placeholder="Select salesperson"
                          data={salespeople.map((u) => ({
                            value: String(u.id),
                            label: `${u.first_name || u.username} (${u.role})`,
                          }))}
                          value={singleUserId}
                          onChange={setSingleUserId}
                          size="xs"
                          searchable
                        />
                      )}
                      <Radio
                        value="round_robin"
                        label="Round-Robin Across Selected Salespeople"
                        color="yellow"
                      />
                      {assignmentMode === 'round_robin' && (
                        <MultiSelect
                          placeholder="Pick team members to distribute equally"
                          data={salespeople.map((u) => ({
                            value: String(u.id),
                            label: `${u.first_name || u.username} (${u.role})`,
                          }))}
                          value={roundRobinUserIds}
                          onChange={setRoundRobinUserIds}
                          size="xs"
                          searchable
                        />
                      )}
                    </Stack>
                  </Radio.Group>
                </Card>
              </SimpleGrid>

              <Alert color="blue" variant="light" mt="md">
                <Text size="xs">
                  <strong>CRM Workflow Rule:</strong> All imported leads will receive status <strong>New</strong> and next follow-up date of <strong>Today</strong> so no lead is left unattended.
                </Text>
              </Alert>

              <Group justify="flex-end" mt="lg">
                <Button variant="default" onClick={() => setActiveStep(1)}>
                  Back
                </Button>
                <Button
                  color="yellow"
                  onClick={() => importMutation.mutate()}
                  loading={importMutation.isPending}
                >
                  Start Lead Import
                </Button>
              </Group>
            </Paper>
          </Stack>
        )}

        {/* STEP 3: RESULTS SCREEN */}
        {activeStep === 3 && importResult && (
          <Paper p="lg" withBorder radius="md">
            <Stack gap="md">
              <Group justify="space-between">
                <div>
                  <Title order={3}>Import Process Completed</Title>
                  <Text size="xs" c="dimmed">
                    Import Batch #{importResult.batch_id} processed {importResult.total_rows} total rows
                  </Text>
                </div>

                <Group gap="xs">
                  <Button
                    variant="light"
                    color="yellow"
                    onClick={() => {
                      setActiveStep(1);
                      setSelectedFile(null);
                      setPreviewData(null);
                      setImportResult(null);
                    }}
                  >
                    Import Another File
                  </Button>
                  <Button
                    color="yellow"
                    rightSection={<IconArrowRight size={14} />}
                    onClick={() => navigate('/leads')}
                  >
                    View Leads List
                  </Button>
                </Group>
              </Group>

              <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
                <Card withBorder padding="md" ta="center">
                  <Text size="xs" c="dimmed">
                    Imported
                  </Text>
                  <Text size="xl" fw={700} c="green">
                    {importResult.imported_count}
                  </Text>
                </Card>

                <Card withBorder padding="md" ta="center">
                  <Text size="xs" c="dimmed">
                    Skipped (Duplicates)
                  </Text>
                  <Text size="xl" fw={700} c="gray">
                    {importResult.skipped_count}
                  </Text>
                </Card>

                <Card withBorder padding="md" ta="center">
                  <Text size="xs" c="dimmed">
                    Duplicates Encountered
                  </Text>
                  <Text size="xl" fw={700} c="orange">
                    {importResult.duplicate_count}
                  </Text>
                </Card>

                <Card withBorder padding="md" ta="center">
                  <Text size="xs" c="dimmed">
                    Validation Failures
                  </Text>
                  <Text size="xl" fw={700} c="red">
                    {importResult.failed_count}
                  </Text>
                </Card>
              </SimpleGrid>

              {importResult.errors.length > 0 && (
                <Paper withBorder p="md" radius="md">
                  <Group justify="space-between" mb="xs">
                    <Text fw={600} size="sm">
                      Failed Rows Breakdown ({importResult.errors.length})
                    </Text>
                    <Button
                      size="xs"
                      color="red"
                      variant="light"
                      leftSection={<IconDownload size={14} />}
                      onClick={() => downloadFailedRowsCsv(importResult.batch_id)}
                    >
                      Download Failed Rows as CSV
                    </Button>
                  </Group>

                  <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                    <Table striped highlightOnHover>
                      <Table.Thead bg="var(--mantine-color-gray-0)">
                        <Table.Tr>
                          <Table.Th>Row #</Table.Th>
                          <Table.Th>Customer Name</Table.Th>
                          <Table.Th>Phone Input</Table.Th>
                          <Table.Th>Validation Failure Reason</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {importResult.errors.map((err, i) => (
                          <Table.Tr key={i}>
                            <Table.Td>Row {err.row}</Table.Td>
                            <Table.Td>{err.name || '—'}</Table.Td>
                            <Table.Td>{err.phone || '—'}</Table.Td>
                            <Table.Td c="red.8">{err.error}</Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </div>
                </Paper>
              )}
            </Stack>
          </Paper>
        )}

        {/* IMPORT BATCHES HISTORY & UNDO SECTION */}
        <Paper p="lg" withBorder radius="md">
          <Group justify="space-between" mb="md">
            <div>
              <Title order={4}>Import Batches History</Title>
              <Text size="xs" c="dimmed">
                Audit past imports and safely undo entire batches in a single click
              </Text>
            </div>
          </Group>

          {batches.length === 0 ? (
            <Text size="xs" c="dimmed" ta="center" py="md">
              No import batches recorded yet.
            </Text>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <Table highlightOnHover verticalSpacing="sm">
                <Table.Thead bg="var(--mantine-color-gray-0)">
                  <Table.Tr>
                    <Table.Th>Batch ID</Table.Th>
                    <Table.Th>File Name</Table.Th>
                    <Table.Th>Imported By</Table.Th>
                    <Table.Th>Date & Time</Table.Th>
                    <Table.Th>Counts</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th ta="right">Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {batches.map((batch) => (
                    <Table.Tr key={batch.id}>
                      <Table.Td>
                        <Badge size="xs" color="gray">
                          #{batch.id}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" fw={600}>
                          {batch.file_name}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{batch.imported_by_name || 'System'}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">
                          {new Date(batch.imported_at).toLocaleString([], {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap={4}>
                          <Badge color="green" size="xs">
                            {batch.imported_count} imported
                          </Badge>
                          {batch.failed_count > 0 && (
                            <Badge color="red" size="xs">
                              {batch.failed_count} failed
                            </Badge>
                          )}
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        {batch.is_reverted ? (
                          <Badge color="red" variant="light" size="xs">
                            Reverted / Undone
                          </Badge>
                        ) : (
                          <Badge color="green" variant="light" size="xs">
                            Active
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td ta="right">
                        {!batch.is_reverted && batch.imported_count > 0 && (
                          <Button
                            size="xs"
                            color="red"
                            variant="subtle"
                            leftSection={<IconRefresh size={12} />}
                            onClick={() => {
                              setUndoTargetBatch(batch);
                              setUndoModalOpen(true);
                            }}
                          >
                            Undo Batch
                          </Button>
                        )}
                        {batch.failed_count > 0 && (
                          <Button
                            size="xs"
                            variant="subtle"
                            color="gray"
                            onClick={() => downloadFailedRowsCsv(batch.id)}
                          >
                            Failed CSV
                          </Button>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
          )}
        </Paper>
      </Stack>

      {/* Undo Batch Confirmation Modal */}
      <ConfirmActionModal
        opened={undoModalOpen}
        onClose={() => setUndoModalOpen(false)}
        onConfirm={() => {
          if (undoTargetBatch) {
            undoMutation.mutate(undoTargetBatch.id);
          }
        }}
        title="Undo Lead Import Batch"
        message={`Are you sure you want to undo Batch #${undoTargetBatch?.id} (${undoTargetBatch?.file_name})? This will permanently delete all ${undoTargetBatch?.imported_count} leads created by this batch.`}
        confirmLabel="Undo & Delete Leads"
        confirmColor="red"
        loading={undoMutation.isPending}
      />
    </Container>
  );
};
