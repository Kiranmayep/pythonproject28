from transformers import BartTokenizer, BartForConditionalGeneration
from PIL import Image
import replicate
import sqlite3
import os
import io
import base64
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

# Initialize Replicate client with your API token
client = replicate.Client(api_token="r8_VypzQxhm3FZcyWjpsXjW9SO4jttpuBa4GY7co")

DB_PATH = os.path.join("database", "chatbot.db")

def create_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS Files (
            id INTEGER PRIMARY KEY,
            file_name TEXT,
            file_type TEXT,
            upload_date TEXT,
            file_content BLOB
        )
    ''')
    conn.commit()
    conn.close()

def save_file_to_db(file, file_name=None, file_type=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if isinstance(file, bytes):
        file_content = file
    else:
        file_content = file.read()
        file_name = file.name
        file_type = file.type
    c.execute('''
        INSERT INTO Files (file_name, file_type, upload_date, file_content)
        VALUES (?, ?, ?, ?)
    ''', (file_name, file_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file_content))
    conn.commit()
    conn.close()

def get_all_files():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, file_name, file_type, file_content FROM Files')
    files = c.fetchall()
    conn.close()
    return files

def summarize_text(text):
    tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
    model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
    inputs = tokenizer(text, max_length=1024, return_tensors="pt", truncation=True)
    summary_ids = model.generate(inputs.input_ids, max_length=300, min_length=150, num_beams=4, early_stopping=True)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary

def summarize_code(code):
    return summarize_text(code)

# Function to encode file content to base64
def encode_file_to_base64(file_content, file_type):
    data = base64.b64encode(file_content).decode('utf-8')
    return f"data:{file_type};base64,{data}"

# Function to run image model and get output
def run_image_model(image_data, prompt):
    input_data = {
        "image": image_data,
        "prompt": prompt
    }
    return client.run(
        "lucataco/qwen-vl-chat:50881b153b4d5f72b3db697e2bbad23bb1277ab741c5b52d80cd6ee17ea660e9",
        input=input_data
    )

def summarize_image(image_bytes, file_type):
    encoded_image = encode_file_to_base64(image_bytes, file_type)
    summary = run_image_model(encoded_image, "Generate a summary for this image")
    return summary

def process_file_content(file_type, file_content):
    if file_type in ['text/plain', 'text/x-python']:
        content = file_content.decode('utf-8')
        summary = summarize_text(content) if file_type == 'text/plain' else summarize_code(content)
    elif file_type in ['image/jpeg', 'image/png']:
        summary = summarize_image(file_content, file_type)
    else:
        summary = "Unsupported file type for summarization."
    return summary

def handle_user_query(query):
    files = get_all_files()
    file_summaries = []

    for file_id, file_name, file_type, file_content in files:
        summary = process_file_content(file_type, file_content)
        file_summaries.append((file_id, file_name, summary))

    vectorizer = TfidfVectorizer().fit_transform([query] + [summary for _, _, summary in file_summaries])
    vectors = vectorizer.toarray()
    cosine_similarities = cosine_similarity([vectors[0]], vectors[1:]).flatten()
    most_similar_file_index = cosine_similarities.argmax()

    most_similar_file_id, most_similar_file_name, most_similar_summary = file_summaries[most_similar_file_index]

    return f"The question is related to '{most_similar_file_name}' file. Here is a summary: {most_similar_summary}"
