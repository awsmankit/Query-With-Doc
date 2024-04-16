from langchain.chains import RetrievalQA

class QuestionRetrievalService:
    def __init__(self, cache, chat_openai):
        self.cache = cache
        self.chat_openai = chat_openai

    def get_questions(self, userId, document_text, num_questions):
        retriever = self.cache.get(f'retriever_{userId}')
        if not retriever:
            return None, "Retriever not found for the user"

        try:
            # Assuming get_relevant_questions is a function you've defined elsewhere
            questions = self.get_relevant_questions(document_text, retriever, num_questions, self.chat_openai)
            return questions, None
        except Exception as e:
            return None, str(e)


    def get_relevant_questions(document_text, retriever, num_questions, chat_openai):
        """Fetch relevant questions from the document using RetrievalQA."""
        query = f"Provide me {num_questions} relevant questions from the document: {document_text}"
        # os.getenvure and create the RetrievalQA chain
        chain = RetrievalQA.from_chain_type(llm=chat_openai, retriever=retriever, chain_type="stuff", verbose=False)
        # Run the query and get the answer
        answer = chain.run(query=query, temperature=0.5, max_tokens=250)
        relevant_questions = [question.replace('<|im_end|>', '').strip() for question in answer.split('\n') if question.strip()]
        relevant_questions = [q for q in relevant_questions if q.strip()]
        return relevant_questions[:num_questions] 