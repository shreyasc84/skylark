"""Google Sheets integration for 2-way sync using Service Account."""
import os
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, List, Dict

# Try to import streamlit for secrets access
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_secret(key: str, default=None):
    """Get secret from Streamlit secrets or environment variables."""
    if HAS_STREAMLIT:
        try:
            return st.secrets.get(key, default)
        except Exception:
            pass
    return os.getenv(key, default)

def get_google_credentials_dict():
    """Get Google credentials dict from Streamlit secrets."""
    if HAS_STREAMLIT:
        try:
            if "google_credentials" in st.secrets:
                return dict(st.secrets["google_credentials"])
        except Exception as e:
            print(f"Error reading google_credentials from secrets: {e}")
    return None

class GoogleSheetsSync:
    """Handle Google Sheets read/write operations using Service Account.
    
    Reads credentials from Streamlit secrets (google_credentials section).
    No local CSV fallback - Google Sheets is the only data source.
    """
    
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API using Service Account."""
        try:
            creds_dict = get_google_credentials_dict()
            
            if not creds_dict:
                print("ERROR: google_credentials not found in Streamlit secrets!")
                print("Please configure google_credentials in .streamlit/secrets.toml")
                return
            
            # Create credentials from service account info
            self.creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=SCOPES
            )
            
            self.service = build('sheets', 'v4', credentials=self.creds)
            print("✓ Google Sheets API initialized successfully")
            
        except Exception as e:
            print(f"ERROR: Failed to authenticate with Google Sheets: {e}")
            self.creds = None
            self.service = None
    
    def _get_first_sheet_name(self, sheet_id: str) -> str:
        """Get the name of the first sheet in a spreadsheet."""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=sheet_id
            ).execute()
            sheets = spreadsheet.get('sheets', [])
            if sheets:
                return sheets[0]['properties']['title']
        except Exception as e:
            print(f"Warning: Could not get sheet name: {e}")
        return 'Sheet1'  # fallback
    
    def read_sheet(self, sheet_id: str, range_name: str = None) -> pd.DataFrame:
        """Read data from Google Sheet. Raises error if unable to read."""
        if self.service is None:
            raise RuntimeError("Google Sheets service not initialized. Check credentials in secrets.toml")
        
        try:
            if range_name:
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=range_name
                ).execute()
            else:
                # Auto-discover the first sheet name instead of hardcoding 'Sheet1'
                first_sheet = self._get_first_sheet_name(sheet_id)
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=first_sheet
                ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print(f"Warning: Sheet {sheet_id} is empty")
                return pd.DataFrame()
            
            # First row as headers
            headers = values[0]
            data = values[1:] if len(values) > 1 else []
            
            # Pad rows to match header length
            padded_data = [row + [''] * (len(headers) - len(row)) for row in data]
            
            df = pd.DataFrame(padded_data, columns=headers)
            print(f"✓ Read {len(df)} rows from sheet")
            return df
        
        except HttpError as error:
            raise RuntimeError(f"Failed to read Google Sheet: {error}")
        except Exception as e:
            raise RuntimeError(f"Error reading sheet: {e}")
    
    def write_sheet(self, sheet_id: str, range_name: str, values: List[List]):
        """Write data to Google Sheet."""
        if self.service is None:
            raise RuntimeError("Google Sheets service not initialized. Check credentials in secrets.toml")
        try:
            body = {'values': values}
            result = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            return result
        except HttpError as error:
            raise RuntimeError(f"Failed to write to Google Sheet: {error}")
    
    def update_cell(self, sheet_id: str, range_name: str, value: str):
        """Update a single cell in Google Sheet."""
        return self.write_sheet(sheet_id, range_name, [[value]])
    
    def get_pilot_roster(self) -> pd.DataFrame:
        """Get pilot roster from Google Sheets (online only)."""
        sheet_id = get_secret('PILOT_ROSTER_SHEET_ID')
        
        if not sheet_id:
            raise RuntimeError("PILOT_ROSTER_SHEET_ID not configured in secrets.toml")
        
        return self.read_sheet(sheet_id)
    
    def get_drone_fleet(self) -> pd.DataFrame:
        """Get drone fleet from Google Sheets (online only)."""
        sheet_id = get_secret('DRONE_FLEET_SHEET_ID')
        
        if not sheet_id:
            raise RuntimeError("DRONE_FLEET_SHEET_ID not configured in secrets.toml")
        
        return self.read_sheet(sheet_id)
    
    def get_missions(self) -> pd.DataFrame:
        """Get missions from Google Sheets (online only)."""
        sheet_id = get_secret('MISSIONS_SHEET_ID')
        
        if not sheet_id:
            raise RuntimeError("MISSIONS_SHEET_ID not configured in secrets.toml")
        
        return self.read_sheet(sheet_id)
    
    def update_pilot_status(self, pilot_id: str, status: str, assignment: str = None):
        """Update pilot status in Google Sheets (online only)."""
        sheet_id = get_secret('PILOT_ROSTER_SHEET_ID')
        if not sheet_id:
            raise RuntimeError("PILOT_ROSTER_SHEET_ID not configured in secrets.toml")
        
        # Read current data
        df = self.get_pilot_roster()
        
        # Find row index
        idx = df[df['pilot_id'] == pilot_id].index
        if len(idx) == 0:
            return
        
        row_num = idx[0] + 2  # +1 for header, +1 for 1-indexing
        
        # Get the actual sheet name
        first_sheet = self._get_first_sheet_name(sheet_id)
        
        # Find column indices dynamically
        status_col_idx = None
        assignment_col_idx = None
        
        if 'status' in df.columns:
            status_col_idx = list(df.columns).index('status')
        if 'current_assignment' in df.columns:
            assignment_col_idx = list(df.columns).index('current_assignment')
        
        # Convert column index to letter (0=A, 1=B, etc.)
        def col_idx_to_letter(idx):
            return chr(ord('A') + idx)
        
        # Update status
        if status_col_idx is not None:
            status_col_letter = col_idx_to_letter(status_col_idx)
            status_range = f'{first_sheet}!{status_col_letter}{row_num}'
            self.update_cell(sheet_id, status_range, status)
        
        # Update assignment if provided
        if assignment and assignment_col_idx is not None:
            assignment_col_letter = col_idx_to_letter(assignment_col_idx)
            assignment_range = f'{first_sheet}!{assignment_col_letter}{row_num}'
            self.update_cell(sheet_id, assignment_range, assignment)
    
    def update_drone_status(self, drone_id: str, status: str, assignment: str = None):
        """Update drone status in Google Sheets (online only)."""
        sheet_id = get_secret('DRONE_FLEET_SHEET_ID')
        if not sheet_id:
            raise RuntimeError("DRONE_FLEET_SHEET_ID not configured in secrets.toml")
        
        # Read current data
        df = self.get_drone_fleet()
        
        # Find row index
        idx = df[df['drone_id'] == drone_id].index
        if len(idx) == 0:
            return
        
        row_num = idx[0] + 2
        
        # Get the actual sheet name
        first_sheet = self._get_first_sheet_name(sheet_id)
        
        # Find column indices dynamically
        status_col_idx = None
        assignment_col_idx = None
        
        if 'status' in df.columns:
            status_col_idx = list(df.columns).index('status')
        if 'current_assignment' in df.columns:
            assignment_col_idx = list(df.columns).index('current_assignment')
        
        # Convert column index to letter (0=A, 1=B, etc.)
        def col_idx_to_letter(idx):
            return chr(ord('A') + idx)
        
        # Update status
        if status_col_idx is not None:
            status_col_letter = col_idx_to_letter(status_col_idx)
            status_range = f'{first_sheet}!{status_col_letter}{row_num}'
            self.update_cell(sheet_id, status_range, status)
        
        # Update assignment if provided
        if assignment and assignment_col_idx is not None:
            assignment_col_letter = col_idx_to_letter(assignment_col_idx)
            assignment_range = f'{first_sheet}!{assignment_col_letter}{row_num}'
            self.update_cell(sheet_id, assignment_range, assignment)
