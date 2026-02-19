"""Google Sheets integration for 2-way sync."""
import os
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetsSync:
    """Handle Google Sheets read/write operations.

    If Google Sheets credentials or Sheet IDs are not configured, this class
    will transparently fall back to using local CSV files only.
    """
    
    def __init__(self):
        self.creds = None
        self.service = None

        # Only attempt Google Sheets auth if at least one Sheet ID is provided.
        pilot_sheet = os.getenv('PILOT_ROSTER_SHEET_ID')
        drone_sheet = os.getenv('DRONE_FLEET_SHEET_ID')
        missions_sheet = os.getenv('MISSIONS_SHEET_ID')

        if any([pilot_sheet, drone_sheet, missions_sheet]):
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'credentials.json')
        token_path = 'token.pickle'
        
        # Load existing token
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    # If credentials are missing, disable Sheets integration and
                    # rely on local CSV fallbacks instead of crashing.
                    print(
                        f"Warning: Credentials file not found at {creds_path}. "
                        "Google Sheets sync will be disabled; using local CSV files only."
                    )
                    self.creds = None
                    self.service = None
                    return
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        self.service = build('sheets', 'v4', credentials=self.creds)
    
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
        """Read data from Google Sheet."""
        # If service is not initialized, fall back immediately
        if self.service is None:
            return pd.DataFrame()
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
                return pd.DataFrame()
            
            # First row as headers
            headers = values[0]
            data = values[1:] if len(values) > 1 else []
            
            # Pad rows to match header length
            padded_data = [row + [''] * (len(headers) - len(row)) for row in data]
            
            return pd.DataFrame(padded_data, columns=headers)
        
        except HttpError as error:
            print(f"An error occurred: {error}")
            return pd.DataFrame()
    
    def write_sheet(self, sheet_id: str, range_name: str, values: List[List]):
        """Write data to Google Sheet."""
        if self.service is None:
            # No remote service available; act as no-op
            print("Warning: Google Sheets service not initialized. Skipping write.")
            return None
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
            print(f"An error occurred: {error}")
            return None
    
    def update_cell(self, sheet_id: str, range_name: str, value: str):
        """Update a single cell in Google Sheet."""
        return self.write_sheet(sheet_id, range_name, [[value]])
    
    def get_pilot_roster(self) -> pd.DataFrame:
        """Get pilot roster from Google Sheets, fallback to CSV."""
        sheet_id = os.getenv('PILOT_ROSTER_SHEET_ID')
        
        # Try Google Sheets first
        if sheet_id:
            df = self.read_sheet(sheet_id)
            if df is not None and not df.empty:
                return df
        
        # Fallback to local CSV
        try:
            if os.path.exists('pilot_roster.csv'):
                return pd.read_csv('pilot_roster.csv')
        except Exception as e:
            print(f"Failed to read pilot_roster.csv: {e}")
        
        return pd.DataFrame()
    
    def get_drone_fleet(self) -> pd.DataFrame:
        """Get drone fleet from Google Sheets, fallback to CSV."""
        sheet_id = os.getenv('DRONE_FLEET_SHEET_ID')
        
        # Try Google Sheets first
        if sheet_id:
            df = self.read_sheet(sheet_id)
            if df is not None and not df.empty:
                return df
        
        # Fallback to local CSV
        try:
            if os.path.exists('drone_fleet.csv'):
                return pd.read_csv('drone_fleet.csv')
        except Exception as e:
            print(f"Failed to read drone_fleet.csv: {e}")
        
        return pd.DataFrame()
    
    def get_missions(self) -> pd.DataFrame:
        """Get missions from Google Sheets, fallback to CSV."""
        sheet_id = os.getenv('MISSIONS_SHEET_ID')
        
        # Try Google Sheets first
        if sheet_id:
            df = self.read_sheet(sheet_id)
            if df is not None and not df.empty:
                return df
        
        # Fallback to local CSV
        try:
            if os.path.exists('missions.csv'):
                return pd.read_csv('missions.csv')
        except Exception as e:
            print(f"Failed to read missions.csv: {e}")
        
        return pd.DataFrame()
    
    def update_pilot_status(self, pilot_id: str, status: str, assignment: str = None):
        """Update pilot status in Google Sheets."""
        sheet_id = os.getenv('PILOT_ROSTER_SHEET_ID')
        if not sheet_id:
            # Fallback: update local CSV
            df = pd.read_csv('pilot_roster.csv')
            idx = df[df['pilot_id'] == pilot_id].index
            if len(idx) > 0:
                df.loc[idx[0], 'status'] = status
                if assignment:
                    df.loc[idx[0], 'current_assignment'] = assignment
                df.to_csv('pilot_roster.csv', index=False)
            return
        
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
            self.update_cell(sheet_id, assignment_range, assignment)
    
    def update_drone_status(self, drone_id: str, status: str, assignment: str = None):
        """Update drone status in Google Sheets."""
        sheet_id = os.getenv('DRONE_FLEET_SHEET_ID')
        if not sheet_id:
            # Fallback: update local CSV
            df = pd.read_csv('drone_fleet.csv')
            idx = df[df['drone_id'] == drone_id].index
            if len(idx) > 0:
                df.loc[idx[0], 'status'] = status
                if assignment:
                    df.loc[idx[0], 'current_assignment'] = assignment
                df.to_csv('drone_fleet.csv', index=False)
            return
        
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
