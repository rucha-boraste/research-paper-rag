import streamlit as st
from api import signup, login, upload_pdf, get_documents

# --- 1. Session State Initialization ---
# Keeps track of variables across page reruns
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "active_doc" not in st.session_state:
    st.session_state.active_doc = None
if "username" not in st.session_state:
    st.session_state.username = None


def logout():
    st.session_state.logged_in = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user = None
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
            email_input = st.text_input("Email")
            pass_input = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                response = login(email=email_input, password=pass_input)

                if response.ok:
                    data = response.json()

                    st.session_state.logged_in = True
                    st.session_state.access_token = data["access_token"]
                    st.session_state.refresh_token = data["refresh_token"]
                    st.session_state.user = data["user"]
                    st.session_state.username = data["user"]["email"]

                    docs_response = get_documents(
                        st.session_state.access_token
                    )

                    if docs_response.ok:
                        st.session_state.documents = docs_response.json()

                        if st.session_state.documents:
                            st.session_state.active_doc = st.session_state.documents[0]

                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Login failed"))
                
    with tab2:
        st.subheader("Sign Up")
        with st.form("signup_form"):
            new_user = st.text_input("Username")
            new_email = st.text_input("Email")
            new_pass = st.text_input("Password", type="password")
            submit_signup = st.form_submit_button("Sign Up")
            
            if submit_signup:
                response = signup(
                    email=new_email,
                    username=new_user,
                    password=new_pass,
                )

                if response.ok:
                    st.success("Account created successfully! Please Login to Continue")

                else:
                    print(response.text)
                    st.error(response.json()["detail"])

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
        uploaded_file = st.file_uploader(
            "Upload a new PDF",
            type=["pdf"]
        )

        if uploaded_file is not None:

            if st.button("Upload Document"):

                with st.spinner("Uploading and processing document..."):

                    response = upload_pdf(
                        uploaded_file,
                        st.session_state.access_token,
                    )

                if response.ok:

                    st.success(response.json()["message"])

                    docs_response = get_documents(
                        st.session_state.access_token
                    )

                    if docs_response.ok:
                        st.session_state.documents = docs_response.json()

                        # Optional: automatically select the newly uploaded document
                        if st.session_state.documents:
                            st.session_state.active_doc = st.session_state.documents[0]

                        st.rerun()

                    else:
                        st.error(
                            docs_response.json().get(
                                "detail",
                                "Failed to refresh documents."
                            )
                        )

                else:

                    st.error(
                        response.json().get(
                            "detail",
                            "Upload failed."
                        )
                    )
        
        # Document Selector
        selected_doc = st.selectbox(
            "Select active document for chat",
            options=st.session_state.documents,
            format_func=lambda doc: doc["filename"],
            index=(
                st.session_state.documents.index(st.session_state.active_doc)
                if st.session_state.active_doc in st.session_state.documents
                else 0
            ),
        )
        
        # If the user switches documents, update state and clear chat history
        if selected_doc != st.session_state.active_doc:
            st.session_state.active_doc = selected_doc
            st.session_state.messages = [] 
            st.rerun()

    # --- Main Panel ---
    if st.session_state.active_doc:
        st.title(
            f"Chatting with: `{st.session_state.active_doc['filename']}`"
        )
    else:
        st.title("No document selected")
    
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