import { useState, useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import './styles.css';

// Sidebar Navigation Component
function Sidebar({ isExpanded, onToggle }) {
  const location = useLocation();
  
  const navItems = [
    { path: '/', label: 'Chat', icon: '💬' },
    { path: '/stats', label: 'Tool Stats', icon: '📊' },
  ];

  const handleToggle = (e) => {
    e.stopPropagation();
    onToggle(!isExpanded);
  };

  return (
    <aside 
      className={`sidebar ${isExpanded ? 'expanded' : 'collapsed'}`}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="sidebar-header">
        <div className="sidebar-header-top">
          <div className="sidebar-avatar">
            <img src="/wonderful.jpg" alt="Wonderful Pharmacy" className="sidebar-avatar-img" />
          </div>
        </div>
        {isExpanded && <p className="sidebar-tagline">Pharmacy AI</p>}
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`sidebar-nav-item ${location.pathname === item.path ? 'active' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              // Don't expand on click - only navigate
            }}
            title={!isExpanded ? item.label : ''}
          >
            <span className="sidebar-nav-icon">{item.icon}</span>
            {isExpanded && <span className="sidebar-nav-label">{item.label}</span>}
          </Link>
        ))}
      </nav>
      <button 
        className="sidebar-toggle"
        onClick={handleToggle}
        aria-label={isExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
      >
        {isExpanded ? '◀' : '▶'}
      </button>
    </aside>
  );
}

// Chat Page Component
function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const chatElRef = useRef(null);
  const toolsElRef = useRef(null);

  useEffect(() => {
    if (chatElRef.current) {
      chatElRef.current.scrollTop = chatElRef.current.scrollHeight;
    }
  }, [messages]);

  function clearTypingIndicator() {
    const last = [...chatElRef.current.querySelectorAll('.msg-row.assistant .msg.assistant')].pop();
    if (!last) return;
    const typingIndicator = last.querySelector('.typing-indicator');
    if (typingIndicator) {
      typingIndicator.remove();
    }
  }

  function addMessage(role, content) {
    const row = document.createElement('div');
    row.className = `msg-row ${role}`;

    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.textContent = content;

    row.appendChild(div);

    if (role === 'assistant') {
      const toolsContainer = document.createElement('div');
      toolsContainer.className = 'msg-tools-container';
      row.appendChild(toolsContainer);
    }

    chatElRef.current.appendChild(row);
    chatElRef.current.scrollTop = chatElRef.current.scrollHeight;
  }

  function appendToLastAssistant(delta) {
    const last = [...chatElRef.current.querySelectorAll('.msg-row.assistant .msg.assistant')].pop();
    if (last) {
      clearTypingIndicator();
      last.textContent += delta;
    }
  }

  function addTypingIndicator() {
    const last = [...chatElRef.current.querySelectorAll('.msg.assistant')].pop();
    if (last && !last.querySelector('.typing-indicator')) {
      const indicator = document.createElement('div');
      indicator.className = 'typing-indicator';
      indicator.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
      last.appendChild(indicator);
    }
  }

  function getOrCreateToolsContainerForLastAssistant() {
    const lastRow = [...chatElRef.current.querySelectorAll('.msg-row.assistant')].pop();
    if (!lastRow) return null;

    const toolsContainer = lastRow.querySelector('.msg-tools-container');
    if (!toolsContainer) return null;

    let details = toolsContainer.querySelector('.msg-tools');
    if (!details) {
      details = document.createElement('details');
      details.className = 'msg-tools';

      const summary = document.createElement('summary');
      summary.textContent = 'Tools used (click to expand)';
      details.appendChild(summary);

      const body = document.createElement('div');
      body.className = 'msg-tools-body';
      details.appendChild(body);

      toolsContainer.appendChild(details);
    }

    return details.querySelector('.msg-tools-body');
  }

  function logTool(obj, attachToMessage = true) {
    const entry = document.createElement('div');
    entry.className = 'tool-entry';

    const details = document.createElement('details');
    details.className = 'tool-details';
    const summary = document.createElement('summary');
    const body = document.createElement('pre');
    body.style.margin = '0';
    body.style.whiteSpace = 'pre-wrap';
    body.style.wordWrap = 'break-word';

    if (obj.type === 'tool_call') {
      entry.classList.add('tool-call');
      summary.textContent = `🔧 Tool Call: ${obj.name}`;
      body.textContent = JSON.stringify(obj.arguments, null, 2);
    } else if (obj.type === 'tool_result') {
      entry.classList.add('tool-result');
      summary.textContent = `✅ Result: ${obj.name}`;
      body.textContent = JSON.stringify(obj.result, null, 2);
    } else if (obj.type === 'error') {
      entry.classList.add('error');
      summary.textContent = '⚠️ Error';
      body.textContent = JSON.stringify(obj.error, null, 2);
    } else {
      summary.textContent = 'ℹ Event';
      body.textContent = JSON.stringify(obj, null, 2);
    }

    details.appendChild(summary);
    details.appendChild(body);
    entry.appendChild(details);

    toolsElRef.current.appendChild(entry);
    toolsElRef.current.scrollTop = toolsElRef.current.scrollHeight;

    if (attachToMessage) {
      const msgToolsBody = getOrCreateToolsContainerForLastAssistant();
      if (msgToolsBody) {
        const cloned = entry.cloneNode(true);
        msgToolsBody.appendChild(cloned);
      }
    }
  }

  async function sendMessage(text) {
    if (isProcessing) {
      return; // Prevent sending if already processing
    }

    setIsProcessing(true);
    const newMessages = [...messages, { role: 'user', content: text }];
    setMessages(newMessages);
    addMessage('user', text);

    newMessages.push({ role: 'assistant', content: '' });
    setMessages([...newMessages]);
    addMessage('assistant', '');
    addTypingIndicator();

    toolsElRef.current.innerHTML = '';

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`Request failed with status ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let errorOccurred = false;
      let assistantContent = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          // Stream ended - ensure processing state is reset
          setIsProcessing(false);
          break;
        }
        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split('\n\n');
        buffer = parts.pop();

        for (const part of parts) {
          const line = part.split('\n').find((l) => l.startsWith('data: '));
          if (!line) continue;
          const jsonStr = line.slice(6);
          const ev = JSON.parse(jsonStr);

          if (ev.type === 'text_delta') {
            assistantContent += ev.delta;
            appendToLastAssistant(ev.delta);
          } else if (ev.type === 'tool_call' || ev.type === 'tool_result') {
            logTool(ev, true);
          } else if (typeof ev.type === 'string' && ev.type.startsWith('tool_') && ev.type !== 'tool_args_delta') {
            logTool(ev, false);
          } else if (ev.type === 'error') {
            logTool(ev, true);
            appendToLastAssistant('\n\n[Error: something went wrong processing your request.]');
            clearTypingIndicator();
            errorOccurred = true;
            setIsProcessing(false);
            break;
          } else if (ev.type === 'done') {
            clearTypingIndicator();
            setIsProcessing(false);
          }
        }

        if (errorOccurred) {
          try {
            if (reader.cancel) {
              await reader.cancel();
            }
          } catch (_) {
            // ignore cancel errors
          }
          setIsProcessing(false);
          break;
        }
      }

      setMessages((prev) => {
        const updated = [...prev];
        if (updated.length > 0 && updated[updated.length - 1].role === 'assistant') {
          updated[updated.length - 1].content = assistantContent;
        }
        return updated;
      });

      clearTypingIndicator();
      setIsProcessing(false);
    } catch (err) {
      logTool(
        { type: 'error', error: { message: err && err.message ? err.message : 'Network or server error' } },
        true
      );
      appendToLastAssistant('\n\n[Error: could not reach the assistant. Please try again.]');
      clearTypingIndicator();
      setIsProcessing(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    const text = inputValue.trim();
    if (!text || isProcessing) return; // Prevent submission if processing
    setInputValue('');
    sendMessage(text);
  }

  function handleClearTools() {
    if (toolsElRef.current) {
      toolsElRef.current.innerHTML = '';
    }
  }

  return (
    <div className="main-content main-content-chat">
      <section className="chat-section">
        <div className="chat-header">
          <div className="chat-header-main">
            <div className="chat-header-title">
              <h2>Chat with Assistant</h2>
              <p className="chat-subtitle">
                Ask about medications, prescriptions, and stock availability
                <span className="info-icon" aria-label="Examples of questions" tabIndex="0">
                  ⓘ
                  <span className="info-tooltip">
                    <strong>Examples you can ask:</strong><br />
                    • What are the active ingredients in Ibuprofen?<br />
                    • Is Acamol available at my local store?<br />
                    • Show my current prescriptions.<br />
                    • Submit a refill for prescription RX-123.
                  </span>
                </span>
              </p>
            </div>
            <div className="status-badge">
              <span className="status-dot"></span>
              <span>Online</span>
            </div>
          </div>
        </div>
        <div ref={chatElRef} className="chat"></div>
        <form onSubmit={handleSubmit} className="composer">
          <div className="input-wrapper">
            <input
              ref={(el) => {
                if (el && !isProcessing) el.focus();
              }}
              type="text"
              placeholder={isProcessing ? "Processing your request..." : "Type your question in English or עברית..."}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              autoComplete="off"
              disabled={isProcessing}
            />
            <button 
              type="submit" 
              className="send-button" 
              aria-label="Send message"
              disabled={isProcessing || !inputValue.trim()}
            >
              {isProcessing ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" strokeDasharray="31.416" strokeDashoffset="31.416">
                    <animate attributeName="stroke-dasharray" dur="2s" values="0 31.416;15.708 15.708;0 31.416;0 31.416" repeatCount="indefinite"/>
                    <animate attributeName="stroke-dashoffset" dur="2s" values="0;-15.708;-31.416;-31.416" repeatCount="indefinite"/>
                  </circle>
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              )}
            </button>
          </div>
        </form>
      </section>

      <aside className="tools-section">
        <div className="tools-header">
          <h2>🔧 Tool Activity</h2>
          <button className="clear-tools" onClick={handleClearTools}>
            Clear
          </button>
        </div>
        <div ref={toolsElRef} className="tools"></div>
      </aside>
    </div>
  );
}

