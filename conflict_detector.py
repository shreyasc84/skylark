"""Conflict detection logic."""
import pandas as pd
from typing import List, Dict, Optional
from utils import (
    dates_overlap, skills_match, certifications_match,
    is_weather_compatible, calculate_pilot_cost
)
from sheets_sync import GoogleSheetsSync
from roster_manager import RosterManager
from inventory_manager import InventoryManager
from assignment_tracker import AssignmentTracker


class ConflictDetector:
    """Detect conflicts in assignments and operations."""
    
    def __init__(
        self,
        sheets_sync: GoogleSheetsSync,
        roster_manager: RosterManager,
        inventory_manager: InventoryManager,
        assignment_tracker: AssignmentTracker
    ):
        self.sheets_sync = sheets_sync
        self.roster_manager = roster_manager
        self.inventory_manager = inventory_manager
        self.assignment_tracker = assignment_tracker
    
    def detect_double_bookings(self) -> List[Dict]:
        """Detect pilots or drones assigned to overlapping projects."""
        conflicts = []
        
        # Get all assignments
        missions = self.assignment_tracker.get_active_missions()
        pilot_assignments = self.roster_manager.get_current_assignments()
        drone_assignments = self.inventory_manager.get_deployed_drones()
        
        # Debug: check what columns we have
        print(f"DEBUG detect_double_bookings - pilot_assignments columns: {list(pilot_assignments.columns) if not pilot_assignments.empty else 'EMPTY'}")
        print(f"DEBUG detect_double_bookings - drone_assignments columns: {list(drone_assignments.columns) if not drone_assignments.empty else 'EMPTY'}")
        
        # Check pilot double bookings
        if not pilot_assignments.empty and 'pilot_id' in pilot_assignments.columns:
            for pilot_id in pilot_assignments['pilot_id'].unique():
                pilot_assigns = pilot_assignments[pilot_assignments['pilot_id'] == pilot_id]
                
                if len(pilot_assigns) > 1:
                    # Multiple assignments - check for overlaps
                    assignments_list = pilot_assigns['current_assignment'].tolist()
                    for i, assign1 in enumerate(assignments_list):
                        for assign2 in assignments_list[i+1:]:
                            if 'project_id' in missions.columns:
                                mission1 = missions[missions['project_id'] == assign1]
                                mission2 = missions[missions['project_id'] == assign2]
                            else:
                                # No project_id to match, skip
                                continue
                            
                            if len(mission1) > 0 and len(mission2) > 0:
                                m1 = mission1.iloc[0]
                                m2 = mission2.iloc[0]
                                
                                if dates_overlap(
                                    m1['start_date'], m1['end_date'],
                                    m2['start_date'], m2['end_date']
                                ):
                                    conflicts.append({
                                        'type': 'double_booking',
                                        'entity_type': 'pilot',
                                        'entity_id': pilot_id,
                                        'assignments': [assign1, assign2],
                                        'severity': 'high'
                                    })
        
        # Check drone double bookings
        if not drone_assignments.empty and 'drone_id' in drone_assignments.columns:
            for drone_id in drone_assignments['drone_id'].unique():
                drone_assigns = drone_assignments[drone_assignments['drone_id'] == drone_id]
                
                if len(drone_assigns) > 1:
                    assignments_list = drone_assigns['current_assignment'].tolist()
                    for i, assign1 in enumerate(assignments_list):
                        for assign2 in assignments_list[i+1:]:
                            if 'project_id' in missions.columns:
                                mission1 = missions[missions['project_id'] == assign1]
                                mission2 = missions[missions['project_id'] == assign2]
                            else:
                                # No project_id to match, skip
                                continue
                            
                            if len(mission1) > 0 and len(mission2) > 0:
                                m1 = mission1.iloc[0]
                                m2 = mission2.iloc[0]
                                
                                if dates_overlap(
                                    m1['start_date'], m1['end_date'],
                                    m2['start_date'], m2['end_date']
                                ):
                                    conflicts.append({
                                        'type': 'double_booking',
                                        'entity_type': 'drone',
                                        'entity_id': drone_id,
                                        'assignments': [assign1, assign2],
                                        'severity': 'high'
                                    })
        
        return conflicts
    
    def detect_skill_mismatches(self) -> List[Dict]:
        """Detect pilots assigned to missions requiring skills/certs they lack."""
        conflicts = []
        
        missions = self.assignment_tracker.get_active_missions()
        pilot_assignments = self.roster_manager.get_current_assignments()
        
        if pilot_assignments.empty or 'pilot_id' not in pilot_assignments.columns:
            return conflicts
        
        for _, assignment in pilot_assignments.iterrows():
            if 'pilot_id' not in assignment or not pd.notna(assignment['pilot_id']):
                continue
            
            pilot_id = assignment['pilot_id']
            project_id = assignment.get('current_assignment', '-')
            
            if project_id == '-' or not 'project_id' in missions.columns:
                continue
            
            mission = missions[missions['project_id'] == project_id]
            if len(mission) == 0:
                continue
            
            mission = mission.iloc[0]
            pilot = self.roster_manager.get_pilot_by_id(pilot_id)
            
            if pilot is None:
                continue
            
            # Check skills
            if not skills_match(pilot.get('skills', ''), mission.get('required_skills', '')):
                conflicts.append({
                    'type': 'skill_mismatch',
                    'pilot_id': pilot_id,
                    'project_id': project_id,
                    'required_skills': mission.get('required_skills', ''),
                    'pilot_skills': pilot.get('skills', ''),
                    'severity': 'high'
                })
            
            # Check certifications
            if not certifications_match(pilot.get('certifications', ''), mission.get('required_certs', '')):
                conflicts.append({
                    'type': 'certification_mismatch',
                    'pilot_id': pilot_id,
                    'project_id': project_id,
                    'required_certs': mission.get('required_certs', ''),
                    'pilot_certs': pilot.get('certifications', ''),
                    'severity': 'high'
                })
        
        return conflicts
    
    def detect_location_mismatches(self) -> List[Dict]:
        """Detect pilots and drones in different locations."""
        conflicts = []
        
        missions = self.assignment_tracker.get_active_missions()
        pilot_assignments = self.roster_manager.get_current_assignments()
        drone_assignments = self.inventory_manager.get_deployed_drones()
        
        if pilot_assignments.empty or 'pilot_id' not in pilot_assignments.columns:
            return conflicts
        
        for _, assignment in pilot_assignments.iterrows():
            if 'pilot_id' not in assignment or not pd.notna(assignment['pilot_id']):
                continue
            
            pilot_id = assignment['pilot_id']
            project_id = assignment.get('current_assignment', '-')
            
            if project_id == '-' or not 'project_id' in missions.columns:
                continue
            
            mission = missions[missions['project_id'] == project_id]
            if len(mission) == 0:
                continue
            
            mission = mission.iloc[0]
            pilot = self.roster_manager.get_pilot_by_id(pilot_id)
            
            if pilot is None:
                continue
            
            # Check if pilot location matches mission location
            pilot_loc = str(pilot.get('location', '')).lower()
            mission_loc = str(mission.get('location', '')).lower()
            
            if pilot_loc and mission_loc and pilot_loc != mission_loc:
                conflicts.append({
                    'type': 'location_mismatch',
                    'entity_type': 'pilot',
                    'entity_id': pilot_id,
                    'project_id': project_id,
                    'entity_location': pilot.get('location', 'Unknown'),
                    'mission_location': mission.get('location', 'Unknown'),
                    'severity': 'medium'
                })
            
            # Check drone location
            if not drone_assignments.empty and 'drone_id' in drone_assignments.columns:
                drone_assign = drone_assignments[drone_assignments['current_assignment'] == project_id]
                if len(drone_assign) > 0:
                    drone = drone_assign.iloc[0]
                    drone_loc = str(drone.get('location', '')).lower()
                    if drone_loc and mission_loc and drone_loc != mission_loc:
                        conflicts.append({
                            'type': 'location_mismatch',
                            'entity_type': 'drone',
                            'entity_id': drone.get('drone_id', 'Unknown'),
                            'project_id': project_id,
                            'entity_location': drone.get('location', 'Unknown'),
                            'mission_location': mission.get('location', 'Unknown'),
                            'severity': 'medium'
                        })
        
        return conflicts
    
    def detect_budget_overruns(self) -> List[Dict]:
        """Detect missions where pilot cost exceeds budget."""
        conflicts = []
        
        missions = self.assignment_tracker.get_active_missions()
        pilot_assignments = self.roster_manager.get_current_assignments()
        
        if pilot_assignments.empty or 'pilot_id' not in pilot_assignments.columns:
            return conflicts
        
        for _, assignment in pilot_assignments.iterrows():
            if 'pilot_id' not in assignment or not pd.notna(assignment['pilot_id']):
                continue
            
            pilot_id = assignment['pilot_id']
            project_id = assignment.get('current_assignment', '-')
            
            if project_id == '-' or not 'project_id' in missions.columns:
                continue
            
            mission = missions[missions['project_id'] == project_id]
            if len(mission) == 0:
                continue
            
            mission = mission.iloc[0]
            pilot = self.roster_manager.get_pilot_by_id(pilot_id)
            
            if pilot is None:
                continue
            
            mission_budget = float(mission.get('budget', mission.get('mission_budget_inr', 0)))
            pilot_cost = self.roster_manager.calculate_cost(
                pilot_id,
                mission.get('start_date', ''),
                mission.get('end_date', '')
            )
            
            if mission_budget > 0 and pilot_cost > mission_budget:
                conflicts.append({
                    'type': 'budget_overrun',
                    'pilot_id': pilot_id,
                    'project_id': project_id,
                    'mission_budget': mission_budget,
                    'pilot_cost': pilot_cost,
                    'overrun': pilot_cost - mission_budget,
                    'severity': 'medium'
                })
        
        return conflicts
    
    def detect_weather_risks(self) -> List[Dict]:
        """Detect drones assigned to missions with incompatible weather."""
        conflicts = []
        
        missions = self.assignment_tracker.get_active_missions()
        drone_assignments = self.inventory_manager.get_deployed_drones()
        
        if drone_assignments.empty or 'drone_id' not in drone_assignments.columns:
            return conflicts
        
        for _, assignment in drone_assignments.iterrows():
            if 'drone_id' not in assignment or not pd.notna(assignment['drone_id']):
                continue
            
            drone_id = assignment['drone_id']
            project_id = assignment.get('current_assignment', '-')
            
            if project_id == '-' or not 'project_id' in missions.columns:
                continue
            
            mission = missions[missions['project_id'] == project_id]
            if len(mission) == 0:
                continue
            
            mission = mission.iloc[0]
            drone = self.inventory_manager.get_drone_by_id(drone_id)
            
            if drone is None:
                continue
            
            if not is_weather_compatible(
                drone.get('weather_resistance', ''), 
                mission.get('weather_forecast', '')
            ):
                conflicts.append({
                    'type': 'weather_risk',
                    'drone_id': drone_id,
                    'project_id': project_id,
                    'drone_weather_resistance': drone.get('weather_resistance', ''),
                    'mission_weather': mission.get('weather_forecast', ''),
                    'severity': 'high'
                })
        
        return conflicts
    
    def detect_maintenance_issues(self) -> List[Dict]:
        """Detect drones assigned but due for maintenance."""
        conflicts = []
        
        try:
            maintenance_due = self.inventory_manager.get_maintenance_due_drones()
            drone_assignments = self.inventory_manager.get_deployed_drones()
            
            if maintenance_due.empty or 'drone_id' not in maintenance_due.columns:
                return conflicts
            
            for _, drone in maintenance_due.iterrows():
                if 'drone_id' not in drone or not pd.notna(drone['drone_id']):
                    continue
                
                drone_id = drone['drone_id']
                if not drone_assignments.empty and 'drone_id' in drone_assignments.columns:
                    assigned = drone_assignments[drone_assignments['drone_id'] == drone_id]
                    
                    if len(assigned) > 0:
                        conflicts.append({
                            'type': 'maintenance_due',
                            'drone_id': drone_id,
                            'maintenance_due_date': drone.get('maintenance_due', 'Unknown'),
                            'current_assignment': assigned.iloc[0].get('current_assignment', '-'),
                            'severity': 'high'
                        })
        except Exception as e:
            print(f"DEBUG: Error in detect_maintenance_issues: {e}")
        
        return conflicts
    
    def detect_all_conflicts(self) -> Dict[str, List[Dict]]:
        """Detect all types of conflicts."""
        return {
            'double_bookings': self.detect_double_bookings(),
            'skill_mismatches': self.detect_skill_mismatches(),
            'location_mismatches': self.detect_location_mismatches(),
            'budget_overruns': self.detect_budget_overruns(),
            'weather_risks': self.detect_weather_risks(),
            'maintenance_issues': self.detect_maintenance_issues()
        }
    
    def get_conflict_summary(self) -> str:
        """Get a human-readable summary of all conflicts."""
        conflicts = self.detect_all_conflicts()
        
        summary_parts = []
        
        for conflict_type, conflict_list in conflicts.items():
            if len(conflict_list) > 0:
                summary_parts.append(f"\n{conflict_type.replace('_', ' ').title()}: {len(conflict_list)}")
                for conflict in conflict_list[:3]:  # Show first 3
                    summary_parts.append(f"  - {conflict}")
        
        if not summary_parts:
            return "No conflicts detected."
        
        return "\n".join(summary_parts)
