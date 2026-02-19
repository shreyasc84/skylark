"""AI Agent for drone operations coordination."""
import os
import json
from typing import Optional, Dict, Any, List
from groq import Groq
from dotenv import load_dotenv

from sheets_sync import GoogleSheetsSync
from roster_manager import RosterManager
from inventory_manager import InventoryManager
from assignment_tracker import AssignmentTracker
from conflict_detector import ConflictDetector

# Load environment variables
load_dotenv(override=True)  # Ensure .env file is loaded


class DroneOperationsAgent:
    """AI agent for coordinating drone operations."""
    
    def __init__(self):
        # Initialize components
        self.sheets_sync = GoogleSheetsSync()
        self.roster_manager = RosterManager(self.sheets_sync)
        self.inventory_manager = InventoryManager(self.sheets_sync)
        self.assignment_tracker = AssignmentTracker(
            self.sheets_sync,
            self.roster_manager,
            self.inventory_manager
        )
        self.conflict_detector = ConflictDetector(
            self.sheets_sync,
            self.roster_manager,
            self.inventory_manager,
            self.assignment_tracker
        )
        
        # Initialize Groq client
        # Read API key directly from .env to avoid env/Process issues
        from dotenv import dotenv_values
        env_vars = dotenv_values('.env')
        api_key = (env_vars.get('GROQ_API_KEY') or '').strip()

        if not api_key:
            # Fallback to environment variable if .env missing
            api_key = (os.getenv('GROQ_API_KEY') or '').strip()

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Please ensure it is set in your .env file "
                "at the project root (GROQ_API_KEY=...) or as an environment variable. "
                "Get your API key from https://console.groq.com"
            )
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"  # Updated from decommissioned llama-3.1-70b-versatile
        
        # System prompt
        self.system_prompt = """You are an AI operations coordinator for Skylark Drones. Your role is to help manage:
1. Pilot roster - track availability, skills, certifications, locations
2. Drone inventory - track fleet status, capabilities, weather compatibility
3. Assignment coordination - match pilots and drones to missions
4. Conflict detection - identify scheduling conflicts, skill mismatches, budget overruns, weather risks

Be helpful, precise, and proactive. When assigning pilots/drones, always check for conflicts first.
When users ask about availability or assignments, provide detailed information.
Always sync updates back to Google Sheets when making changes.

Available functions you can call:
- query_pilots: Query pilots by skills, location, certifications, or status
- query_drones: Query drones by capabilities, location, status, or weather compatibility
- calculate_cost: Calculate total cost for a pilot for a mission duration
- assign_to_mission: Assign a pilot and drone to a mission (auto-matches best options)
- check_conflicts: Check for conflicts in current assignments
- update_pilot_status: Update pilot status (Available, Assigned, On Leave, Unavailable)
- get_mission_info: Get information about a mission/project
- handle_urgent_reassignment: Handle urgent reassignment for a project

When the user asks a question, analyze what function(s) you need to call and provide helpful responses."""
    
    def _call_tool(self, tool_name: str, **kwargs) -> str:
        """Call a tool function by name."""
        tools = {
            "query_pilots": self._query_pilots,
            "query_drones": self._query_drones,
            "calculate_cost": self._calculate_cost,
            "assign_to_mission": self._assign_to_mission,
            "check_conflicts": self._check_conflicts,
            "update_pilot_status": self._update_pilot_status,
            "get_mission_info": self._get_mission_info,
            "handle_urgent_reassignment": self._handle_urgent_reassignment,
        }
        
        if tool_name not in tools:
            return f"Unknown tool: {tool_name}"
        
        try:
            return tools[tool_name](**kwargs)
        except Exception as e:
            return f"Error calling {tool_name}: {str(e)}"
    
    def _query_pilots(self, query: str = "") -> str:
        """Query pilots by skills, location, certifications, or status."""
        import json
        query_lower = query.lower() if query else ""
        
        skills = None
        location = None
        status = None
        certifications = None
        
        if "mapping" in query_lower:
            skills = ["Mapping"]
        elif "inspection" in query_lower:
            skills = ["Inspection"]
        elif "thermal" in query_lower:
            skills = ["Thermal"]
        elif "survey" in query_lower:
            skills = ["Survey"]
        
        if "bangalore" in query_lower:
            location = "Bangalore"
        elif "mumbai" in query_lower:
            location = "Mumbai"
        
        if "available" in query_lower:
            status = "Available"
        elif "on leave" in query_lower or "leave" in query_lower:
            status = "On Leave"
        
        if "dgca" in query_lower:
            certifications = ["DGCA"]
        
        df = self.roster_manager.query_pilots(
            skills=skills,
            certifications=certifications,
            location=location,
            status=status
        )
        
        if len(df) == 0:
            result = {"type": "pilots", "count": 0, "data": [], "message": "No pilots found matching the criteria."}
        else:
            result = {
                "type": "pilots",
                "count": len(df),
                "data": df.to_dict('records'),
                "message": f"Found {len(df)} pilot(s)"
            }
        
        return json.dumps(result, indent=2)
    
    def _query_drones(self, query: str = "") -> str:
        """Query drones by capabilities, location, status, or weather compatibility."""
        import json
        query_lower = query.lower() if query else ""
        
        capabilities = None
        location = None
        status = None
        weather = None
        
        if "thermal" in query_lower:
            capabilities = ["Thermal"]
        elif "rgb" in query_lower:
            capabilities = ["RGB"]
        elif "lidar" in query_lower:
            capabilities = ["LiDAR"]
        
        if "bangalore" in query_lower:
            location = "Bangalore"
        elif "mumbai" in query_lower:
            location = "Mumbai"
        
        if "available" in query_lower:
            status = "Available"
        
        if "rain" in query_lower or "rainy" in query_lower:
            weather = "Rainy"
        elif "sunny" in query_lower:
            weather = "Sunny"
        elif "cloudy" in query_lower:
            weather = "Cloudy"
        
        df = self.inventory_manager.query_drones(
            capabilities=capabilities,
            location=location,
            status=status,
            weather_forecast=weather
        )
        
        if len(df) == 0:
            result = {"type": "drones", "count": 0, "data": [], "message": "No drones found matching the criteria."}
        else:
            result = {
                "type": "drones",
                "count": len(df),
                "data": df.to_dict('records'),
                "message": f"Found {len(df)} drone(s)"
            }
        
        return json.dumps(result, indent=2)
    
    def _calculate_cost(self, pilot_id: str, start_date: str, end_date: str) -> str:
        """Calculate total cost for a pilot for a mission duration."""
        import json
        cost = self.roster_manager.calculate_cost(pilot_id, start_date, end_date)
        pilot = self.roster_manager.get_pilot_by_id(pilot_id)
        pilot_name = pilot['name'] if pilot is not None else pilot_id
        result = {
            "type": "cost_calculation",
            "pilot_id": pilot_id,
            "pilot_name": pilot_name,
            "start_date": start_date,
            "end_date": end_date,
            "total_cost_inr": round(cost, 2),
            "currency": "INR"
        }
        return json.dumps(result, indent=2)
    
    def _assign_to_mission(self, project_id: str) -> str:
        """Assign a pilot and drone to a mission."""
        import json
        result = self.assignment_tracker.create_assignment(project_id)
        if result['success']:
            response = {
                "type": "assignment",
                "status": "success",
                "project_id": project_id,
                "pilot_id": result['pilot_id'],
                "drone_id": result['drone_id'],
                "message": f"Successfully assigned Pilot {result['pilot_id']} and Drone {result['drone_id']} to {project_id}"
            }
        else:
            response = {
                "type": "assignment",
                "status": "failed",
                "project_id": project_id,
                "error": result.get('error', 'Unknown error')
            }
        return json.dumps(response, indent=2)
    
    def _check_conflicts(self) -> str:
        """Check for conflicts in current assignments."""
        import json
        conflicts = self.conflict_detector.detect_all_conflicts()
        
        total_conflicts = sum(len(v) for v in conflicts.values())
        response = {
            "type": "conflict_check",
            "total_conflicts": total_conflicts,
            "conflicts": {k: v[:5] for k, v in conflicts.items() if v}
        }
        
        if total_conflicts == 0:
            response["message"] = "No conflicts detected in current assignments."
        else:
            response["message"] = f"Found {total_conflicts} conflict(s)"
        
        return json.dumps(response, indent=2)
    
    def _update_pilot_status(self, pilot_id: str, status: str) -> str:
        """Update pilot status."""
        import json
        success = self.roster_manager.update_pilot_status(pilot_id, status)
        if success:
            response = {
                "type": "pilot_status_update",
                "status": "success",
                "pilot_id": pilot_id,
                "new_status": status,
                "message": f"Successfully updated pilot {pilot_id} status to {status}"
            }
        else:
            response = {
                "type": "pilot_status_update",
                "status": "failed",
                "pilot_id": pilot_id,
                "error": "Failed to update status",
                "valid_statuses": ["Available", "Assigned", "On Leave", "Unavailable"]
            }
        return json.dumps(response, indent=2)
    
    def _get_mission_info(self, project_id: str) -> str:
        """Get information about a mission/project."""
        mission = self.assignment_tracker.get_mission_by_id(project_id)
        if mission is None:
            return f"Mission {project_id} not found."
        
        return mission.to_string()
    
    def _handle_urgent_reassignment(self, project_id: str) -> str:
        """Handle urgent reassignment for a project."""
        result = self.assignment_tracker.handle_urgent_reassignment(project_id)
        if result['success']:
            return f"Urgent reassignment completed: Pilot {result['pilot_id']} and Drone {result['drone_id']} assigned to {project_id}"
        else:
            return f"Urgent reassignment failed: {result.get('error', 'Unknown error')}"
    
    def chat(self, message: str, chat_history: Optional[List[Dict]] = None) -> str:
        """Chat with the agent using Groq API."""
        try:
            if chat_history is None:
                chat_history = []
            
            # Build messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add chat history
            for msg in chat_history[-10:]:  # Keep last 10 messages for context
                messages.append(msg)
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            
            # Check if response contains function calls (simple pattern matching)
            # If user asks for specific operations, call the appropriate tool
            import re
            message_lower = message.lower()
            
            # Use regex for more flexible pattern matching
            pilot_pattern = r'\b(find|query|show|available|list)\s+.*\b(pilot|pilots)\b'
            drone_pattern = r'\b(find|query|show|available|list)\s+.*\b(drone|drones)\b'
            assign_pattern = r'\b(assign|assign.*to|match)\b'
            project_pattern = r'\b(prj|project|mission)\b\s*\d+'
            cost_pattern = r'\b(calculate|cost|price)\b'
            conflict_pattern = r'\b(conflict|check)\b'
            status_pattern = r'\b(update|change|set).*\b(status|state)\b'
            reassign_pattern = r'\b(urgent|reassign|re-assign)\b'
            
            # Pattern matching for tool calls
            if re.search(pilot_pattern, message_lower):
                tool_result = self._query_pilots(message)
                print(f"DEBUG: Found pilot query, result: {tool_result[:100]}")
                if "no pilots found" not in tool_result.lower():
                    return tool_result + "\n\n" + response_text
            
            if re.search(drone_pattern, message_lower):
                tool_result = self._query_drones(message)
                print(f"DEBUG: Found drone query, result: {tool_result[:100]}")
                if "no drones found" not in tool_result.lower():
                    return tool_result + "\n\n" + response_text
            
            if re.search(cost_pattern, message_lower):
                # Try to extract pilot_id, start_date, end_date from message
                pilot_match = re.search(r'[Pp]\d{3}', message)
                date_match = re.findall(r'\d{4}-\d{2}-\d{2}', message)
                if pilot_match and len(date_match) >= 2:
                    tool_result = self._calculate_cost(pilot_match.group(), date_match[0], date_match[1])
                    return tool_result + "\n\n" + response_text
            
            if re.search(assign_pattern, message_lower) and re.search(project_pattern, message_lower):
                # Extract project ID
                project_match = re.search(r'[Pp][Rr][Jj]\d{3}', message)
                if not project_match:
                    project_match = re.search(r'\b(project|mission|prj)\b\s*(\d{3})', message, re.IGNORECASE)
                if project_match:
                    project_id = project_match.group() if 'group' not in dir(project_match) or len(project_match.groups()) == 0 else f"PRJ{project_match.group(2)}"
                    tool_result = self._assign_to_mission(project_id)
                    print(f"DEBUG: Assigning to mission, result: {tool_result}")
                    return tool_result + "\n\n" + response_text
            
            if re.search(conflict_pattern, message_lower):
                tool_result = self._check_conflicts()
                print(f"DEBUG: Checking conflicts, result: {tool_result[:100]}")
                return tool_result + "\n\n" + response_text
            
            if re.search(status_pattern, message_lower):
                # Extract pilot_id and status
                pilot_match = re.search(r'[Pp]\d{3}', message)
                status_match = re.search(r'(Available|Assigned|On Leave|Unavailable)', message, re.IGNORECASE)
                if pilot_match and status_match:
                    tool_result = self._update_pilot_status(pilot_match.group().upper(), status_match.group())
                    return tool_result + "\n\n" + response_text
            
            if re.search(reassign_pattern, message_lower):
                project_match = re.search(r'[Pp][Rr][Jj]\d{3}', message)
                if project_match:
                    tool_result = self._handle_urgent_reassignment(project_match.group().upper())
                    return tool_result + "\n\n" + response_text
            
            return response_text
            
        except Exception as e:
            return f"Error: {str(e)}. Please check your API key and try again."
