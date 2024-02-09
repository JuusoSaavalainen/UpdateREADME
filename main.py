import streamlit as st
import requests
from wordcloud import WordCloud
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


@dataclass
class Commit:
    message: str
    time: datetime
    repo: str


def get_own_repositories(username):
    try:
        repos_url = f'https://api.github.com/users/{username}/repos'
        repos_response = requests.get(repos_url)
        repos_response.raise_for_status()
        repos_data = repos_response.json()

        own_repositories = []

        for repo in repos_data:
            if not repo['fork'] and repo['owner']['login'] == username:
                own_repositories.append(repo['name'])

        return own_repositories
    except Exception as e:
        st.error(f'Error fetching repositories: {e}')
        return []


def get_commit_messages_with_time(username):
    try:
        own_repositories = get_own_repositories(username)
        all_commits = []

        for repo_name in own_repositories:
            commits_url = f'https://api.github.com/repos/{username}/{repo_name}/commits?per_page=100'
            commits_response = requests.get(commits_url)
            commits_response.raise_for_status()
            commits_data = commits_response.json()

            for commit in commits_data:
                commit_message = commit['commit']['message']
                commit_time = datetime.strptime(
                    commit['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ")
                all_commits.append(
                    Commit(message=commit_message, time=commit_time, repo=repo_name))

        return all_commits
    except Exception as e:
        st.error(f'Error fetching commit messages: {e}')
        return []


def filter_commit_data(commit_messages):
    one_year_ago = datetime.now() - timedelta(days=365)
    return [commit for commit in commit_messages if commit.time >= one_year_ago]


def plot_commit_frequency(commit_messages):
    if commit_messages:
        commit_df = pd.DataFrame([(commit.time, commit.message) for commit in commit_messages], columns=[
                                 'Commit Date', 'Commit Message'])
        commit_df = commit_df.sort_values(by='Commit Date')
        commit_df['LastYear/WeeklyBins'] = commit_df['Commit Date'].dt.to_period(
            'W')
        commit_counts = commit_df.groupby('LastYear/WeeklyBins').size()
        all_weeks = pd.date_range(
            end=datetime.now(), periods=52, freq='W').to_period('W')
        commit_counts = commit_counts.reindex(all_weeks, fill_value=0)
        commit_percentages = commit_counts / commit_counts.sum() * 100
        data = pd.DataFrame({'LastYear/WeeklyBins': commit_percentages.index.astype(
            str), 'Percentage of Commits': commit_percentages.values})
        st.line_chart(data, x='LastYear/WeeklyBins', y='Percentage of Commits',
                      use_container_width=True)
    else:
        st.warning("No commit data available for the past year.")


def get_commit_counts_per_repo(commit_messages):
    commit_counts = Counter([commit.repo for commit in commit_messages])
    return commit_counts


st.sidebar.title('Options')
st.sidebar.header('Notices', divider='rainbow')
st.sidebar.subheader(
    '1. API is rate limited so it will fail after few uses')
st.sidebar.subheader('2. We fetch max 100 commits / repo',  divider='blue')
info_placeholder = st.sidebar.empty()
username = st.sidebar.text_input('Enter GitHub Username')

if st.sidebar.button('Generate Word Cloud and Timeline') or username:
    if username:
        info_placeholder.info(f"Fetching commit messages for {username}...")
        commit_messages = get_commit_messages_with_time(username)
        commit_messages_filtered = filter_commit_data(commit_messages)
        if commit_messages_filtered:
            commit_counts = get_commit_counts_per_repo(
                commit_messages_filtered)
            st.sidebar.subheader("Commit Counts per Repository:")
            for repo, count in commit_counts.items():
                st.sidebar.write(f"- {repo}: {count} commits")
            formatted_messages = ' '.join(
                commit.message for commit in commit_messages_filtered)
            wordcloud = WordCloud(
                width=800, height=400, background_color="rgba(255, 255, 255, 0)", mode="RGBA").generate(formatted_messages)
            st.image(wordcloud.to_array(),
                     caption=f'Word Cloud of {username} Commit Messages')
            info_placeholder.empty()
            info_placeholder.info("Generating Commit Frequency Plot...")
            plot_commit_frequency(commit_messages_filtered)
            info_placeholder.empty()
        else:
            st.warning('No commit messages found for the given username.')
    else:
        st.warning('Please enter a GitHub username.')
