"""Assignment tracking and matching logic."""
import pandas as pd
from typing import Optional, Dict, Tuple
from utils import dates_overlap, calculate_mission_duration
from sheets_sync import GoogleSheetsSync
from roster_manager import RosterManager
from inventory_manager import InventoryManager


class AssignmentTracker:
    """Track and manage pilot/drone assignments."""
    
    def __init__(
        self, 
        sheets_sync: GoogleSheetsSync,
        roster_manager: RosterManager,
        inventory_manager: InventoryManager
    ):
        self.sheets_sync = sheets_sync
        self.roster_manager = roster_manager
        self.inventory_manager = inventory_manager
        self._missions = None
        self._refresh_missions()
    
    def _refresh_missions(self):
        """Refresh missions data from Google Sheets."""
        self._missions = self.sheets_sync.get_missions()
        
        # Handle column name variations
        if 'mission_id' in self._missions.columns and 'project_id' not in self._missions.columns:
            self._missions['project_id'] = self._missions['mission_id']
        
        # Ensure required columns exist
        if 'assigned_pilot' not in self._missions.columns:
            self._missions['assigned_pilot'] = '-'
        if 'assigned_drone' not in self._missions.columns:
            self._missions['assigned_drone'] = '-'
        if 'status' not in self._missions.columns:
            self._missions['status'] = 'Pending'
        if 'project_id' not in self._missions.columns:
            # If no ID column exists, create one from index
            self._missions['project_id'] = [f"PROJ{i:03d}" for i in range(len(self._missions))]
    
    def get_mission_by_id(self, project_id: str) -> Optional[pd.Series]:
        """Get mission by project ID."""
        self._refresh_missions()
        matches = self._missions[self._missions['project_id'] == project_id]
        return matches.iloc[0] if len(matches) > 0 else None
    
    def get_active_missions(self) -> pd.DataFrame:
        """Get all active missions."""
        self._refresh_missions()
        # In a full implementation, filter by date ranges
        return self._missions
    
    def match_pilot_to_mission(self, project_id: str) -> Optional[str]:
        """Find best matching pilot for a mission."""
        mission = self.get_mission_by_id(project_id)
        if mission is None:
            return None
        
        matching_pilots = self.roster_manager.find_matching_pilots(
            required_skills=mission['required_skills'],
            required_certs=mission['required_certs'],
            location=mission['location'],
            start_date=mission['start_date'],
            end_date=mission['end_date'],
            max_budget=float(mission.get('mission_budget_inr', float('inf')))
        )
        
        if len(matching_pilots) == 0:
            return None
        
        # Return first matching pilot (could be enhanced with ranking)
        return matching_pilots.iloc[0]['pilot_id']
    
    def match_drone_to_mission(self, project_id: str) -> Optional[str]:
        """Find best matching drone for a mission."""
        mission = self.get_mission_by_id(project_id)
        if mission is None:
            return None
        
        # Determine required capabilities from required skills
        # This is a simplified mapping
        skill_to_capability = {
            'Thermal': 'Thermal',
            'Mapping': 'RGB',
            'Survey': 'RGB',
            'Inspection': 'RGB',
            'LiDAR': 'LiDAR'
        }
        
        required_capabilities = []
        for skill in mission['required_skills'].split(','):
            skill = skill.strip()
            if skill in skill_to_capability:
                required_capabilities.append(skill_to_capability[skill])
        
        if not required_capabilities:
            required_capabilities = ['RGB']  # Default
        
        matching_drones = self.inventory_manager.find_matching_drones(
            required_capabilities=','.join(required_capabilities),
            location=mission['location'],
            weather_forecast=mission['weather_forecast']
        )
        
        if len(matching_drones) == 0:
            return None
        
        # Return first matching drone
        return matching_drones.iloc[0]['drone_id']
    
    def assign_pilot_to_mission(
        self, 
        pilot_id: str, 
        project_id: str
    ) -> bool:
        """Assign pilot to mission."""
        mission = self.get_mission_by_id(project_id)
        if mission is None:
            return False
        
        # Check availability
        if not self.roster_manager.is_pilot_available(
            pilot_id, 
            mission['start_date'], 
            mission['end_date']
        ):
            return False
        
        # Update pilot status
        return self.roster_manager.update_pilot_status(
            pilot_id, 
            'Assigned', 
            project_id
        )
    
    def assign_drone_to_mission(
        self, 
        drone_id: str, 
        project_id: str
    ) -> bool:
        """Assign drone to mission."""
        mission = self.get_mission_by_id(project_id)
        if mission is None:
            return False
        
        # Check availability
        if not self.inventory_manager.is_drone_available(drone_id):
            return False
        
        # Update drone status
        return self.inventory_manager.update_drone_status(
            drone_id, 
            'Assigned', 
            project_id
        )
    
    def create_assignment(
        self, 
        project_id: str,
        pilot_id: Optional[str] = None,
        drone_id: Optional[str] = None
    ) -> Dict:
        """Create a complete assignment (pilot + drone) for a mission."""
        mission = self.get_mission_by_id(project_id)
        if mission is None:
            return {'success': False, 'error': 'Mission not found'}
        
        # Auto-match if not provided
        if not pilot_id:
            pilot_id = self.match_pilot_to_mission(project_id)
            if not pilot_id:
                return {'success': False, 'error': 'No suitable pilot found'}
        
        if not drone_id:
            drone_id = self.match_drone_to_mission(project_id)
            if not drone_id:
                return {'success': False, 'error': 'No suitable drone found'}
        
        # Assign pilot
        pilot_assigned = self.assign_pilot_to_mission(pilot_id, project_id)
        if not pilot_assigned:
            return {'success': False, 'error': 'Failed to assign pilot'}
        
        # Assign drone
        drone_assigned = self.assign_drone_to_mission(drone_id, project_id)
        if not drone_assigned:
            # Rollback pilot assignment
            self.roster_manager.update_pilot_status(pilot_id, 'Available', None)
            return {'success': False, 'error': 'Failed to assign drone'}
        
        return {
            'success': True,
            'pilot_id': pilot_id,
            'drone_id': drone_id,
            'project_id': project_id
        }
    
    def handle_urgent_reassignment(
        self,
        project_id: str,
        reason: str = "Urgent"
    ) -> Dict:
        """Handle urgent reassignments by finding alternative pilots/drones."""
        mission = self.get_mission_by_id(project_id)
        if mission is None:
            return {'success': False, 'error': 'Mission not found'}
        
        # Get current assignments
        current_pilots = self.roster_manager.get_current_assignments()
        current_drones = self.inventory_manager.get_deployed_drones()
        
        # Find if mission already has assignments
        assigned_pilot = current_pilots[
            current_pilots['current_assignment'] == project_id
        ]
        assigned_drone = current_drones[
            current_drones['current_assignment'] == project_id
        ]
        
        # Free up current assignments
        if len(assigned_pilot) > 0:
            old_pilot_id = assigned_pilot.iloc[0]['pilot_id']
            self.roster_manager.update_pilot_status(old_pilot_id, 'Available', None)
        
        if len(assigned_drone) > 0:
            old_drone_id = assigned_drone.iloc[0]['drone_id']
            self.inventory_manager.update_drone_status(old_drone_id, 'Available', None)
        
        # Create new assignment
        return self.create_assignment(project_id)
