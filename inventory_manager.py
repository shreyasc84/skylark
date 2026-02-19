"""Drone inventory management logic."""
import pandas as pd
from typing import List, Dict, Optional
from utils import is_maintenance_due, is_weather_compatible
from sheets_sync import GoogleSheetsSync


class InventoryManager:
    """Manage drone inventory operations."""
    
    def __init__(self, sheets_sync: GoogleSheetsSync):
        self.sheets_sync = sheets_sync
        self._fleet = None
        self._refresh_fleet()
    
    def _refresh_fleet(self):
        """Refresh fleet data from Google Sheets."""
        self._fleet = self.sheets_sync.get_drone_fleet()
        
        # Debug: print available columns
        if self._fleet is not None and not self._fleet.empty:
            print(f"DEBUG: Fleet columns available: {list(self._fleet.columns)}")
        
        # Handle empty dataframe
        if self._fleet is None or self._fleet.empty:
            print("WARNING: Fleet data is empty")
            self._fleet = pd.DataFrame(columns=[
                'drone_id', 'model', 'capabilities', 'status', 
                'location', 'current_assignment', 'weather_resistance', 'maintenance_due'
            ])
        
        # Ensure drone_id column exists
        if 'drone_id' not in self._fleet.columns:
            # Try to find alternate ID column names
            id_candidates = [col for col in self._fleet.columns if 'id' in col.lower() or 'drone' in col.lower()]
            if id_candidates:
                alt_id = id_candidates[0]
                self._fleet['drone_id'] = self._fleet[alt_id]
            else:
                # Create drone_id from index
                if len(self._fleet) > 0:
                    self._fleet['drone_id'] = [f"D{i:03d}" for i in range(len(self._fleet))]
                else:
                    self._fleet['drone_id'] = []
        
        # Ensure required columns exist
        if 'current_assignment' not in self._fleet.columns:
            self._fleet['current_assignment'] = '-'
        if 'status' not in self._fleet.columns:
            self._fleet['status'] = 'Available'
        if 'weather_resistance' not in self._fleet.columns:
            self._fleet['weather_resistance'] = ''
        if 'maintenance_due' not in self._fleet.columns:
            self._fleet['maintenance_due'] = 'No'
    
    def query_drones(
        self,
        capabilities: Optional[List[str]] = None,
        status: Optional[str] = None,
        location: Optional[str] = None,
        weather_forecast: Optional[str] = None
    ) -> pd.DataFrame:
        """Query drones by various criteria."""
        self._refresh_fleet()
        df = self._fleet.copy()
        
        if capabilities:
            df = df[df['capabilities'].apply(
                lambda x: any(cap in str(x) for cap in capabilities)
            )]
        
        if status:
            df = df[df['status'].str.contains(status, case=False, na=False)]
        
        if location:
            df = df[df['location'].str.contains(location, case=False, na=False)]
        
        if weather_forecast:
            df = df[df.apply(
                lambda row: is_weather_compatible(
                    row['weather_resistance'], 
                    weather_forecast
                ),
                axis=1
            )]
        
        return df
    
    def get_available_drones(self) -> pd.DataFrame:
        """Get all available drones."""
        return self.query_drones(status='Available')
    
    def get_drone_by_id(self, drone_id: str) -> Optional[pd.Series]:
        """Get drone by ID."""
        self._refresh_fleet()
        matches = self._fleet[self._fleet['drone_id'] == drone_id]
        return matches.iloc[0] if len(matches) > 0 else None
    
    def get_drones_by_weather(self, weather_forecast: str) -> pd.DataFrame:
        """Get drones compatible with weather forecast."""
        return self.query_drones(weather_forecast=weather_forecast, status='Available')
    
    def get_maintenance_due_drones(self) -> pd.DataFrame:
        """Get drones with maintenance due."""
        self._refresh_fleet()
        return self._fleet[
            self._fleet['maintenance_due'].apply(is_maintenance_due)
        ]
    
    def get_deployed_drones(self) -> pd.DataFrame:
        """Get all deployed drones."""
        self._refresh_fleet()
        return self._fleet[
            (self._fleet['current_assignment'].notna()) & 
            (self._fleet['current_assignment'] != '-')
        ]
    
    def update_drone_status(
        self,
        drone_id: str,
        status: str,
        assignment: Optional[str] = None
    ) -> bool:
        """Update drone status and sync to Google Sheets."""
        valid_statuses = ['Available', 'Assigned', 'Maintenance', 'Unavailable']
        
        if status not in valid_statuses:
            return False
        
        self.sheets_sync.update_drone_status(drone_id, status, assignment)
        self._refresh_fleet()
        return True
    
    def is_drone_available(self, drone_id: str) -> bool:
        """Check if drone is available."""
        drone = self.get_drone_by_id(drone_id)
        if drone is None:
            return False
        
        return drone['status'] == 'Available'
    
    def find_matching_drones(
        self,
        required_capabilities: str,
        location: str,
        weather_forecast: str
    ) -> pd.DataFrame:
        """Find drones matching mission requirements."""
        capabilities_list = [c.strip() for c in required_capabilities.split(",")]
        
        df = self.query_drones(
            capabilities=capabilities_list,
            status='Available',
            location=location,
            weather_forecast=weather_forecast
        )
        
        # Filter out drones in maintenance
        df = df[~df['status'].str.contains('Maintenance', case=False, na=False)]
        
        return df
