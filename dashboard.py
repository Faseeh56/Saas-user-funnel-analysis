import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from textblob import TextBlob
from datetime import datetime
from collections import Counter

# ------------------------------------------------------------
# PAGE CONFIG & DARK MODE STYLING
# ------------------------------------------------------------
st.set_page_config(
    page_title="Complete SaaS Funnel Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .css-1d391kg, .st-bb, .st-at { background-color: #1E1E2E; }
    .st-bw, .st-ae { color: #FFFFFF; }
    h1, h2, h3, h4 { color: #FFFFFF; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 8px; }
    .stButton>button:hover { background-color: #45a049; }
</style>
""", unsafe_allow_html=True)

st.title("🚀 Complete SaaS Funnel Analytics Dashboard")
st.markdown("Conversion funnel | Cohort retention | Sentiment analysis | Behavior insights")

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("cleaned_saas_data.csv")
    df['signup_date'] = pd.to_datetime(df['signup_date'])
    df['signup_month'] = df['signup_date'].dt.to_period('M').astype(str)
    ref_date = df['signup_date'].max() + pd.Timedelta(days=30)
    df['months_since_signup'] = ((ref_date - df['signup_date']).dt.days / 30).astype(int).clip(upper=6)
    return df

df = load_data()

# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------
st.sidebar.header("🔍 Filters")
channel_filter = st.sidebar.multiselect("Acquisition Channel", df['acquisition_channel'].unique(), default=df['acquisition_channel'].unique())
country_filter = st.sidebar.multiselect("Country", df['country'].unique(), default=df['country'].unique())
funnel_filter = st.sidebar.multiselect("Funnel Stage", df['funnel_stage'].unique(), default=df['funnel_stage'].unique())
device_filter = st.sidebar.multiselect("Device Type", df['device_type'].unique(), default=df['device_type'].unique())
plan_filter = st.sidebar.multiselect("Plan Type", df['plan_type'].unique(), default=df['plan_type'].unique())
month_filter = st.sidebar.multiselect("Signup Month", sorted(df['signup_month'].unique()), default=sorted(df['signup_month'].unique()))

filtered_df = df[
    (df['acquisition_channel'].isin(channel_filter)) &
    (df['country'].isin(country_filter)) &
    (df['funnel_stage'].isin(funnel_filter)) &
    (df['device_type'].isin(device_filter)) &
    (df['plan_type'].isin(plan_filter)) &
    (df['signup_month'].isin(month_filter))
]

# ------------------------------------------------------------
# DOWNLOAD BUTTON
# ------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📥 Export Data")
csv_data = filtered_df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button("Download Filtered CSV", csv_data, "filtered_saas_data.csv", "text/csv")

# ------------------------------------------------------------
# KPI ROW
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Total Users", f"{len(filtered_df):,}")
with col2: st.metric("Upgrade Rate", f"{filtered_df['upgraded'].mean()*100:.1f}%")
with col3: st.metric("Churn Rate", f"{filtered_df['churned'].mean()*100:.1f}%")
with col4: st.metric("Avg Satisfaction", f"{filtered_df['satisfaction_score'].mean():.2f} / 5.0")

# ------------------------------------------------------------
# 1. FUNNEL CHART + CONVERSION / DROP-OFF RATES
# ------------------------------------------------------------
st.subheader("📉 Conversion Funnel")

funnel_order = [
    'Upgrade',
    'First Feature Use',
    'Onboarding',
    'Sign-up',
    'Landing'
        
]

# CUMULATIVE funnel counts
funnel_counts = []

for stage in funnel_order:

    if stage == 'Landing':
        count = len(filtered_df)

    elif stage == 'Sign-up':
        count = len(filtered_df[
            filtered_df['funnel_stage'].isin([
                'Sign-up',
                'Onboarding',
                'First Feature Use',
                'Upgrade'
            ])
        ])

    elif stage == 'Onboarding':
        count = len(filtered_df[
            filtered_df['funnel_stage'].isin([
                'Onboarding',
                'First Feature Use',
                'Upgrade'
            ])
        ])

    elif stage == 'First Feature Use':
        count = len(filtered_df[
            filtered_df['funnel_stage'].isin([
                'First Feature Use',
                'Upgrade'
            ])
        ])

    elif stage == 'Upgrade':
        count = len(filtered_df[
            filtered_df['funnel_stage'] == 'Upgrade'
        ])

    funnel_counts.append(count)

funnel_counts = pd.DataFrame({
    'stage': funnel_order,
    'count': funnel_counts
})

fig_funnel = px.funnel(funnel_counts, x='count', y='stage', title='User Conversion Funnel', color='stage',
                       color_discrete_sequence=px.colors.qualitative.Pastel,
                       labels={'count': 'Number of Users', 'stage': 'Funnel Stage'})
st.plotly_chart(fig_funnel, use_container_width=True)

# Calculate conversion and drop-off rates
st.subheader("📊 Conversion & Drop-off Rates")
conversion_data = []
for i in range(len(funnel_order)):
    current_count = funnel_counts.iloc[i]['count']
    if i == 0:
        conversion_rate = 100.0
    else:
        prev_count = funnel_counts.iloc[i-1]['count']
        conversion_rate = (current_count / prev_count * 100) if prev_count > 0 else 0
    drop_off = 100 - conversion_rate if i > 0 else 0
    conversion_data.append({
        'Stage': funnel_order[i],
        'Users': int(current_count),
        'Conversion Rate (%)': round(conversion_rate, 1),
        'Drop-off Rate (%)': round(drop_off, 1) if i > 0 else '-'
    })

st.dataframe(pd.DataFrame(conversion_data), use_container_width=True)

# Optional: bar chart of drop-off rates
dropoff_df = pd.DataFrame(conversion_data[1:])  # skip Landing
if not dropoff_df.empty:
    fig_drop = px.bar(dropoff_df, x='Stage', y='Drop-off Rate (%)', title='Drop-off Rate by Funnel Step',
                      color='Stage', text='Drop-off Rate (%)')
    fig_drop.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    st.plotly_chart(fig_drop, use_container_width=True)

# ------------------------------------------------------------
# 2. USER BEHAVIOR ANALYSIS
# ------------------------------------------------------------
st.subheader("📈 User Behavior by Funnel Stage")

# Session duration analysis
session_avg = filtered_df.groupby('funnel_stage')['session_duration_min'].mean().reindex(funnel_order).reset_index()
session_avg.columns = ['Funnel Stage', 'Avg Session Duration (min)']
fig_session = px.bar(session_avg, x='Funnel Stage', y='Avg Session Duration (min)', 
                     title='Average Session Duration per Funnel Stage', color='Funnel Stage')
st.plotly_chart(fig_session, use_container_width=True)

# Feature usage analysis
features_avg = filtered_df.groupby('funnel_stage')['features_used'].mean().reindex(funnel_order).reset_index()
features_avg.columns = ['Funnel Stage', 'Avg Features Used']
fig_features = px.bar(features_avg, x='Funnel Stage', y='Avg Features Used',
                      title='Average Number of Features Used per Funnel Stage', color='Funnel Stage')
st.plotly_chart(fig_features, use_container_width=True)

# ------------------------------------------------------------
# 3. DEVICE ANALYSIS
# ------------------------------------------------------------
st.subheader("📱 Performance by Device Type")
device_upgrade = filtered_df.groupby('device_type')['upgraded'].mean().reset_index()
device_upgrade['upgraded'] *= 100
fig_device = px.bar(device_upgrade, x='device_type', y='upgraded', title='Upgrade Rate by Device Type',
                    color='device_type', text='upgraded', labels={'upgraded': 'Upgrade Rate (%)'})
fig_device.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
st.plotly_chart(fig_device, use_container_width=True)

# Optionally: device funnel completion (percentage of users reaching Upgrade)
device_funnel = filtered_df.groupby('device_type')['funnel_stage'].apply(lambda x: (x == 'Upgrade').mean() * 100).reset_index()
device_funnel.columns = ['Device Type', '% Reached Upgrade']
fig_device_funnel = px.bar(device_funnel, x='Device Type', y='% Reached Upgrade', title='% of Users Who Reach Upgrade by Device',
                           color='Device Type', text='% Reached Upgrade')
fig_device_funnel.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
st.plotly_chart(fig_device_funnel, use_container_width=True)

# ------------------------------------------------------------
# 4. COHORT RETENTION HEATMAP
# ------------------------------------------------------------
st.subheader("📅 Cohort Retention Heatmap")
retention_data = filtered_df.groupby(['signup_month', 'months_since_signup'])['churned'].apply(lambda x: (1 - x.mean()) * 100).reset_index()
retention_data.columns = ['signup_month', 'months_since', 'retention_rate']
pivot_retention = retention_data.pivot(index='signup_month', columns='months_since', values='retention_rate')
fig_heatmap = px.imshow(pivot_retention, text_auto=True, aspect="auto", color_continuous_scale='RdYlGn',
                        title='Cohort Retention (%) by Month Since Signup',
                        labels=dict(x="Months Since Signup", y="Signup Month", color="Retention"))
fig_heatmap.update_layout(height=500)
st.plotly_chart(fig_heatmap, use_container_width=True)

# ------------------------------------------------------------
# 5. SENTIMENT ANALYSIS (TextBlob)
# ------------------------------------------------------------
st.subheader("💬 Sentiment Analysis of User Feedback")

def get_sentiment(text):
    blob = TextBlob(str(text))
    return blob.sentiment.polarity

filtered_df['sentiment_score'] = filtered_df['user_feedback'].apply(get_sentiment)
filtered_df['sentiment_label'] = pd.cut(filtered_df['sentiment_score'], bins=[-1, -0.1, 0.1, 1], labels=['Negative', 'Neutral', 'Positive'])

sentiment_counts = filtered_df['sentiment_label'].value_counts().reset_index()
sentiment_counts.columns = ['Sentiment', 'Count']
fig_sentiment = px.pie(sentiment_counts, values='Count', names='Sentiment', title='Sentiment Distribution',
                       color='Sentiment', color_discrete_map={'Positive':'#2E8B57', 'Neutral':'#FFD700', 'Negative':'#CD5C5C'})
st.plotly_chart(fig_sentiment, use_container_width=True)

st.markdown("**Average satisfaction score per sentiment:**")
st.dataframe(filtered_df.groupby('sentiment_label')['satisfaction_score'].mean().round(2).reset_index())

# ------------------------------------------------------------
# 6. POSITIVE FEEDBACK KEYWORDS (new)
# ------------------------------------------------------------
st.subheader("👍 Positive Feedback Keywords")
positive_df = filtered_df[filtered_df['sentiment_label'] == 'Positive']
if not positive_df.empty:
    all_text = " ".join(positive_df['user_feedback'].astype(str).str.lower())
    # Simple keyword extraction (common words, remove stopwords)
    stopwords = set(['the', 'and', 'to', 'of', 'a', 'is', 'it', 'for', 'with', 'on', 'was', 'are', 'as', 'be', 'this', 'that', 'i', 'you', 'we', 'they', 'he', 'she', 'it', 'my', 'your', 'our', 'their', 'very', 'really', 'just', 'but', 'so', 'not', 'have', 'were', 'had', 'been', 'from', 'at', 'by', 'in', 'out', 'up', 'down', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under', 'over'])
    words = [w for w in all_text.split() if len(w) > 3 and w not in stopwords and w.isalpha()]
    word_freq = Counter(words).most_common(20)
    if word_freq:
        kw_df = pd.DataFrame(word_freq, columns=['Keyword', 'Frequency'])
        st.dataframe(kw_df, use_container_width=True)
        # Optional: simple bar chart
        fig_kw = px.bar(kw_df, x='Frequency', y='Keyword', orientation='h', title='Top 20 Positive Keywords')
        st.plotly_chart(fig_kw, use_container_width=True)
    else:
        st.info("No positive feedback to extract keywords from.")
else:
    st.info("No positive feedback in filtered data.")

# ------------------------------------------------------------
# 7. TOP COMPLAINTS (Negative feedback)
# ------------------------------------------------------------
st.subheader("🔥 Top User Complaints (Negative Feedback)")
negative_df = filtered_df[filtered_df['sentiment_label'] == 'Negative']
if not negative_df.empty:
    top_complaints = negative_df['user_feedback'].value_counts().head(10).reset_index()
    top_complaints.columns = ['Complaint', 'Frequency']
    st.dataframe(top_complaints, use_container_width=True)
else:
    st.info("No negative feedback in filtered data.")

# ------------------------------------------------------------
# 8. WORD CLOUD (all feedback)
# ------------------------------------------------------------
st.subheader("🧠 Word Cloud of All User Feedback")
text = " ".join(filtered_df['user_feedback'].dropna().astype(str))
if text.strip():
    wordcloud = WordCloud(width=800, height=400, background_color='#1E1E2E', colormap='plasma', contour_color='white', contour_width=1).generate(text)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)
else:
    st.warning("No feedback text available.")

# ------------------------------------------------------------
# 9. RAW DATA PREVIEW
# ------------------------------------------------------------
st.subheader("🗂 Filtered Raw Data Preview")
st.dataframe(filtered_df.head(20), use_container_width=True)

# ------------------------------------------------------------
# Sidebar note
# ------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.info("💡 **Complete Dashboard** | Includes conversion rates, behavior KPIs, device analysis, and positive keywords.")