import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import time

# Set page config
st.set_page_config(
    page_title="NFL Fantasy Football Draft Board",
    page_icon="🏈",
    layout="wide"
)

# Initialize session state for drafted players and Sleeper data
if 'drafted_players' not in st.session_state:
    st.session_state.drafted_players = set()
if 'sleeper_picks' not in st.session_state:
    st.session_state.sleeper_picks = {}
if 'sleeper_league_info' not in st.session_state:
    st.session_state.sleeper_league_info = None
if 'sleeper_draft_info' not in st.session_state:
    st.session_state.sleeper_draft_info = None
if 'connection_type' not in st.session_state:
    st.session_state.connection_type = None
if 'current_league_id' not in st.session_state:
    st.session_state.current_league_id = None
if 'current_draft_id' not in st.session_state:
    st.session_state.current_draft_id = None
if 'auto_sync_active' not in st.session_state:
    st.session_state.auto_sync_active = False
if 'last_sync_time' not in st.session_state:
    st.session_state.last_sync_time = 0
if 'sync_in_progress' not in st.session_state:
    st.session_state.sync_in_progress = False
if 'url_params_processed' not in st.session_state:
    st.session_state.url_params_processed = False

def get_url_params():
    """Extract URL parameters from the current page"""
    try:
        # Get URL parameters using st.query_params (Streamlit 1.28+)
        return st.query_params
    except AttributeError:
        # Fallback for older Streamlit versions
        return {}

def set_url_params(**params):
    """Set URL parameters"""
    try:
        # Set URL parameters using st.query_params (Streamlit 1.28+)
        for key, value in params.items():
            if value:
                st.query_params[key] = value
            elif key in st.query_params:
                del st.query_params[key]
    except AttributeError:
        # Fallback for older Streamlit versions - just pass
        pass

def process_url_params():
    """Process URL parameters and auto-connect if league_id or draft_id is provided"""
    if st.session_state.url_params_processed:
        return
    
    params = get_url_params()
    
    # Check for league_id parameter
    if 'league_id' in params:
        league_id = params['league_id']
        if league_id and league_id != st.session_state.current_league_id:
            with st.spinner("Auto-connecting to Sleeper League from URL..."):
                st.session_state.current_league_id = league_id
                st.session_state.current_draft_id = None
                
                # Fetch league info
                league_info = get_sleeper_league_info(league_id)
                if league_info:
                    st.session_state.sleeper_league_info = league_info
                    st.session_state.sleeper_draft_info = None
                    st.session_state.connection_type = "league"
                    
                    # Fetch drafted players
                    sleeper_picks = get_sleeper_draft_picks(league_id)
                    st.session_state.sleeper_picks = sleeper_picks
                    st.session_state.drafted_players.update(sleeper_picks.keys())
                    
                    st.success(f"Auto-connected to: {league_info.get('name', 'Unknown League')}")
                    st.success(f"Loaded {len(sleeper_picks)} drafted players")
                else:
                    st.error(f"Could not connect to league ID: {league_id}")
    
    # Check for draft_id parameter
    elif 'draft_id' in params:
        draft_id = params['draft_id']
        if draft_id and draft_id != st.session_state.current_draft_id:
            with st.spinner("Auto-connecting to Mock Draft from URL..."):
                st.session_state.current_draft_id = draft_id
                st.session_state.current_league_id = None
                
                # Fetch draft info
                draft_info = get_sleeper_draft_info(draft_id)
                if draft_info:
                    st.session_state.sleeper_draft_info = draft_info
                    st.session_state.sleeper_league_info = None
                    st.session_state.connection_type = "mock"
                    
                    # Fetch drafted players
                    sleeper_picks = get_sleeper_draft_picks_by_id(draft_id)
                    st.session_state.sleeper_picks = sleeper_picks
                    st.session_state.drafted_players.update(sleeper_picks.keys())
                    
                    draft_type = draft_info.get('type', 'unknown')
                    st.success(f"Auto-connected to: {draft_type.title()} Draft")
                    st.success(f"Loaded {len(sleeper_picks)} drafted players")
                else:
                    st.error(f"Could not connect to draft ID: {draft_id}")
    
    st.session_state.url_params_processed = True

@st.cache_data
def get_sleeper_draft_info(draft_id):
    """Fetch draft information directly by draft ID (works for mock drafts and league drafts)"""
    try:
        response = requests.get(f"https://api.sleeper.app/v1/draft/{draft_id}")
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching draft info: {e}")
        return None

