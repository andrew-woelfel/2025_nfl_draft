import streamlit as st
import pandas as pd
import numpy as np

# Set page config
st.set_page_config(
    page_title="NFL Fantasy Football Draft Board",
    page_icon="🏈",
    layout="wide"
)

# Initialize session state for drafted players
if 'drafted_players' not in st.session_state:
    st.session_state.drafted_players = set()

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

def main():
    st.title("🏈 NFL Fantasy Football Draft Board")
    
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
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Position filter
    positions = ['All'] + sorted([pos for pos in df['position'].unique() if pd.notna(pos)])
    selected_position = st.sidebar.selectbox("Position", positions)
    
    # Team filter
    teams = ['All'] + sorted([team for team in df['team'].unique() if pd.notna(team)])
    selected_team = st.sidebar.selectbox("Team", teams)
    
    # Drafted status filter
    drafted_filter = st.sidebar.radio("Show", ["All Players", "Available Only", "Drafted Only"])
    
    # Search box
    search_term = st.sidebar.text_input("Search Player", placeholder="Enter player name...")
    
    # Sort options
    st.sidebar.header("📊 Sorting")
    sort_options = {
        'Overall Rank': 'overallRank',
        'Fantasy Points': 'fantasy',
        'Position Rank': 'positionRank',
        'Player Name': 'player'
    }
    sort_by = st.sidebar.selectbox("Sort by", list(sort_options.keys()))
    ascending = st.sidebar.checkbox("Ascending order", value=True)
    
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
    
    # Display player list
    st.header("Player List")
    
    if filtered_df.empty:
        st.warning("No players match the current filters.")
        return
    
    # Player statistics and draft controls
    if filtered_df.empty:
        st.warning("No players match the current filters.")
        return
    
    # Prepare data for display with draft status
    display_df = filtered_df.copy()
    
    # Add draft status column at the beginning
    display_df.insert(0, 'Draft Status', display_df['player'].apply(
        lambda x: "✅ DRAFTED" if x in st.session_state.drafted_players else "⭕ Available"
    ))
    
    # Add CSS for better table styling and color coding
    st.markdown("""
    <style>
    /* Ensure horizontal scrolling works properly */
    div[data-testid="stDataFrame"] {
        overflow-x: auto !important;
        max-width: 100% !important;
    }
    
    div[data-testid="stDataFrame"] > div {
        min-width: max-content !important;
        white-space: nowrap !important;
    }
    
    /* Style the dataframe */
    .dataframe {
        font-size: 12px !important;
    }
    
    /* Color coding for drafted players */
    .dataframe tbody tr:has(td:first-child:contains("✅ DRAFTED")) {
        background-color: #ffebee !important;
        opacity: 0.8 !important;
    }
    
    .dataframe tbody tr:has(td:first-child:contains("⭕ Available")) {
        background-color: #e8f5e8 !important;
    }
    
    /* Style draft status cells specifically */
    .dataframe td:contains("✅ DRAFTED") {
        background-color: #f44336 !important;
        color: white !important;
        font-weight: bold !important;
    }
    
    .dataframe td:contains("⭕ Available") {
        background-color: #4caf50 !important;
        color: white !important;
        font-weight: bold !important;
    }
    
    /* Ensure scrollbars are visible */
    div[data-testid="stDataFrame"]::-webkit-scrollbar {
        height: 12px;
        background-color: #f1f1f1;
    }
    
    div[data-testid="stDataFrame"]::-webkit-scrollbar-thumb {
        background-color: #888;
        border-radius: 6px;
    }
    
    div[data-testid="stDataFrame"]::-webkit-scrollbar-thumb:hover {
        background-color: #555;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Player statistics table
    st.subheader("📊 Player Statistics")
    
    # Reorder and select columns for display (including draft status)
    columns_to_show = [
        'Draft Status', 'player', 'team', 'position', 'overallRank', 'positionRank', 'fantasy',
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
                width="medium",
                help="Shows if player is drafted (✅) or available (⭕)"
            ),
            "Player": st.column_config.TextColumn("Player", width="large"),
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
    current_drafted = sum(1 for player in table_df['Player'] if player in st.session_state.drafted_players)
    current_available = len(table_df) - current_drafted
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📋 Drafted (in current view)", current_drafted)
    with col2:
        st.metric("⭕ Available (in current view)", current_available)
    
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
                    
                    # Player info
                    st.markdown(f"**{player_name}**")
                    st.text(f"{row['team']} - {row['position']}")
                    st.text(f"Rank: {format_stat(row.get('overallRank'))}")
                    
                    # Draft button
                    if player_name in st.session_state.drafted_players:
                        if st.button(f"✅ Drafted", key=f"individual_undraft_{idx}", type="secondary", use_container_width=True):
                            st.session_state.drafted_players.discard(player_name)
                            st.rerun()
                        st.markdown("*Player is drafted*")
                    else:
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