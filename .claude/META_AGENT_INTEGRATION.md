# Meta Internal Agent Integration - Vision + Tool Calling

**Status:** Planning phase - Architecture to be determined tomorrow

**Game Changer:** User has access to Meta internal agent with custom tool calling capabilities. This transforms LocalCluely from a basic meeting assistant into a hyper-contextualized work intelligence system.

---

## The Vision

### Current LocalCluely:
```
Audio → Whisper → Transcript → Ollama/Claude → Generic suggestions
```

### With Meta Agent Integration:
```
Audio → Whisper → Transcript
  +
Screen → Vision Model → Screenshot
  ↓
Meta Internal Agent (with vision + tool calling)
  ↓
Tools: search_workplace, search_docs, search_code, query_analytics, etc.
  ↓
Hyper-contextualized suggestions with full company knowledge
```

---

## Why This is Revolutionary

### Standard LLM:
- "Based on this conversation, you could say..."
- Generic, no context beyond the transcript

### Meta Agent with Tools:
- "Based on this conversation AND what's on your screen..."
- "I searched Workplace and found this related discussion from 3 months ago..."
- "Your design differs from the design system - here's the guideline..."
- "Similar feature shipped last quarter - here's what they learned..."
- "The person you're talking to posted about this yesterday - here's the link..."

**It has institutional memory + visual understanding + real-time context.**

---

## Killer Use Cases

### 1. Design Reviews
```
Screen: Figma mockup
Audio: Client: "Why did you choose this layout?"

Agent:
- SEES: The design (vision model)
- SEARCHES: search_workplace("layout patterns mobile")
- SEARCHES: search_docs("design system layout guidelines")
- FINDS: 12 relevant discussions, UXR data, past decisions

Returns:
"This layout follows the mobile-first card pattern that tested 34%
better in the Q3 UXR study (link). It's also used in Messenger's
new inbox redesign (link to Dave's post). The design system
recommends 16px padding which you're using correctly (link to docs)."
```

### 2. Technical Discussions
```
Screen: Architecture diagram
Audio: "How do other teams handle authentication?"

Agent:
- SEES: Your auth flow diagram
- SEARCHES: search_code("authentication patterns")
- SEARCHES: search_workplace("auth architecture")
- QUERIES: Internal security docs

Returns:
"Across Meta, 3 main patterns:
1. OAuth 2.0 + PKCE (Instagram, WhatsApp) - recommended
2. Custom tokens (Messenger) - being deprecated
3. Passkey (newer products) - future direction

Your diagram shows #2. Security team recommends #1 (post link).
Migration guide: [internal link]
Reference implementation: [John's team, link to code]"
```

### 3. Presentations
```
Screen: Your quarterly review slides
Audio: You: *practicing presentation*

Agent analyzes:
- SEES: Slide content, data visualizations
- SEARCHES: Supporting data from analytics
- SEARCHES: Competitive intel from internal reports
- SEARCHES: Related projects and learnings

After presentation, generates:
"Presentation feedback:
- Slide 3: Mentioned 'growth' but no number
  → Found: Q3 was +23% (analytics dashboard)
- Slide 7: Competitor analysis needs update
  → Recent intel report shows Competitor X launched similar (link)
- Slide 10: Next steps
  → PMM team already scoped Q1 roadmap - align with this (link)

Suggested additions:
- User testimonials (found 5 quotes in Workplace feedback)
- ROI calculation (finance analysis: link)
- Success story: Instagram team did similar, 40% adoption (link)"
```

### 4. Content Design Work
```
Screen: Typography/layout exploration
Audio: "I'm worried about readability..."

Agent:
- SEES: Current design (detects 95-char line length, 1.3 line height)
- KNOWS: Optimal is 50-75 chars, 1.5 line height
- SEARCHES: Design system typography guidelines
- SEARCHES: Accessibility standards

Returns:
"I can see the line length is 95 characters - optimal for web is
50-75 for readability (Meta design system guidelines: link).

Line height is 1.3 - recommend 1.5 for body text (accessibility
docs: link).

Here's how the Feed team solved this same issue (Workplace post
by Sarah Chen with examples: link)."
```

---

## Architecture Decision (To Determine Tomorrow)

