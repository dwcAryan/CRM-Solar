import React, { useState, useEffect } from 'react';
import { ActionIcon, Tooltip } from '@mantine/core';
import { IconSparkles } from '@tabler/icons-react';
import { HelpbotChatModal } from './HelpbotChatModal';

interface HelpbotFabProps {
  userRole?: string;
}

export const HelpbotFab: React.FC<HelpbotFabProps> = ({ userRole = 'salesperson' }) => {
  const [opened, setOpened] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input, textarea, or contentEditable
      const target = e.target as HTMLElement;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        e.preventDefault();
        setOpened(prev => !prev);
      } else if (e.key === 'Escape' && opened) {
        setOpened(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [opened]);

  return (
    <>
      <Tooltip label="Need help? (Press ?)" position="left" withArrow>
        <ActionIcon
          data-tour="helpbot-fab"
          size={48}
          radius="xl"
          variant="filled"
          color="blue"
          onClick={() => setOpened(true)}
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 999,
            boxShadow: '0 8px 24px rgba(37, 99, 235, 0.35)',
            border: '2px solid #ffffff',
          }}
          aria-label="Help Assistant"
        >
          <IconSparkles size={24} />
        </ActionIcon>
      </Tooltip>

      <HelpbotChatModal
        opened={opened}
        onClose={() => setOpened(false)}
        userRole={userRole}
      />
    </>
  );
};
