import os
import pickle
from utility.security import decrypt_file_aes
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pdfminer.high_level import extract_text
from io import BytesIO
from service.utility_service import Utility

class UploadService:
    def __init__(self, cache):
        self.cache = cache

    def process_upload(self, userId, filename, file_content, key):
        # Save the file locally for processing
        local_filename = self.save_local_copy(userId, file_content, filename)
        
        # Load, decrypt, and process text
        loaded_text = self.load_docs(userId, local_filename, key)
        splits = self.split_texts(loaded_text, chunk_size=1000, overlap=0)
        cache_key_splits = f'splits_{userId}'
        self.cache.set(cache_key_splits, splits, timeout=3000)

        # Pickle the splits locally
        self.save_local_pickle(userId, splits)
        
        return 'File uploaded & Text Extracted'

    def save_local_copy(self, userId, file_content, filename):
        user_dir = f'./uploads/{userId}'
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        local_path = os.path.join(user_dir, filename)
        file_content.save(local_path)
        return local_path

    def save_local_pickle(self, userId, data):
        pickle_path = f'./uploads/{userId}/splits_{userId}.pkl'
        with open(pickle_path, 'wb') as pickle_file:
            pickle.dump(data, pickle_file)

    def load_docs(self, userId, filepath, key):
        # Decrypt the file and load the content
        decrypted_bytes = decrypt_file_aes(filepath, key)
        if not decrypted_bytes:
            return ""
        
        pdf_stream = BytesIO(decrypted_bytes)
        pdf_text = extract_text(pdf_stream)

        # Reinitialize the stream for OCR processing
        pdf_stream.seek(0)
        utility_service = Utility(userId, self.cache)
        image_text = utility_service.local_ocr_from_pdf(pdf_stream)

        full_text = pdf_text + image_text

        return full_text
    
    def split_texts(self, text, chunk_size, overlap):
        if not text or text.strip() == '':
            return []
        try:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
            splits = text_splitter.split_text(text)
            if not splits:
                return []
            return splits
        except Exception as e:
            print(f"Error during text splitting: {str(e)}")
            return []
