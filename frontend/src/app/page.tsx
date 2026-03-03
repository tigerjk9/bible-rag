'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ChatInput from '@/components/ChatInput';
import ChatMessageBubble from '@/components/ChatMessageBubble';
import WelcomeScreen from '@/components/WelcomeScreen';
import SearchMethodWarning from '@/components/SearchMethodWarning';
import { ChatMessage, ChatMessageUser, ChatMessageAssistant, SearchMetadata, StrongsVerse } from '@/types';

function HomeContent() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTranslations, setSelectedTranslations] = useState<string[]>(['NIV', 'KRV']);
  const [defaultTranslation, setDefaultTranslation] = useState<string>('NIV');
  const [latestSearchMetadata, setLatestSearchMetadata] = useState<SearchMetadata | undefined>();
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();

  // Auto-scroll to bottom unless user has scrolled up
  const scrollToBottom = useCallback(() => {
    if (!userScrolledRef.current && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  // Detect if user scrolled away from bottom
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const threshold = 100;
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
    userScrolledRef.current = !isAtBottom;
  }, []);

  // Scroll on new messages or streaming updates
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Handle ?strongs= query param from OriginalLanguage "Find all" links
  useEffect(() => {
    const strongsNumber = searchParams.get('strongs');
    if (!strongsNumber) return;

    // Clear the param from URL immediately
    router.replace('/');

    const assistantMsg: ChatMessageAssistant = {
      id: crypto.randomUUID(),
      role: 'assistant',
      results: null,
      aiText: '',
      isStreaming: true,
      error: null,
      timestamp: Date.now(),
    };
    const assistantId = assistantMsg.id;

    // Show a user-side label message
    const userMsg: ChatMessageUser = {
      id: crypto.randomUUID(),
      role: 'user',
      content: `Find all verses: ${strongsNumber}`,
      translations: [...selectedTranslations],
      defaultTranslation,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setIsLoading(true);
    userScrolledRef.current = false;

    import('@/lib/api').then(({ getStrongsVerses }) =>
      getStrongsVerses(strongsNumber, selectedTranslations)
    ).then((data) => {
      // Build a synthetic SearchResponse to reuse existing VerseCard rendering
      const syntheticResults = {
        query_time_ms: 0,
        results: data.verses.map((v: StrongsVerse) => ({
          reference: v.reference,
          translations: v.translations,
          relevance_score: 1,
        })),
        search_metadata: {
          total_results: data.total_count,
          cached: false,
        },
      };

      // Build AI text summary
      const defText = data.definition ? ` — "${data.definition}"` : '';
      const transText = data.transliteration ? ` (${data.transliteration})` : '';
      const summary = `${data.strongs_number}${transText}${defText}\n\n${data.language.charAt(0).toUpperCase() + data.language.slice(1)} word found in ${data.total_count} verse${data.total_count !== 1 ? 's' : ''} across the Bible. Showing the first ${data.verses.length}.`;

      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, results: syntheticResults, aiText: summary, isStreaming: false } as ChatMessageAssistant
          : m
      ));
    }).catch((err: Error) => {
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, error: err.message, isStreaming: false } as ChatMessageAssistant
          : m
      ));
    }).finally(() => {
      setIsLoading(false);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleSend = useCallback(async (query: string) => {
    const userMsg: ChatMessageUser = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      translations: [...selectedTranslations],
      defaultTranslation,
      timestamp: Date.now(),
    };

    const assistantMsg: ChatMessageAssistant = {
      id: crypto.randomUUID(),
      role: 'assistant',
      results: null,
      aiText: '',
      isStreaming: true,
      error: null,
      timestamp: Date.now(),
    };

    const assistantId = assistantMsg.id;

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setIsLoading(true);
    userScrolledRef.current = false;

    // Cancel any in-flight request before starting a new one
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    // Build conversation history from prior messages (last 10 messages = ~5 turns)
    const history = messages
      .slice(-10)
      .map(m => {
        if (m.role === 'user') {
          return { role: 'user' as const, content: m.content };
        }
        return { role: 'assistant' as const, content: (m as ChatMessageAssistant).aiText };
      })
      .filter(m => m.content);

    try {
      const { streamSearchVerses } = await import('@/lib/api');

      await streamSearchVerses({
        query,
        languages: ['en', 'ko'],
        translations: selectedTranslations,
        max_results: 10,
        include_original: false,
        conversation_history: history.length > 0 ? history : undefined,
      }, {
        onResults: (data) => {
          setLatestSearchMetadata(data.search_metadata);
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, results: data } as ChatMessageAssistant : m
          ));
        },
        onToken: (token) => {
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, aiText: (m as ChatMessageAssistant).aiText + token } as ChatMessageAssistant
              : m
          ));
        },
        onError: (msg) => {
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, error: msg, isStreaming: false } as ChatMessageAssistant
              : m
          ));
          setIsLoading(false);
        },
        onComplete: () => {
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, isStreaming: false } as ChatMessageAssistant : m
          ));
          setIsLoading(false);
        },
      }, signal);
    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, error: err instanceof Error ? err.message : 'An error occurred', isStreaming: false } as ChatMessageAssistant
          : m
      ));
      setIsLoading(false);
    }
  }, [selectedTranslations, defaultTranslation, messages]);

  // Find the user query for a given assistant message index
  const getUserQueryForAssistant = (index: number): string => {
    for (let i = index - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        return (messages[i] as ChatMessageUser).content;
      }
    }
    return '';
  };

  const getDefaultTranslationForAssistant = (index: number): string => {
    for (let i = index - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        return (messages[i] as ChatMessageUser).defaultTranslation;
      }
    }
    return defaultTranslation;
  };

  return (
    <main className="flex-1 flex flex-col min-h-0 overflow-hidden bg-background dark:bg-background-dark transition-colors">
      {/* Production warning */}
      <SearchMethodWarning searchMetadata={latestSearchMetadata} />

      {/* Scrollable message area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto"
      >
        {messages.length === 0 ? (
          <WelcomeScreen onExampleClick={handleSend} />
        ) : (
          <div className="max-w-[1000px] mx-auto px-4 py-6">
            {messages.map((msg, index) => (
              <ChatMessageBubble
                key={msg.id}
                message={msg}
                userQuery={msg.role === 'assistant' ? getUserQueryForAssistant(index) : undefined}
                defaultTranslation={msg.role === 'assistant' ? getDefaultTranslationForAssistant(index) : undefined}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Bottom-fixed input */}
      <ChatInput
        onSend={handleSend}
        isLoading={isLoading}
        selectedTranslations={selectedTranslations}
        defaultTranslation={defaultTranslation}
        onTranslationsChange={setSelectedTranslations}
        onDefaultTranslationChange={setDefaultTranslation}
      />
    </main>
  );
}

export default function Home() {
  return (
    <Suspense>
      <HomeContent />
    </Suspense>
  );
}
