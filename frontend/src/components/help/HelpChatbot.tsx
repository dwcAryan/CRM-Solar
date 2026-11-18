import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Affix,
  Transition,
  Paper,
  Group,
  Stack,
  Text,
  TextInput,
  ActionIcon,
  Button,
  Badge,
  ScrollArea,
  Avatar,
  ThemeIcon,
  Box,
  Divider,
  Loader,
  rem,
  Tooltip,
} from '@mantine/core';
import {
  IconMessageChatbot,
  IconX,
  IconSend,
  IconRefresh,
  IconSparkles,
  IconArrowRight,
  IconRobot,
  IconUser,
  IconBulb,
} from '@tabler/icons-react';
import { queryHelpAssistant } from '../../api/client';
import type { HelpQueryResponse } from '../../api/types';

interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  category?: string;
  action?: { label: string; path: string };
  related?: string[];
  timestamp: string;
}

const DEFAULT_CHIPS = [
  "How does the 'No answer' retry ladder work?",
  "How do I import leads from CSV or Excel?",
  "Who is allowed to mark a lead as Lost?",
  "What is the Golden Rule for follow-up dates?",
  "How do quotation revisions work?",
  "How do site surveys and roof suitability work?",
  "How to merge duplicate leads?",
  "What keyboard shortcuts are available?",
];

interface HelpChatbotProps {
  onStartTour?: () => void;
}

