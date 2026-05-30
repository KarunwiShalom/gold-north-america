import os
import json
import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from google.cloud import bigquery
from google.oauth2 import service_account
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model.monte_carlo import run_monte_carlo, load_fixtures
from streamlit_extras.let_it_rain import rain

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gold in North America",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── WC CSS ───────────────────────────────────────────────────────────────
# Load CSS
with open("app/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Confetti function ─────────────────────────────────────────────────────────
rain(
    emoji="🎉",
    font_size=30,
    falling_speed=5,
    animation_length=3,
)

# ── Connect to BigQuery ───────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    if "GCP_CREDENTIALS" in st.secrets:
        # Streamlit Cloud: credentials injected as secret
        credentials_info = json.loads(st.secrets["GCP_CREDENTIALS"])
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info
        )
        return bigquery.Client(
            credentials=credentials,
            project="gold-north-america"
        )
    else:
        # Local: fall back to key file
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        return bigquery.Client.from_service_account_json(
            key_path, project="gold-north-america"
        )

@st.cache_data(ttl=3600)
def load_fixture_data():
    client = get_client()
    query = """
        SELECT *
        FROM `gold-north-america.gold_north_america.mart_group_fixtures_enriched`
        ORDER BY date, group_name
    """
    return client.query(query).to_dataframe()

@st.cache_data(ttl=3600)
def load_mc_results():
    fixtures = load_fixture_data()
    return run_monte_carlo(fixtures, n=10000)

