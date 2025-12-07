"""
LocalCluely - Cluely-style floating overlay UI.
Designed to match the polished aesthetic of Cluely's meeting intelligence overlay.
"""

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QPushButton, QFrame, QScrollArea,
    QLineEdit, QTextEdit, QFileDialog, QSystemTrayIcon, QMenu,
    QStackedWidget, QGraphicsOpacityEffect, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation,
    QEasingCurve, QPoint, QSize, QRect
)
from PyQt6.QtGui import (
    QFont, QIcon, QPixmap, QColor, QPainter, QTextCursor,
    QLinearGradient, QPen, QPainterPath, QRegion, QBrush
)
import sys
import os
import base64
import math
import random
from datetime import datetime


class SignalBridge(QObject):
    """Bridge for thread-safe UI updates."""
    update_suggestion = pyqtSignal(str)
    update_transcript = pyqtSignal(str)
    update_notes = pyqtSignal(str)
    update_answer = pyqtSignal(str)
    show_overlay = pyqtSignal()
    hide_overlay = pyqtSignal()
    request_suggestion = pyqtSignal()
    request_clear = pyqtSignal()
    request_quit = pyqtSignal()
    context_changed = pyqtSignal(str)
    ask_question = pyqtSignal(str)
    file_loaded = pyqtSignal(str, str, str)


# Cluely-inspired color palette - darker, more neutral
COLORS = {
    'bg_overlay': '#1a1a1e',
    'bg_card': '#242428',
    'bg_card_solid': '#1e1e22',
    'bg_input': '#2d2d32',
    'bg_hover': '#38383e',
    'border': '#3a3a40',
    'border_light': '#4a4a52',
    'text_primary': '#ffffff',
    'text_secondary': 'rgba(255, 255, 255, 0.7)',
    'text_muted': 'rgba(255, 255, 255, 0.45)',
    'accent': '#7c5cff',
    'accent_light': '#9d85ff',
    'accent_dim': 'rgba(124, 92, 255, 0.2)',
    'success': '#34d399',
    'success_dim': 'rgba(52, 211, 153, 0.15)',
    'red': '#f87171',
}