export const HelpChatbot: React.FC<HelpChatbotProps> = ({ onStartTour }) => {
  const [opened, setOpened] = useState(false);
  const [inputVal, setInputVal] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'bot',
      text: (
        "Namaste! 👋 I am your **Solar CRM Assistant**.\n\n" +
        "You can ask me anything about software workflows, policies, retry ladders, " +
        "site surveys, quotation revisions, or lead importing. Or tap any topic below:"
      ),
      category: 'Welcome Guide',
      action: { label: 'Take System Tour', path: 'TOUR' },
      related: [
        "What is the Golden Rule for follow-up dates?",
        "How does the 'No answer' retry ladder work?",
        "How do I import leads from CSV or Excel?",
      ],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const navigate = useNavigate();
  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    if (opened && scrollViewportRef.current) {
      scrollViewportRef.current.scrollTo({
        top: scrollViewportRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages, opened, loading]);

  // Focus input when opened
  useEffect(() => {
    if (opened) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [opened]);

  const handleSendMessage = async (queryText: string) => {
    const q = queryText.trim();
    if (!q || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputVal('');
    setLoading(true);

    try {
      const data: HelpQueryResponse = await queryHelpAssistant(q);
      const botMsg: ChatMessage = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: data.answer,
        category: data.category,
        action: data.action,
        related: data.related,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      const errorMsg: ChatMessage = {
        id: `bot-err-${Date.now()}`,
        sender: 'bot',
        text: "I encountered a network issue reaching the knowledge service. You can browse the [User Manual](/docs/USER_MANUAL.md) or launch the guided tour.",
        action: { label: 'Start Guided Tour', path: 'TOUR' },
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleActionClick = (action: { label: string; path: string }) => {
    if (action.path === 'TOUR') {
      if (onStartTour) onStartTour();
      setOpened(false);
    } else {
      navigate(action.path);
      setOpened(false);
    }
  };

  const handleResetChat = () => {
    setMessages([
      {
        id: 'welcome-reset',
        sender: 'bot',
        text: "Conversation reset. What would you like to know about Solar CRM?",
        category: 'Assistant Help',
        action: { label: 'Take System Tour', path: 'TOUR' },
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  // Helper to render markdown-like simple formatting (bold, italic, bullets)
  const renderFormattedText = (rawText: string) => {
    const lines = rawText.split('\n');
    return lines.map((line, idx) => {
      if (line.startsWith('### ')) {
        return (
          <Text key={idx} fw={700} size="sm" mt={4} mb={2}>
            {line.replace('### ', '')}
          </Text>
        );
      }
      if (line.startsWith('- ')) {
        const bulletText = line.replace('- ', '');
        return (
          <Group key={idx} align="flex-start" gap={6} my={2} wrap="nowrap">
            <Text size="xs" c="yellow.9" fw={700}>
              •
            </Text>
            <Text size="xs" style={{ lineHeight: 1.4 }}>
              {renderInlineStyles(bulletText)}
            </Text>
          </Group>
        );
      }
      if (line.trim() === '') {
        return <Box key={idx} h={6} />;
      }
      return (
        <Text key={idx} size="xs" style={{ lineHeight: 1.45 }}>
          {renderInlineStyles(line)}
        </Text>
      );
    });
  };

  const renderInlineStyles = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*|\*.*?\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('*') && part.endsWith('*')) {
        return <em key={i}>{part.slice(1, -1)}</em>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={i}
            style={{
              backgroundColor: 'var(--mantine-color-gray-1)',
              padding: '1px 4px',
              borderRadius: '4px',
              fontSize: '11px',
            }}
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  return (
    <>
      <Affix position={{ bottom: 24, right: 24 }} zIndex={1000}>
        <Transition transition="slide-up" mounted={opened}>
          {(transitionStyles) => (
            <Paper
              shadow="xl"
              radius="lg"
              withBorder
              style={{
                ...transitionStyles,
                width: rem(390),
                maxWidth: '92vw',
                height: rem(530),
                maxHeight: '80vh',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                backgroundColor: 'var(--mantine-color-body)',
              }}
            >
              {/* Chat Header */}
              <Group justify="space-between" px="md" py="xs" bg="var(--mantine-color-yellow-6)">
                <Group gap="xs">
                  <Avatar radius="xl" size="sm" color="dark">
                    <IconRobot size={18} />
                  </Avatar>
                  <div>
                    <Text size="xs" fw={700} c="dark">
                      Solar CRM Assistant
                    </Text>
                    <Group gap={4}>
                      <Box
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          backgroundColor: '#2b8a3e',
                        }}
                      />
                      <Text size="10px" c="dark.8">
                        Online • Software Guide
                      </Text>
                    </Group>
                  </div>
                </Group>

                <Group gap={6}>
                  {onStartTour && (
                    <Tooltip label="Start guided product tour" withArrow position="bottom">
                      <Button
                        size="compact-xs"
                        variant="white"
                        color="dark"
                        radius="xl"
                        leftSection={<IconSparkles size={12} />}
                        onClick={() => {
                          onStartTour();
                          setOpened(false);
                        }}
                      >
                        Tour
                      </Button>
                    </Tooltip>
                  )}
                  <Tooltip label="Reset conversation" withArrow position="bottom">
                    <ActionIcon variant="subtle" color="dark" size="sm" onClick={handleResetChat}>
                      <IconRefresh size={14} />
                    </ActionIcon>
                  </Tooltip>
                  <ActionIcon variant="subtle" color="dark" size="sm" onClick={() => setOpened(false)}>
                    <IconX size={16} />
                  </ActionIcon>
                </Group>
              </Group>

              {/* Chat Messages Viewport */}
              <ScrollArea
                style={{ flex: 1 }}
                viewportRef={scrollViewportRef}
                p="sm"
                bg="var(--mantine-color-gray-0)"
              >
                <Stack gap="sm">
                  {messages.map((msg) => {
                    const isUser = msg.sender === 'user';
                    return (
                      <Group
                        key={msg.id}
                        align="flex-start"
                        justify={isUser ? 'flex-end' : 'flex-start'}
                        gap="xs"
                        wrap="nowrap"
                      >
                        {!isUser && (
                          <Avatar radius="xl" size="xs" color="yellow" variant="filled" mt={4}>
                            <IconRobot size={12} />
                          </Avatar>
                        )}

                        <Box style={{ maxWidth: '82%' }}>
                          <Paper
                            p="xs"
                            radius="md"
                            withBorder={!isUser}
                            bg={isUser ? 'var(--mantine-color-yellow-5)' : 'var(--mantine-color-body)'}
                            c={isUser ? 'dark.9' : undefined}
                          >
                            {!isUser && msg.category && (
                              <Badge size="xs" color="yellow" variant="dot" mb={4}>
                                {msg.category}
                              </Badge>
                            )}

                            <div>{renderFormattedText(msg.text)}</div>

                            {/* Deep link button if attached */}
                            {msg.action && (
                              <Button
                                size="compact-xs"
                                variant="light"
                                color="yellow"
                                mt="xs"
                                rightSection={<IconArrowRight size={12} />}
                                onClick={() => handleActionClick(msg.action!)}
                              >
                                {msg.action.label}
                              </Button>
                            )}
                          </Paper>

                          {/* Related topic suggestion chips */}
                          {!isUser && msg.related && msg.related.length > 0 && (
                            <Group gap={4} mt={6}>
                              {msg.related.map((topic, tidx) => (
                                <Badge
                                  key={tidx}
                                  size="xs"
                                  variant="outline"
                                  color="gray"
                                  style={{ cursor: 'pointer', textTransform: 'none' }}
                                  onClick={() => handleSendMessage(topic)}
                                >
                                  {topic}
                                </Badge>
                              ))}
                            </Group>
                          )}

                          <Text size="9px" c="dimmed" mt={2} ta={isUser ? 'right' : 'left'}>
                            {msg.timestamp}
                          </Text>
                        </Box>

                        {isUser && (
                          <Avatar radius="xl" size="xs" color="blue" variant="light" mt={4}>
                            <IconUser size={12} />
                          </Avatar>
                        )}
                      </Group>
                    );
                  })}

                  {loading && (
                    <Group align="center" gap="xs">
                      <Avatar radius="xl" size="xs" color="yellow" variant="filled">
                        <IconRobot size={12} />
                      </Avatar>
                      <Paper p="xs" radius="md" withBorder bg="var(--mantine-color-body)">
                        <Group gap="xs">
                          <Loader size="xs" color="yellow" />
                          <Text size="xs" c="dimmed">
                            Consulting Solar CRM knowledge...
                          </Text>
                        </Group>
                      </Paper>
                    </Group>
                  )}
                </Stack>
              </ScrollArea>

              {/* Suggested Quick Question Chips Bar */}
              <ScrollArea type="never" bg="var(--mantine-color-body)" px="xs" py={6} style={{ borderTop: '1px solid var(--mantine-color-gray-2)' }}>
                <Group gap={6} wrap="nowrap">
                  <ThemeIcon size={16} radius="xl" color="yellow" variant="light">
                    <IconBulb size={10} />
                  </ThemeIcon>
                  {DEFAULT_CHIPS.map((chip, idx) => (
                    <Badge
                      key={idx}
                      size="xs"
                      variant="subtle"
                      color="dark"
                      style={{
                        cursor: 'pointer',
                        textTransform: 'none',
                        flexShrink: 0,
                        backgroundColor: 'var(--mantine-color-gray-1)',
                      }}
                      onClick={() => handleSendMessage(chip)}
                    >
                      {chip}
                    </Badge>
                  ))}
                </Group>
              </ScrollArea>

              <Divider />

              {/* Chat Input Bar */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage(inputVal);
                }}
              >
                <Group p="xs" gap="xs" wrap="nowrap" bg="var(--mantine-color-body)">
                  <TextInput
                    ref={inputRef}
                    placeholder="Ask about retry rules, CSV import, status..."
                    size="xs"
                    radius="md"
                    value={inputVal}
                    onChange={(e) => setInputVal(e.currentTarget.value)}
                    style={{ flex: 1 }}
                    disabled={loading}
                  />
                  <ActionIcon
                    type="submit"
                    color="yellow"
                    variant="filled"
                    radius="md"
                    size="md"
                    disabled={!inputVal.trim() || loading}
                  >
                    <IconSend size={14} />
                  </ActionIcon>
                </Group>
              </form>
            </Paper>
          )}
        </Transition>

        {/* Floating Launcher Button */}
        {!opened && (
          <Tooltip label="Need help? Ask the Solar CRM Assistant" withArrow position="left">
            <Button
              color="yellow"
              size="md"
              radius="xl"
              leftSection={
                <ThemeIcon size={26} radius="xl" color="dark" variant="filled">
                  <IconMessageChatbot size={18} color="#fab005" />
                </ThemeIcon>
              }
              onClick={() => setOpened(true)}
              styles={{
                root: {
                  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.16)',
                  border: '2px solid #fab005',
                  transition: 'transform 0.15s ease',
                  '&:hover': {
                    transform: 'scale(1.04)',
                  },
                },
              }}
            >
              Help & Guide
            </Button>
          </Tooltip>
        )}
      </Affix>
    </>
  );
};
