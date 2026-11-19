import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Paper,
  Stack,
  Title,
  Text,
  Group,
  Table,
  Badge,
  Switch,
  Button,
  Select,
  TextInput,
  Textarea,
  Pagination,
  Alert,
  Progress,
  ActionIcon,
  Modal,
  FileInput,
  Divider,
  SimpleGrid,
} from '@mantine/core';
import {
  IconSparkles,
  IconDownload,
  IconUpload,
  IconCheck,
  IconAlertCircle,
  IconSearch,
  IconBook,
} from '@tabler/icons-react';
import { apiClient } from '../../api/client';

interface Language {
  id: number;
  code: string;
  name: string;
  native_name: string;
  direction: 'ltr' | 'rtl';
  is_enabled: boolean;
  completeness_pct: number;
  review_status: string;
  sort_order: number;
}

interface TranslationEntry {
  id: number;
  language: number;
  language_code: string;
  namespace: string;
  key: string;
  english_text: string;
  translated_text: string;
  status: 'missing' | 'draft' | 'reviewed' | 'approved';
  is_customer_facing: boolean;
}

export const LanguagesAndTranslationsTab: React.FC = () => {
  const queryClient = useQueryClient();

  const [selectedLang, setSelectedLang] = useState<string>('hi');
  const [selectedNamespace, setSelectedNamespace] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [searchKey, setSearchKey] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 15;

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingText, setEditingText] = useState<string>('');
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [glossaryOpened, setGlossaryOpened] = useState(false);

  // Fetch languages
  const { data: languages = [] } = useQuery<Language[]>({
    queryKey: ['admin-languages'],
    queryFn: async () => {
      const res = await apiClient.get<Language[]>('/api/masters/languages/');
      return res.data;
    },
  });

  // Fetch translation entries
  const { data: translationsData, isLoading: loadingTranslations } = useQuery<{
    results: TranslationEntry[];
    count: number;
  }>({
    queryKey: ['admin-translations', selectedLang, selectedNamespace, selectedStatus, searchKey, page],
    queryFn: async () => {
      const params: any = {
        language__code: selectedLang,
        page,
      };
      if (selectedNamespace) params.namespace = selectedNamespace;
      if (selectedStatus) params.status = selectedStatus;
      if (searchKey) params.search = searchKey;

      const res = await apiClient.get<any>('/api/masters/translations/', { params });
      if (Array.isArray(res.data)) {
        return { results: res.data, count: res.data.length };
      }
      return res.data;
    },
  });

  // Toggle Language Enabled
  const toggleMutation = useMutation({
    mutationFn: async (langId: number) => {
      const res = await apiClient.post(`/api/masters/languages/${langId}/toggle_enabled/`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-languages'] });
    },
  });

  // Save single translation edit
  const saveTranslationMutation = useMutation({
    mutationFn: async ({ id, text }: { id: number; text: string }) => {
      const res = await apiClient.patch(`/api/masters/translations/${id}/`, {
        translated_text: text,
        status: 'reviewed',
      });
      return res.data;
    },
    onSuccess: () => {
      setEditingId(null);
      queryClient.invalidateQueries({ queryKey: ['admin-translations'] });
      queryClient.invalidateQueries({ queryKey: ['admin-languages'] });
    },
  });

  // Auto-Draft Missing Strings
  const draftMissingMutation = useMutation({
    mutationFn: async (langCode: string) => {
      const res = await apiClient.post('/api/masters/translations/translate_missing/', {
        lang: langCode,
      });
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['admin-translations'] });
      queryClient.invalidateQueries({ queryKey: ['admin-languages'] });
      alert(`Auto-drafted ${data.drafted_count} missing strings! Completeness: ${data.completeness_pct}%`);
    },
    onError: (err: any) => {
      alert(`Drafting error: ${err.response?.data?.error || err.message}`);
    },
  });

  // Export Translations
  const handleExport = (format: 'json' | 'csv') => {
    window.open(`/api/masters/translations/export/?lang=${selectedLang}&format=${format}`, '_blank');
  };

  // Import Translations
  const handleImport = async () => {
    if (!importFile) return;
    setImportError(null);
    setImportResult(null);

    const formData = new FormData();
    formData.append('file', importFile);
    formData.append('lang', selectedLang);

    try {
      const res = await apiClient.post('/api/masters/translations/import/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImportResult(`Successfully imported! Created: ${res.data.created_count}, Updated: ${res.data.updated_count}. Completeness: ${res.data.completeness_pct}%`);
      setImportFile(null);
      queryClient.invalidateQueries({ queryKey: ['admin-translations'] });
      queryClient.invalidateQueries({ queryKey: ['admin-languages'] });
    } catch (err: any) {
      setImportError(err.response?.data?.error || 'Import failed. Ensure file is under 5MB and valid.');
    }
  };

  const translations = translationsData?.results || [];
  const totalCount = translationsData?.count || 0;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <Stack gap="lg">
      {/* 1. LANGUAGE SUMMARY & TOGGLES */}
      <Paper p="lg" withBorder radius="md">
        <Group justify="space-between" mb="md">
          <div>
            <Title order={4}>Multi-Language System Configuration</Title>
            <Text size="xs" c="dimmed">
              Enable or disable languages, inspect completeness, and manage draft reviews.
            </Text>
          </div>
          <Button
            variant="light"
            size="xs"
            leftSection={<IconBook size={16} />}
            onClick={() => setGlossaryOpened(true)}
          >
            Glossary Reference
          </Button>
        </Group>

        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Code</Table.Th>
              <Table.Th>Language</Table.Th>
              <Table.Th>Native Name</Table.Th>
              <Table.Th>Direction</Table.Th>
              <Table.Th>Completeness</Table.Th>
              <Table.Th>Review Status</Table.Th>
              <Table.Th>Enabled for Staff</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {languages.map((lang) => (
              <Table.Tr key={lang.code}>
                <Table.Td>
                  <Badge variant="outline" size="sm">
                    {lang.code}
                  </Badge>
                </Table.Td>
                <Table.Td fw={500}>{lang.name}</Table.Td>
                <Table.Td>{lang.native_name}</Table.Td>
                <Table.Td>{lang.direction.toUpperCase()}</Table.Td>
                <Table.Td style={{ minWidth: 150 }}>
                  <Group gap="xs" wrap="nowrap">
                    <Progress
                      value={lang.completeness_pct}
                      size="sm"
                      style={{ flex: 1 }}
                      color={lang.completeness_pct >= 90 ? 'teal' : lang.completeness_pct >= 50 ? 'yellow' : 'red'}
                    />
                    <Text size="xs" fw={600}>
                      {lang.completeness_pct}%
                    </Text>
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Badge
                    size="xs"
                    color={
                      lang.review_status === 'approved'
                        ? 'green'
                        : lang.review_status === 'needs_review'
                        ? 'yellow'
                        : 'gray'
                    }
                  >
                    {lang.review_status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Switch
                    checked={lang.is_enabled}
                    disabled={lang.code === 'en'} // English cannot be disabled
                    onChange={() => toggleMutation.mutate(lang.id)}
                    size="sm"
                    color="yellow"
                  />
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      {/* 2. TRANSLATION CATALOG & EDITOR */}
      <Paper p="lg" withBorder radius="md">
        <Stack gap="md">
          <Group justify="space-between" align="center" wrap="wrap">
            <div>
              <Title order={4}>Translation Editor & Catalog</Title>
              <Text size="xs" c="dimmed">
                Review and update interface strings side-by-side. Validates ICU placeholders.
              </Text>
            </div>

            <Group gap="xs">
              <Button
                variant="light"
                color="indigo"
                size="xs"
                leftSection={<IconSparkles size={16} />}
                loading={draftMissingMutation.isPending}
                onClick={() => draftMissingMutation.mutate(selectedLang)}
              >
                Auto-Draft Missing Strings
              </Button>
              <Button
                variant="default"
                size="xs"
                leftSection={<IconDownload size={16} />}
                onClick={() => handleExport('json')}
              >
                Export JSON
              </Button>
              <Button
                variant="default"
                size="xs"
                leftSection={<IconDownload size={16} />}
                onClick={() => handleExport('csv')}
              >
                Export CSV
              </Button>
            </Group>
          </Group>

          {/* Filters Bar */}
          <SimpleGrid cols={{ base: 1, sm: 4 }} spacing="sm">
            <Select
              label="Target Language"
              value={selectedLang}
              onChange={(val) => {
                setSelectedLang(val || 'hi');
                setPage(1);
              }}
              data={languages.map((l) => ({ value: l.code, label: `${l.native_name} (${l.code})` }))}
              size="xs"
            />
            <Select
              label="Namespace"
              value={selectedNamespace}
              onChange={(val) => {
                setSelectedNamespace(val || '');
                setPage(1);
              }}
              placeholder="All Namespaces"
              data={[
                { value: '', label: 'All Namespaces' },
                { value: 'common', label: 'common' },
                { value: 'auth', label: 'auth' },
                { value: 'leads', label: 'leads' },
                { value: 'surveys', label: 'surveys' },
                { value: 'quotes', label: 'quotes' },
                { value: 'activities', label: 'activities' },
                { value: 'tour', label: 'tour' },
                { value: 'helpbot', label: 'helpbot' },
                { value: 'admin', label: 'admin' },
                { value: 'errors', label: 'errors' },
              ]}
              size="xs"
            />
            <Select
              label="Status"
              value={selectedStatus}
              onChange={(val) => {
                setSelectedStatus(val || '');
                setPage(1);
              }}
              placeholder="All Statuses"
              data={[
                { value: '', label: 'All Statuses' },
                { value: 'missing', label: 'Missing' },
                { value: 'draft', label: 'Draft (Needs Review)' },
                { value: 'reviewed', label: 'Reviewed' },
                { value: 'approved', label: 'Approved' },
              ]}
              size="xs"
            />
            <TextInput
              label="Search"
              placeholder="Key, English, or translation..."
              leftSection={<IconSearch size={14} />}
              value={searchKey}
              onChange={(e) => {
                setSearchKey(e.currentTarget.value);
                setPage(1);
              }}
              size="xs"
            />
          </SimpleGrid>

          {/* Translations Table */}
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th style={{ width: 140 }}>Namespace:Key</Table.Th>
                <Table.Th style={{ width: '35%' }}>English Master</Table.Th>
                <Table.Th style={{ width: '40%' }}>Translation ({selectedLang})</Table.Th>
                <Table.Th style={{ width: 90 }}>Status</Table.Th>
                <Table.Th style={{ width: 90 }}>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {loadingTranslations ? (
                <Table.Tr>
                  <Table.Td colSpan={5} ta="center" py="lg">
                    Loading translations...
                  </Table.Td>
                </Table.Tr>
              ) : translations.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={5} ta="center" py="lg" c="dimmed">
                    No translations found matching query.
                  </Table.Td>
                </Table.Tr>
              ) : (
                translations.map((item) => {
                  const isEditing = editingId === item.id;
                  return (
                    <Table.Tr key={item.id}>
                      <Table.Td>
                        <Text size="xs" fw={600}>
                          {item.namespace}
                        </Text>
                        <Text size="11px" c="dimmed" style={{ wordBreak: 'break-all' }}>
                          {item.key}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{item.english_text}</Text>
                      </Table.Td>
                      <Table.Td>
                        {isEditing ? (
                          <Textarea
                            size="xs"
                            autosize
                            minRows={1}
                            maxRows={3}
                            value={editingText}
                            onChange={(e) => setEditingText(e.currentTarget.value)}
                          />
                        ) : (
                          <Text size="xs" fw={item.translated_text ? 500 : 400} c={item.translated_text ? undefined : 'dimmed'}>
                            {item.translated_text || '— Missing —'}
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Badge
                          size="xs"
                          variant="light"
                          color={
                            item.status === 'approved'
                              ? 'green'
                              : item.status === 'reviewed'
                              ? 'blue'
                              : item.status === 'draft'
                              ? 'yellow'
                              : 'red'
                          }
                        >
                          {item.status}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        {isEditing ? (
                          <Group gap={4}>
                            <ActionIcon
                              size="sm"
                              color="green"
                              variant="filled"
                              loading={saveTranslationMutation.isPending}
                              onClick={() => saveTranslationMutation.mutate({ id: item.id, text: editingText })}
                            >
                              <IconCheck size={14} />
                            </ActionIcon>
                            <Button size="compact-xs" variant="subtle" color="gray" onClick={() => setEditingId(null)}>
                              ✕
                            </Button>
                          </Group>
                        ) : (
                          <Button
                            size="compact-xs"
                            variant="light"
                            onClick={() => {
                              setEditingId(item.id);
                              setEditingText(item.translated_text || '');
                            }}
                          >
                            Edit
                          </Button>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  );
                })
              )}
            </Table.Tbody>
          </Table>

          {/* Pagination */}
          {totalPages > 1 && (
            <Group justify="space-between" mt="sm">
              <Text size="xs" c="dimmed">
                Showing {translations.length} of {totalCount} keys
              </Text>
              <Pagination size="sm" total={totalPages} value={page} onChange={setPage} color="yellow" />
            </Group>
          )}

          <Divider my="md" />

          {/* 3. CSV / JSON IMPORT */}
          <div>
            <Title order={5} mb="xs">
              Bulk Import Translations
            </Title>
            <Text size="xs" c="dimmed" mb="sm">
              Upload a JSON or CSV file of translation keys for {selectedLang}. Maximum size 5MB, 5,000 rows.
            </Text>

            {importError && (
              <Alert icon={<IconAlertCircle size={16} />} color="red" mb="sm" withCloseButton onClose={() => setImportError(null)}>
                {importError}
              </Alert>
            )}
            {importResult && (
              <Alert icon={<IconCheck size={16} />} color="green" mb="sm" withCloseButton onClose={() => setImportResult(null)}>
                {importResult}
              </Alert>
            )}

            <Group align="flex-end">
              <FileInput
                placeholder="Choose JSON or CSV file"
                accept=".json,.csv"
                value={importFile}
                onChange={setImportFile}
                size="xs"
                w={300}
              />
              <Button
                size="xs"
                color="yellow"
                leftSection={<IconUpload size={14} />}
                disabled={!importFile}
                onClick={handleImport}
              >
                Import into {selectedLang}
              </Button>
            </Group>
          </div>
        </Stack>
      </Paper>

      {/* GLOSSARY VIEWER MODAL */}
      <Modal
        opened={glossaryOpened}
        onClose={() => setGlossaryOpened(false)}
        title={
          <Group gap="xs">
            <IconBook size={18} />
            <Text fw={600}>Translation Glossary (Source of Truth)</Text>
          </Group>
        }
        size="lg"
      >
        <Stack gap="sm">
          <Text size="xs" c="dimmed">
            Standard product terminology agreed for Solar CRM. Machine translations and human reviews must follow this standard.
          </Text>

          <Table striped withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>English (en)</Table.Th>
                <Table.Th>Hindi (hi)</Table.Th>
                <Table.Th>Australia (en-AU)</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              <Table.Tr>
                <Table.Td fw={500}>Lead</Table.Td>
                <Table.Td>लीड (संभावित ग्राहक)</Table.Td>
                <Table.Td>Lead</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td fw={500}>Quote / Proposal</Table.Td>
                <Table.Td>कोटेशन (प्रस्ताव)</Table.Td>
                <Table.Td>Proposal</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td fw={500}>Site Survey</Table.Td>
                <Table.Td>साइट सर्वेक्षण (साइट सर्वे)</Table.Td>
                <Table.Td>Site Inspection</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td fw={500}>Electricity Bill</Table.Td>
                <Table.Td>बिजली का बिल</Table.Td>
                <Table.Td>Power Bill</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td fw={500}>Subsidy / Incentive</Table.Td>
                <Table.Td>सब्सिडी (सरकारी प्रोत्साहन)</Table.Td>
                <Table.Td>Government Rebate (STC)</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td fw={500}>Electricity Provider</Table.Td>
                <Table.Td>बिजली वितरण कंपनी (डिस्कॉम)</Table.Td>
                <Table.Td>Electricity Retailer</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td fw={500}>Won / Lost</Table.Td>
                <Table.Td>सफल (Won) / विफल (Lost)</Table.Td>
                <Table.Td>Won / Lost</Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>

          <Text size="xs" fw={600} mt="xs">
            Terms Never to Translate:
          </Text>
          <Text size="xs" c="dimmed">
            Solar CRM, kW, kWh, kWp, GST, STC, DISCOM, E.164, PDF, CSV, XLSX, API, WhatsApp, SMS, RCC, Colorbond, Mono PERC.
          </Text>
        </Stack>
      </Modal>
    </Stack>
  );
};
