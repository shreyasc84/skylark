"""Streamlit web interface for Drone Operations Coordinator AI Agent."""
import streamlit as st
import os
import json
from dotenv import load_dotenv

# Load environment variables before importing agent
load_dotenv(override=True)  # override=True ensures .env values take precedence

def format_response(response_text):
    """Format response as JSON or markdown depending on content."""
    if not isinstance(response_text, str):
        return {"type": "text", "data": str(response_text)}
    
    # Check if it looks like JSON (starts with { or [)
    response_text = response_text.strip()
    if response_text.startswith('{') or response_text.startswith('['):
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            return data
        except json.JSONDecodeError:
            # Return as plain text if not valid JSON
            return {"type": "text", "data": response_text}
    else:
        # Not JSON, return as plain text
        return {"type": "text", "data": response_text}

def display_response(response_data):
    """Display response in a beautiful, frontend-friendly way."""
    if isinstance(response_data, dict):
        response_type = response_data.get("type", "unknown")
        
        if response_type == "text":
            # Plain text display
            st.markdown(response_data.get('data', ''))
            st.divider()
        
        elif response_type == "pilots":
            # Pilot list display
            count = response_data.get('count', 0)
            data = response_data.get('data', [])
            message = response_data.get('message', f'Found {count} pilot(s)')
            
            col1, col2 = st.columns([0.7, 0.3])
            with col1:
                st.subheader("🧑‍✈️ Available Pilots")
            with col2:
                st.metric("Count", count, delta=None)
            
            if data:
                st.dataframe(data, use_container_width=True, hide_index=True)
            else:
                st.info(message)
            st.divider()
        
        elif response_type == "drones":
            # Drone list display
            count = response_data.get('count', 0)
            data = response_data.get('data', [])
            message = response_data.get('message', f'Found {count} drone(s)')
            
            col1, col2 = st.columns([0.7, 0.3])
            with col1:
                st.subheader("✈️ Available Drones")
            with col2:
                st.metric("Count", count, delta=None)
            
            if data:
                st.dataframe(data, use_container_width=True, hide_index=True)
            else:
                st.info(message)
            st.divider()
        
        elif response_type == "missions":
            # Missions list display
            count = response_data.get('count', 0)
            data = response_data.get('data', [])
            message = response_data.get('message', f'Found {count} mission(s)')
            
            col1, col2 = st.columns([0.7, 0.3])
            with col1:
                st.subheader("📋 Active Missions")
            with col2:
                st.metric("Count", count, delta=None)
            
            if data:
                st.dataframe(data, use_container_width=True, hide_index=True)
            else:
                st.info(message)
            st.divider()
        
        elif response_type == "assignment":
            # Assignment display with nice visual feedback
            status = response_data.get('status', 'unknown')
            pilot_id = response_data.get('pilot_id', 'N/A')
            drone_id = response_data.get('drone_id', 'N/A')
            project_id = response_data.get('project_id', 'N/A')
            message = response_data.get('message', 'Assignment processed')
            
            if status == 'success':
                st.success("✅ Assignment Successful")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Project", project_id)
                with col2:
                    st.metric("Pilot Assigned", pilot_id)
                with col3:
                    st.metric("Drone Assigned", drone_id)
                
                st.markdown(f"**Status**: {message}")
            else:
                st.error("❌ Assignment Failed")
                error = response_data.get('error', 'Unknown error')
                st.markdown(f"**Error**: {error}")
            st.divider()
        
        elif response_type == "cost_calculation":
            # Cost display with beautiful metrics
            pilot_name = response_data.get('pilot_name', 'Unknown')
            start_date = response_data.get('start_date', 'N/A')
            end_date = response_data.get('end_date', 'N/A')
            total_cost = response_data.get('total_cost_inr', 0)
            currency = response_data.get('currency', 'INR')
            
            st.subheader("💰 Cost Calculation")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Pilot", pilot_name)
            with col2:
                st.metric("Duration", f"{start_date} → {end_date}")
            with col3:
                st.metric("Total Cost", f"₹{total_cost:,.2f}", delta=f"{currency}")
            st.divider()
        
        elif response_type == "pilot_status_update":
            # Status update display
            status = response_data.get('status', 'unknown')
            pilot_id = response_data.get('pilot_id', 'N/A')
            new_status = response_data.get('new_status', 'N/A')
            message = response_data.get('message', 'Status update processed')
            
            if status == 'success':
                st.success("✅ Status Updated")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Pilot ID", pilot_id)
                with col2:
                    st.metric("New Status", new_status)
                
                st.markdown(f"**Update**: {message}")
            else:
                st.error("❌ Status Update Failed")
                valid_statuses = response_data.get('valid_statuses', [])
                st.markdown(f"**Pilot ID**: {pilot_id}")
                if valid_statuses:
                    st.markdown(f"**Valid statuses**: {', '.join(valid_statuses)}")
            st.divider()
        
        elif response_type == "conflict_check":
            # Conflict detection display
            total_conflicts = response_data.get('total_conflicts', 0)
            conflicts = response_data.get('conflicts', {})
            message = response_data.get('message', '')
            
            if total_conflicts > 0:
                st.warning(f"⚠️ {total_conflicts} Conflict(s) Detected")
            else:
                st.success("✅ No Conflicts Found")
            
            st.metric("Total Conflicts", total_conflicts)
            
            if conflicts:
                with st.expander("📋 View Conflict Details"):
                    for conflict_id, details in conflicts.items():
                        st.markdown(f"**{conflict_id}**: {details}")
            
            if message:
                st.markdown(f"**Summary**: {message}")
            st.divider()
        
        else:
            # Fallback for unknown types
            st.subheader("📊 Response Data")
            
            # Extract message if available
            message = response_data.get('message', '')
            if message:
                st.markdown(f"**{message}**")
            
            # Show key metrics
            if 'count' in response_data:
                st.metric("Count", response_data['count'])
            
            # Show data in expandable section
            if 'data' in response_data:
                with st.expander("📄 View Raw Data"):
                    st.json(response_data['data'])
            st.divider()
    else:
        st.markdown(response_text)

