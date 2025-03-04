from django.shortcuts import render
from django.http import HttpResponse
import numpy as np 
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from data_processing.models import DocumentChunks
from data_processing.views import get_embedding_function

def qa_workflow(request):
    chat_input_text = ""
    chat_output_text = ""

    if request.method == 'POST':
        chat_input_text = request.POST.get('chat_input', '')
        # In later steps, we will process chat_input_text and generate chat_output_text
        chat_output_text = query_rag(chat_input_text)

    context = {
        'chat_input_text': chat_input_text,
        'chat_output_text': chat_output_text,
    }
    return render(request, 'qa_app/qa_workflow.html', context)



# PROMPT_TEMPLATE = """
# Answer the question based only on the following context:

# {context}

# ---

# Answer the question based on the above context: {question}
# """

def query_rag(query_text: str):
    # Get the embedding function
    embedding_model = get_embedding_function()
    # Generate embedding for the query
    embedding_vector = embedding_model.embed_query(query_text)

    # 3. Fetch all DocumentChunks from MongoDB (or filter if needed)
    document_chunks_queryset = DocumentChunks.objects.all() # Or apply filters here if necessary (e.g., based on crawled_url)
    document_chunks = list(document_chunks_queryset) # Convert queryset to list

    if not document_chunks:
        return [] # Return empty list if no chunks found

    # 4. Calculate cosine similarity between query embedding and each chunk embedding
    similarities = []
    documents_for_search = [] # To store Langchain Documents for result formatting

    for chunk_obj in document_chunks:
        chunk_embedding = chunk_obj.embedding # Assuming embeddings are stored as lists in JSONField

        if chunk_embedding: # Ensure embedding exists (handle cases where embedding might be missing)
            # Calculate cosine similarity
            similarity_score = np.dot(np.array(query_embedding_vector), np.array(chunk_embedding)) / (np.linalg.norm(np.array(query_embedding_vector)) * np.linalg.norm(np.array(chunk_embedding)))
            similarities.append((similarity_score, chunk_obj)) # Store similarity and DocumentChunks object
        else:
            similarities.append((0.0, chunk_obj)) # Assign 0 similarity if embedding is missing

        documents_for_search.append(
            Document(page_content=chunk_obj.content, metadata={"chunk_id": chunk_obj.chunk_id, "crawled_url_id": chunk_obj.crawled_url_id})
        )


    # 5. Sort chunks by similarity score in descending order
    similarities.sort(key=lambda x: x[0], reverse=True)

    # 6. Get top k most similar chunks (e.g., top 3)
    top_k = min(3, len(similarities)) # Adjust k as needed
    top_chunks_with_scores = similarities[:top_k] # Get top chunks with their scores
    top_chunks = [chunk_obj for similarity_score, chunk_obj in top_chunks_with_scores] # Extract just the DocumentChunks objects
    top_documents = [documents_for_search[document_chunks.index(chunk)] for chunk in top_chunks] # Get corresponding Langchain Documents

    # 7. (Optional) You might want to return the similarity scores as well
    # For now, just return the top Document objects
    return top_documents # Or return top_chunks_with_scores if you need scores

    # db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # # Search the DB.
    # results = db.similarity_search_with_score(query_text, k=5)

    # context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    # prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    # prompt = prompt_template.format(context=context_text, question=query_text)
    # # print(prompt)

    # model = Ollama(model="mistral")
    # response_text = model.invoke(prompt)

    # sources = [doc.metadata.get("id", None) for doc, _score in results]
    # formatted_response = f"Response: {response_text}\nSources: {sources}"
    # print(formatted_response)
    # return response_text