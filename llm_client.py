"""
LLM client for generating responses.
Local-only version using Ollama.
"""

import ollama
from typing import Optional
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
        model: str = "llama3.1:8b",  # Good balance of speed/quality
    ):
        """
        Initialize LLM client with Ollama.

        Args:
            model: Ollama model name (e.g., "llama3.1:8b", "mistral", "phi3")
        """
        self.model = model

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
        result = self._query_ollama(system, user_msg, max_tokens)

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
        return self._query_ollama(system, user_msg, max_tokens)

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
        return self._query_ollama(system, user_msg, max_tokens)

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
