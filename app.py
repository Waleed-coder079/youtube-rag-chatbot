# app.py

import streamlit as st
from youtube_chatbot import load_chatbot, get_transcript
import time

# Setup page
st.set_page_config(
    page_title="YouTube Video Chatbot", 
    page_icon="🤖", 
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #FF6B6B;
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #4ECDC4;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        /* Force readable dark text regardless of app theme */
        color: #0f172a;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
    }
    .bot-message {
        background-color: #F3E5F5;
        border-left: 4px solid #9C27B0;
    }
    .chat-message strong { color: #0b132b; }
    .success-box {
        background-color: #E8F5E8;
        border: 1px solid #4CAF50;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        /* Ensure readable text on light green background */
        color: #0f172a;
    }
    /* Optional: better contrast for Transcript preview text area */
    textarea[disabled] { color: #0f172a !important; }
</style>
""", unsafe_allow_html=True)

# Main title
st.markdown('<h1 class="main-header">🤖 YouTube Video Chatbot</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Ask questions about any YouTube video by providing its ID and language.</p>', unsafe_allow_html=True)

center_cols = st.columns([1, 2, 1])
with center_cols[1]:
    
    video_id = st.text_input(
        "YouTube Video ID",
        placeholder="Enter the video id",
        help="Enter the video ID from the YouTube URL. For example, if the URL is 'https://www.youtube.com/watch?v=HAnw168huqA', the ID is 'HAnw168huqA'"
    )

    # Language selection
    language_options = {
        "English": "en",
        "Hindi": "hi",
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Italian": "it",
        "Portuguese": "pt",
        "Arabic": "ar",
        "Chinese": "zh",
        "Japanese": "ja",
        "Korean": "ko",
        "Russian": "ru"
    }

    selected_language = st.selectbox(
        "🌐 Language",
        options=list(language_options.keys()),
        index=0
    )
    language = language_options[selected_language]

    # Load video button
    if st.button("📥 Load Video & Initialize Chatbot", type="primary", use_container_width=True):
        if not video_id.strip():
            st.error("❌ Please enter a valid video ID!")
        else:
            with st.spinner("🔄 Fetching transcript and building chatbot..."):
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Step 1: Fetch transcript
                status_text.text("📋 Fetching video transcript...")
                progress_bar.progress(25)
                transcript = get_transcript(video_id.strip(), language.strip())

                if transcript:
                    progress_bar.progress(50)
                    status_text.text("✅ Transcript fetched successfully!")
                    time.sleep(0.5)

                    # Step 2: Build chatbot
                    status_text.text("🤖 Building RAG chatbot...")
                    progress_bar.progress(75)

                    try:
                        chatbot = load_chatbot(transcript)
                        progress_bar.progress(100)
                        status_text.text("🎉 Chatbot ready!")

                        # Store in session state
                        st.session_state.chatbot = chatbot
                        st.session_state.transcript = transcript
                        st.session_state.video_id = video_id.strip()
                        st.session_state.language = selected_language
                        st.session_state.chat_history = []

                        time.sleep(1)
                        progress_bar.empty()
                        status_text.empty()

                        st.success("🎉 Chatbot initialized successfully! You can now ask questions.")

                    except Exception as e:
                        st.error(f"❌ Error building chatbot: {str(e)}")
                        progress_bar.empty()
                        status_text.empty()
                else:
                    progress_bar.empty()
                    status_text.empty()
                    st.error("❌ Could not fetch transcript. Please check the video ID and try again.")

# Initialize session state
if 'chatbot' not in st.session_state:
    st.session_state.chatbot = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'clear_input' not in st.session_state:
    st.session_state.clear_input = False
if 'prefill_input' not in st.session_state:
    st.session_state.prefill_input = None

# Main chat interface
if st.session_state.chatbot:
    # Display current video info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**📽️ Video ID:** `{st.session_state.get('video_id', 'N/A')}`")
    with col2:
        st.markdown(f"**🌐 Language:** {st.session_state.get('language', 'N/A')}")
    
    # Transcript preview (collapsible)
    if st.session_state.transcript:
        with st.expander("📋 View Transcript Preview", expanded=False):
            preview_text = st.session_state.transcript[:500] + "..." if len(st.session_state.transcript) > 500 else st.session_state.transcript
            st.text_area("Transcript", preview_text, height=150, disabled=True)
    
    st.markdown("---")
    
    # Chat interface
    st.subheader("💬 Chat with the Video")
    
    # Apply any pending input state changes BEFORE creating the widget
    if st.session_state.clear_input:
        st.session_state.user_input = ""
        st.session_state.clear_input = False
    if st.session_state.prefill_input:
        st.session_state.user_input = st.session_state.prefill_input
        st.session_state.prefill_input = None

    # Chat input
    user_input = st.text_input(
        "Ask a question about the video:", 
        placeholder="e.g., What are the main topics discussed in this video?",
        key="user_input"
    )
    
    # Send button
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        send_button = st.button("📤 Send", type="primary")
    with col2:
        clear_button = st.button("🗑️ Clear Chat")
    
    # Handle clear chat
    if clear_button:
        st.session_state.chat_history = []
        st.rerun()
    
    # Handle user input
    if (send_button or user_input) and user_input.strip():
        with st.spinner("🤔 Thinking..."):
            try:
                response = st.session_state.chatbot.invoke(user_input.strip())
                
                # Add to chat history
                st.session_state.chat_history.append({
                    "user": user_input.strip(),
                    "bot": response,
                    "timestamp": time.strftime("%H:%M:%S")
                })
                
                # Schedule input clear on next run (avoid modifying widget key post-instantiation)
                st.session_state.clear_input = True
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error generating response: {str(e)}")
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("### 📝 Chat History")
        
        # Display messages in reverse order (newest first)
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.container():
                # User message
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 You ({chat['timestamp']}):</strong><br>
                    {chat['user']}
                </div>
                """, unsafe_allow_html=True)
                
                # Bot message
                st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>🤖 Assistant:</strong><br>
                    {chat['bot']}
                </div>
                """, unsafe_allow_html=True)
                
                if i < len(st.session_state.chat_history) - 1:
                    st.markdown("---")
    
    # Quick question suggestions
    # if not st.session_state.chat_history:
    #     st.markdown("### 💡 Quick Question Suggestions:")
        
    #     suggestions = [
    #         "What are the main topics discussed in this video?",
    #         "Can you summarize the key points?",
    #         "What are the benefits mentioned in the video?",
    #         "Are there any important tips or advice?",
    #         "What conclusions does the speaker draw?"
    #     ]
        
    #     cols = st.columns(2)
    #     for i, suggestion in enumerate(suggestions):
    #         with cols[i % 2]:
    #             if st.button(suggestion, key=f"suggestion_{i}"):
    #                 # Schedule prefill on next run (avoid modifying widget key post-instantiation)
    #                 st.session_state.prefill_input = suggestion
    #                 st.rerun()

