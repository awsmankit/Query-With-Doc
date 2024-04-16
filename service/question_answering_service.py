import os
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS

class QuestionAnsweringService:
    def __init__(self, chat_openai, embeddings):
        self.chat_openai = chat_openai
        self.embeddings = embeddings

    def answer_question(self, userId, user_question):
        # Define the directory path where the vectorstore files will be stored
        vectorstores_directory = os.path.abspath(os.path.join(os.getcwd(), '..', 'vectorstores'))
        if not os.path.exists(vectorstores_directory):
            os.makedirs(vectorstores_directory)

        # Define the local file path for the vectorstore
        local_file_path = os.path.join(vectorstores_directory, f'vectorstore_{userId}.pkl')

        try:
            # Ensure that the vectorstore exists or handle its absence
            if not os.path.exists(local_file_path):
                return "No data available to answer questions. Please upload relevant documents first.", None

            # Load the vectorstore
            vectorStore = FAISS.load_local(local_file_path, self.embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            return None, f'Error loading vectorstore: {str(e)}'

        try:
            retriever = vectorStore.as_retriever(k=5)
            qa = RetrievalQA.from_chain_type(llm=self.chat_openai, retriever=retriever, chain_type="basic_retrieval", verbose=False)
            answer = qa.run(user_question)
            if not answer or not answer.strip():
                return "Sorry, I couldn't find an answer to your question.", None
            return answer.strip(), None
        except Exception as e:
            return None, f'Error during question answering: {str(e)}'
