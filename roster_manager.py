"""Pilot roster management logic."""
import pandas as pd
from typing import List, Dict, Optional
from utils import (
    parse_skills, parse_certifications, skills_match, 
    certifications_match, calculate_pilot_cost, dates_overlap
)
from sheets_sync import GoogleSheetsSync


class RosterManager:
    """Manage pilot roster operations."""
    
    def __init__(self, sheets_sync: GoogleSheetsSync):
        self.sheets_sync = sheets_sync
        self._roster = None
        self._refresh_roster()
    
    def _refresh_roster(self):
        """Refresh roster data from Google Sheets."""
        self._roster = self.sheets_sync.get_pilot_roster()
        
        # Debug: print available columns
        if self._roster is not None and not self._roster.empty:
            print(f"DEBUG: Roster columns available: {list(self._roster.columns)}")
        
        # Handle empty dataframe
        if self._roster is None or self._roster.empty:
            print("WARNING: Roster data is empty")
            self._roster = pd.DataFrame(columns=[
                'pilot_id', 'name', 'skills', 'certifications', 
                'hourly_rate', 'location', 'status', 'current_assignment'
            ])
        
        # Ensure pilot_id column exists
        if 'pilot_id' not in self._roster.columns:
            # Try to find alternate ID column names
            id_candidates = [col for col in self._roster.columns if 'id' in col.lower()]
            if id_candidates:
                alt_id = id_candidates[0]
                self._roster['pilot_id'] = self._roster[alt_id]
            else:
                # Create pilot_id from index or first column
                if len(self._roster) > 0:
                    self._roster['pilot_id'] = [f"P{i:03d}" for i in range(len(self._roster))]
                else:
                    self._roster['pilot_id'] = []
        
        # Ensure required columns exist
        if 'current_assignment' not in self._roster.columns:
            self._roster['current_assignment'] = '-'
        if 'status' not in self._roster.columns:
            self._roster['status'] = 'Available'
    
    def query_pilots(
        self, 
        skills: Optional[List[str]] = None,
        certifications: Optional[List[str]] = None,
        location: Optional[str] = None,
        status: Optional[str] = None
    ) -> pd.DataFrame:
        """Query pilots by various criteria."""
        self._refresh_roster()
        df = self._roster.copy()
        
        if skills:
            df = df[df['skills'].apply(
                lambda x: any(skill in parse_skills(x) for skill in skills)
            )]
        
        if certifications:
            df = df[df['certifications'].apply(
                lambda x: any(cert in parse_certifications(x) for cert in certifications)
            )]
        
        if location:
            df = df[df['location'].str.contains(location, case=False, na=False)]
        
        if status:
            df = df[df['status'].str.contains(status, case=False, na=False)]
        
        return df
    
    def get_available_pilots(self) -> pd.DataFrame:
        """Get all available pilots."""
        return self.query_pilots(status='Available')
    
    def get_pilot_by_id(self, pilot_id: str) -> Optional[pd.Series]:
        """Get pilot by ID."""
        self._refresh_roster()
        matches = self._roster[self._roster['pilot_id'] == pilot_id]
        return matches.iloc[0] if len(matches) > 0 else None
    
    def calculate_cost(self, pilot_id: str, start_date: str, end_date: str) -> float:
        """Calculate total cost for a pilot for a mission."""
        pilot = self.get_pilot_by_id(pilot_id)
        if pilot is None:
            return 0.0
        
        daily_rate = float(pilot.get('daily_rate_inr', 0))
        return calculate_pilot_cost(daily_rate, start_date, end_date)
    
    def get_current_assignments(self) -> pd.DataFrame:
        """Get all pilots with current assignments."""
        self._refresh_roster()
        return self._roster[
            (self._roster['current_assignment'].notna()) & 
            (self._roster['current_assignment'] != '-')
        ]
    
    def update_pilot_status(
        self, 
        pilot_id: str, 
        status: str, 
        assignment: Optional[str] = None
    ) -> bool:
        """Update pilot status and sync to Google Sheets."""
        valid_statuses = ['Available', 'Assigned', 'On Leave', 'Unavailable']
        
        if status not in valid_statuses:
            return False
        
        self.sheets_sync.update_pilot_status(pilot_id, status, assignment)
        self._refresh_roster()
        return True
    
    def is_pilot_available(
        self, 
        pilot_id: str, 
        start_date: str, 
        end_date: str
    ) -> bool:
        """Check if pilot is available for given date range."""
        pilot = self.get_pilot_by_id(pilot_id)
        if pilot is None:
            return False
        
        # Check status
        if pilot['status'] not in ['Available']:
            return False
        
        # Check if pilot has overlapping assignments
        assignments = self.get_current_assignments()
        pilot_assignments = assignments[assignments['pilot_id'] == pilot_id]
        
        # For now, if pilot has any assignment, they're not available
        # In a full implementation, we'd check date overlaps
        if len(pilot_assignments) > 0:
            return False
        
        return True
    
    def find_matching_pilots(
        self,
        required_skills: str,
        required_certs: str,
        location: str,
        start_date: str,
        end_date: str,
        max_budget: Optional[float] = None
    ) -> pd.DataFrame:
        """Find pilots matching mission requirements."""
        self._refresh_roster()
        
        # Filter by skills
        df = self._roster[
            self._roster['skills'].apply(
                lambda x: skills_match(x, required_skills)
            )
        ]
        
        # Filter by certifications
        df = df[
            df['certifications'].apply(
                lambda x: certifications_match(x, required_certs)
            )
        ]
        
        # Filter by location
        df = df[df['location'].str.contains(location, case=False, na=False)]
        
        # Filter by availability
        df = df[df['status'] == 'Available']
        
        # Filter by budget if specified
        if max_budget:
            df = df[
                df.apply(
                    lambda row: calculate_pilot_cost(
                        float(row['daily_rate_inr']), 
                        start_date, 
                        end_date
                    ) <= max_budget,
                    axis=1
                )
            ]
        
        return df
