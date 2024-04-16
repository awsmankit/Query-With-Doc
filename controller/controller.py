import os
from flask import Blueprint, request, jsonify
from utility.security import  key
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

from service.utility_service import Utility
from service.upload_service import UploadService
from service.pdf_processing_service import PDFProcessingAzureService
from service.question_answering_service import QuestionAnsweringServiceAzure
from service.question_retrieval_service import QuestionRetrievalService

from langchain_openai import AzureOpenAIEmbeddings

load_dotenv()

_cache = None
def init_cache(cache):
    global _cache
    _cache = cache

routes_blueprint = Blueprint('routes', __name__)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

embeddings = AzureOpenAIEmbeddings(azure_endpoint="https://finetune-bot.openai.azure.com/",azure_deployment="embeddings_model",openai_api_version="2023-05-15")
chat_openai = AzureChatOpenAI(azure_endpoint="https://finetune-bot.openai.azure.com/", azure_deployment="logsifters_model")


@routes_blueprint.route('/upload', methods=['POST'])
def upload_file():
    userId = request.headers.get('userId')
    if not userId:
        return jsonify({'error': 'User ID not provided in the header'}), 400
    
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No file provided or file name is empty'}), 400
    
    # Delegate to a service method
    try:
        message = handle_file_upload(userId, file)
        return jsonify({'message': message}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to process the upload'}), 500
    
def handle_file_upload(userId, file):
    utility_service = Utility(userId, _cache)
    if not utility_service.allowed_file(file.filename):
        raise ValueError('File type not allowed')

    utility_service.clear_cache_data()

    upload_service = UploadService(_cache)
    return upload_service.process_upload(userId, file.filename, file, key)

@routes_blueprint.route('/process_pdf', methods=['POST'])
def process_pdf():
    userId = request.headers.get('userId')
    if not userId:
        return jsonify({'error': 'User ID not provided in the header'}), 400

    pdf_processing_service_azure = PDFProcessingAzureService(embeddings)
    result_message = pdf_processing_service_azure.process_pdf(userId)

    return jsonify({'message': result_message}), 200

@routes_blueprint.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request data missing'}), 400

    user_question = data.get('question', '').strip()
    if not user_question:
        return jsonify({'error': 'Invalid or empty question provided'}), 400

    userId = request.headers.get('userId')
    if not userId:
        return jsonify({'error': 'User ID not provided in the header'}), 400

    question_answering_service_azure = QuestionAnsweringServiceAzure(chat_openai, embeddings)
    answer, error = question_answering_service_azure.answer_question(userId, user_question)

    if error:
        return jsonify({'error': error}), 400
    return jsonify({"answer": answer}), 200


@routes_blueprint.route('/get-questions', methods=['POST'])
def get_questions():
    data = request.get_json()

    document_text = data.get('document_text', '')
    num_questions = data.get('num_questions', 5)

    userId = request.headers.get('userId')
    if not userId:
        return jsonify({'error': 'User ID not provided in the header'}), 400

    question_retrieval_service = QuestionRetrievalService(_cache)
    questions, error = question_retrieval_service.get_questions(userId, document_text, num_questions)

    if error:
        return jsonify({"status": "error", "message": error}), 500
    return jsonify({"status": "success", "questions": questions}), 200


@routes_blueprint.route('/flush', methods=['POST'])
def flush_user_data():
    userId = request.headers.get('userId')
    if not userId:
        return jsonify({'error': 'User ID not provided in the header'}), 400

    try:
        # Delete Azure blobs and Clear cache data
        utility = Utility(userId, _cache)
        utility.clear_cache_data(userId)

        return jsonify({'message': 'User data flushed successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
