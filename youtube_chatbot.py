def get_transcript(video_id, language='en'):
    import subprocess
    import sys
    import yt_dlp
    import requests
    import json
    import re

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"], stdout=subprocess.DEVNULL)
    except Exception as e:
        print(f"❌ yt-dlp install failed: {e}")
        return None

    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': [language],
        'skip_download': True,
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    except Exception as e:
        print(f"❌ Error fetching info: {e}")
        return None

    # Try manual first, fallback to auto
    caption_info = None
    source = ""

    if 'subtitles' in info and language in info['subtitles']:
        caption_info = info['subtitles'][language][0]
        source = "manual"
    elif 'automatic_captions' in info and language in info['automatic_captions']:
        caption_info = info['automatic_captions'][language][0]
        source = "auto"
    else:
        print(f"⚠️ No subtitles found for language '{language}'")
        return None

    try:
        captions_url = caption_info['url']
        response = requests.get(captions_url)

        if response.status_code != 200:
            print(f"❌ Failed to download caption file: {response.status_code}")
            return None

        content_type = response.headers.get("Content-Type", "")
        print(f"ℹ️ Fetched {source} subtitles with content-type: {content_type}")

        # Case 1: JSON subtitles (used in both manual and auto captions)
        if "json" in content_type:
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = json.loads(response.text)

            transcript_lines = []
            for event in data.get('events', []):
                for seg in event.get('segs', []):
                    text = seg.get('utf8', '').strip()
                    if text:
                        transcript_lines.append(text)
            print("✅ Auto-generated captions parsed.")
            return " ".join(transcript_lines)

        # Case 2: VTT subtitles (used in both manual and auto)
        elif captions_url.endswith(".vtt") or "text/vtt" in content_type:
            lines = response.text.splitlines()
            transcript_lines = [
                line.strip() for line in lines
                if "-->" not in line
                and line.strip().lower() != "webvtt"
                and not line.strip().lower().startswith("kind:")
                and not line.strip().lower().startswith("language:")
                and line.strip() != ""
            ]
            print(f"✅ {'Manual' if source == 'manual' else 'Likely Manual'} captions parsed from VTT.")
            return " ".join(transcript_lines)

        # ✅ Case 3: M3U8 playlist format (used for segmented auto captions)
        elif "mpegurl" in content_type or captions_url.endswith(".m3u8"):
            print("ℹ️ M3U8 playlist detected, fetching segments...")
            segment_urls = []
            for line in response.text.splitlines():
                line = line.strip()
                if line.startswith("http"):
                    segment_urls.append(line)

            transcript_lines = []
            for segment_url in segment_urls:
                seg_resp = requests.get(segment_url)
                if seg_resp.status_code == 200:
                    lines = seg_resp.text.splitlines()
                    for line in lines:
                        if "-->" not in line and line.strip() and not line.strip().lower().startswith(("kind:", "language:", "webvtt")):
                            transcript_lines.append(line.strip())
                else:
                    print(f"⚠️ Failed to fetch segment: {segment_url}")

            print(f"✅ Combined {len(segment_urls)} segments.")
            return " ".join(transcript_lines)

        else:
            print("⚠️ Unknown caption format. Returning raw text.")
            return response.text

    except Exception as e:
        print(f"❌ Error during caption processing: {e}")
        return None

# Removed CLI prompt and top-level execution to make this module import-safe.


def load_chatbot(transcript):
    # Split transcript into chunks
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=200
    )
    chunks = splitter.create_documents([transcript])

    # Build vector store
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain.vectorstores import FAISS
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = FAISS.from_documents(chunks, embeddings)
    retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 3})

    # LLM
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    from langchain_groq import ChatGroq
    from dotenv import load_dotenv
    import os
    load_dotenv()
    llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile"
    )

    # Prompt and chain
    from langchain.prompts import PromptTemplate
    prompt = PromptTemplate(
        template='''You are YouTube Chatbot, a polite and helpful assistant developed by Waleed Ali.
      Only answer questions related to the video's content. If a question is irrelevant, gently reply: "I'm YouTube Chatbot, and I can only help with the video context."
      Stay respectful, calm, and to the point — no aggression, even if the user misbehaves.
      Use bullet points for pros, cons, benefits, or similar questions.
      If the video doesn't cover the topic, say: "I didn't find any information about this topic in the video."
    Context:\n{context}\n\nQuestion: {question}''',
        input_variables=["context", "question"]
    )

    from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
    from langchain_core.output_parsers import StrOutputParser

    def format_docs(docs):
        return "\n\n".join([doc.page_content for doc in docs])

    parallel_chain = RunnableParallel({
        "context": retriever | RunnableLambda(format_docs),
        "question": RunnablePassthrough()
    })

    parser = StrOutputParser()
    final_chain = parallel_chain | prompt | llm | parser

    # Return the chain so Streamlit can call .invoke(question)
    return final_chain