### Option A: Desktop via VPN ⭐ (Preferred - if possible)
```
Desktop (Windows)
├─ Tauri UI
├─ Audio capture (WASAPI)
├─ Screen capture
├─ Python backend
│   └─ Connects to Meta agent via VPN
└─ Full local experience

Requirements:
- Meta VPN access to internal APIs
- Auth token/credentials
- Network access to agent endpoint
```

**Test tomorrow:**
```bash
# Connect to Meta VPN, then test:
curl https://meta-agent-api.internal.meta.com/health
# If this works → use this approach!
```

### Option B: Hybrid (Desktop + OD)
```
Desktop (Windows)          OD (Linux)
├─ Tauri UI                ├─ Python service
├─ Audio capture           ├─ Meta agent client
├─ Screen capture          └─ Tool integrations
└─ Local processing              │
      │                          │
      └──────── HTTP ────────────┘
```

**When to use:**
- VPN doesn't expose internal APIs
- Need to be inside Meta network for tools
- Auth is easier from OD

**Setup:**
- Desktop: FastAPI client sends audio + screen
- OD: FastAPI service proxies to Meta agent
- Desktop gets responses back

### Option C: Full OD (Not Recommended)
**Issues:**
- No Windows audio capture (need Linux alternatives)
- No local UI (X11 forwarding is slow)
- Can't test UX properly

**Only if:** Building purely as backend service, no UI

---

## Technical Implementation

### Screen Capture
```python
from mss import mss
import base64

def capture_screen():
    with mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        # Convert to base64
        img_bytes = screenshot.rgb
        return base64.b64encode(img_bytes).decode()
```

### Meta Agent API Call (Pseudocode)
```python
import requests

def query_meta_agent(transcript: str, screenshot: str):
    response = requests.post(
        'https://meta-agent-api.internal/v1/chat',
        headers={
            'Authorization': f'Bearer {META_TOKEN}',
        },
        json={
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': transcript
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/png;base64,{screenshot}'
                            }
                        }
                    ]
                }
            ],
            'tools': [
                {'type': 'function', 'function': {'name': 'search_workplace'}},
                {'type': 'function', 'function': {'name': 'search_docs'}},
                {'type': 'function', 'function': {'name': 'search_code'}},
                {'type': 'function', 'function': {'name': 'query_analytics'}},
                # ... other custom tools
            ],
            'tool_choice': 'auto'  # Let agent decide when to use tools
        }
    )

    return response.json()
```

### Integration into llm_client.py
```python
# Add to llm_client.py

elif self.provider == "meta":
    # Capture screen if vision enabled
    screenshot = None
    if self.supports_vision:
        screenshot = capture_screen()

    # Build message with vision
    content = [{"type": "text", "text": user_msg}]
    if screenshot:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{screenshot}"}
        })

    response = requests.post(
        f"{self.meta_api_url}/chat",
        headers={"Authorization": f"Bearer {self.meta_token}"},
        json={
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content}
            ],
            "tools_enabled": True,
            "max_tokens": max_tokens
        }
    )

    return response.json()["response"]
```

---

## Privacy & Security Considerations

### Data Handling
- ✅ Everything stays within Meta infrastructure
- ✅ Uses existing auth/permissions
- ✅ Tools respect user's access levels
- ⚠️ Screen captures might contain sensitive data
- ⚠️ Meeting transcripts contain confidential info

### Controls Needed
```json
{
  "privacy": {
    "capture_audio": true,
    "capture_screen": false,  // Toggle per meeting
    "save_logs": false,       // Don't persist locally
    "allowed_tools": [
      "search_workplace",
      "search_docs"
      // Only tools user has permission for
    ]
  }
}
```

### Questions for Meta IT/Security
1. Is using internal agent API for this purpose allowed?
2. Are there rate limits on tool calls?
3. Should screen captures be logged/audited?
4. Compliance requirements for meeting transcripts?
5. Data retention policies?

---

## What Makes This Different from Generic AI

### GitHub Copilot:
- Code context only
- No audio, no meetings
- Can't search company knowledge

### Notion AI:
- Docs context only
- No real-time
- No vision

### Slack AI:
- Chat context only
- No screen sharing
- Limited to Slack data

