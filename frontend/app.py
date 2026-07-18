import streamlit as st
import time
from api import signup, login, upload_pdf, get_documents, answer_query, get_chat_history, get_document_status

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

def load_active_document_history():
    st.session_state.messages = []
    if not st.session_state.active_doc:
        return

    # st.write(st.session_state.active_doc)
    # st.write(type(st.session_state.active_doc["id"]))
    response = get_chat_history(
        st.session_state.active_doc["id"],
        st.session_state.access_token,
    )

    # print(response.text)

    if response.ok:
        for chat in response.json()["chats"]:
            st.session_state.messages.extend([
                {"role": "user", "content": chat["question"]},
                {"role": "assistant", "content": chat["answer"]},
            ])


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
                            load_active_document_history()
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
        uploaded_files = st.file_uploader(
            "Upload PDF(s)",
            type=["pdf"],
            accept_multiple_files=True,
        )

        if uploaded_files:

            if st.button("Upload Document(s)"):

                progress = st.progress(0)

                successful = 0

                for index, uploaded_file in enumerate(uploaded_files):

                    with st.spinner(f"Uploading {uploaded_file.name}..."):

                        response = upload_pdf(
                            uploaded_file,
                            st.session_state.access_token,
                        )

                    if response.ok:

                        successful += 1

                        data = response.json()

                        document_id = data["document_id"]

                        status = data["status"]

                        status_placeholder = st.empty()

                        while status in ["QUEUED", "PROCESSING"]:

                            status_placeholder.info(
                                f"{uploaded_file.name}: {status}"
                            )

                            time.sleep(2)

                            status_response = get_document_status(
                                document_id,
                                st.session_state.access_token,
                            )

                            if not status_response.ok:
                                break

                            status_data = status_response.json()

                            status = status_data["status"]

                        if status == "COMPLETED":

                            status_placeholder.success(
                                f"{uploaded_file.name}: Processing completed."
                            )

                            docs_response = get_documents(
                                st.session_state.access_token
                            )

                            if docs_response.ok:
                                st.session_state.documents = docs_response.json()

                                if st.session_state.documents:
                                    st.session_state.active_doc = (
                                        st.session_state.documents[0]
                                    )

                        elif status == "FAILED":

                            status_placeholder.error(
                                status_data.get(
                                    "error_message",
                                    "Document processing failed.",
                                )
                            )

                    else:

                        st.error(
                            f"Failed to upload {uploaded_file.name}"
                        )

                    progress.progress((index + 1) / len(uploaded_files))

                st.success(
                    f"{successful}/{len(uploaded_files)} document(s) uploaded successfully."
                )

                st.rerun()
        
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
            load_active_document_history()
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
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = answer_query(
            prompt,
            st.session_state.active_doc["id"],
            st.session_state.access_token,
        )

        if response.ok:
            answer = response.json()["answer"]
            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)
        else:
            st.error(response.text)