# Try to import the agent, handle import errors gracefully
try:
    from agent import DroneOperationsAgent
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    IMPORT_ERROR = str(e)
except Exception as e:
    AGENT_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Page config
st.set_page_config(
    page_title="Skylark Drones Operations Coordinator",
    page_icon="🚁",
    layout="wide"
)

# Initialize session state
if "agent" not in st.session_state:
    if not AGENT_AVAILABLE:
        st.session_state.initialized = False
        st.session_state.error = f"Failed to import agent module: {IMPORT_ERROR}\n\nPlease install dependencies: pip install langchain-groq"
    else:
        try:
            st.session_state.agent = DroneOperationsAgent()
            st.session_state.initialized = True
        except Exception as e:
            st.session_state.initialized = False
            st.session_state.error = str(e)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Header
st.title("🚁 Skylark Drones Operations Coordinator")
st.markdown("AI-powered agent for managing drone operations, pilot assignments, and fleet coordination")

# Sidebar
with st.sidebar:
    st.header("Quick Actions")
    
    action = None
    
    if st.button("🔍 Check All Conflicts"):
        action = "conflicts"
    
    if st.button("👥 View Available Pilots"):
        action = "pilots"
    
    if st.button("✈️ View Available Drones"):
        action = "drones"
    
    if st.button("📋 View Active Missions"):
        action = "missions"
    
    st.divider()
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.chat_history = []

# Process sidebar actions
if "action" in locals() and action:
    if st.session_state.initialized:
        with st.spinner("Processing..."):
            if action == "conflicts":
                result = st.session_state.agent.conflict_detector.get_conflict_summary()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result
                })
            elif action == "pilots":
                pilots = st.session_state.agent.roster_manager.get_available_pilots()
                result = json.dumps({
                    "type": "pilots",
                    "count": len(pilots),
                    "data": pilots.to_dict(orient='records'),
                    "message": f"Found {len(pilots)} available pilot(s)"
                })
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result
                })
            elif action == "drones":
                drones = st.session_state.agent.inventory_manager.get_available_drones()
                result = json.dumps({
                    "type": "drones",
                    "count": len(drones),
                    "data": drones.to_dict(orient='records'),
                    "message": f"Found {len(drones)} available drone(s)"
                })
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result
                })
            elif action == "missions":
                missions = st.session_state.agent.assignment_tracker.get_active_missions()
                result = json.dumps({
                    "type": "missions",
                    "count": len(missions),
                    "data": missions.to_dict(orient='records'),
                    "message": f"Found {len(missions)} active mission(s)"
                })
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result
                })
        st.rerun()

# Main content area
if not st.session_state.initialized:
    error_msg = st.session_state.get('error', 'Unknown error')
    st.error(f"❌ Failed to initialize agent: {error_msg}")
    
    if not AGENT_AVAILABLE:
        st.warning("""
        **Missing Dependencies:**
        
        Please install the required packages:
        ```bash
        pip install groq
        ```
        
        Or install all dependencies:
        ```bash
        pip install -r requirements.txt
        ```
        """)
    else:
        st.info("""
        **Setup Instructions:**
        1. Make sure you have set up your `.env` file with:
           - `GROQ_API_KEY` - Your Groq API key (get from https://console.groq.com/)
           - `GOOGLE_SHEETS_CREDENTIALS_PATH` - Path to Google Sheets credentials JSON
           - `PILOT_ROSTER_SHEET_ID`, `DRONE_FLEET_SHEET_ID`, `MISSIONS_SHEET_ID` - Your Google Sheet IDs
        
        2. If you don't have Google Sheets set up yet, the agent will fall back to local CSV files.
        
        3. For Google Sheets setup:
           - Create a Google Cloud Project
           - Enable Google Sheets API
           - Create OAuth 2.0 credentials
           - Upload your CSV files to Google Sheets
        """)
else:
    # Chat interface
    st.subheader("💬 Chat with Operations Coordinator")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                # Try to format assistant responses as structured data
                response_data = format_response(message["content"])
                if isinstance(response_data, dict) and response_data.get("type"):
                    display_response(response_data)
                else:
                    st.markdown(message["content"])
            else:
                st.markdown(message["content"])
    
    # Chat input (must not be inside columns or other containers)
    prompt = st.chat_input("Ask me anything about drone operations...", key="main_chat_input")
    
    # Process new message if submitted
    if prompt and prompt.strip():
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Update chat history for context
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })
        
        # Get agent response
        try:
            with st.spinner("Thinking..."):
                response = st.session_state.agent.chat(
                    prompt,
                    st.session_state.chat_history
                )
            
            # Add assistant response to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Rerun to display new messages
            st.rerun()
        
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })
            st.rerun()
