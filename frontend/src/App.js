import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

function speak(text) {
  if (!window.speechSynthesis) {
    console.error("Text-to-Speech not supported in this browser.");
    return;
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function getSpeechRecognition() {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.error("SpeechRecognition not supported in this browser.");
    return null;
  }
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const initializeRecipe = async () => {
    if (!url.trim()) {
      alert('Please enter a recipe URL');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/initialize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url.trim(), session_id: 'default' }),
      });

      const data = await res.json();

      if (res.ok) {
        setInitialized(true);
        setMessages([{ type: 'bot', text: 'Recipe loaded! Ask me anything.' }]);
      } else {
        alert(`Error: ${data.error || 'Failed to load recipe'}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const msg = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { type: 'user', text: msg }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: msg,
          session_id: 'default',
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setMessages((prev) => [...prev, { type: 'bot', text: data.response }]);
        setCurrentStep(data.current_step || 0);
        setTotalSteps(data.total_steps || 0);
      } else {
        setMessages((prev) => [...prev, { type: 'bot', text: `Error: ${data.error}` }]);
      }
    } catch (error) {
      setMessages((prev) => [...prev, { type: 'bot', text: `Error: ${error.message}` }]);
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
      alert("Speech recognition is not supported in this browser. Try Chrome.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      setListening(true);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      setListening(false);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInput((prev) => (prev ? prev + " " + transcript : transcript));
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
                  className={`message ${msg.type === 'user' ? 'user-message' : 'bot-message'}`}
                >
                  <div className="message-content">
                    {msg.text.split('\n').map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}

                    {msg.type === 'bot' && (
                      <button
                        className="speak-btn"
                        onClick={() => speak(msg.text)}
                        style={{ marginTop: '4px' }}
                      >
                        🔊 Speak
                      </button>
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
