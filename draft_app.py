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
    
    # Column headers at the top
    col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([0.8, 2, 1.5, 0.8, 1, 1, 1, 1, 1])
    with col1:
        st.markdown("**Draft**")
    with col2:
        st.markdown("**Player**")
    with col3:
        st.markdown("**Team**")
    with col4:
        st.markdown("**Pos**")
    with col5:
        st.markdown("**Overall**")
    with col6:
        st.markdown("**Pos Rank**")
    with col7:
        st.markdown("**Fantasy**")
    with col8:
        st.markdown("**Yards**")
    with col9:
        st.markdown("**TDs**")
    
    st.markdown("---")
    
    # Create display dataframe
    display_df = filtered_df.copy()
    
    # Quick draft buttons and player table
    for idx, row in display_df.iterrows():
        col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([0.8, 2, 1.5, 0.8, 1, 1, 1, 1, 1])
        
        with col1:
            # Draft button
            if row['player'] in st.session_state.drafted_players:
                if st.button("✅", key=f"undraft_{idx}", help="Click to undraft"):
                    st.session_state.drafted_players.discard(row['player'])
                    st.rerun()
            else:
                if st.button("⭕", key=f"draft_{idx}", help="Click to draft"):
                    st.session_state.drafted_players.add(row['player'])
                    st.rerun()
        
        with col2:
            # Player name with drafted indicator
            player_name = row['player']
            if row['player'] in st.session_state.drafted_players:
                st.markdown(f"~~{player_name}~~ ✅")
            else:
                st.markdown(f"**{player_name}**")
        
        with col3:
            st.text(f"{row['team']}")
        
        with col4:
            # Position with color coding
            pos = row['position']
            if pos == 'QB':
                st.markdown(f'<span style="background-color: #FF6B6B; color: white; padding: 2px 6px; border-radius: 3px;">{pos}</span>', unsafe_allow_html=True)
            elif pos == 'RB':
                st.markdown(f'<span style="background-color: #4ECDC4; color: white; padding: 2px 6px; border-radius: 3px;">{pos}</span>', unsafe_allow_html=True)
            elif pos == 'WR':
                st.markdown(f'<span style="background-color: #45B7D1; color: white; padding: 2px 6px; border-radius: 3px;">{pos}</span>', unsafe_allow_html=True)
            elif pos == 'TE':
                st.markdown(f'<span style="background-color: #96CEB4; color: white; padding: 2px 6px; border-radius: 3px;">{pos}</span>', unsafe_allow_html=True)
            elif pos == 'K':
                st.markdown(f'<span style="background-color: #FFEAA7; color: black; padding: 2px 6px; border-radius: 3px;">{pos}</span>', unsafe_allow_html=True)
            else:
                st.text(pos or "-")
        
        with col5:
            st.text(format_stat(row.get('overallRank'), "float"))
        
        with col6:
            st.text(format_stat(row.get('positionRank'), "float"))
        
        with col7:
            st.text(format_stat(row.get('fantasy')))
        
        with col8:
            # Show relevant stats based on position
            if row['position'] == 'QB':
                st.text(format_stat(row.get('passingYards')))
            elif row['position'] in ['RB', 'WR', 'TE']:
                if row['position'] == 'RB':
                    st.text(format_stat(row.get('rushingYards')))
                else:
                    st.text(format_stat(row.get('receivingYards')))
            else:
                st.text("-")
        
        with col9:
            # Show TDs based on position
            if row['position'] == 'QB':
                st.text(format_stat(row.get('passingTouchdowns')))
            elif row['position'] == 'RB':
                total_tds = (row.get('rushingTouchdowns', 0) or 0) + (row.get('receivingTouchdowns', 0) or 0)
                st.text(format_stat(total_tds))
            elif row['position'] in ['WR', 'TE']:
                st.text(format_stat(row.get('receivingTouchdowns')))
            else:
                st.text("-")
    
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