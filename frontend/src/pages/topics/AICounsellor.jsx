import React, { useState } from 'react';
import ChatWindow from '../../components/ChatWindow';
import PreferenceList from '../../components/PreferenceList';
import DisclaimerBanner from '../../components/DisclaimerBanner';
import { sendChatMessage, fetchRecommendations } from '../../services/api';

const INITIAL_MESSAGES = [
  {
    role: 'assistant',
    content:
      'Hello! I am your AI Admission Counsellor. I help students strategically plan their college choices based on historical cutoffs, curriculum fit, and placement goals. What is your entrance exam rank and category?',
  },
];

export default function AICounsellor() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [currentProfile, setCurrentProfile] = useState({
    rank: null,
    category: 'General',
    academic_strengths: [],
    interests: [],
    career_goals: [],
    preferred_locations: [],
  });
  const [recommendations, setRecommendations] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [recLoading, setRecLoading] = useState(false);

  const handleSendMessage = async (userText) => {
    const newHistory = [...messages, { role: 'user', content: userText }];
    setMessages(newHistory);
    setChatLoading(true);

    try {
      const response = await sendChatMessage(userText, newHistory, currentProfile);
      setMessages([
        ...newHistory,
        {
          role: 'assistant',
          content: response.reply,
          structured_data: response.structured_data,
        },
      ]);
      setCurrentProfile(response.extracted_profile);

      if (response.extracted_profile?.rank) {
        setRecLoading(true);
        try {
          const recData = await fetchRecommendations(response.extracted_profile);
          setRecommendations(recData);
        } catch (recErr) {
          console.error('Failed to fetch recommendations:', recErr);
        } finally {
          setRecLoading(false);
        }
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages([
        ...newHistory,
        {
          role: 'assistant',
          content:
            'Sorry, I encountered an issue connecting to the counselling backend. Please verify that the FastAPI backend server is running on port 8000.',
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="topic-content">
      <DisclaimerBanner text={recommendations?.disclaimer} />
      <div className="counsellor-split-grid">
        <ChatWindow
          messages={messages}
          currentProfile={currentProfile}
          onSendMessage={handleSendMessage}
          loading={chatLoading}
        />
        <PreferenceList
          recommendations={recommendations}
          loading={recLoading}
        />
      </div>
    </div>
  );
}
