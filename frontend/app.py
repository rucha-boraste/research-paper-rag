import streamlit as st
import time
from api import signup, login, upload_pdf, get_documents, answer_query, get_chat_history, get_document_status, refresh_access_token
from streamlit_cookies_manager import EncryptedCookieManager

COOKIE_PASSWORD = "A9vK7mQ2xLp8RzN4fH1cUw6YjE3sTb5GqX0nMdW9PkVr2"

cookies = EncryptedCookieManager(
    prefix="rag",
    password=COOKIE_PASSWORD,
)

if not cookies.ready():
    st.stop()


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
    
    response = get_chat_history(
        st.session_state.active_doc["id"],
        st.session_state.access_token,
    )


    if response.ok:
        for chat in response.json()["chats"]:
            st.session_state.messages.extend([
                {"role": "user", "content": chat["question"]},
                {"role": "assistant", "content": chat["answer"]},
            ])


refresh_token = cookies.get("refresh_token")

if (
    not st.session_state.logged_in
    and refresh_token
    and refresh_token.strip() != ""
):
    response = refresh_access_token(refresh_token)

    if response.ok:

        data = response.json()

        st.session_state.logged_in = True
        st.session_state.access_token = data["access_token"]
        st.session_state.user = data["user"]
        st.session_state.username = data["user"]["email"]

        docs = get_documents(
            st.session_state.access_token
        )

        if docs.ok:
            st.session_state.documents = docs.json()

            if st.session_state.documents:
                st.session_state.active_doc = (
                    st.session_state.documents[0]
                )

                load_active_document_history()

        st.rerun()

    else:

        del cookies["refresh_token"]
        cookies.save()

def logout():
    st.session_state.logged_in = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user = None
    st.session_state.username = None
    st.session_state.messages = []
    st.session_state.documents = []
    st.session_state.active_doc = None

    cookies["refresh_token"] = ""
    cookies.save()

    st.rerun()

st.set_page_config(page_title="RAG PDF Chat", layout="wide")

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
                    cookies["refresh_token"] = data["refresh_token"]
                    cookies.save()
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

else:
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
                documents = []

            # Upload all PDFs first
                for index, uploaded_file in enumerate(uploaded_files):

                    with st.spinner(f"Uploading {uploaded_file.name}..."):
                        response = upload_pdf(
                            uploaded_file,
                            st.session_state.access_token,
                        )

                    if response.ok:
                        successful += 1

                        data = response.json()

                        documents.append({
                            "id": data["document_id"],
                            "filename": uploaded_file.name,
                        })

                    else:
                        st.error(f"Failed to upload {uploaded_file.name}")

                    progress.progress((index + 1) / len(uploaded_files))


                # Now wait for all PDFs simultaneously
                remaining = documents.copy()

                while remaining:

                    time.sleep(2)

                    finished = []

                    for doc in remaining:

                        status_response = get_document_status(
                            doc["id"],
                            st.session_state.access_token,
                        )

                        if not status_response.ok:
                            continue

                        status = status_response.json()["status"]

                        if status == "COMPLETED":
                            st.success(f"{doc['filename']} completed.")
                            finished.append(doc)

                        elif status == "FAILED":
                            st.error(f"{doc['filename']} failed.")
                            finished.append(doc)

                    for doc in finished:
                        remaining.remove(doc)


                docs_response = get_documents(st.session_state.access_token)

                if docs_response.ok:
                    st.session_state.documents = docs_response.json()

                    if st.session_state.documents:
                        st.session_state.active_doc = st.session_state.documents[0]
                        load_active_document_history()

                st.success(f"{successful}/{len(uploaded_files)} document(s) uploaded successfully.")

                st.rerun()
        
        # Document Selector
        search_query = st.text_input(
            "🔍 Search documents",
            placeholder="Type a filename...",
        )

        # Filter documents
        filtered_documents = sorted(
            [
                doc
                for doc in st.session_state.documents
                if search_query.lower() in doc["filename"].lower()
            ],
            key=lambda doc: doc["filename"].lower(),
        )

        if filtered_documents:
            default_index = 0

            if (
                st.session_state.active_doc
                and st.session_state.active_doc in filtered_documents
            ):
                default_index = filtered_documents.index(
                    st.session_state.active_doc
                )

            selected_doc = st.selectbox(
                "Select active document for chat",
                options=filtered_documents,
                format_func=lambda doc: doc["filename"],
                index=default_index,
            )

            if selected_doc != st.session_state.active_doc:
                st.session_state.active_doc = selected_doc
                load_active_document_history()
                st.rerun()

        else:
            st.info("No matching documents found.")

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