# ── Poisson prediction ────────────────────────────────────────────────────────
def predict_match(lambda_home, lambda_away, max_goals=10):
    home_probs = [poisson.pmf(i, lambda_home) for i in range(max_goals + 1)]
    away_probs = [poisson.pmf(i, lambda_away) for i in range(max_goals + 1)]
    matrix = np.outer(home_probs, away_probs)
    prob_home_win = float(np.sum(np.tril(matrix, -1)))
    prob_away_win = float(np.sum(np.triu(matrix, 1)))
    prob_draw     = float(np.sum(np.diag(matrix)))
    idx = np.unravel_index(matrix.argmax(), matrix.shape)
    return {
        "prob_home_win":     round(prob_home_win * 100, 1),
        "prob_draw":         round(prob_draw * 100, 1),
        "prob_away_win":     round(prob_away_win * 100, 1),
        "most_likely_score": f"{idx[0]}-{idx[1]}",
        "matrix":            matrix
    }

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
    <h1 style="margin:0; padding:0; line-height:1; 
               background: linear-gradient(90deg, #B22234, #FFFFFF, #B22234, #006847, #CE1126);
               -webkit-background-clip: text;
               -webkit-text-fill-color: transparent;
               background-clip: text;">
        Gold in North America
    </h1>
    <div style="display:flex; gap:12px; align-items:center; font-size:2.5rem;">
        <span title="United States">🇺🇸</span>
        <span title="Mexico">🇲🇽</span>
        <span title="Canada">🇨🇦</span>
    </div>
</div>
<p style="color:rgba(255,255,255,0.6); font-size:0.85rem; letter-spacing:0.08em; 
          text-transform:uppercase; margin-top:6px;">
    2026 FIFA World Cup Predictor &nbsp;·&nbsp; Poisson + Monte Carlo Model 
    &nbsp;·&nbsp; 
    <span style="background:rgba(255,255,255,0.08); color:rgba(255,255,255,0.6); 
                 border:1px solid rgba(255,255,255,0.15); border-radius:4px; 
                 padding:2px 8px; font-size:0.72rem; font-weight:700;">
        10,000 SIMULATIONS
    </span>
</p>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("⚡ Loading model..."):
    mc_results    = load_mc_results()
    fixtures_df   = load_fixture_data()

# ── Winner banner + confetti ──────────────────────────────────────────────────
winner = mc_results.iloc[0]['team']
win_pct = mc_results.iloc[0]['win_pct']

st.markdown(f"""
<div class="winner-banner">
    <div class="stripe-block">
        <div class="stripe" style="background:#E63946;"></div>
        <div class="stripe" style="background:#2A9D8F;"></div>
        <div class="stripe" style="background:#457B9D;"></div>
        <div class="stripe" style="background:#6A4C93;"></div>
    </div>
    <div>
        <h2>Congratulations, {winner}</h2>
        <p>The model predicts <strong>{winner}</strong> as the most likely 
        2026 World Cup winner &mdash; <strong>{win_pct}%</strong> chance 
        of lifting the trophy in New Jersey on July 19.</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🏆 Tournament Predictions",
    "👥 Group Stage",
    "⚔️ Head to Head"
])

# ── Tab 1: Tournament Predictions ────────────────────────────────────────────
with tab1:
    st.markdown("<p style='color:rgba(255,255,255,0.7); font-size:0.9rem;'>Based on 10,000 Monte Carlo simulations across all 48 teams.</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.25);
                    border-left:4px solid #f5c518; border-radius:12px; padding:20px 24px;">
            <div style="color:rgba(255,255,255,0.6); font-size:0.72rem; font-weight:700;
                        letter-spacing:0.1em; text-transform:uppercase; margin-bottom:8px;">
                🥇 Favourite</div>
            <div style="color:#FFFFFF; font-size:1.75rem; font-weight:800; margin-bottom:6px;">
                {mc_results.iloc[0]['team']}</div>
            <div style="color:#f5c518; font-size:0.85rem; font-weight:600;">
                {mc_results.iloc[0]['win_pct']}% to win</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.25);
                    border-left:4px solid rgba(255,255,255,0.4); border-radius:12px; padding:20px 24px;">
            <div style="color:rgba(255,255,255,0.6); font-size:0.72rem; font-weight:700;
                        letter-spacing:0.1em; text-transform:uppercase; margin-bottom:8px;">
                🥈 Second Favourite</div>
            <div style="color:#FFFFFF; font-size:1.75rem; font-weight:800; margin-bottom:6px;">
                {mc_results.iloc[1]['team']}</div>
            <div style="color:#f5c518; font-size:0.85rem; font-weight:600;">
                {mc_results.iloc[1]['win_pct']}% to win</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.25);
                    border-left:4px solid rgba(255,255,255,0.25); border-radius:12px; padding:20px 24px;">
            <div style="color:rgba(255,255,255,0.6); font-size:0.72rem; font-weight:700;
                        letter-spacing:0.1em; text-transform:uppercase; margin-bottom:8px;">
                🥉 Third Favourite</div>
            <div style="color:#FFFFFF; font-size:1.75rem; font-weight:800; margin-bottom:6px;">
                {mc_results.iloc[2]['team']}</div>
            <div style="color:#f5c518; font-size:0.85rem; font-weight:600;">
                {mc_results.iloc[2]['win_pct']}% to win</div>
        </div>
        """, unsafe_allow_html=True)

    # Full width container below columns
    st.markdown("---")
    with st.container():
        st.dataframe(
            mc_results.style.background_gradient(
                subset=['win_pct', 'final_pct', 'semi_pct'],
                cmap='YlOrRd'
            ).format({
                'win_pct':     '{:.2f}%',
                'final_pct':   '{:.2f}%',
                'semi_pct':    '{:.2f}%',
                'quarter_pct': '{:.2f}%',
                'r16_pct':     '{:.2f}%',
            }),
            use_container_width=True,
            height=600
        )

# ── Tab 2: Group Stage ────────────────────────────────────────────────────────
with tab2:
    st.header("Group Stage Predictions")

    st.markdown("<p style='color:rgba(255,255,255,0.7); font-size:0.85rem; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px;'>Filter by Group</p>", unsafe_allow_html=True)
    groups = sorted(fixtures_df['group_name'].unique())
    selected_group = st.selectbox("", ["All Groups"] + list(groups))

    if selected_group != "All Groups":
        filtered = fixtures_df[fixtures_df['group_name'] == selected_group]
    else:
        filtered = fixtures_df

    st.markdown(f"<p style='color:rgba(255,255,255,0.7); font-size:0.9rem;'>Showing <strong style='color:#FFFFFF;'>{len(filtered)}</strong> fixtures</p>", unsafe_allow_html=True)
    st.divider()

    for _, row in filtered.iterrows():
        pred = predict_match(row['lambda_home'], row['lambda_away'])

        st.markdown(f"""
        <div class="fixture-card">
            <div style="display:flex; justify-content:space-between; 
                        align-items:center; margin-bottom:12px;">
                <span style="color:#6b7280; font-size:0.8rem;">
                    GROUP {row['group_name']} &nbsp;·&nbsp; 
                    {str(row['date'])[:10]} &nbsp;·&nbsp; 
                    {row['city']}, {row['country']}
                </span>
            </div>
            <div style="display:grid; grid-template-columns:1fr auto 1fr; 
                        align-items:center; gap:16px;">
                <div>
                    <div style="font-size:1.2rem; font-weight:700; 
                                color:#e8eaf0;">{row['home_team']}</div>
                    <div style="color:#f5c518; font-size:1.5rem; 
                                font-weight:700;">{pred['prob_home_win']}%</div>
                    <div style="color:#6b7280; font-size:0.8rem;">
                        λ = {row['lambda_home']}</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#6b7280; font-size:0.85rem; 
                                margin-bottom:4px;">DRAW</div>
                    <div style="color:#e8eaf0; font-size:1.1rem; 
                                font-weight:600;">{pred['prob_draw']}%</div>
                    <div style="color:#6b7280; font-size:0.75rem; 
                                margin-top:4px;">Likely: {pred['most_likely_score']}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.2rem; font-weight:700; 
                                color:#e8eaf0;">{row['away_team']}</div>
                    <div style="color:#f5c518; font-size:1.5rem; 
                                font-weight:700;">{pred['prob_away_win']}%</div>
                    <div style="color:#6b7280; font-size:0.8rem;">
                        λ = {row['lambda_away']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Tab 3: Head to Head ───────────────────────────────────────────────────────
with tab3:
    st.header("Head to Head Predictor")
    st.markdown("<p style='color:rgba(255,255,255,0.7); font-size:0.9rem;'>Pick any two teams and simulate a match using the model.</p>", unsafe_allow_html=True)

    all_teams = sorted(set(
        fixtures_df['home_team'].tolist() +
        fixtures_df['away_team'].tolist()
    ))

    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("🏠 Home Team", all_teams, index=0)
    with col2:
        away_team = st.selectbox("✈️ Away Team", all_teams,
                                  index=min(1, len(all_teams)-1))

    if home_team == away_team:
        st.warning("Please select two different teams.")
    else:
        # Get attack/defence ratings
        home_row = fixtures_df[fixtures_df['home_team'] == home_team]
        if home_row.empty:
            home_row = fixtures_df[fixtures_df['away_team'] == home_team]
            lh = float(home_row.iloc[0]['away_attack']) if not home_row.empty else 1.0
            hd = float(home_row.iloc[0]['away_defence']) if not home_row.empty else 1.0
        else:
            lh = float(home_row.iloc[0]['home_attack'])
            hd = float(home_row.iloc[0]['home_defence'])

        away_row = fixtures_df[fixtures_df['away_team'] == away_team]
        if away_row.empty:
            away_row = fixtures_df[fixtures_df['home_team'] == away_team]
            la = float(away_row.iloc[0]['home_attack']) if not away_row.empty else 1.0
            ad = float(away_row.iloc[0]['home_defence']) if not away_row.empty else 1.0
        else:
            la = float(away_row.iloc[0]['away_attack'])
            ad = float(away_row.iloc[0]['away_defence'])

        # Squad multipliers
        home_sq = fixtures_df[fixtures_df['home_team'] == home_team]['home_squad_multiplier']
        if home_sq.empty:
            home_sq = fixtures_df[fixtures_df['away_team'] == home_team]['away_squad_multiplier']
        home_mult = float(home_sq.iloc[0]) if not home_sq.empty else 1.0

        away_sq = fixtures_df[fixtures_df['away_team'] == away_team]['away_squad_multiplier']
        if away_sq.empty:
            away_sq = fixtures_df[fixtures_df['home_team'] == away_team]['home_squad_multiplier']
        away_mult = float(away_sq.iloc[0]) if not away_sq.empty else 1.0

        baseline = fixtures_df['lambda_home'].mean()
        lambda_home = round(lh * ad * baseline * home_mult, 4)
        lambda_away = round(la * hd * baseline * away_mult, 4)

        pred = predict_match(lambda_home, lambda_away)

        st.divider()

        # Result display
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.04); border:1px solid 
                    rgba(255,255,255,0.08); border-radius:16px; 
                    padding:32px; margin-bottom:24px;">
            <div style="display:grid; grid-template-columns:1fr auto 1fr; 
                        align-items:center; gap:24px; text-align:center;">
                <div>
                    <div style="font-size:1.4rem; font-weight:700; 
                                color:#e8eaf0; margin-bottom:8px;">
                        🏠 {home_team}</div>
                    <div style="font-size:3rem; font-weight:800; 
                                color:#f5c518;">{pred['prob_home_win']}%</div>
                    <div style="color:#6b7280; font-size:0.85rem;">Win probability</div>
                    <div style="color:#6b7280; font-size:0.8rem; 
                                margin-top:8px;">λ = {lambda_home}</div>
                </div>
                <div>
                    <div style="color:#6b7280; font-size:0.85rem; 
                                text-transform:uppercase; letter-spacing:0.1em;
                                margin-bottom:8px;">Draw</div>
                    <div style="font-size:2rem; font-weight:700; 
                                color:#e8eaf0;">{pred['prob_draw']}%</div>
                    <div style="margin-top:16px; color:#6b7280; 
                                font-size:0.8rem;">Most likely</div>
                    <div style="font-size:1.4rem; font-weight:700; 
                                color:#f5c518;">{pred['most_likely_score']}</div>
                </div>
                <div>
                    <div style="font-size:1.4rem; font-weight:700; 
                                color:#e8eaf0; margin-bottom:8px;">
                        ✈️ {away_team}</div>
                    <div style="font-size:3rem; font-weight:800; 
                                color:#f5c518;">{pred['prob_away_win']}%</div>
                    <div style="color:#6b7280; font-size:0.85rem;">Win probability</div>
                    <div style="color:#6b7280; font-size:0.8rem; 
                                margin-top:8px;">λ = {lambda_away}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Scoreline matrix
        st.subheader("Scoreline Probability Matrix")
        st.markdown("<p style='color:rgba(255,255,255,0.7); font-size:0.9rem;'>Each cell shows the probability of that exact scoreline.</p>", unsafe_allow_html=True)

        max_show = 6
        matrix_df = pd.DataFrame(
            pred['matrix'][:max_show, :max_show] * 100,
            index=[f"{home_team} {i}" for i in range(max_show)],
            columns=[f"{away_team} {i}" for i in range(max_show)]
        ).round(2)

        st.dataframe(
            matrix_df.style.background_gradient(
                cmap='YlOrRd'
            ).format("{:.2f}%"),
            use_container_width=True
        )