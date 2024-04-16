import os
import pickle
from langchain_community.vectorstores import FAISS

class PDFProcessingService:
    def __init__(self, embeddings):
        self.embeddings = embeddings
    
    def process_pdf(self, userId, split_content):
        # It is assumed that split_content is already a byte-like object that can be deserialized
        try:
            loaded_data = pickle.loads(split_content)
        except Exception as e:
            return f"Deserialization failed: {str(e)}"

        if not loaded_data:
            return "No data to process"

        # Create a vectorstore from the loaded data
        try:
            vectorstore = FAISS.from_texts(loaded_data, self.embeddings)
        except Exception as e:
            return f"Error during vectorstore creation: {str(e)}"

        # Ensure the vectorstore directory exists
        folder_path = os.path.join(os.getcwd(), 'vectorstores')
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Save the vectorstore locally
        local_file_path = os.path.join(folder_path, f'vectorstore_{userId}.pkl')
        try:
            vectorstore.save_local(local_file_path)
        except Exception as e:
            return f"Error saving vectorstore: {str(e)}"

        return "File has been processed successfully"