### LocalCluely + Meta Agent:
- ✅ Audio (hears conversation)
- ✅ Vision (sees screen)
- ✅ Real-time (during meetings)
- ✅ Full company context (Workplace, docs, code, analytics)
- ✅ Proactive (surfaces relevant info)
- ✅ Multi-modal understanding
- ✅ Tool calling (can search/query anything)

**= Personal work assistant with full institutional memory**

---

## Potential Impact

### For Content Designers
- Never miss relevant past discussions
- Instant access to design system guidelines
- Automatic competitive analysis references
- Design pattern recommendations from company learnings
- UXR data at your fingertips
- Auto-generated meeting notes with screenshots

### For Engineers
- Architecture decisions with historical context
- Code patterns from successful projects
- Security/compliance guidelines automatically surfaced
- Performance data and benchmarks
- Error patterns and solutions from past incidents

### For PMs
- Product decisions with full context
- User research insights
- Competitive intelligence
- Roadmap alignment across teams
- Metric tracking and dashboards

### For Everyone
- Never search Workplace manually again
- Automatic meeting summaries
- Decision tracking and documentation
- Institutional knowledge accessible in real-time
- Learning from past projects

---

## Next Steps (Tomorrow)

### 1. Architecture Decision
- [ ] Test Meta VPN access to internal APIs
- [ ] Determine: Desktop-only vs Hybrid
- [ ] Get API endpoint and auth details

### 2. API Investigation
- [ ] Find Meta agent API documentation
- [ ] Get auth token/credentials
- [ ] List available tools
- [ ] Check vision model support (Llama 3.2 Vision?)
- [ ] Rate limits and quotas

### 3. Quick Prototype
- [ ] Add Meta provider to llm_client.py
- [ ] Test basic audio transcript → agent → response
- [ ] Verify tool calling works
- [ ] Test with one internal tool (e.g., search_workplace)

### 4. Vision Integration
- [ ] Add screen capture
- [ ] Send screenshot to agent
- [ ] Test vision + audio together
- [ ] Verify agent can "see" and understand context

### 5. Testing
- [ ] Real meeting scenario
- [ ] Design review with Figma
- [ ] Code review with screenshot
- [ ] Presentation practice

---

## Open Questions

**Technical:**
- What's the Meta agent API endpoint?
- Is it OpenAI-compatible or custom format?
- Does it support Llama 3.2 Vision?
- What's the latency for vision + tool calls?
- Can we stream responses?

**Product:**
- How often to capture screens? (Every 10s? On-demand?)
- Privacy controls for sensitive meetings?
- How to display tool results in UI?
- Notification when agent finds relevant context?

**Organizational:**
- Is this allowed under Meta policies?
- Need approval from security/compliance?
- Can we share this internally?
- Should this be open-sourced (probably not with internal tools)?

---

## Priority After Tauri

1. **Tauri migration** (tomorrow) - Get native glassmorphic UI
2. **Meta agent integration** (next) - Add this killer feature
3. **Vision capabilities** (part of #2) - Screen capture + multimodal
4. **Tool optimization** (later) - Fine-tune which tools, when
5. **macOS support** (future) - Cross-platform

---

## Success Metrics

**This is successful when:**
- Agent can see screen + hear conversation
- Tools are called automatically when relevant
- Responses include rich context from internal systems
- User rarely needs to manually search Workplace/docs
- Meeting notes are auto-generated with context
- Saves 30+ minutes per day on context gathering

**Dream outcome:**
"I never manually search for anything at work anymore.
The assistant knows everything and brings me exactly
what I need, when I need it, in context."

---

## Notes for Tomorrow's Claude

**Context:**
User works at Meta, has access to internal agent with custom tool calling. This could transform LocalCluely from a meeting assistant into a work intelligence system with full company context.

**Start with:**
1. Check VPN access to Meta internal APIs (determines architecture)
2. Get API details and auth setup
3. Quick test integration before Tauri work

**Keep in mind:**
- This is MORE important than Tauri (but do both!)
- Privacy/security considerations are critical
- User wants this for work (content design)
- Vision + tool calling = game changer

**User's excitement level:** 🔥🔥🔥
This is the feature that makes this indispensable.

---

Good night! Tomorrow we build something incredible. 🚀✨