// Stats Page Component
function StatsPage() {
  const [stats, setStats] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadToolStats();
  }, []);

  async function loadToolStats() {
    setLoading(true);
    try {
      const res = await fetch('/api/tools/stats');
      if (!res.ok) {
        throw new Error(`Status ${res.status}`);
      }
      const data = await res.json();
      const tools = Array.isArray(data.tools) ? data.tools : [];
      setStats(tools);
    } catch (err) {
      console.error('Failed to load stats:', err);
      setStats([]);
    } finally {
      setLoading(false);
    }
  }

  const maxCount = stats.reduce((max, t) => Math.max(max, t.call_count || 0), 0) || 1;

  return (
    <div className="main-content">
      <section className="stats-section-full">
        <div className="stats-header">
          <h2>Tool Usage Statistics</h2>
          <p className="stats-subtitle">Histogram of how often each tool is called.</p>
        </div>
        <div className="stats-body">
          {loading ? (
            <div className="stats-loading">Loading tool statistics...</div>
          ) : stats.length === 0 ? (
            <div className="stats-empty">
              No tool usage recorded yet. Start a chat to see statistics.
            </div>
          ) : (
            stats.map((tool) => {
              const widthPct = Math.max(10, (tool.call_count / maxCount) * 100);
              return (
                <div key={tool.tool_name} className="stats-row">
                  <div className="stats-row-header">
                    <span className="stats-row-name">{tool.tool_name}</span>
                    <span className="stats-row-count">{tool.call_count}</span>
                  </div>
                  <div className="stats-bar-track">
                    <div className="stats-bar-fill" style={{ width: `${widthPct}%` }}></div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}

// Main App Component
function App() {
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  
  const handleMainClick = (e) => {
    // Only collapse if clicking on non-interactive elements (not buttons, links, inputs, etc.)
    const target = e.target;
    const isInteractive = target.tagName === 'BUTTON' || 
                         target.tagName === 'A' || 
                         target.tagName === 'INPUT' || 
                         target.tagName === 'TEXTAREA' ||
                         target.closest('button') ||
                         target.closest('a') ||
                         target.closest('input') ||
                         target.closest('form');
    
    if (sidebarExpanded && !isInteractive) {
      setSidebarExpanded(false);
    }
  };
  
  return (
    <BrowserRouter>
      <div 
        className={`app-container ${sidebarExpanded ? 'sidebar-expanded' : 'sidebar-collapsed'}`}
        onClick={handleMainClick}
      >
        <Sidebar isExpanded={sidebarExpanded} onToggle={setSidebarExpanded} />
        <div className="app-main">
          <header className="header">
            <div className="header-content">
              <div className="logo">
                <img src="/wonderful_logo.png" alt="Wonderful Chat logo" className="logo-image" />
              </div>
              <p className="header-tagline">Your pharmacy AI assistant for medications, prescriptions, and refills.</p>
            </div>
          </header>
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/stats" element={<StatsPage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

// Render the app
const root = createRoot(document.getElementById('root'));
root.render(<App />);
