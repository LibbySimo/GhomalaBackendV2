from flask import Blueprint, request, jsonify
import os
from werkzeug.utils import secure_filename
import uuid
from app.services.rag import get_rag_service
from flask import current_app
from pathlib import Path
from openai import OpenAI
api = Blueprint('api', __name__, url_prefix='/api')

allowed_extensions = ['.pdf']

rag_service = get_rag_service()

client = OpenAI()

def chat_with_openai(question, results):
    try:
        # Make a request using the new client interface
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4o", "gpt-4", etc.
            messages=[
                {"role": "system", "content": "you are a dictionary assistant that answers questions based on the provided search results. the language is ghomala, do not answer none "},
                {"role": "user", "content": f"Question: {question}\n\nSearch Results: {results}"}
            ],
            max_tokens=150,
            temperature=0.7
        )
        # Extract and return the assistant's reply
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def allowed_file(filename):
    # return '.' in filename and \
    #        filename.rsplit('.', 1)[1].lower() in allowed_extensions
    return True

@api.route("/upload", methods=['POST'])
def upload():
    # Check if a file is part of the request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    # Check if a file was actually selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate and process the file
    if file and allowed_file(file.filename):
        try:
            # Secure the filename to prevent path traversal attacks
            file_id = str(uuid.uuid4())
            filename = secure_filename(file.filename)

            filename = f"{file_id}_{filename}"

            # Define the upload folder (adjust path as needed)
            upload_folder = 'uploads'
            os.makedirs(upload_folder, exist_ok=True)

            # Save the file
            file_path = os.path.join(Path(current_app.root_path).parent,upload_folder, filename)

            file.save(file_path)



            try:
                result = rag_service.process_and_store_document(file_path, file_id)
                if result.get('status') == 'error':
                    return jsonify({'error': f'Error processing file: {result.get("message")}'}), 500
            except Exception as e:
                print(e)
                return jsonify({'error': f'Error processing file: {str(e)}'}), 500

            return jsonify({
                'document_id': filename,
                'status': 'success',
                'extracted_text': 'File uploaded successfully',
                'file_path': file_path
            }), 201

        except Exception as e:
            return jsonify({'error': f'Error saving file: {str(e)}'}), 500

    return jsonify({'error': 'Invalid file type. Only PDF files are allowed'}), 400

@api.route("/query", methods=['POST'])
def query():
    """ Expects
    {
        'file_path': 'path/to/file',
        'question': 'users questions'
    }
    Returns
    {
        'status': 'success' or 'error',
        'question': 'users question',
        'answer': 'generated answer based on relevant chunks',
        'relevant_sections': 'text of the most relevant document chunk(s)'
    }
    """
    data = request.get_json()

    if not data or 'file_path' not in data or 'question' not in data:
        return jsonify({
            'status': 'error',
            'question': data.get('question', ''),
            'answer': '',
            'relevant_sections': '',
            'error': 'Missing required parameters'
        }), 400

    file_path = data['file_path']
    question = data['question']

    # Extract document_id from file_path (assumes format: uuid_filename)
    try:

        document_id = file_path.split("/")[-1].split('_')[0]
    except IndexError:
        return jsonify({
            'status': 'error',
            'question': question,
            'answer': '',
            'relevant_sections': '',
            'error': 'Invalid file_path format. Expected format: uuid_filename'
        }), 400

    try:
        # Query the RAG service
        results = rag_service.query(question, document_id, top_k=3)


        if isinstance(results, dict) and results.get('status') == 'error':
            return jsonify({
                'status': 'error',
                'question': question,
                'answer': '',
                'relevant_sections': '',
                'error': f'Query failed: {results.get("message")}'
            }), 500

        # Generate answer and relevant section
        if not results:
            return jsonify({
                'status': 'success',
                'question': question,
                'answer': 'No relevant information found.',
                'relevant_sections': ''
            }), 200

        # Use the top result's text as the answer and relevant section
        # Alternatively, concatenate multiple results if needed
        top_result = results[0]
        answer = top_result
        relevant_section = top_result['text']



        # Optionally combine multiple chunks for relevant_section
        if len(results) > 1:
            relevant_section = "\n\n".join(result['text'] for result in results)

        return jsonify({
            'status': 'success',
            'question': question,
            'answer': answer,
            'relevant_sections': relevant_section
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'question': question,
            'answer': '',
            'relevant_sections': '',
            'error': f'Error processing query: {str(e)}'
        }), 500
