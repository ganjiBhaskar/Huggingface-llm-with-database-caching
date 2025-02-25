import os
import streamlit as st
import sqlite3
from langchain_huggingface import HuggingFaceEndpoint
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Set your Hugging Face API token
os.environ['HUGGINGFACEHUB_API_TOKEN'] = "api-tocken"

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('qa_database.db')
    c = conn.cursor()
    # Create table for question-answer pairs
    c.execute('''CREATE TABLE IF NOT EXISTS qa_pairs
                 (question TEXT PRIMARY KEY, answer TEXT)''')
    # Create table for hit counters
    c.execute('''CREATE TABLE IF NOT EXISTS hit_counters
                 (source TEXT PRIMARY KEY, count INTEGER)''')
    # Initialize counters if they don't exist
    c.execute("INSERT OR IGNORE INTO hit_counters (source, count) VALUES ('Database Hits', 0)")
    c.execute("INSERT OR IGNORE INTO hit_counters (source, count) VALUES ('LLM Hits', 0)")
    conn.commit()
    conn.close()

# Function to insert question-answer pair into the database
def insert_into_db(question, answer):
    conn = sqlite3.connect('qa_database.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO qa_pairs (question, answer) VALUES (?, ?)", (question, answer))
    conn.commit()
    conn.close()

# Function to retrieve answer from the database
def get_from_db(question):
    conn = sqlite3.connect('qa_database.db')
    c = conn.cursor()
    c.execute("SELECT answer FROM qa_pairs WHERE question=?", (question,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# Function to update hit counters
def update_hit_counter(source):
    conn = sqlite3.connect('qa_database.db')
    c = conn.cursor()
    c.execute("UPDATE hit_counters SET count = count + 1 WHERE source = ?", (source,))
    conn.commit()
    conn.close()

# Function to get hit counters
def get_hit_counters():
    conn = sqlite3.connect('qa_database.db')
    c = conn.cursor()
    c.execute("SELECT source, count FROM hit_counters")
    results = c.fetchall()
    conn.close()
    return {source: count for source, count in results}

# Initialize Hugging Face LLM
repo_id = "mistralai/Mistral-7B-Instruct-v0.3"
llm = HuggingFaceEndpoint(repo_id=repo_id, max_length=128, temperature=0.7, huggingfacehub_api_token="api-tocken")

# Define a prompt template
prompt_template = PromptTemplate(
    input_variables=["question"],
    template="Answer the following question: {question}"
)

# Create an LLMChain
qa_chain = LLMChain(llm=llm, prompt=prompt_template)

# Streamlit UI
st.title("Q&A App with Hugging Face LLM and Database Caching")

# Initialize the database
init_db()

# Input box for the user to ask a question
user_question = st.text_input("Ask your question here:")

if user_question:
    # Check if the question is already in the database
    cached_answer = get_from_db(user_question)
    if cached_answer:
        update_hit_counter("Database Hits")  # Increment database hit counter
        st.write(f"**Answer (from database):** {cached_answer}")
    else:
        # Query the LLM for the answer
        with st.spinner("Fetching answer from Hugging Face LLM..."):
            llm_answer = qa_chain.run(user_question)
        
        # Store the question-answer pair in the database
        insert_into_db(user_question, llm_answer)
        
        update_hit_counter("LLM Hits")  # Increment LLM hit counter
        st.write(f"**Answer (from LLM):** {llm_answer}")

# Display cumulative hit statistics
st.subheader("Cumulative Query Hit Statistics")
hit_counters = get_hit_counters()
chart_data = {
    "Source": list(hit_counters.keys()),
    "Count": list(hit_counters.values())
}
st.bar_chart(chart_data, x="Source", y="Count")
