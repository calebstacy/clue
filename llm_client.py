"""
LLM client for generating responses.
Supports Ollama (local), Claude API, and OpenAI-compatible endpoints.
"""

import ollama
import requests
from typing import Optional
import os
import json
from datetime import datetime
from pathlib import Path


class SessionLogger:
    """Logs transcripts and suggestions to a file."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create session file with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"session_{timestamp}.jsonl"
        self.session_start = datetime.now().isoformat()

        # Write session header
        self._write_entry({
            "type": "session_start",
            "timestamp": self.session_start
        })

    def _write_entry(self, entry: dict):
        """Append entry to log file."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_transcript(self, text: str):
        """Log a transcript chunk."""
        self._write_entry({
            "type": "transcript",
            "timestamp": datetime.now().isoformat(),
            "text": text
        })

    def log_suggestion(self, transcript: str, suggestion: str, model: str):
        """Log a suggestion request and response."""
        self._write_entry({
            "type": "suggestion",
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "transcript_used": transcript,
            "suggestion": suggestion
        })


# Global logger instance
_logger: Optional[SessionLogger] = None

def get_logger() -> SessionLogger:
    """Get or create the session logger."""
    global _logger
    if _logger is None:
        _logger = SessionLogger()
    return _logger


class LLMClient:
    def __init__(
        self,
        provider: str = "ollama",
        model: str = "llama3.1:8b",  # Good balance of speed/quality
        anthropic_api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize LLM client.

        Args:
            provider: "ollama", "claude", or "openai" (for OpenAI-compatible APIs)
            model: Model name
            anthropic_api_key: API key for Claude (optional)
            api_base_url: Base URL for OpenAI-compatible API (e.g., your internal endpoint)
            api_key: API key for OpenAI-compatible API
        """
        self.provider = provider
        self.model = model
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.api_base_url = api_base_url or os.getenv("OPENAI_API_BASE")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if provider == "claude" and not self.anthropic_api_key:
            print("Warning: No Anthropic API key found, falling back to Ollama")
            self.provider = "ollama"

        if provider == "openai":
            if not self.api_base_url:
                print("Warning: No API base URL set. Use --api-url or OPENAI_API_BASE env var")
            else:
                print(f"Using OpenAI-compatible API at: {self.api_base_url}")
                print(f"Model: {model}")

        if provider == "ollama":
            # Test Ollama connection
            try:
                ollama.list()
                print(f"Ollama connected, using model: {model}")
            except Exception as e:
                print(f"Ollama not running? Error: {e}")
                print("Start Ollama with: ollama serve")
                print(f"Then pull model: ollama pull {model}")
                
    def _build_prompt(self, transcript: str, user_context: Optional[str] = None) -> tuple:
        """Build the prompt for the LLM."""

        system = """You are a real-time conversation assistant helping the user during calls, meetings, or while watching content. Based on the transcript provided, suggest what the user could say or comment on.

Your job is to help - this could be:
- Suggesting a response in a meeting or call
- Commenting on entertainment content (TV, movies, podcasts)
- Helping formulate thoughts on what's being discussed

Rules:
- Be concise and natural (1-2 sentences)
- Match the tone - professional for work, casual for casual content
- If it's media/entertainment, offer an interesting observation or reaction
- Never refuse - always provide something helpful or insightful

Respond with ONLY the suggested text, no explanations."""

        user_msg = f"CONVERSATION TRANSCRIPT:\n{transcript}\n\n"

        if user_context:
            user_msg += f"ADDITIONAL CONTEXT:\n{user_context}\n\n"

        user_msg += "What should I say next?"

        return system, user_msg

    def _build_interpretation_prompt(self, transcript: str, context: Optional[str] = None) -> tuple:
        """Build prompt for meeting notes style summary."""

        system = """You are creating professional meeting notes from a live conversation. Write in a clean, structured format that someone could use as actual meeting documentation.

Structure your notes like this:

<b>Overview</b>
One sentence describing what this conversation is about.

<b>Key Points</b>
• Main topic or decision discussed
• Another important point
• Significant information shared

<b>Action Items</b> (if any)
• [Person]: Task or commitment they made
• [Person]: Another action item

<b>Open Questions</b> (if any)
• Questions raised but not answered
• Topics to follow up on

Guidelines:
- Write in third person past tense ("discussed", "decided", "mentioned")
- Focus on substance, not play-by-play
- Combine related points rather than listing everything said
- Use names when you hear them, otherwise use roles
- For media/entertainment: focus on main topics, interesting points, key moments
- Keep it scannable - someone should get the gist in 10 seconds
- Update the overview as you learn more about the conversation

Format using HTML: <b>bold</b> for headers, • for bullets, <br> for line breaks."""

        user_msg = ""
        if context:
            user_msg += f"CONTEXT: {context}\n\n"
        user_msg += f"TRANSCRIPT:\n{transcript}\n\n---\nCreate meeting notes:"

        return system, user_msg

    def _build_question_prompt(self, transcript: str, question: str, context: Optional[str] = None) -> tuple:
        """Build prompt for answering questions about the conversation."""

        system = """You are a helpful assistant that answers questions about a conversation transcript. The user may have missed something or wants clarification about what was discussed.

Guidelines:
- Answer based ONLY on what's in the transcript
- If the information isn't in the transcript, say so
- Be specific - quote relevant parts when helpful
- If the question is about something that wasn't discussed, let them know
- Keep answers concise but complete

Format: Use plain text for simple answers. For longer answers, use HTML:
- <b>bold</b> for emphasis
- • for bullet points if listing multiple items"""

        user_msg = ""
        if context:
            user_msg += f"CONTEXT: {context}\n\n"
        user_msg += f"TRANSCRIPT:\n{transcript}\n\n---\nQuestion: {question}"

        return system, user_msg
        
    def get_suggestion(
        self,
        transcript: str,
        context: Optional[str] = None,
        files: list = None,
        max_tokens: int = 150
    ) -> str:
        """
        Get a response suggestion based on the transcript.

        Args:
            transcript: The conversation transcript
            context: Optional additional context (notes, docs, etc.)
            files: Optional list of (path, type, base64_data) for documents/images
            max_tokens: Maximum response length

        Returns:
            Suggested response text
        """
        if not transcript.strip():
            return "No conversation detected yet..."

        system, user_msg = self._build_prompt(transcript, context)

        if self.provider == "ollama":
            result = self._query_ollama(system, user_msg, max_tokens)
        elif self.provider == "openai":
            result = self._query_openai(system, user_msg, max_tokens)
        else:
            result = self._query_claude(system, user_msg, max_tokens, files=files)

        # Log the suggestion
        get_logger().log_suggestion(transcript, result, self.model)

        return result

    def get_interpretation(
        self,
        transcript: str,
        context: Optional[str] = None,
        files: list = None,
        max_tokens: int = 500
    ) -> str:
        """
        Get a live interpretation/summary of the transcript.

        Args:
            transcript: The conversation transcript
            context: Optional context about the conversation
            files: Optional list of (path, type, base64_data) for documents/images
            max_tokens: Maximum response length

        Returns:
            HTML-formatted interpretation summary
        """
        if not transcript.strip():
            return "Waiting for conversation..."

        system, user_msg = self._build_interpretation_prompt(transcript, context)

        if self.provider == "ollama":
            result = self._query_ollama(system, user_msg, max_tokens)
        elif self.provider == "openai":
            result = self._query_openai(system, user_msg, max_tokens)
        else:
            result = self._query_claude(system, user_msg, max_tokens, files=files)

        return result

    def ask_question(
        self,
        transcript: str,
        question: str,
        context: Optional[str] = None,
        files: list = None,
        max_tokens: int = 300
    ) -> str:
        """
        Answer a question about the conversation.

        Args:
            transcript: The conversation transcript
            question: The user's question
            context: Optional context about the conversation
            files: Optional list of (path, type, base64_data) for documents/images
            max_tokens: Maximum response length

        Returns:
            Answer to the question
        """
        if not transcript.strip():
            return "No conversation to reference yet."

        if not question.strip():
            return "Please enter a question."

        system, user_msg = self._build_question_prompt(transcript, question, context)

        if self.provider == "ollama":
            result = self._query_ollama(system, user_msg, max_tokens)
        elif self.provider == "openai":
            result = self._query_openai(system, user_msg, max_tokens)
        else:
            result = self._query_claude(system, user_msg, max_tokens, files=files)

        return result

    def _query_ollama(self, system: str, user_msg: str, max_tokens: int) -> str:
        """Query local Ollama instance."""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg}
                ],
                options={
                    "num_predict": max_tokens,
                    "temperature": 0.7,
                }
            )
            return response["message"]["content"].strip()
            
        except Exception as e:
            return f"Ollama error: {e}"
            
    def _query_claude(self, system: str, user_msg: str, max_tokens: int, files: list = None) -> str:
        """
        Query Claude API.

        Args:
            system: System prompt
            user_msg: User message
            max_tokens: Max response tokens
            files: Optional list of (path, type, base64_data) tuples for images/PDFs
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.anthropic_api_key)

            # Build content array (supports multimodal)
            content = []

            # Add any files/images first
            if files:
                for file_path, file_type, file_data in files:
                    if file_type == 'image':
                        # Determine media type from extension
                        ext = os.path.splitext(file_path)[1].lower()
                        media_types = {
                            '.png': 'image/png',
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.gif': 'image/gif',
                            '.webp': 'image/webp',
                            '.bmp': 'image/bmp'
                        }
                        media_type = media_types.get(ext, 'image/png')

                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": file_data
                            }
                        })
                    elif file_type == 'pdf':
                        # Claude supports PDF via document type
                        content.append({
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": file_data
                            }
                        })
                    elif file_type == 'text':
                        # Add text content inline
                        file_name = os.path.basename(file_path)
                        content.append({
                            "type": "text",
                            "text": f"[Content from {file_name}]:\n{file_data}\n\n"
                        })

            # Add the main user message
            content.append({"type": "text", "text": user_msg})

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system,
                messages=[
                    {"role": "user", "content": content}
                ]
            )
            return response.content[0].text.strip()

        except ImportError:
            return "anthropic package not installed. Run: pip install anthropic"
        except Exception as e:
            return f"Claude API error: {e}"

    def _query_openai(self, system: str, user_msg: str, max_tokens: int) -> str:
        """Query OpenAI-compatible API (works with internal endpoints)."""
        try:
            url = f"{self.api_base_url.rstrip('/')}/chat/completions"

            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            return "API timeout - try again"
        except requests.exceptions.RequestException as e:
            return f"API error: {e}"
        except (KeyError, IndexError) as e:
            return f"Unexpected API response format: {e}"


# Quick test
if __name__ == "__main__":
    client = LLMClient(provider="ollama", model="llama3.1:8b")
    
    test_transcript = """
    Other person: Hi, thanks for taking the time to meet with me today.
    Me: Of course, happy to chat.
    Other person: So I wanted to discuss the proposal you sent over. 
    The pricing looks good but I have some questions about the timeline.
    Can you walk me through that?
    """
    
    suggestion = client.get_suggestion(test_transcript)
    print(f"Suggestion: {suggestion}")
