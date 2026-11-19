import React, { useState, useEffect } from 'react';
import { Menu, Button, Group, Text, Badge, rem } from '@mantine/core';
import { IconWorld, IconCheck, IconChevronDown } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { SUPPORTED_LANGUAGES, changeAppLanguage } from '../../i18n/i18n';

interface LanguageSelectorProps {
  variant?: 'subtle' | 'default' | 'filled' | 'light';
  size?: 'xs' | 'sm' | 'md';
  compact?: boolean;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  variant = 'subtle',
  size = 'sm',
  compact = false,
}) => {
  const queryClient = useQueryClient();
  const { i18n, t } = useTranslation('common');
  const [currentLang, setCurrentLang] = useState(i18n.language || 'en');

  useEffect(() => {
    const handleLangChanged = (lng: string) => {
      setCurrentLang(lng);
    };
    i18n.on('languageChanged', handleLangChanged);
    return () => {
      i18n.off('languageChanged', handleLangChanged);
    };
  }, [i18n]);

  const activeObj =
    SUPPORTED_LANGUAGES.find((l) => l.code === currentLang) ||
    SUPPORTED_LANGUAGES.find((l) => currentLang.startsWith(l.code)) ||
    SUPPORTED_LANGUAGES[0];

  const handleSelect = async (code: string) => {
    await changeAppLanguage(code);
    setCurrentLang(code);
    queryClient.invalidateQueries();
  };

  return (
    <Menu position="bottom-end" shadow="md" width={220} withArrow>
      <Menu.Target>
        <Button
          variant={variant}
          size={size}
          leftSection={<IconWorld style={{ width: rem(16), height: rem(16) }} />}
          rightSection={<IconChevronDown style={{ width: rem(12), height: rem(12) }} />}
          aria-label={t('language.selector_label', 'Language')}
          data-testid="language-selector-btn"
          px="xs"
        >
          {compact ? activeObj.code.toUpperCase() : activeObj.nativeName}
        </Button>
      </Menu.Target>

      <Menu.Dropdown data-testid="language-dropdown-menu">
        <Menu.Label>{t('language.selector_label', 'Select Language')}</Menu.Label>
        {SUPPORTED_LANGUAGES.map((lang) => {
          const isSelected = lang.code === currentLang;
          return (
            <Menu.Item
              key={lang.code}
              onClick={() => handleSelect(lang.code)}
              data-testid={`lang-option-${lang.code}`}
              rightSection={isSelected ? <IconCheck style={{ width: rem(14), height: rem(14) }} color="var(--mantine-color-primary-6)" /> : undefined}
            >
              <Group justify="space-between" wrap="nowrap">
                <div>
                  <Text size="sm" fw={isSelected ? 600 : 400}>
                    {lang.nativeName}
                  </Text>
                  {lang.name !== lang.nativeName && (
                    <Text size="xs" c="dimmed">
                      {lang.name}
                    </Text>
                  )}
                </div>
                {lang.dir === 'rtl' && (
                  <Badge size="xs" variant="light" color="orange">
                    RTL
                  </Badge>
                )}
              </Group>
            </Menu.Item>
          );
        })}
      </Menu.Dropdown>
    </Menu>
  );
};
