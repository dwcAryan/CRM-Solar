import React, { useState, useEffect, useRef } from 'react';
import {
  Modal,
  Stack,
  Group,
  Text,
  Badge,
  TextInput,
  ActionIcon,
  Button,
  Paper,
  ScrollArea,
  ThemeIcon,
  Loader,
  Alert,
} from '@mantine/core';
import {
  IconSend,
  IconSparkles,
  IconThumbUp,
  IconThumbDown,
  IconCompass,
  IconShieldCheck,
} from '@tabler/icons-react';
import {
  askHelpbot,
  fetchHelpbotSuggestions,
  submitHelpbotFeedback,
} from '../../api/client';
import type { HelpbotAskResponse } from '../../api/types';
import { startTour } from '../tour/ProductTourService';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  queryId?: number;
  tour?: { id: string; title: string } | null;
  suggestedQuestions?: string[];
  feedbackGiven?: 'helpful' | 'unhelpful';
  isRefusal?: boolean;
}

interface HelpbotChatModalProps {
  opened: boolean;
  onClose: () => void;
  userRole?: string;
}

export const HelpbotChatModal: React.FC<HelpbotChatModalProps> = ({
  opened,
  onClose,
  userRole = 'salesperson',
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [starters, setStarters] = useState<string[]>([]);
  const scrollViewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (opened) {
      fetchHelpbotSuggestions()
        .then(res => setStarters(res))
        .catch(() => {
          setStarters([
            'What is the CRM golden rule for logging calls?',
            'How does the automated retry ladder work?',
            'Who has permission to mark a lead as Lost?',
          ]);
        });

      if (messages.length === 0) {
        setMessages([
          {
            id: 'welcome',
            sender: 'assistant',
            text: `Hello! I am your **Solar CRM Help Assistant**. You are signed in as **${userRole}**. Ask me anything about using this CRM—such as call outcomes, retry ladders, surveys, quotes, or permissions.`,
          },
        ]);
      }
    }
  }, [opened]);

  useEffect(() => {
    if (scrollViewportRef.current) {
      scrollViewportRef.current.scrollTo({
        top: scrollViewportRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages, loading]);

  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText || input).trim();
    if (!textToSend || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend,
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const resp: HelpbotAskResponse = await askHelpbot(textToSend);
      const assistantMsg: ChatMessage = {
        id: `assist-${Date.now()}`,
        sender: 'assistant',
        text: resp.answer,
        queryId: resp.query_id,
        tour: resp.tour,
        suggestedQuestions: resp.suggested_questions,
        isRefusal: resp.is_refusal,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: 'assistant',
          text: 'Sorry, I encountered a temporary network issue. Please try again.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (queryId: number, helpful: boolean, msgId: string) => {
    try {
      await submitHelpbotFeedback({ query_id: queryId, helpful });
      setMessages(prev =>
        prev.map(m =>
          m.id === msgId ? { ...m, feedbackGiven: helpful ? 'helpful' : 'unhelpful' } : m
        )
      );
    } catch (e) {
      console.error('Feedback failed:', e);
    }
  };

  const handleStartTour = (tourId: string) => {
    onClose();
    setTimeout(() => {
      startTour(tourId);
    }, 250);
  };

  const renderFormattedText = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      let cleanLine = line;

      // Bold **text**
      const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
      const renderedParts = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      if (line.startsWith('# ')) {
        return <Text key={idx} fw={700} size="sm" mt="xs">{renderedParts}</Text>;
      }
      if (line.startsWith('## ') || line.startsWith('### ')) {
        return <Text key={idx} fw={600} size="xs" mt="xs">{renderedParts}</Text>;
      }
      if (line.startsWith('- ') || line.startsWith('* ')) {
        return (
          <Text key={idx} size="xs" style={{ paddingLeft: 12 }}>
            • {renderedParts}
          </Text>
        );
      }
      if (/^\d+\.\s/.test(line)) {
        return (
          <Text key={idx} size="xs" style={{ paddingLeft: 12 }}>
            {renderedParts}
          </Text>
        );
      }
      if (!line.trim()) {
        return <div key={idx} style={{ height: 6 }} />;
      }
      return <Text key={idx} size="xs">{renderedParts}</Text>;
    });
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <ThemeIcon size="md" color="blue" variant="light" radius="xl">
            <IconSparkles size={18} />
          </ThemeIcon>
          <div>
            <Group gap="xs">
              <Text fw={700} size="sm">
                Solar CRM Help Assistant
              </Text>
              <Badge size="xs" color="blue" variant="filled">
                Beta
              </Badge>
            </Group>
          </div>
        </Group>
      }
      size="lg"
      padding="md"
      radius="md"
    >
      <Stack gap="xs" style={{ height: 460 }}>
        {/* PII & Scope Notice */}
        <Alert
          icon={<IconShieldCheck size={16} />}
          color="gray"
          variant="light"
          py={4}
          px={8}
          styles={{ message: { fontSize: 11 } }}
        >
          Specialized in Solar CRM features only. Please do not share passwords or private customer data.
        </Alert>

        {/* Messages Stream */}
        <ScrollArea style={{ flex: 1 }} viewportRef={scrollViewportRef} pr="xs">
          <Stack gap="sm">
            {messages.map(msg => {
              const isUser = msg.sender === 'user';
              return (
                <Stack key={msg.id} align={isUser ? 'flex-end' : 'flex-start'} gap={4}>
                  <Paper
                    radius="md"
                    p="xs"
                    style={{
                      maxWidth: '85%',
                      backgroundColor: isUser ? '#2563eb' : '#f1f5f9',
                      color: isUser ? '#ffffff' : '#0f172a',
                    }}
                  >
                    {isUser ? (
                      <Text size="xs">{msg.text}</Text>
                    ) : (
                      renderFormattedText(msg.text)
                    )}

                    {/* Interactive Tour Button if available */}
                    {msg.tour && (
                      <Button
                        size="compact-xs"
                        variant="light"
                        color="blue"
                        mt="xs"
                        leftSection={<IconCompass size={14} />}
                        onClick={() => handleStartTour(msg.tour!.id)}
                      >
                        Show me how ({msg.tour.title})
                      </Button>
                    )}
                  </Paper>

                  {/* Assistant Feedback & Follow-ups */}
                  {!isUser && msg.queryId && (
                    <Group gap="xs" mt={2}>
                      <Text size="10px" c="dimmed">
                        Was this helpful?
                      </Text>
                      <ActionIcon
                        size="xs"
                        variant={msg.feedbackGiven === 'helpful' ? 'filled' : 'subtle'}
                        color={msg.feedbackGiven === 'helpful' ? 'teal' : 'gray'}
                        onClick={() => handleFeedback(msg.queryId!, true, msg.id)}
                        title="Helpful"
                      >
                        <IconThumbUp size={12} />
                      </ActionIcon>
                      <ActionIcon
                        size="xs"
                        variant={msg.feedbackGiven === 'unhelpful' ? 'filled' : 'subtle'}
                        color={msg.feedbackGiven === 'unhelpful' ? 'red' : 'gray'}
                        onClick={() => handleFeedback(msg.queryId!, false, msg.id)}
                        title="Not helpful"
                      >
                        <IconThumbDown size={12} />
                      </ActionIcon>
                    </Group>
                  )}

                  {/* Suggested follow-up chips */}
                  {!isUser && msg.suggestedQuestions && msg.suggestedQuestions.length > 0 && (
                    <Group gap={4} mt={4}>
                      {msg.suggestedQuestions.map((q, idx) => (
                        <Button
                          key={idx}
                          size="compact-xs"
                          variant="outline"
                          color="gray"
                          radius="xl"
                          styles={{ label: { fontSize: 10 } }}
                          onClick={() => handleSend(q)}
                        >
                          {q}
                        </Button>
                      ))}
                    </Group>
                  )}
                </Stack>
              );
            })}

            {loading && (
              <Group gap="xs" p="xs">
                <Loader size="xs" color="blue" />
                <Text size="xs" c="dimmed">
                  Thinking...
                </Text>
              </Group>
            )}
          </Stack>
        </ScrollArea>

        {/* Starter Suggestion Chips if conversation is short */}
        {messages.length <= 2 && starters.length > 0 && (
          <Group gap={4}>
            {starters.map((starter, idx) => (
              <Button
                key={idx}
                size="compact-xs"
                variant="light"
                color="blue"
                radius="xl"
                styles={{ label: { fontSize: 11 } }}
                onClick={() => handleSend(starter)}
              >
                {starter}
              </Button>
            ))}
          </Group>
        )}

        {/* Input Bar */}
        <Group gap="xs" align="center">
          <TextInput
            placeholder="Ask about call outcomes, quotes, surveys, or shortcuts..."
            value={input}
            onChange={e => setInput(e.currentTarget.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') handleSend();
            }}
            maxLength={500}
            style={{ flex: 1 }}
            size="xs"
            disabled={loading}
          />
          <ActionIcon
            color="blue"
            variant="filled"
            size="md"
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
          >
            <IconSend size={16} />
          </ActionIcon>
        </Group>
      </Stack>
    </Modal>
  );
};
