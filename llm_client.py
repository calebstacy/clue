"""
LLM client for generating responses.
Supports multiple providers: Ollama (local), Claude (Anthropic), and OpenAI.
"""

import ollama
from typing import Optional
import json
from datetime import datetime
from pathlib import Path

# Optional imports for API providers
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


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
        model: str = "llama3.2:3b",
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        """
        Initialize LLM client with specified provider.

        Args:
            provider: "ollama", "claude", or "openai"
            model: Model name (e.g., "llama3.2:3b", "claude-3-5-sonnet-20241022", "gpt-4")
            api_base_url: Base URL for OpenAI-compatible API
            api_key: API key for OpenAI-compatible API
            anthropic_api_key: API key for Claude
        """
        self.provider = provider.lower()
        self.model = model

        # Initialize provider-specific clients
        if self.provider == "ollama":
            try:
                ollama.list()
                print(f"Ollama connected, using model: {model}")
            except Exception as e:
                print(f"Ollama not running? Error: {e}")
                print("Start Ollama with: ollama serve")
                print(f"Then pull model: ollama pull {model}")

        elif self.provider == "claude":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            if not anthropic_api_key:
                raise ValueError("anthropic_api_key required for Claude provider")
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            print(f"Claude API initialized, using model: {model}")

        elif self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            if not api_key:
                raise ValueError("api_key required for OpenAI provider")
            self.openai_client = openai.OpenAI(
                api_key=api_key,
                base_url=api_base_url
            )
            print(f"OpenAI API initialized, using model: {model}")

        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'ollama', 'claude', or 'openai'")

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

        system = """Create brief meeting notes. Be extremely concise.

Format:
<b>Topic:</b> One line summary

<b>Key Points</b>
• Point 1
• Point 2
• Point 3

<b>Action Items</b> (only if mentioned)
• Who: What

Rules: Max 5 bullet points total. No fluff. HTML format only."""

        user_msg = ""
        if context:
            user_msg += f"CONTEXT: {context}\n\n"
        user_msg += f"TRANSCRIPT:\n{transcript}\n\n---\nCreate meeting notes:"

        return system, user_msg

    def _build_question_prompt(self, transcript: str, question: str, context: Optional[str] = None) -> tuple:
        """Build prompt for answering questions about the conversation."""

        system = """Answer questions about this conversation. Be brief and direct.
Only use info from the transcript. Say "not mentioned" if it wasn't discussed.
1-3 sentences max. Use <b>bold</b> for key terms if needed."""

        user_msg = ""
        if context:
            user_msg += f"CONTEXT: {context}\n\n"
        user_msg += f"TRANSCRIPT:\n{transcript}\n\n---\nQuestion: {question}"

        return system, user_msg

    def get_suggestion(
        self,
        transcript: str,
        context: Optional[str] = None,
        max_tokens: int = 150
    ) -> str:
        """
        Get a response suggestion based on the transcript.

        Args:
            transcript: The conversation transcript
            context: Optional additional context (notes, docs, etc.)
            max_tokens: Maximum response length

        Returns:
            Suggested response text
        """
        if not transcript.strip():
            return "No conversation detected yet..."

        system, user_msg = self._build_prompt(transcript, context)
        result = self._query_llm(system, user_msg, max_tokens)

        # Log the suggestion
        get_logger().log_suggestion(transcript, result, self.model)

        return result

    def get_interpretation(
        self,
        transcript: str,
        context: Optional[str] = None,
        max_tokens: int = 500
    ) -> str:
        """
        Get a live interpretation/summary of the transcript.

        Args:
            transcript: The conversation transcript
            context: Optional context about the conversation
            max_tokens: Maximum response length

        Returns:
            HTML-formatted interpretation summary
        """
        if not transcript.strip():
            return "Waiting for conversation..."

        system, user_msg = self._build_interpretation_prompt(transcript, context)
        return self._query_llm(system, user_msg, max_tokens)

    def ask_question(
        self,
        transcript: str,
        question: str,
        context: Optional[str] = None,
        max_tokens: int = 300
    ) -> str:
        """
        Answer a question about the conversation.

        Args:
            transcript: The conversation transcript
            question: The user's question
            context: Optional context about the conversation
            max_tokens: Maximum response length

        Returns:
            Answer to the question
        """
        if not transcript.strip():
            return "No conversation to reference yet."

        if not question.strip():
            return "Please enter a question."

        system, user_msg = self._build_question_prompt(transcript, question, context)
        return self._query_llm(system, user_msg, max_tokens)

    def _query_llm(self, system: str, user_msg: str, max_tokens: int) -> str:
        """Query the LLM based on configured provider."""
        try:
            if self.provider == "ollama":
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

            elif self.provider == "claude":
                response = self.anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    system=system,
                    messages=[
                        {"role": "user", "content": user_msg}
                    ]
                )
                return response.content[0].text.strip()

            elif self.provider == "openai":
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg}
                    ]
                )
                return response.choices[0].message.content.strip()

        except Exception as e:
            return f"{self.provider.capitalize()} error: {e}"


# Quick test
if __name__ == "__main__":
    client = LLMClient(model="llama3.1:8b")

    test_transcript = """
    Other person: Hi, thanks for taking the time to meet with me today.
    Me: Of course, happy to chat.
    Other person: So I wanted to discuss the proposal you sent over.
    The pricing looks good but I have some questions about the timeline.
    Can you walk me through that?
    """

    suggestion = client.get_suggestion(test_transcript)
    print(f"Suggestion: {suggestion}")
