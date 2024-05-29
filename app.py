import streamlit as st
import os
import shutil
from chatbot import handle_user_query, create_database, save_file_to_db

# Define the database path
DB_PATH = os.path.join("database", "chatbot.db")

def main():
    create_database()
    st.title("OnboardMate")

    # Initialize session state for conversation history and query
    if "history" not in st.session_state:
        st.session_state.history = [("OnboardMate Assistant", "Hello! How can I help you today?")]

    if "query" not in st.session_state:
        st.session_state.query = ""

    # File uploader
    uploaded_files = st.file_uploader("Upload Project Files", type=["txt", "py", "md", "jpg", "png", "pdf", "zip", "mp4"], accept_multiple_files=True)

    if st.button("Upload Files"):
        if uploaded_files:
            with st.spinner("Processing files..."):
                for uploaded_file in uploaded_files:
                    if uploaded_file.type == "application/zip":
                        process_zip_folder(uploaded_file)
                    else:
                        save_file_to_db(uploaded_file)
            st.success("Files uploaded successfully")
        else:
            st.error("Please upload at least one file.")

    st.header("OnboardMate Assistant")

    # Chat area
    chat_area = st.empty()
    with chat_area.container():
        chat_container = st.container()
        with chat_container:
            for role, message in st.session_state.history:
                if role == "User":
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <img src="https://img.icons8.com/ios-filled/50/000000/user.png" style="width: 25px; margin-right: 10px;">
                        <strong>User:</strong>
                    </div>
                    <div style="margin-left: 35px;">{message}</div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <img src="https://img.icons8.com/ios-filled/50/000000/robot.png" style="width: 25px; margin-right: 10px;">
                        <strong>OnboardMate Assistant:</strong>
                    </div>
                    <div style="">{message}</div>
                    """, unsafe_allow_html=True)

    # User input
    st.session_state.query = st.text_input("Ask your question about the project files:", st.session_state.query)

    # Create two equal columns
    button_col1, space1, button_col2 = st.columns([1, 2.2, 1])

    # Place the "Ask" button in the first column
    with button_col1:
        ask_button = st.button("Ask")
    with space1:
        st.empty()
    # Place the "Clear Conversation" button in the second column
    with button_col2:
        clear_button = st.button("Clear Conversation")

    st.markdown(f"""
    </div>
    """, unsafe_allow_html=True)

    if ask_button:
        if st.session_state.query:
            with st.spinner("Generating response..."):
                answer = handle_user_query(st.session_state.query)
                st.session_state.query = ""

                if not answer:
                    answer = "The question does not hold any relevance to the project's context."
                st.session_state.history.append(("User", st.session_state.query))
                st.session_state.history.append(("OnboardMate Assistant", answer))
                st.session_state.query = ""  # Clear the input box for the next question
                st.experimental_rerun()  # Refresh the page to display the new message

        else:
            st.error("Please enter a question.")

    if clear_button:
        st.session_state.query = ""
        st.session_state.history = [("OnboardMate Assistant", "Hello! How can I help you today?")]
        st.experimental_rerun()

def process_zip_folder(uploaded_folder):
    folder_path = "uploaded_folder.zip"
    with open(folder_path, "wb") as f:
        f.write(uploaded_folder.getbuffer())

    shutil.unpack_archive(folder_path, "temp_folder")

    for root, dirs, files in os.walk("temp_folder"):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, "rb") as f:
                file_content = f.read()
                file_name = os.path.basename(file_path)
                file_type = 'text/plain' if file_name.endswith('.txt') else 'text/x-python' if file_name.endswith('.py') else 'image/jpeg' if file_name.endswith('.jpg') else 'image/png' if file_name.endswith('.png') else 'video/mp4' if file_name.endswith('.mp4') else 'application/octet-stream'
                save_file_to_db(file_content, file_name, file_type)

    shutil.rmtree("temp_folder")
    os.remove(folder_path)

if __name__ == "__main__":
    main()
