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
        'Player Name': 'player',
        'Passing Yards': 'passingYards',
        'Passing TDs': 'passingTouchdowns',
        'Rushing Yards': 'rushingYards',
        'Rushing TDs': 'rushingTouchdowns',
        'Receiving Yards': 'receivingYards',
        'Receiving TDs': 'receivingTouchdowns',
        'Receptions': 'receptions',
        'Targets': 'targets'
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
    
    # Create display dataframe
    display_df = filtered_df.copy()
    
    # Column headers (display at top)
    st.subheader("Player Statistics")
    
    # Define headers and corresponding column widths
    headers = ["Draft", "Player", "Team", "Pos", "OR", "PR", "Fant", "Comp/Att", "PaYd", "PaTD", "INT", "RuAtt", "RuYd", "RuTD", "Rec", "Tgt", "ReYd", "ReTD", "XPA", "XPM", "FGA", "FGM", "FG0-19", "FG20-29", "FG30-39", "FG40-49", "FG50+"]
    col_widths = [0.6, 1.5, 1.2, 0.6] + [0.7] * (len(headers) - 4)  # First 4 cols have custom widths, rest are uniform
    
    header_cols = st.columns(col_widths)
    
    for i, header in enumerate(headers):
        with header_cols[i]:
            st.markdown(f"**{header}**")
    
    st.markdown("---")
    
    # Player rows with buttons and data
    for idx, row in display_df.iterrows():
        # Create a unique container for each row
        row_container = st.container()
        
        with row_container:
            # Create columns for the draft button (separate from the data row)
            button_col, data_col = st.columns([0.1, 0.9])
            
            with button_col:
                # Draft button
                if row['player'] in st.session_state.drafted_players:
                    if st.button("✅", key=f"undraft_{idx}", help="Click to undraft"):
                        st.session_state.drafted_players.discard(row['player'])
                        st.rerun()
                else:
                    if st.button("⭕", key=f"draft_{idx}", help="Click to draft"):
                        st.session_state.drafted_players.add(row['player'])
                        st.rerun()
            
            with data_col:
                # Player data row with HTML for horizontal scrolling
                player_name = row['player']
                if row['player'] in st.session_state.drafted_players:
                    player_display = f"<s>{player_name}</s> ✅"
                    row_style = "opacity: 0.6;"
                else:
                    player_display = f"<strong>{player_name}</strong>"
                    row_style = ""
                
                # Position badge styling
                pos = row['position']
                if pos == 'QB':
                    pos_badge = f'<span style="background-color: #FF6B6B; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{pos}</span>'
                elif pos == 'RB':
                    pos_badge = f'<span style="background-color: #4ECDC4; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{pos}</span>'
                elif pos == 'WR':
                    pos_badge = f'<span style="background-color: #45B7D1; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{pos}</span>'
                elif pos == 'TE':
                    pos_badge = f'<span style="background-color: #96CEB4; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{pos}</span>'
                elif pos == 'K':
                    pos_badge = f'<span style="background-color: #FFEAA7; color: black; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{pos}</span>'
                else:
                    pos_badge = pos or "-"
                
                # Create the data row HTML
                row_html = f'''
                <div class="player-row" style="{row_style}">
                    <div class="player-cell col-draft">-</div>
                    <div class="player-cell col-player">{player_display}</div>
                    <div class="player-cell col-team">{row['team']}</div>
                    <div class="player-cell col-pos">{pos_badge}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('overallRank'), "float")}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('positionRank'), "float")}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('fantasy'))}</div>
                    <div class="player-cell col-comp-att">{str(row.get('completionsAttempts', '') or '-')}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('passingYards'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('passingTouchdowns'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('interceptionsThrown'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('rushingAttempts'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('rushingYards'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('rushingTouchdowns'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('receptions'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('targets'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('receivingYards'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('receivingTouchdowns'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('extraPointsAttempted'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('extraPointsMade'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('fieldGoalsAttempted'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('fieldGoalsMade'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('fieldGoalsMade0To19'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('fieldGoalsMade20To29'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('fieldGoalsMade30To39'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('fieldGoalsMade40To49'))}</div>
                    <div class="player-cell col-stat">{format_stat(row.get('fieldGoalsMade50Plus'))}</div>
                </div>
                '''
                st.markdown(row_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close the scrollable container
    

    
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