@st.cache_data
def get_sleeper_draft_picks_by_id(draft_id):
    """Fetch draft picks directly by draft ID (works for mock drafts and league drafts)"""
    try:
        # Fetch draft picks
        response = requests.get(f"https://api.sleeper.app/v1/draft/{draft_id}/picks")
        if response.status_code == 200:
            picks = response.json()
            
            # Get player info to map player IDs to names
            players_response = requests.get("https://api.sleeper.app/v1/players/nfl")
            if players_response.status_code == 200:
                players_data = players_response.json()
                
                # Create a mapping of picks to player names
                drafted_players = {}
                for pick in picks:
                    player_id = pick.get('player_id')
                    if player_id and player_id in players_data:
                        player_info = players_data[player_id]
                        full_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()
                        drafted_players[full_name] = {
                            'pick_no': pick.get('pick_no'),
                            'round': pick.get('round'),
                            'picked_by': pick.get('picked_by'),
                            'team': player_info.get('team', ''),
                            'position': player_info.get('position', '')
                        }
                
                return drafted_players
        
        return {}
    except Exception as e:
        st.error(f"Error fetching draft picks: {e}")
        return {}

@st.cache_data
def get_sleeper_league_info(league_id):
    """Fetch league information from Sleeper API"""
    try:
        response = requests.get(f"https://api.sleeper.app/v1/league/{league_id}")
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching league info: {e}")
        return None

@st.cache_data
def get_sleeper_draft_picks(league_id):
    """Fetch draft picks from Sleeper API using league ID"""
    try:
        # First get the league info to find draft IDs
        league_info = get_sleeper_league_info(league_id)
        if not league_info:
            return {}
        
        # Get the most recent draft ID
        draft_id = league_info.get('draft_id')
        if not draft_id:
            st.warning("No draft found for this league")
            return {}
        
        return get_sleeper_draft_picks_by_id(draft_id)
        
    except Exception as e:
        st.error(f"Error fetching draft picks: {e}")
        return {}

@st.cache_data
def get_sleeper_users(league_id):
    """Fetch league users from Sleeper API"""
    try:
        response = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/users")
        if response.status_code == 200:
            users = response.json()
            return {user['user_id']: user['display_name'] for user in users}
        return {}
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return {}

@st.cache_data
def load_data(uploaded_file=None):
    """Load and preprocess the NFL projections data"""
    try:
        if uploaded_file is not None:
            # Load from uploaded file
            df = pd.read_csv(uploaded_file)
        else:
            # Try to load from local file
            df = pd.read_csv('2025 NFL Projections  ALL.csv')
        
        # Clean up the data
        df = df.dropna(subset=['player', 'position'])
        
        # Convert numeric columns to proper types
        numeric_columns = ['passingYards', 'passingTouchdowns', 'interceptionsThrown', 
                          'rushingAttempts', 'rushingYards', 'rushingTouchdowns',
                          'receptions', 'targets', 'receivingYards', 'receivingTouchdowns',
                          'fantasy', 'positionRank', 'overallRank']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Add drafted status column
        df['drafted'] = df['player'].isin(st.session_state.drafted_players)
        
        return df
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def format_stat(value, stat_type="float"):
    """Format statistics for display"""
    if pd.isna(value) or value == 0:
        return "-"
    if stat_type == "float":
        return f"{value:.1f}"
    return str(int(value))

