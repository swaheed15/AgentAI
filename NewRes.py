import os 
import logging
import streamlit as st
from langchain_groq import ChatGroq
from langchain_community.utilities import PubMedAPIWrapper
from langchain.tools import Tool 
from langchain_community.tools.pubmed.tool import PubmedQueryRun  # Corrected import

from langchain.agents import initialize_agent, AgentType
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv() 

# Retrieve the PubMed API Key
pubmed_api_key = st.secrets["PUBMED_API_KEY"]
groq_api_key = st.secrets["GROQ_API_KEY"]

# Ensure the API key is available for PubMed
if not pubmed_api_key:
    raise ValueError("PubMed API key is missing. Please add it to the environment variables.")

# Set up PubMed API Wrapper with the API key
pubmed_wrapper = PubMedAPIWrapper(top_k_results=1, doc_content_chars_max=300, api_key=pubmed_api_key)

# Initialize PubMedQueryRun tool with PubMed API Wrapper
pubmed = PubmedQueryRun(api_wrapper=pubmed_wrapper)  # Corrected initialization

# Google Scholar Query Function using scholarly
from scholarly import scholarly

def google_scholar_query(query, num_results=10, start=0):
    search_results = scholarly.search_pubs(query)
    results = []  # Initialize results as an empty list
    try:
        for _ in range(num_results):
            result = next(search_results)
            results.append(result["bib"])
    except StopIteration:
        return results
    return results


# Wrap Google Scholar query function as a tool
google_scholar_tool = Tool(
    name="GoogleScholarQuery",
    description="Search Google Scholar for academic articles.",
    func=google_scholar_query
)

# Initialize Tools
tools = (pubmed, google_scholar_tool)

# Streamlit app setup
st.title("Research Agent")
st.write("This agent helps you search PubMed and Google Scholar")


# Add sliders for user customization in a vertical layout
st.write("Customize your search:")

# Create a vertical layout for better visibility
top_k_results = st.slider(
    label="Top Results:",
    min_value=1,
    max_value=10,
    value=5,
    step=1,
    help="Select the number of top search results to display."
)

doc_content_chars_max = st.slider(
    label="Max Characters:",
    min_value=100,
    max_value=500,
    value=250,
    step=100,
    help="Set the maximum number of characters per document."
)

# Display the selected values for debugging or user confirmation (optional)
st.write(f"Selected Top Results: {top_k_results}")
st.write(f"Selected Max Characters: {doc_content_chars_max}")

st.sidebar.title("Settings")
api_key = st.sidebar.text_input("Please Enter your Groq API key:", type="password")

# Initialize message history for the chat
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "Assistant",
            "content": "Hi, I am your research assistant. How can I help you?"
        }
    ]

# Display previous messages in a scrollable container
with st.container():
    # Display previous messages
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])


# Chat Input Box and Prompt Handling
if prompt := st.chat_input("Search me recent 5 years articles on role of oxytocin in prevention of PPH"):

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

        # Log the slider values for debugging
    logging.info(f"Top K Results: {top_k_results}, Max Characters: {doc_content_chars_max}")
        
        
        # Update PubMed Wrapper with slider values
    pubmed_wrapper.top_k_results = top_k_results
    pubmed_wrapper.doc_content_chars_max = doc_content_chars_max


    # LLM Initialization
    llm = ChatGroq(
            groq_api_key=api_key,
            model_name="gemma2-9b-it",
            streaming=True
    )

        # Initialize Tools for the Search Agent
    tools = (pubmed, google_scholar_query)

        # Initialize the agent with the tools
    search_agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        handling_parsing_errors=True
    )

    with st.chat_message("assistant"):
        # Set up the callback handler for streamlit messages
        st_cb = StreamlitCallbackHandler(st.container(), expand_new_thoughts=False)

        # Run the agent with the current messages
        response = search_agent.run(st.session_state.messages, callback=[st_cb])

        # Append the assistant's response to the session messages
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

        # Display the response from the assistant
    st.write(response)
    