import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

function speak(text) {
  if (!window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function stopSpeaking() {
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

function getSpeechRecognition() {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;
  return SpeechRecognition;
}

function App() {
  const [url, setUrl] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(0);
  const messagesEndRef = useRef(null);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  const [autoSpeak, setAutoSpeak] = useState(false);

  const [mode, setMode] = useState('classical');

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const initializeRecipe = async () => {
    if (!url.trim()) return alert('Please enter a recipe URL');

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url.trim(),
          session_id: 'default',
          mode,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setInitialized(true);
        setMessages([{ type: 'bot', text: 'Recipe loaded! Ask me anything.' }]);

        if (data.mode) {
          setMode(data.mode);
        }

        setCurrentStep(0);
        setTotalSteps(0);
      } else {
        alert(`Error: ${data.error || 'Failed to load recipe'}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (e, overrideText) => {
    if (e) e.preventDefault();
    const text = overrideText !== undefined ? overrideText : input;
    if (!text.trim() || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { type: 'user', text }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text, session_id: 'default' }),
      });

      const data = await res.json();

      if (res.ok) {
        setMessages((prev) => [...prev, { type: 'bot', text: data.response }]);

        setCurrentStep(data.current_step || 0);
        setTotalSteps(data.total_steps || 0);

        if (data.mode) {
          setMode(data.mode);
        }

        if (autoSpeak) speak(data.response);
      } else {
        setMessages((prev) => [
          ...prev,
          { type: 'bot', text: `Error: ${data.error}` },
        ]);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { type: 'bot', text: `Error: ${error.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const resetChat = () => {
    setInitialized(false);
    setMessages([]);
    setUrl('');
    setCurrentStep(0);
    setTotalSteps(0);
  };

  const toggleListening = () => {
    if (listening && recognitionRef.current) {
      recognitionRef.current.stop();
      return;
    }

    const SpeechRecognition = getSpeechRecognition();
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      sendMessage(null, transcript);
    };

    recognition.start();
  };

  return (
    <div className="app">
      <div className="chat-container">
        <div className="chat-header">
          <div>
            <h1>Recipe Chatbot</h1>
            <p className="course-info">CS 337 - Group 10</p>
            {initialized && (
              <p style={{ fontSize: '0.9rem', color: '#ccc', marginTop: '4px' }}>
                Mode:{' '}
                {mode === 'classical'
                  ? 'Classical NLP'
                  : mode === 'llm'
                  ? 'LLM (Gemini)'
                  : 'Hybrid (NLP + LLM)'}
              </p>
            )}
          </div>
          {initialized && (
            <div className="recipe-info">
              {totalSteps > 0 && (
                <span className="step-indicator">
                  Step {currentStep + 1} of {totalSteps}
                </span>
              )}
              <button onClick={resetChat} className="reset-btn">
                New Recipe
              </button>
            </div>
          )}
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginBottom: "20px",
            marginTop: "10px"
          }}
        >
          <button
            onClick={() => setAutoSpeak((prev) => !prev)}
            style={{
              padding: "14px 28px",
              fontSize: "18px",
              borderRadius: "12px",
              cursor: "pointer",
              backgroundColor: autoSpeak ? "#4caf50" : "#888",
              color: "white",
              border: "none",
              minWidth: "260px"
            }}
          >
            {autoSpeak ? "Auto Speak: On" : "Auto Speak: Off"}
          </button>
        </div>

        {!initialized ? (
          <div className="init-screen">
            <div className="init-content">
              <h2>Recipe Chatbot</h2>
              <p className="course-info">CS 337 - Group 10</p>
              <p>Enter a recipe URL to get started</p>

              <div className="url-input-container">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://www.allrecipes.com/recipe/..."
                  className="url-input"
                  onKeyPress={(e) => e.key === 'Enter' && initializeRecipe()}
                />
                <button
                  onClick={initializeRecipe}
                  disabled={loading}
                  className="load-btn"
                >
                  {loading ? 'Loading...' : 'Load Recipe'}
                </button>
              </div>

              <div
                style={{
                  marginTop: '20px',
                  display: 'flex',
                  justifyContent: 'center',
                  gap: '20px'
                }}
              >
                <button
                  onClick={() => setMode('classical')}
                  className="mode-btn"
                  style={{
                    padding: '12px 22px',
                    borderRadius: '10px',
                    border: mode === 'classical' ? '2px solid #2196f3' : '2px solid #1b3a57',
                    backgroundColor: mode === 'classical' ? '#2196f3' : '#1b3a57',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '16px',
                    transition: '0.2s ease',
                    minWidth: '190px',
                  }}
                >
                  Classical NLP
                </button>

                <button
                  onClick={() => setMode('llm')}
                  className="mode-btn"
                  style={{
                    padding: '12px 22px',
                    borderRadius: '10px',
                    border: mode === 'llm' ? '2px solid #2196f3' : '2px solid #1b3a57',
                    backgroundColor: mode === 'llm' ? '#2196f3' : '#1b3a57',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '16px',
                    transition: '0.2s ease',
                    minWidth: '190px',
                  }}
                >
                  LLM (Gemini)
                </button>

                <button
                  onClick={() => setMode('hybrid')}
                  className="mode-btn"
                  style={{
                    padding: '12px 22px',
                    borderRadius: '10px',
                    border: mode === 'hybrid' ? '2px solid #2196f3' : '2px solid #1b3a57',
                    backgroundColor: mode === 'hybrid' ? '#2196f3' : '#1b3a57',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '16px',
                    transition: '0.2s ease',
                    minWidth: '190px',
                  }}
                >
                  Hybrid (NLP + LLM)
                </button>
              </div>

              {mode === 'hybrid' && (
                <p
                  style={{
                    marginTop: '16px',
                    color: '#ff4d4f',
                    fontWeight: 600,
                    textAlign: 'center',
                    maxWidth: '520px',
                  }}
                >
                  Hybrid mode may be very slow without a Gemini subscription — loading can take up to around 5 minutes.
                </p>
              )}

              <div className="supported-sites">
                <p>Supported sites:</p>
                <ul>
                  <li>allrecipes.com</li>
                  <li>epicurious.com</li>
                  <li>bonappetit.com</li>
                </ul>
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="messages-container">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`message ${
                    msg.type === 'user' ? 'user-message' : 'bot-message'
                  }`}
                >
                  <div className="message-content">
                    {msg.text.split('\n').map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}

                    {msg.type === 'bot' && (
                      <div
                        style={{
                          display: "flex",
                          gap: "10px",
                          marginTop: "6px"
                        }}
                      >
                        <button
                          className="speak-btn"
                          onClick={() => speak(msg.text)}
                        >
                          🔊 Speak
                        </button>

                        <button
                          className="stop-btn"
                          onClick={stopSpeaking}
                        >
                          🛑 Stop
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="message bot-message">
                  <div className="message-content">
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={sendMessage} className="input-container">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about the recipe..."
                className="message-input"
                disabled={loading}
              />

              <button
                type="button"
                onClick={toggleListening}
                className="mic-btn"
                style={{ marginLeft: '8px', marginRight: '8px' }}
                disabled={loading}
              >
                {listening ? '🛑 Stop' : '🎤 Record'}
              </button>

              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="send-btn"
              >
                Send
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

export default App;
