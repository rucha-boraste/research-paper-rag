import streamlit as st

# --- 1. Session State Initialization ---
# Keeps track of variables across page reruns
if "logged_in" not in st.session_state:
    st.session_state.logged_in = True
if "username" not in st.session_state:
    st.session_state.username = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = ["Onboarding_Guide.pdf"] # Placeholder for existing docs
if "active_doc" not in st.session_state:
    st.session_state.active_doc = "Onboarding_Guide.pdf"

# --- 2. Authentication Helper Functions ---
def login(username, password):
    # Add your actual database validation here
    if username and password:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.rerun()

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.messages = []
    st.rerun()

# --- 3. Page Configuration ---
st.set_page_config(page_title="RAG PDF Chat", layout="wide")

# ==========================================
# ROUTE A: LOGIN & SIGNUP PAGE
# ==========================================
if not st.session_state.logged_in:
    st.title("Welcome to the AI Document Assistant")
    st.write("Please log in or create an account to continue.")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                login(user_input, pass_input)
                
    with tab2:
        st.subheader("Sign Up")
        with st.form("signup_form"):
            new_user = st.text_input("Username")
            new_pass = st.text_input("Password", type="password")
            submit_signup = st.form_submit_button("Sign Up")
            
            if submit_signup:
                # Add your database insertion logic here
                st.success("Account created successfully! Please log in.")

# ==========================================
# ROUTE B: MAIN DASHBOARD
# ==========================================
else:
    # --- Sidebar Controls ---
    with st.sidebar:
        st.header("👤 User Info")
        st.write(f"**Logged in as:** {st.session_state.username}")
        if st.button("Logout", use_container_width=True):
            logout()
            
        st.divider()
        
        st.header("📄 Document Management")
        
        # Upload PDF
        uploaded_file = st.file_uploader("Upload a new PDF", type=["pdf"])
        if uploaded_file:
            if uploaded_file.name not in st.session_state.documents:
                st.session_state.documents.append(uploaded_file.name)
                st.success(f"Uploaded '{uploaded_file.name}'!")
                # Add logic here to chunk and embed the PDF into your vector database
        
        # Document Selector
        selected_doc = st.selectbox(
            "Select active document for chat", 
            options=st.session_state.documents,
            # Ensure the current active doc is selected by default
            index=st.session_state.documents.index(st.session_state.active_doc) if st.session_state.active_doc in st.session_state.documents else 0
        )
        
        # If the user switches documents, update state and clear chat history
        if selected_doc != st.session_state.active_doc:
            st.session_state.active_doc = selected_doc
            st.session_state.messages = [] 
            st.rerun()

    # --- Main Panel ---
    st.title(f"Chatting with: `{st.session_state.active_doc}`")
    
    # 1. Render Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # 2. Chat Input
    if prompt := st.chat_input("Ask a question about this document..."):
        
        # Display user prompt
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Display assistant response (Replace with your LLM/LangChain call)
        mock_response = f"Based on the context in `{st.session_state.active_doc}`, here is the answer to: '{prompt}'"
        
        st.session_state.messages.append({"role": "assistant", "content": mock_response})
        with st.chat_message("assistant"):
            st.markdown(mock_response)