def get_team_logo_url(team_name):
    """Get team logo URL - using ESPN logos"""
    team_logos = {
        'Arizona Cardinals': 'https://a.espncdn.com/i/teamlogos/nfl/500/ari.png',
        'Atlanta Falcons': 'https://a.espncdn.com/i/teamlogos/nfl/500/atl.png',
        'Baltimore Ravens': 'https://a.espncdn.com/i/teamlogos/nfl/500/bal.png',
        'Buffalo Bills': 'https://a.espncdn.com/i/teamlogos/nfl/500/buf.png',
        'Carolina Panthers': 'https://a.espncdn.com/i/teamlogos/nfl/500/car.png',
        'Chicago Bears': 'https://a.espncdn.com/i/teamlogos/nfl/500/chi.png',
        'Cincinnati Bengals': 'https://a.espncdn.com/i/teamlogos/nfl/500/cin.png',
        'Cleveland Browns': 'https://a.espncdn.com/i/teamlogos/nfl/500/cle.png',
        'Dallas Cowboys': 'https://a.espncdn.com/i/teamlogos/nfl/500/dal.png',
        'Denver Broncos': 'https://a.espncdn.com/i/teamlogos/nfl/500/den.png',
        'Detroit Lions': 'https://a.espncdn.com/i/teamlogos/nfl/500/det.png',
        'Green Bay Packers': 'https://a.espncdn.com/i/teamlogos/nfl/500/gb.png',
        'Houston Texans': 'https://a.espncdn.com/i/teamlogos/nfl/500/hou.png',
        'Indianapolis Colts': 'https://a.espncdn.com/i/teamlogos/nfl/500/ind.png',
        'Jacksonville Jaguars': 'https://a.espncdn.com/i/teamlogos/nfl/500/jax.png',
        'Kansas City Chiefs': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png',
        'Las Vegas Raiders': 'https://a.espncdn.com/i/teamlogos/nfl/500/lv.png',
        'Los Angeles Chargers': 'https://a.espncdn.com/i/teamlogos/nfl/500/lac.png',
        'Los Angeles Rams': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png',
        'Miami Dolphins': 'https://a.espncdn.com/i/teamlogos/nfl/500/mia.png',
        'Minnesota Vikings': 'https://a.espncdn.com/i/teamlogos/nfl/500/min.png',
        'New England Patriots': 'https://a.espncdn.com/i/teamlogos/nfl/500/ne.png',
        'New Orleans Saints': 'https://a.espncdn.com/i/teamlogos/nfl/500/no.png',
        'New York Giants': 'https://a.espncdn.com/i/teamlogos/nfl/500/nyg.png',
        'New York Jets': 'https://a.espncdn.com/i/teamlogos/nfl/500/nyj.png',
        'Philadelphia Eagles': 'https://a.espncdn.com/i/teamlogos/nfl/500/phi.png',
        'Pittsburgh Steelers': 'https://a.espncdn.com/i/teamlogos/nfl/500/pit.png',
        'San Francisco 49ers': 'https://a.espncdn.com/i/teamlogos/nfl/500/sf.png',
        'Seattle Seahawks': 'https://a.espncdn.com/i/teamlogos/nfl/500/sea.png',
        'Tampa Bay Buccaneers': 'https://a.espncdn.com/i/teamlogos/nfl/500/tb.png',
        'Tennessee Titans': 'https://a.espncdn.com/i/teamlogos/nfl/500/ten.png',
        'Washington Commanders': 'https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png'
    }
    return team_logos.get(team_name, '')

def perform_sync(connection_type, league_id=None, draft_id=None):
    """Perform sync operation for either league or mock draft"""
    if st.session_state.sync_in_progress:
        return False, "Sync already in progress"
    
    try:
        st.session_state.sync_in_progress = True
        
        if connection_type == "league" and league_id:
            # Clear cache and fetch league data - ensure cache is actually cleared
            st.cache_data.clear()  # Clear all cached data
            sleeper_picks = get_sleeper_draft_picks(league_id)
        elif connection_type == "mock" and draft_id:
            # Clear cache and fetch mock draft data - ensure cache is actually cleared
            st.cache_data.clear()  # Clear all cached data
            sleeper_picks = get_sleeper_draft_picks_by_id(draft_id)
        else:
            return False, "Invalid sync parameters"
        
        # Update session state
        old_count = len(st.session_state.sleeper_picks)
        st.session_state.sleeper_picks = sleeper_picks
        
        # Update drafted players set (preserve manual picks, update with Sleeper picks)
        manual_picks = {player for player in st.session_state.drafted_players 
                      if player not in st.session_state.sleeper_picks}
        st.session_state.drafted_players = manual_picks.union(set(sleeper_picks.keys()))
        
        # Update last sync time
        st.session_state.last_sync_time = time.time()
        
        new_count = len(sleeper_picks)
        change_indicator = f" (+{new_count - old_count} new)" if new_count > old_count else f" ({new_count - old_count})" if new_count < old_count else ""
        return True, f"Synced {new_count} picks{change_indicator}"
        
    except Exception as e:
        return False, f"Sync error: {str(e)}"
    finally:
        st.session_state.sync_in_progress = False