class AudioIndicator(QWidget):
    """Compact audio level indicator bars."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 16)
        self.bars = [0.4, 0.7, 0.5]
        self.target_bars = [0.4, 0.7, 0.5]
        self.is_active = True

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(80)

    def _animate(self):
        if self.is_active:
            for i in range(len(self.target_bars)):
                if random.random() < 0.4:
                    self.target_bars[i] = random.uniform(0.3, 1.0)
        else:
            self.target_bars = [0.2, 0.2, 0.2]

        for i in range(len(self.bars)):
            self.bars[i] += (self.target_bars[i] - self.bars[i]) * 0.35

        self.update()

    def set_active(self, active: bool):
        self.is_active = active

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_width = 3
        gap = 3
        max_height = 12

        for i, height_pct in enumerate(self.bars):
            x = i * (bar_width + gap)
            bar_height = max(2, int(height_pct * max_height))
            y = (self.height() - bar_height) // 2

            color = QColor(COLORS['accent_light']) if self.is_active else QColor(COLORS['text_muted'])
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)

            path = QPainterPath()
            path.addRoundedRect(float(x), float(y), float(bar_width), float(bar_height), 1.5, 1.5)
            painter.drawPath(path)


class ControlBar(QFrame):
    """Floating control bar at the top - Cluely style."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("controlBar")
        self.setFixedHeight(44)
        self.setMinimumHeight(44)

        self.start_time = datetime.now()
        self.is_recording = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Pause/Play button
        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setObjectName("iconBtn")
        self.pause_btn.setFixedSize(28, 28)
        self.pause_btn.clicked.connect(self._toggle_recording)
        layout.addWidget(self.pause_btn)

        # Audio indicator
        self.audio_indicator = AudioIndicator()
        layout.addWidget(self.audio_indicator)

        # Timer
        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("timerLabel")
        layout.addWidget(self.timer_label)

        layout.addStretch()

        # Ask AI label
        ask_label = QLabel("Ask AI")
        ask_label.setObjectName("askLabel")
        layout.addWidget(ask_label)

        # Keyboard shortcut hint
        shortcut = QLabel("⌘ ↵")
        shortcut.setObjectName("shortcutHint")
        layout.addWidget(shortcut)

        layout.addSpacing(8)

        # Show/Hide toggle
        self.toggle_label = QLabel("Show/Hide")
        self.toggle_label.setObjectName("toggleLabel")
        layout.addWidget(self.toggle_label)

        shortcut2 = QLabel("⌘ \\")
        shortcut2.setObjectName("shortcutHint")
        layout.addWidget(shortcut2)

        # Timer update
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(1000)

    def _update_timer(self):
        if self.is_recording:
            elapsed = datetime.now() - self.start_time
            mins = int(elapsed.total_seconds() // 60)
            secs = int(elapsed.total_seconds() % 60)
            self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def _toggle_recording(self):
        self.is_recording = not self.is_recording
        self.pause_btn.setText("▶" if not self.is_recording else "⏸")
        self.audio_indicator.set_active(self.is_recording)

    def reset_timer(self):
        self.start_time = datetime.now()
        self.timer_label.setText("00:00")


class ActionButton(QPushButton):
    """Cluely-style action button with icon."""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("actionBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 14, 8)
        layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setObjectName("actionIcon")
        layout.addWidget(icon_label)

        text_label = QLabel(text)
        text_label.setObjectName("actionText")
        layout.addWidget(text_label)


class InsightsPanel(QFrame):
    """The main Live Insights panel - Cluely style floating card."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("insightsPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("panelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(10)

        # Sparkle icon and title
        sparkle = QLabel("✨")
        sparkle.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(sparkle)

        title = QLabel("Live insights")
        title.setObjectName("panelTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Show transcript button
        transcript_btn = QPushButton("A≡  Show transcript")
        transcript_btn.setObjectName("headerBtn")
        transcript_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(transcript_btn)

        # Copy button
        copy_btn = QPushButton("⧉")
        copy_btn.setObjectName("iconBtnSmall")
        copy_btn.setFixedSize(24, 24)
        header_layout.addWidget(copy_btn)

        layout.addWidget(header)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {COLORS['border']};")
        layout.addWidget(divider)

        # Content area
        content = QFrame()
        content.setObjectName("panelContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 12)
        content_layout.setSpacing(12)

        # Topic title
        self.topic_label = QLabel("Discussion topic")
        self.topic_label.setObjectName("topicLabel")
        content_layout.addWidget(self.topic_label)

        # Insights text
        self.insights_text = QLabel()
        self.insights_text.setObjectName("insightsText")
        self.insights_text.setWordWrap(True)
        self.insights_text.setTextFormat(Qt.TextFormat.RichText)
        self.insights_text.setText(
            "Waiting for conversation to begin...<br><br>"
            "<span style='color: rgba(255,255,255,0.4);'>Insights will appear here as the meeting progresses.</span>"
        )
        content_layout.addWidget(self.insights_text)

        content_layout.addStretch()

        # Actions section
        actions_label = QLabel("Actions")
        actions_label.setObjectName("actionsLabel")
        content_layout.addWidget(actions_label)

        # Action buttons
        self.action_buttons_layout = QVBoxLayout()
        self.action_buttons_layout.setSpacing(6)
        content_layout.addLayout(self.action_buttons_layout)

        layout.addWidget(content, 1)

    def set_topic(self, topic: str):
        self.topic_label.setText(topic)

    def set_insights(self, text: str):
        formatted = text.replace('\n', '<br>')
        self.insights_text.setText(formatted)

    def clear_actions(self):
        while self.action_buttons_layout.count():
            item = self.action_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_action(self, icon: str, text: str, callback=None):
        btn = QPushButton()
        btn.setObjectName("actionBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setText(f"{icon}  {text}")
        if callback:
            btn.clicked.connect(callback)
        self.action_buttons_layout.addWidget(btn)
        return btn


class ResponsePanel(QFrame):
    """AI Response panel that appears alongside insights."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("responsePanel")
        self.setFixedWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("panelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 12, 12)
        header_layout.setSpacing(10)

        title = QLabel("AI response")
        title.setObjectName("responseTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Web search indicator
        self.web_search = QLabel("🌐 Search the web for informati...")
        self.web_search.setObjectName("webSearchHint")
        self.web_search.hide()
        header_layout.addWidget(self.web_search)

        # Copy button
        copy_btn = QPushButton("⧉")
        copy_btn.setObjectName("iconBtnSmall")
        copy_btn.setFixedSize(24, 24)
        header_layout.addWidget(copy_btn)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setObjectName("iconBtnSmall")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {COLORS['border']};")
        layout.addWidget(divider)

        # Content
        content = QFrame()
        content.setObjectName("panelContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)

        self.response_text = QLabel()
        self.response_text.setObjectName("responseText")
        self.response_text.setWordWrap(True)
        self.response_text.setTextFormat(Qt.TextFormat.RichText)
        self.response_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.addWidget(self.response_text, 1)

        layout.addWidget(content, 1)

    def set_response(self, text: str):
        formatted = text.replace('\n', '<br>')
        self.response_text.setText(formatted)
        self.show()

    def show_web_search(self, visible: bool = True):
        self.web_search.setVisible(visible)


class ChatPanel(QFrame):
    """Chat interface panel."""

    ask_question = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("panelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Chat")
        title.setObjectName("panelTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        layout.addWidget(header)

        # Messages area
        self.scroll = QScrollArea()
        self.scroll.setObjectName("chatScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(16, 16, 16, 16)
        self.messages_layout.setSpacing(12)
        self.messages_layout.addStretch()

        self.scroll.setWidget(self.messages_container)
        layout.addWidget(self.scroll, 1)

        # Input area
        input_container = QFrame()
        input_container.setObjectName("chatInputContainer")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 10, 10, 10)
        input_layout.setSpacing(10)

        self.input = QLineEdit()
        self.input.setObjectName("chatInput")
        self.input.setPlaceholderText("Ask about the conversation...")
        self.input.returnPressed.connect(self._send)
        input_layout.addWidget(self.input)

        send_btn = QPushButton("Send")
        send_btn.setObjectName("sendBtn")
        send_btn.clicked.connect(self._send)
        input_layout.addWidget(send_btn)

        layout.addWidget(input_container)

        # Quick actions
        quick_actions = QFrame()
        quick_actions.setObjectName("quickActions")
        quick_layout = QHBoxLayout(quick_actions)
        quick_layout.setContentsMargins(12, 8, 12, 12)
        quick_layout.setSpacing(8)

        suggest_btn = QPushButton("What should I say?")
        suggest_btn.setObjectName("quickBtn")
        suggest_btn.clicked.connect(lambda: self._quick("What should I say next?"))
        quick_layout.addWidget(suggest_btn)

        summarize_btn = QPushButton("Summarize")
        summarize_btn.setObjectName("quickBtn")
        summarize_btn.clicked.connect(lambda: self._quick("Summarize the conversation so far."))
        quick_layout.addWidget(summarize_btn)

        quick_layout.addStretch()

        layout.addWidget(quick_actions)

    def _send(self):
        text = self.input.text().strip()
        if text:
            self.add_message(text, is_user=True)
            self.input.clear()
            self.ask_question.emit(text)

    def _quick(self, text: str):
        self.add_message(text, is_user=True)
        self.ask_question.emit(text)

    def add_message(self, text: str, is_user: bool = False):
        msg = QFrame()
        msg.setObjectName("userMsg" if is_user else "aiMsg")

        msg_layout = QVBoxLayout(msg)
        msg_layout.setContentsMargins(12, 10, 12, 10)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setObjectName("msgText")
        msg_layout.addWidget(label)

        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg)

        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    def clear(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class TranscriptPanel(QFrame):
    """Transcript display panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("transcriptPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("panelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Transcript")
        title.setObjectName("panelTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        live_badge = QLabel("● LIVE")
        live_badge.setObjectName("liveBadge")
        header_layout.addWidget(live_badge)

        layout.addWidget(header)

        # Content
        content = QFrame()
        content.setObjectName("panelContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)

        self.text = QTextEdit()
        self.text.setObjectName("transcriptText")
        self.text.setReadOnly(True)
        self.text.setPlaceholderText("Transcript will appear here as people speak...")
        content_layout.addWidget(self.text)

        layout.addWidget(content, 1)

    def append(self, text: str):
        if text.strip():
            cursor = self.text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            if self.text.toPlainText():
                cursor.insertText(" ")
            cursor.insertText(text)
            self.text.setTextCursor(cursor)
            self.text.ensureCursorVisible()

    def clear(self):
        self.text.clear()


class OverlayWindow(QWidget):
    """Main overlay window - Cluely-style floating UI."""

    def __init__(self):
        super().__init__()

        self.signals = SignalBridge()
        self.signals.update_suggestion.connect(self._add_suggestion)
        self.signals.update_transcript.connect(self._append_transcript)
        self.signals.update_notes.connect(self._set_notes)
        self.signals.update_answer.connect(self._add_answer)
        self.signals.show_overlay.connect(self._show_window)
        self.signals.hide_overlay.connect(self._minimize_to_tray)

        self._tray_icon = None
        self._loaded_files = []
        self._current_view = "insights"
        self._context = ""
        self._drag_pos = None

        self._setup_ui()
        self._setup_tray_icon()
        self._apply_styles()

    def _setup_ui(self):
        """Set up the floating overlay UI."""
        self.setWindowTitle("LocalCluely")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Size for the overlay
        self.setMinimumSize(440, 520)
        self.resize(460, 600)

        # Main layout - more top padding to prevent clipping
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Control bar
        self.control_bar = ControlBar()
        main_layout.addWidget(self.control_bar)

        # Content stack
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentStack")

        # Insights panel (main view)
        self.insights_panel = InsightsPanel()
        self.insights_panel.add_action("📋", "Define key topics", lambda: self._quick_action("define"))
        self.insights_panel.add_action("🌐", "Search the web for information", lambda: self._quick_action("search"))
        self.insights_panel.add_action("💬", "Suggest follow-up questions", lambda: self._quick_action("followup"))
        self.insights_panel.add_action("✨", "Give me helpful information", lambda: self._quick_action("help"))
        self.stack.addWidget(self.insights_panel)

        # Chat panel
        self.chat_panel = ChatPanel()
        self.chat_panel.ask_question.connect(lambda q: self.signals.ask_question.emit(q))
        self.stack.addWidget(self.chat_panel)

        # Transcript panel
        self.transcript_panel = TranscriptPanel()
        self.stack.addWidget(self.transcript_panel)

        main_layout.addWidget(self.stack, 1)

        # Response panel (slides in from right when needed)
        self.response_panel = ResponsePanel(self)
        self.response_panel.hide()

        # Navigation tabs at bottom
        nav = QFrame()
        nav.setObjectName("navBar")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(4)

        self.tab_insights = QPushButton("Insights")
        self.tab_insights.setObjectName("navTab")
        self.tab_insights.setCheckable(True)
        self.tab_insights.setChecked(True)
        self.tab_insights.clicked.connect(lambda: self._switch_view("insights"))
        nav_layout.addWidget(self.tab_insights)

        self.tab_chat = QPushButton("Chat")
        self.tab_chat.setObjectName("navTab")
        self.tab_chat.setCheckable(True)
        self.tab_chat.clicked.connect(lambda: self._switch_view("chat"))
        nav_layout.addWidget(self.tab_chat)

        self.tab_transcript = QPushButton("Transcript")
        self.tab_transcript.setObjectName("navTab")
        self.tab_transcript.setCheckable(True)
        self.tab_transcript.clicked.connect(lambda: self._switch_view("transcript"))
        nav_layout.addWidget(self.tab_transcript)

        main_layout.addWidget(nav)

    def _apply_styles(self):
        """Apply Cluely-style stylesheet."""
        self.setStyleSheet(f"""
            QWidget {{
                font-family: -apple-system, 'SF Pro Display', 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}

            #controlBar {{
                background: {COLORS['bg_card']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}

            #iconBtn {{
                background: transparent;
                border: none;
                border-radius: 6px;
                color: {COLORS['text_primary']};
                font-size: 14px;
            }}

            #iconBtn:hover {{
                background: {COLORS['bg_hover']};
            }}

            #timerLabel {{
                font-size: 14px;
                font-weight: 500;
                color: {COLORS['text_primary']};
                font-variant-numeric: tabular-nums;
            }}

            #askLabel {{
                font-size: 12px;
                color: {COLORS['text_secondary']};
            }}

            #shortcutHint {{
                font-size: 11px;
                color: {COLORS['text_muted']};
                background: {COLORS['bg_input']};
                padding: 2px 6px;
                border-radius: 4px;
            }}

            #toggleLabel {{
                font-size: 12px;
                color: {COLORS['text_secondary']};
            }}

            #insightsPanel, #chatPanel, #transcriptPanel, #responsePanel {{
                background: {COLORS['bg_card']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}

            #panelHeader {{
                background: transparent;
            }}

            #panelTitle {{
                font-size: 14px;
                font-weight: 600;
                color: {COLORS['text_primary']};
            }}

            #responseTitle {{
                font-size: 14px;
                font-weight: 600;
                color: {COLORS['accent_light']};
            }}

            #headerBtn {{
                background: transparent;
                border: none;
                color: {COLORS['text_secondary']};
                font-size: 12px;
                padding: 4px 8px;
            }}

            #headerBtn:hover {{
                color: {COLORS['text_primary']};
            }}

            #iconBtnSmall {{
                background: transparent;
                border: none;
                border-radius: 4px;
                color: {COLORS['text_muted']};
                font-size: 12px;
            }}

            #iconBtnSmall:hover {{
                background: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
            }}

            #panelContent {{
                background: transparent;
            }}

            #topicLabel {{
                font-size: 15px;
                font-weight: 600;
                color: {COLORS['text_primary']};
            }}

            #insightsText, #responseText {{
                font-size: 13px;
                line-height: 1.6;
                color: {COLORS['text_secondary']};
            }}

            #actionsLabel {{
                font-size: 12px;
                font-weight: 600;
                color: {COLORS['text_primary']};
                margin-top: 8px;
            }}

            #actionBtn {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
                color: {COLORS['text_secondary']};
                font-size: 13px;
            }}

            #actionBtn:hover {{
                background: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
            }}

            #actionIcon {{
                font-size: 14px;
            }}

            #actionText {{
                font-size: 13px;
            }}

            #webSearchHint {{
                font-size: 11px;
                color: {COLORS['text_muted']};
                background: {COLORS['accent_dim']};
                padding: 3px 8px;
                border-radius: 4px;
            }}

            #navBar {{
                background: {COLORS['bg_card']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}

            #navTab {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
                color: {COLORS['text_muted']};
            }}

            #navTab:hover {{
                color: {COLORS['text_secondary']};
            }}

            #navTab:checked {{
                background: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
            }}

            #chatScroll {{
                background: transparent;
                border: none;
            }}

            #chatInputContainer {{
                background: {COLORS['bg_input']};
                border-top: 1px solid {COLORS['border']};
                border-radius: 0 0 12px 12px;
            }}

            #chatInput {{
                background: transparent;
                border: none;
                padding: 6px;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}

            #sendBtn {{
                background: {COLORS['accent']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                color: white;
            }}

            #sendBtn:hover {{
                background: {COLORS['accent_light']};
            }}

            #quickActions {{
                background: transparent;
            }}

            #quickBtn {{
                background: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                color: {COLORS['text_secondary']};
            }}

            #quickBtn:hover {{
                background: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
            }}

            #userMsg {{
                background: {COLORS['accent_dim']};
                border-radius: 10px;
                border: 1px solid {COLORS['accent']};
            }}

            #aiMsg {{
                background: {COLORS['bg_input']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}

            #msgText {{
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}

            #liveBadge {{
                font-size: 10px;
                font-weight: 700;
                color: {COLORS['success']};
                background: {COLORS['success_dim']};
                padding: 4px 8px;
                border-radius: 8px;
            }}

            #transcriptText {{
                background: transparent;
                border: none;
                font-size: 13px;
                line-height: 1.7;
                color: {COLORS['text_secondary']};
            }}

            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
            }}

            QScrollBar::handle:vertical {{
                background: {COLORS['border_light']};
                border-radius: 3px;
                min-height: 30px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {COLORS['text_muted']};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

    def _switch_view(self, view: str):
        """Switch between views."""
        self._current_view = view

        self.tab_insights.setChecked(view == "insights")
        self.tab_chat.setChecked(view == "chat")
        self.tab_transcript.setChecked(view == "transcript")

        idx = {"insights": 0, "chat": 1, "transcript": 2}[view]
        self.stack.setCurrentIndex(idx)

    def _quick_action(self, action: str):
        """Handle quick action from insights panel."""
        if action == "define":
            self.signals.ask_question.emit("What are the key topics being discussed?")
        elif action == "search":
            self.signals.ask_question.emit("Search for relevant information about what's being discussed.")
        elif action == "followup":
            self.signals.ask_question.emit("What follow-up questions should I ask?")
        elif action == "help":
            self.signals.ask_question.emit("Give me helpful information about this conversation.")

    def _add_suggestion(self, text):
        """Add AI suggestion to chat."""
        self.chat_panel.add_message(f'"{text}"', is_user=False)
        self.set_listening()

    def _add_answer(self, text):
        """Add AI answer."""
        self.chat_panel.add_message(text, is_user=False)
        self.response_panel.set_response(text)
        self.set_listening()

    def _append_transcript(self, text):
        """Append to transcript."""
        self.transcript_panel.append(text)

    def _set_notes(self, text):
        """Set meeting notes/insights."""
        self.insights_panel.set_insights(text)

    def _setup_tray_icon(self):
        """Set up system tray icon."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(COLORS['accent']))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()

        self._tray_icon = QSystemTrayIcon(QIcon(pixmap), self)
        self._tray_icon.setToolTip("LocalCluely")

        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self._show_window)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(lambda: self.signals.request_quit.emit())

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)

    def _minimize_to_tray(self):
        self.hide()
        if self._tray_icon:
            self._tray_icon.show()

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()
        if self._tray_icon:
            self._tray_icon.hide()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    # Dragging support for frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # Public API
    def get_context(self) -> str:
        return self._context

    def set_context(self, context: str):
        self._context = context
        self.signals.context_changed.emit(context)

    def get_loaded_files(self) -> list:
        return self._loaded_files.copy()

    def set_loading(self):
        self.control_bar.audio_indicator.set_active(False)

    def set_listening(self):
        self.control_bar.audio_indicator.set_active(True)

    def clear_session(self):
        self.transcript_panel.clear()
        self.chat_panel.clear()
        self.insights_panel.set_insights(
            "Waiting for conversation to begin...<br><br>"
            "<span style='color: rgba(255,255,255,0.4);'>Insights will appear here as the meeting progresses.</span>"
        )
        self.control_bar.reset_timer()
        self._loaded_files = []

    def closeEvent(self, event):
        event.ignore()
        self._minimize_to_tray()


class OverlayController:
    """Controller for managing the overlay."""

    def __init__(self):
        self.app = None
        self.window = None

    def init_qt(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.window = OverlayWindow()
        return self.app, self.window

    def show(self):
        if self.window:
            self.window.signals.show_overlay.emit()

    def hide(self):
        if self.window:
            self.window.signals.hide_overlay.emit()

    def set_suggestion(self, text: str):
        if self.window:
            self.window.signals.update_suggestion.emit(text)
            self.window.set_listening()

    def set_transcript(self, text: str):
        if self.window:
            self.window.signals.update_transcript.emit(text)

    def set_loading(self):
        if self.window:
            self.window.set_loading()

    def set_notes(self, text: str):
        if self.window:
            self.window.signals.update_notes.emit(text)

    def set_interpretation(self, text: str):
        self.set_notes(text)

    def show_interpretation(self):
        pass

    def hide_interpretation(self):
        pass

    def set_answer(self, text: str):
        if self.window:
            self.window.signals.update_answer.emit(text)
            self.window.set_listening()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OverlayWindow()

    # Position in top-right area of screen
    screen = app.primaryScreen().geometry()
    window.move(screen.width() - window.width() - 50, 100)

    window.show()

    def test_update():
        window._set_notes(
            "<b>Discussion about news</b><br><br>"
            "You started talking about how there's a lot of big startup acquisitions happening<br><br>"
            "Neel asked you about who recently acquired Windsurf"
        )
        window.insights_panel.set_topic("Discussion about news")
        window._append_transcript("So I think there's been a lot of big startup acquisitions lately. ")
        window._append_transcript("Who acquired Windsurf? ")

    QTimer.singleShot(500, test_update)
    sys.exit(app.exec())
