import os
from pytesseract import image_to_string
from pdf2image import convert_from_path
import tempfile

ALLOWED_EXTENSIONS = {'txt', 'pdf'}

class Utility:
    def __init__(self, userId, cache):
        self.userId = userId
        self.cache = cache
    
    def allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def clear_local_data(self):
        user_folder = f'./uploads/{self.userId}'
        for file in os.listdir(user_folder):
            os.remove(os.path.join(user_folder, file))

    def clear_cache_data(self):
        self.cache.delete(f'splits_{self.userId}')
        self.cache.delete(f'retriever_{self.userId}')

    def local_ocr_from_pdf(self, pdf_path):
        """
        Use pytesseract to extract text from a PDF file.
        """
        text = ""
        with tempfile.TemporaryDirectory() as path:
            images_from_path = convert_from_path(pdf_path, output_folder=path)
            for page in images_from_path:
                text += image_to_string(page) + "\n"
        return text
