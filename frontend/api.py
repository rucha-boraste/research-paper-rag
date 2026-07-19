import requests

API_URL = "http://backend:8000/api/v1"

def signup(email, username, password):
    response = requests.post(
        f"{API_URL}/auth/signup",
        json={
            "username": username,
            "email": email,
            "password": password
        },
        timeout=30,
    )

    return response


def login(email, password):
    response = requests.post(
        f"{API_URL}/auth/login",
        json={
            "email": email,
            "password": password,
        },
        timeout=30
    )

    return response


def upload_pdf(file, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    files = {
        "file": (
            file.name,
            file.getvalue(),
            "application/pdf",
        )
}

    response = requests.post(
        f"{API_URL}/rag/upload",
        headers=headers,
        files=files,
        timeout=300,      
    )

    return response


def get_documents(access_token):

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{API_URL}/rag/get_documents"
    print(url)

    response = requests.get(
        url,
        headers=headers,
    )

    return response

def answer_query(query, document_id, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(
        f"{API_URL}/rag/answer",
        headers=headers,
        json={
            "query": query,
            "document_id": document_id,
        },
        timeout=120,
    )
    return response


def get_chat_history(document_id, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"{API_URL}/rag/get_history",
        headers=headers,
        params={"document_id": document_id},
        timeout=30,
    )
    return response

def get_document_status(document_id, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(
        f"{API_URL}/rag/documents/{document_id}/status",
        headers=headers,
        timeout=30,
    )

    return response

def refresh_access_token(refresh_token):
    response = requests.post(
        f"{API_URL}/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
        timeout=30,
    )

    return response