def main():
    # Process URL parameters first
    process_url_params()
    
    st.title("🏈 NFL Fantasy Football Draft Board")
    
    # Sleeper API Integration Section
    st.sidebar.header("🛏️ Sleeper Integration")
    
    # Show current URL parameters info
    params = get_url_params()
    if params:
        st.sidebar.info("📎 URL Parameters detected")
        if 'league_id' in params:
            st.sidebar.caption(f"League ID: {params['league_id']}")
        if 'draft_id' in params:
            st.sidebar.caption(f"Draft ID: {params['draft_id']}")
    
    # Choose connection type
    connection_type = st.sidebar.radio(
        "Connection Type:",
        ["League Draft", "Mock Draft (Direct ID)"],
        help="Choose how to connect to Sleeper"
    )
    
    if connection_type == "League Draft":
        # Input for Sleeper League ID (pre-populated from URL if available)
        default_league_id = params.get('league_id', st.session_state.current_league_id or '')
        sleeper_league_id = st.sidebar.text_input(
            "Sleeper League ID",
            value=default_league_id,
            placeholder="Enter your Sleeper league ID",
            help="Find your league ID in your Sleeper league URL: sleeper.app/leagues/{league_id}/team"
        )
        
        # Connect to Sleeper League button
        if st.sidebar.button("Connect to League Draft", type="primary"):
            if sleeper_league_id:
                with st.sidebar:
                    with st.spinner("Connecting to Sleeper League..."):
                        # Store the league ID for syncing and update URL
                        st.session_state.current_league_id = sleeper_league_id
                        st.session_state.current_draft_id = None  # Clear draft ID
                        set_url_params(league_id=sleeper_league_id, draft_id=None)
                        
                        # Fetch league info
                        league_info = get_sleeper_league_info(sleeper_league_id)
                        if league_info:
                            st.session_state.sleeper_league_info = league_info
                            st.session_state.sleeper_draft_info = None
                            st.session_state.connection_type = "league"
                            st.success(f"Connected to: {league_info.get('name', 'Unknown League')}")
                            
                            # Fetch drafted players
                            sleeper_picks = get_sleeper_draft_picks(sleeper_league_id)
                            st.session_state.sleeper_picks = sleeper_picks
                            
                            # Update drafted players set (preserve any existing manual picks)
                            st.session_state.drafted_players.update(sleeper_picks.keys())
                            
                            st.success(f"Loaded {len(sleeper_picks)} drafted players")
                        else:
                            st.error("Could not connect to Sleeper. Check your league ID.")
            else:
                st.sidebar.error("Please enter a league ID")
    
    else:  # Mock Draft (Direct ID)
        # Input for Draft ID (pre-populated from URL if available)
        default_draft_id = params.get('draft_id', st.session_state.current_draft_id or '')
        sleeper_draft_id = st.sidebar.text_input(
            "Sleeper Draft ID", 
            value=default_draft_id,
            placeholder="Enter your mock draft ID",
            help="Find your draft ID in the Sleeper mock draft URL: sleeper.app/draft/nfl/{draft_id}"
        )
        
        # Connect to Mock Draft button
        if st.sidebar.button("Connect to Mock Draft", type="primary"):
            if sleeper_draft_id:
                with st.sidebar:
                    with st.spinner("Connecting to Mock Draft..."):
                        # Store the draft ID for syncing and update URL
                        st.session_state.current_draft_id = sleeper_draft_id
                        st.session_state.current_league_id = None  # Clear league ID
                        set_url_params(draft_id=sleeper_draft_id, league_id=None)
                        
                        # Fetch draft info
                        draft_info = get_sleeper_draft_info(sleeper_draft_id)
                        if draft_info:
                            st.session_state.sleeper_draft_info = draft_info
                            st.session_state.sleeper_league_info = None
                            st.session_state.connection_type = "mock"
                            
                            draft_type = draft_info.get('type', 'unknown')
                            st.success(f"Connected to: {draft_type.title()} Draft")
                            
                            # Fetch drafted players
                            sleeper_picks = get_sleeper_draft_picks_by_id(sleeper_draft_id)
                            st.session_state.sleeper_picks = sleeper_picks
                            
                            # Update drafted players set (preserve any existing manual picks)
                            st.session_state.drafted_players.update(sleeper_picks.keys())
                            
                            st.success(f"Loaded {len(sleeper_picks)} drafted players")
                        else:
                            st.error("Could not connect to draft. Check your draft ID.")
            else:
                st.sidebar.error("Please enter a draft ID")
    
    # Display connection status
    if st.session_state.sleeper_league_info or st.session_state.sleeper_draft_info:
        st.sidebar.success("✅ Connected to Sleeper")
        
        # Share URL section
        st.sidebar.markdown("---")
        st.sidebar.subheader("📎 Share URL")
        
        current_url = st.get_option("browser.serverAddress") or "localhost:8501"
        if st.session_state.connection_type == "league" and st.session_state.current_league_id:
            share_url = f"http://{current_url}?league_id={st.session_state.current_league_id}"
            st.sidebar.code(share_url, language=None)
            st.sidebar.caption("Share this URL to let others view your league draft")
        elif st.session_state.connection_type == "mock" and st.session_state.current_draft_id:
            share_url = f"http://{current_url}?draft_id={st.session_state.current_draft_id}"
            st.sidebar.code(share_url, language=None)
            st.sidebar.caption("Share this URL to let others view your mock draft")
        
        if st.session_state.connection_type == "league" and st.session_state.sleeper_league_info:
            st.sidebar.info(f"League: {st.session_state.sleeper_league_info.get('name')}")
            st.sidebar.info(f"Season: {st.session_state.sleeper_league_info.get('season')}")
            
            # Sync button for league draft
            if st.sidebar.button("🔄 Sync League Draft"):
                if st.session_state.current_league_id:
                    with st.sidebar:
                        with st.spinner("Syncing..."):
                            # Clear all cache to force fresh data fetch
                            st.cache_data.clear()
                            
                            sleeper_picks = get_sleeper_draft_picks(st.session_state.current_league_id)
                            st.session_state.sleeper_picks = sleeper_picks
                            
                            # Update drafted players set (preserve manual picks, update with Sleeper picks)
                            manual_picks = {player for player in st.session_state.drafted_players 
                                          if player not in st.session_state.sleeper_picks}
                            st.session_state.drafted_players = manual_picks.union(set(sleeper_picks.keys()))
                            
                            st.success("League draft data synced!")
                            st.success(f"Updated with {len(sleeper_picks)} Sleeper picks")
                else:
                    st.sidebar.error("No league ID stored. Please reconnect to league.")
            
            # Auto-sync toggle for league draft
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("🔄 Auto-Sync ON" if not st.session_state.auto_sync_active else "⏸️ Auto-Sync OFF", 
                           type="secondary" if not st.session_state.auto_sync_active else "primary"):
                    st.session_state.auto_sync_active = not st.session_state.auto_sync_active
                    if st.session_state.auto_sync_active:
                        st.success("Auto-sync started!")
                    else:
                        st.info("Auto-sync stopped")
            
            with col2:
                if st.session_state.auto_sync_active:
                    st.markdown("🟢 **LIVE**")
                else:
                    st.markdown("⚫ **MANUAL**")
        
        elif st.session_state.connection_type == "mock" and st.session_state.sleeper_draft_info:
            draft_info = st.session_state.sleeper_draft_info
            st.sidebar.info(f"Draft Type: {draft_info.get('type', 'Unknown').title()}")
            st.sidebar.info(f"Status: {draft_info.get('status', 'Unknown').title()}")
            st.sidebar.info(f"Settings: {draft_info.get('settings', {}).get('teams', 'Unknown')} teams")
            
            # Sync button for mock draft
            if st.sidebar.button("🔄 Sync Mock Draft"):
                if st.session_state.current_draft_id:
                    with st.sidebar:
                        with st.spinner("Syncing..."):
                            # Clear all cache to force fresh data fetch
                            st.cache_data.clear()
                            
                            sleeper_picks = get_sleeper_draft_picks_by_id(st.session_state.current_draft_id)
                            st.session_state.sleeper_picks = sleeper_picks
                            
                            # Update drafted players set (preserve manual picks, update with Sleeper picks)
                            manual_picks = {player for player in st.session_state.drafted_players 
                                          if player not in st.session_state.sleeper_picks}
                            st.session_state.drafted_players = manual_picks.union(set(sleeper_picks.keys()))
                            
                            st.success("Mock draft data synced!")
                            st.success(f"Updated with {len(sleeper_picks)} Sleeper picks")
                else:
                    st.sidebar.error("No draft ID stored. Please reconnect to mock draft.")
            
            # Auto-sync toggle for mock draft
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("🔄 Auto-Sync ON" if not st.session_state.auto_sync_active else "⏸️ Auto-Sync OFF", 
                           type="secondary" if not st.session_state.auto_sync_active else "primary"):
                    st.session_state.auto_sync_active = not st.session_state.auto_sync_active
                    if st.session_state.auto_sync_active:
                        st.success("Auto-sync started!")
                    else:
                        st.info("Auto-sync stopped")
            
            with col2:
                if st.session_state.auto_sync_active:
                    st.markdown("🟢 **LIVE**")
                else:
                    st.markdown("⚫ **MANUAL**")
    
    st.sidebar.markdown("---")
    
    # Auto-sync functionality with improved timing control
    if st.session_state.auto_sync_active and (st.session_state.current_league_id or st.session_state.current_draft_id):
        current_time = time.time()
        
        # Initialize last sync time if not set
        if st.session_state.last_sync_time == 0:
            st.session_state.last_sync_time = current_time
        
        time_since_last_sync = current_time - st.session_state.last_sync_time
        
        # Only sync if 5 seconds have passed and no sync is in progress
        if time_since_last_sync >= 5.0 and not st.session_state.sync_in_progress:
            # Create a placeholder for sync status
            with st.sidebar:
                sync_placeholder = st.empty()
                sync_placeholder.info("🔄 Auto-syncing...")
                
            # Perform auto-sync
            success, message = perform_sync(
                st.session_state.connection_type,
                st.session_state.current_league_id,
                st.session_state.current_draft_id
            )
            
            # Show result
            if success:
                sync_placeholder.success(f"✅ {message}")
            else:
                sync_placeholder.error(f"❌ {message}")
            
            # Brief pause to show message, then refresh
            time.sleep(1)
            sync_placeholder.empty()
        
        # Always rerun to maintain the auto-sync loop
        time.sleep(0.5)  # Small delay to prevent too rapid refreshes
        st.rerun()
    
    # Show auto-sync status if active
    if st.session_state.auto_sync_active:
        st.sidebar.info("🔄 Auto-sync active")
        
        if st.session_state.last_sync_time > 0:
            current_time = time.time()
            time_since_last = current_time - st.session_state.last_sync_time
            
            if time_since_last < 5.0:
                time_until_next = 5.0 - time_since_last
                st.sidebar.caption(f"Next sync in: {time_until_next:.1f}s")
            else:
                st.sidebar.caption("Ready to sync...")
            
            last_sync_formatted = time.strftime('%H:%M:%S', time.localtime(st.session_state.last_sync_time))
            st.sidebar.caption(f"Last sync: {last_sync_formatted}")
        
        # Show sync status with cache clearing indicator
        if st.session_state.sync_in_progress:
            st.sidebar.warning("⏳ Sync in progress... (Cache cleared)")
        else:
            st.sidebar.success("✅ Sync ready")
            
        # Add cache status indicator
        st.sidebar.caption("🗂️ Cache cleared on each sync")
    
    # File upload section
    uploaded_file = st.file_uploader(
        "Upload your NFL projections CSV file", 
        type=['csv'],
        help="Upload the '2025 NFL Projections ALL.csv' file"
    )
    
    # Load data
    df = load_data(uploaded_file)
    
    if df is None and uploaded_file is None:
        st.info("👆 Please upload your NFL projections CSV file to get started!")
        st.markdown("""
        **Expected file format:**
        - File name: `2025 NFL Projections ALL.csv` (or any CSV with similar structure)
        - Required columns: player, team, position, fantasy, overallRank, positionRank
        - Optional columns: passing/rushing/receiving stats
        """)
        return
    elif df is None:
        st.error("Could not load the data. Please check your CSV file format.")
        return
    elif df.empty:
        st.error("The uploaded file appears to be empty or has no valid data.")
        return
    
    st.markdown("---")
    
    # Filters section in main content area
    st.header("🔍 Filters & Sorting")
    
    # Create columns for filters
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    with filter_col1:
        # Position filter
        positions = ['All'] + sorted([pos for pos in df['position'].unique() if pd.notna(pos)])
        selected_position = st.selectbox("Position", positions)
    
    with filter_col2:
        # Team filter
        teams = ['All'] + sorted([team for team in df['team'].unique() if pd.notna(team)])
        selected_team = st.selectbox("Team", teams)
    
    with filter_col3:
        # Drafted status filter
        drafted_filter = st.radio("Show", ["All Players", "Available Only", "Drafted Only"])
    
    with filter_col4:
        # Search box
        search_term = st.text_input("Search Player", placeholder="Enter player name...")
    
    # Sorting section
    st.subheader("📊 Sorting Options")
    sort_col1, sort_col2 = st.columns(2)
    
    with sort_col1:
        sort_options = {
            'Overall Rank': 'overallRank',
            'Fantasy Points': 'fantasy',
            'Position Rank': 'positionRank',
            'Player Name': 'player'
        }
        sort_by = st.selectbox("Sort by", list(sort_options.keys()))
    
    with sort_col2:
        ascending = st.checkbox("Ascending order", value=True)
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_position != 'All':
        filtered_df = filtered_df[filtered_df['position'] == selected_position]
    
    if selected_team != 'All':
        filtered_df = filtered_df[filtered_df['team'] == selected_team]
    
    if search_term:
        filtered_df = filtered_df[filtered_df['player'].str.contains(search_term, case=False, na=False)]
    
    if drafted_filter == "Available Only":
        filtered_df = filtered_df[~filtered_df['drafted']]
    elif drafted_filter == "Drafted Only":
        filtered_df = filtered_df[filtered_df['drafted']]
    
    # Sort data
    if sort_options[sort_by] in filtered_df.columns:
        if sort_by == 'Player Name':
            filtered_df = filtered_df.sort_values(sort_options[sort_by], ascending=ascending)
        else:
            # For numeric columns, handle NaN values
            filtered_df = filtered_df.sort_values(sort_options[sort_by], ascending=ascending, na_position='last')
    
    # Main content
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.metric("Total Players", len(df))
    with col2:
        st.metric("Drafted", len(st.session_state.drafted_players))
    with col3:
        st.metric("Available", len(df) - len(st.session_state.drafted_players))
    
    st.markdown("---")
    
    # Player statistics and draft controls
    if filtered_df.empty:
        st.warning("No players match the current filters.")
        return
    
    # Prepare data for display with draft status and team logos
    display_df = filtered_df.copy()
    
    # Function to determine draft status (prioritizes Sleeper data)
    def get_draft_status(player_name):
        if player_name in st.session_state.sleeper_picks:
            # Player was drafted in Sleeper
            pick_info = st.session_state.sleeper_picks[player_name]
            return f"✅ SLEEPER (R{pick_info['round']}, #{pick_info['pick_no']})"
        elif player_name in st.session_state.drafted_players:
            # Player was manually drafted in app
            return "✅ MANUAL"
        else:
            return "⭕ Available"
    
    # Add draft status column at the beginning with enhanced status
    display_df.insert(0, 'Draft Status', display_df['player'].apply(get_draft_status))
    
    # Add team logo column
    display_df.insert(2, 'Logo', display_df['team'].apply(get_team_logo_url))
    
    # Player statistics table
    st.subheader("📊 Player Statistics")
    
    # Reorder and select columns for display (including logo and draft status)
    columns_to_show = [
        'Draft Status', 'player', 'Logo', 'team', 'position', 'overallRank', 'positionRank', 'fantasy',
        'completionsAttempts', 'passingYards', 'passingTouchdowns', 'interceptionsThrown',
        'rushingAttempts', 'rushingYards', 'rushingTouchdowns',
        'receptions', 'targets', 'receivingYards', 'receivingTouchdowns',
        'extraPointsAttempted', 'extraPointsMade', 'fieldGoalsAttempted', 'fieldGoalsMade',
        'fieldGoalsMade0To19', 'fieldGoalsMade20To29', 'fieldGoalsMade30To39', 
        'fieldGoalsMade40To49', 'fieldGoalsMade50Plus'
    ]
    
    # Filter to only columns that exist
    available_columns = [col for col in columns_to_show if col in display_df.columns]
    table_df = display_df[available_columns].copy()
    
    # Rename columns for better display
    column_renames = {
        'player': 'Player',
        'team': 'Team',
        'position': 'Pos',
        'overallRank': 'Overall',
        'positionRank': 'Pos Rank', 
        'fantasy': 'Fantasy',
        'completionsAttempts': 'Comp/Att',
        'passingYards': 'Pass Yds',
        'passingTouchdowns': 'Pass TD',
        'interceptionsThrown': 'INT',
        'rushingAttempts': 'Rush Att',
        'rushingYards': 'Rush Yds',
        'rushingTouchdowns': 'Rush TD',
        'receptions': 'Rec',
        'targets': 'Targets',
        'receivingYards': 'Rec Yds',
        'receivingTouchdowns': 'Rec TD',
        'extraPointsAttempted': 'XP Att',
        'extraPointsMade': 'XP Made',
        'fieldGoalsAttempted': 'FG Att',
        'fieldGoalsMade': 'FG Made',
        'fieldGoalsMade0To19': 'FG 0-19',
        'fieldGoalsMade20To29': 'FG 20-29',
        'fieldGoalsMade30To39': 'FG 30-39',
        'fieldGoalsMade40To49': 'FG 40-49',
        'fieldGoalsMade50Plus': 'FG 50+'
    }
    
    table_df = table_df.rename(columns=column_renames)
    
    # Display the scrollable dataframe with enhanced column configuration
    st.dataframe(
        table_df,
        use_container_width=False,
        hide_index=True,
        height=400,
        column_config={
            "Draft Status": st.column_config.TextColumn(
                "Draft Status",
                width="large",
                help="Shows if player is available (⭕), drafted in Sleeper (✅ SLEEPER), or manually drafted (✅ MANUAL)"
            ),
            "Player": st.column_config.TextColumn("Player", width="large"),
            "Logo": st.column_config.ImageColumn(
                "Logo",
                width="small",
                help="Team logo"
            ),
            "Team": st.column_config.TextColumn("Team", width="medium"),
            "Pos": st.column_config.TextColumn("Position", width="small"),
            "Overall": st.column_config.NumberColumn("Overall Rank", width="small", format="%.1f"),
            "Pos Rank": st.column_config.NumberColumn("Position Rank", width="small", format="%.1f"),
            "Fantasy": st.column_config.NumberColumn("Fantasy Points", width="medium", format="%.1f"),
            "Comp/Att": st.column_config.TextColumn("Completions/Attempts", width="medium"),
            "Pass Yds": st.column_config.NumberColumn("Passing Yards", width="small", format="%.0f"),
            "Pass TD": st.column_config.NumberColumn("Passing TDs", width="small", format="%.1f"),
            "INT": st.column_config.NumberColumn("Interceptions", width="small", format="%.1f"),
            "Rush Att": st.column_config.NumberColumn("Rushing Attempts", width="small", format="%.1f"),
            "Rush Yds": st.column_config.NumberColumn("Rushing Yards", width="small", format="%.0f"),
            "Rush TD": st.column_config.NumberColumn("Rushing TDs", width="small", format="%.1f"),
            "Rec": st.column_config.NumberColumn("Receptions", width="small", format="%.1f"),
            "Targets": st.column_config.NumberColumn("Targets", width="small", format="%.1f"),
            "Rec Yds": st.column_config.NumberColumn("Receiving Yards", width="small", format="%.0f"),
            "Rec TD": st.column_config.NumberColumn("Receiving TDs", width="small", format="%.1f")
        }
    )
    
    # Show summary of drafted vs available players in current view
    current_sleeper_picks = sum(1 for player in table_df['Player'] if player in st.session_state.sleeper_picks)
    current_manual_picks = sum(1 for player in table_df['Player'] if player in st.session_state.drafted_players and player not in st.session_state.sleeper_picks)
    current_available = len(table_df) - current_sleeper_picks - current_manual_picks
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🛏️ Sleeper Picks", current_sleeper_picks)
    with col2:
        st.metric("✋ Manual Picks", current_manual_picks) 
    with col3:
        st.metric("⭕ Available", current_available)
    with col4:
        if st.session_state.sleeper_league_info or st.session_state.sleeper_draft_info:
            connection_label = "🛏️ Total Sleeper" if st.session_state.connection_type == "league" else "🛏️ Total Mock"
            st.metric(connection_label, len(st.session_state.sleeper_picks))
    
    # Display Sleeper draft details if connected
    if st.session_state.sleeper_picks:
        st.markdown("---")
        
        # Dynamic header based on connection type
        if st.session_state.connection_type == "league":
            st.subheader("🛏️ Sleeper League Draft Details")
        else:
            st.subheader("🛏️ Sleeper Mock Draft Details")
        
        # Create a dataframe of Sleeper picks
        sleeper_data = []
        for player_name, pick_info in st.session_state.sleeper_picks.items():
            sleeper_data.append({
                'Pick #': pick_info['pick_no'],
                'Round': pick_info['round'],
                'Player': player_name,
                'Position': pick_info['position'],
                'Team': pick_info['team']
            })
        
        if sleeper_data:
            sleeper_df = pd.DataFrame(sleeper_data).sort_values('Pick #')
            
            st.dataframe(
                sleeper_df,
                use_container_width=True,
                hide_index=True,
                height=300,
                column_config={
                    "Pick #": st.column_config.NumberColumn("Pick #", width="small"),
                    "Round": st.column_config.NumberColumn("Round", width="small"), 
                    "Player": st.column_config.TextColumn("Player", width="large"),
                    "Position": st.column_config.TextColumn("Position", width="small"),
                    "Team": st.column_config.TextColumn("NFL Team", width="small")
                }
            )
    
    st.markdown("---")
    
    # Individual draft controls for each player
    st.subheader("🏈 Draft Controls")
    
    # Create a more compact button layout
    players_per_row = 4
    
    for i in range(0, len(display_df), players_per_row):
        cols = st.columns(players_per_row)
        
        for j, (idx, row) in enumerate(display_df.iloc[i:i+players_per_row].iterrows()):
            if j < len(cols):
                with cols[j]:
                    player_name = row['player']
                    
                    # Player info with enhanced status
                    st.markdown(f"**{player_name}**")
                    st.text(f"{row['team']} - {row['position']}")
                    st.text(f"Rank: {format_stat(row.get('overallRank'))}")
                    
                    # Check different draft statuses
                    if player_name in st.session_state.sleeper_picks:
                        # Player drafted in Sleeper - show info but disable button
                        pick_info = st.session_state.sleeper_picks[player_name]
                        st.button(f"🛏️ Sleeper Pick", key=f"sleeper_pick_{idx}", disabled=True, use_container_width=True)
                        st.markdown(f"*R{pick_info['round']}, #{pick_info['pick_no']}*")
                    elif player_name in st.session_state.drafted_players:
                        # Player manually drafted - allow undrafting
                        if st.button(f"✅ Manually Drafted", key=f"individual_undraft_{idx}", type="secondary", use_container_width=True):
                            st.session_state.drafted_players.discard(player_name)
                            st.rerun()
                        st.markdown("*Manual pick*")
                    else:
                        # Player available - allow drafting
                        if st.button(f"⭕ Draft Player", key=f"individual_draft_{idx}", type="primary", use_container_width=True):
                            st.session_state.drafted_players.add(player_name)
                            st.rerun()
                        st.markdown("*Available*")
                    
                    st.markdown("---")
    
    # Draft summary
    if st.session_state.drafted_players:
        st.markdown("---")
        st.header("📋 Drafted Players Summary")
        
        drafted_df = df[df['player'].isin(st.session_state.drafted_players)]
        
        if not drafted_df.empty:
            # Group by position
            pos_counts = drafted_df['position'].value_counts()
            
            cols = st.columns(len(pos_counts))
            for i, (pos, count) in enumerate(pos_counts.items()):
                with cols[i]:
                    st.metric(f"{pos}", count)
            
            # Clear all drafted players button
            if st.button("🗑️ Clear All Drafted Players", type="secondary"):
                st.session_state.drafted_players.clear()
                st.rerun()

if __name__ == "__main__":
    main()