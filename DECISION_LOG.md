# Decision Log

This document records key technical and architectural decisions made during the development of the Skylark Drones Operations Coordinator system.

---

## Decision 1: LLM Provider Selection

**Date**: February 2026  
**Status**: Accepted

### Context
Needed a fast, cost-effective LLM for natural language processing of operational queries.

### Options Considered
1. **OpenAI GPT-4** - High quality, expensive, rate limited
2. **Groq (Llama 3.3 70B)** - Fast inference, free tier, good quality
3. **Local LLM** - Private, but requires hardware

### Decision
Selected **Groq** with `llama-3.3-70b-versatile` model.

### Rationale
- Free tier available for development/small scale
- Extremely fast inference (< 1 second)
- Good reasoning capabilities for operational tasks
- Easy API integration

---

## Decision 2: Data Storage - Google Sheets vs Database

**Date**: February 2026  
**Status**: Accepted

### Context
Need persistent storage for pilot roster, drone fleet, and missions data that's accessible to non-technical users.

### Options Considered
1. **PostgreSQL/MySQL** - Robust, requires server setup
2. **SQLite** - Simple, local only
3. **Google Sheets** - Accessible, collaborative, no server needed
4. **Airtable** - Good UI, API limits, cost

### Decision
Selected **Google Sheets API v4** as primary data source.

### Rationale
- Non-technical staff can edit data directly
- Built-in collaboration features
- No database server to maintain
- Free for typical usage
- Two-way sync allows real-time updates

---

## Decision 3: Frontend Framework

**Date**: February 2026  
**Status**: Accepted

### Context
Need a web interface for the AI operations coordinator.

### Options Considered
1. **React/Next.js** - Flexible, requires separate backend
2. **Flask/Django** - Python, but more boilerplate
3. **Streamlit** - Python-native, rapid prototyping, built-in chat UI
4. **Gradio** - Good for ML demos, less customizable

### Decision
Selected **Streamlit**.

### Rationale
- Single Python file for entire UI
- Native chat interface components
- Easy deployment to Streamlit Cloud
- No JavaScript required
- Fast iteration for prototyping

---

## Decision 4: Dynamic Column Detection for Google Sheets

**Date**: February 2026  
**Status**: Accepted

### Context
Google Sheets columns may vary (users add/remove columns). Hardcoded column references break when sheet structure changes.

### Options Considered
1. **Hardcoded column letters (A, B, C...)** - Simple but fragile
2. **Column name lookup** - Dynamic but slower
3. **Header row parsing** - Flexible, handles changes

### Decision
Implemented **dynamic column detection** using DataFrame column indices.

### Rationale
- Automatically adapts to column reordering
- Uses `list(df.columns).index('column_name')` to find position
- Converts index to letter with `chr(ord('A') + idx)`
- Works with any sheet structure

### Implementation
```python
status_col_idx = list(df.columns).index('status')
status_col_letter = chr(ord('A') + status_col_idx)
range_name = f'{sheet_name}!{status_col_letter}{row_num}'
```

---

## Decision 5: Response Format - JSON vs Plain Text

**Date**: February 2026  
**Status**: Accepted

### Context
Agent responses need to be displayed in a user-friendly format on the frontend.

### Options Considered
1. **Plain text** - Simple but hard to parse/style
2. **Markdown** - Better formatting, limited structure
3. **Structured JSON** - Machine-parseable, enables rich UI

### Decision
All agent methods return **structured JSON** with type classification.

### Rationale
- Frontend can render different UI based on response type
- Consistent structure: `{type, data, count, message, status}`
- Enables tables for lists, metrics for stats, alerts for errors
- Backward compatible with plain text fallback

### Response Types
| Type | UI Rendering |
|------|-------------|
| `pilots` | DataTable with count metric |
| `drones` | DataTable with count metric |
| `missions` | DataTable with count metric |
| `assignment` | Success/Error alert with details |
| `cost_calculation` | Metric cards |
| `conflict_check` | Warning/Success with expandable details |
| `pilot_status_update` | Success/Error alert |
| `text` | Plain markdown |

---

## Decision 6: Authentication - OAuth vs Service Account

**Date**: February 2026  
**Status**: Accepted

### Context
Google Sheets API requires authentication. Need to support both local development and cloud deployment.

### Options Considered
1. **OAuth 2.0 (User consent)** - Interactive, requires browser
2. **Service Account** - Non-interactive, good for servers
3. **API Key** - Limited functionality

### Decision
Support **both OAuth 2.0 and Service Account**.

### Rationale
- OAuth for local development (token.pickle caching)
- Service Account for Streamlit Cloud deployment
- Code checks for Streamlit secrets first, falls back to local credentials

---

## Decision 7: Error Handling - Fail Silent vs Explicit

**Date**: February 2026  
**Status**: Accepted

### Context
Data operations may fail (API errors, missing data, invalid inputs).

### Options Considered
1. **Fail silent** - Return empty, log error
2. **Raise exceptions** - Crash on error
3. **Graceful degradation** - Return partial results with error info

### Decision
Implemented **graceful degradation** with defensive programming.

### Rationale
- Missing columns don't crash the app
- Partial data is better than no data
- Errors are returned in response JSON for user feedback
- Debug info logged for troubleshooting

### Example
```python
if 'pilot_id' in df.columns:
    # proceed with operation
else:
    return {"status": "error", "message": "pilot_id column not found"}
```

---

## Decision 8: Chat History Persistence

**Date**: February 2026  
**Status**: Accepted

### Context
Streamlit reruns the entire script on each interaction. Chat messages were being lost.

### Options Considered
1. **Database storage** - Persistent across sessions
2. **Session state** - Persistent within session
3. **Cookie/LocalStorage** - Client-side, limited

### Decision
Use **Streamlit session_state** for chat history.

### Rationale
- Built-in to Streamlit
- No external dependencies
- Persists across reruns within same browser session
- Simple: `st.session_state.messages = []`

---

## Decision 9: Deployment Platform

**Date**: February 2026  
**Status**: Accepted

### Context
Need to deploy the application for user access.

### Options Considered
1. **AWS/GCP** - Powerful, complex setup
2. **Heroku** - Easy, paid
3. **Railway** - Simple, reasonable pricing
4. **Streamlit Cloud** - Free, native integration

### Decision
Primary deployment on **Streamlit Community Cloud**.

### Rationale
- Free hosting
- Native Streamlit support
- GitHub integration
- Secrets management built-in
- Auto-deploy on push

---

## Future Considerations

### Potential Improvements
1. **Database migration** - If data volume grows significantly
2. **User authentication** - Multi-tenant support
3. **Notification system** - Alerts for conflicts/issues
4. **Mobile app** - For field operations
5. **Offline mode** - Local caching when disconnected

### Technical Debt
- [ ] Add comprehensive unit tests
- [ ] Implement retry logic for API failures
- [ ] Add request rate limiting
- [ ] Improve error messages for end users

---

*Last Updated: February 19, 2026*
