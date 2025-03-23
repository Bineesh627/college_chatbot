from django.shortcuts import render
from prompt_management.models import SystemPrompt
from django.http import JsonResponse
import numpy as np 
from langchain.prompts import ChatPromptTemplate # Import ChatPromptTemplate
from pdf_data.models import DocumentChunks
from langchain_community.docstore.document import Document
from model_api.views import generate_embeddings, invoke_llama3
from .models import ChatSession #if using a relational database.
import logging

logger = logging.getLogger('custom_logger')

# Create your views here.

def prompt_temp(context, question):
    # Use __in lookup for boolean filtering
    prompt_obj = SystemPrompt.objects.filter(is_active__in=[True]).first()
    if not prompt_obj:
        prompt_obj = SystemPrompt.objects.first()  # Fallback if no active prompt is found
    
    PROMPT_TEMPLATE = (
        f"{prompt_obj.prompt_text}\n\n"
        "Context:\n"
        f"{context}\n\n"
        "Question:\n"
        f"{question}\n\n"
        "Answer:\n"
    )
    return PROMPT_TEMPLATE

def qa_workflow(request):
    chat_input_text = ""
    chat_output_text = ""
    search_results_text = ""
    current_session = None  # Initialize to avoid UnboundLocalError

    if request.method == 'POST':
        chat_input_text = request.POST.get('chat_input_text', '')

        if not chat_input_text.strip():
            chat_output_text = "Please enter a question or message."
        else:
            try:
                search_results_docs = query_rag(chat_input_text)

                if search_results_docs:
                    context_text = "\n\n---\n\n".join([doc.page_content for doc in search_results_docs])
                    PROMPT_TEMPLATE = prompt_temp(context_text, chat_input_text)
                    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
                    prompt = prompt_template.format(context=context_text, question=chat_input_text)
                    response_text = invoke_llama3(prompt)

                    chat_output_text = response_text
                    search_results_text = "Retrieved Document Chunks:\n"
                    for i, doc in enumerate(search_results_docs):
                        search_results_text += f"Result {i+1}:\nContent: {doc.page_content[:200]}...\nMetadata: {doc.metadata}\n---\n"
                else:
                    search_results_text = "No relevant document chunks found for your query."
                    chat_output_text = "I'm sorry, but I couldn't find relevant information to answer your question."

                session_id = request.session.session_key
                if not session_id:
                    request.session.create()
                    session_id = request.session.session_key

                try:
                    current_session = ChatSession.objects.get(session_id=session_id)
                    history = current_session.conversation_history.get('history', []) if current_session.conversation_history else []
                except ChatSession.DoesNotExist:
                    history = []
                    current_session = ChatSession(session_id=session_id, conversation_history={'history': history})
                    current_session.save()

                history.append({"user": chat_input_text, "bot": chat_output_text})

                current_session.conversation_history = {'history': history}
                current_session.save()

                request.session['history'] = history
                request.session.modified = True

            except Exception as e:
                logger.error(f"Error processing request: {e}", exc_info=True)
                chat_output_text = "I'm sorry, but there was an error processing your request."

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'response': chat_output_text,
                'search_results': search_results_text,
            })

    context = {
        'chat_input_text': chat_input_text,
        'chat_output_text': chat_output_text,
        'search_results_text': search_results_text,
    }

    return render(request, 'chatbot/chatbot.html', context)


def get_chat_history(request):
    session_id = request.session.session_key
    if not session_id:
        request.session.create()  # Ensure the session exists
        session_id = request.session.session_key

    try:
        current_session = ChatSession.objects.get(session_id=session_id)
        history = current_session.conversation_history.get('history', []) if current_session.conversation_history else []
    except ChatSession.DoesNotExist:
        history = []

    return JsonResponse({'history': history})


def query_rag(query_text):
    # Generate embedding for the query
    query_embedding_vector = generate_embeddings(query_text)

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

        # Store Langchain Document for search results formatting
        documents_for_search.append(
            Document(page_content=chunk_obj.content, metadata={"chunk_id": chunk_obj.chunk_id, "crawled_url_id": chunk_obj.crawled_url_id})
        )


    # 5. Sort chunks by similarity score in descending order
    similarities.sort(key=lambda x: x[0], reverse=True)

    # 6. Get top k most similar chunks (e.g., top 3)
    top_k = min(5, len(similarities)) # Adjust k as needed
    top_chunks_with_scores = similarities[:top_k] # Get top chunks with their scores
    top_chunks = [chunk_obj for similarity_score, chunk_obj in top_chunks_with_scores] # Extract just the DocumentChunks objects
    top_documents = [documents_for_search[document_chunks.index(chunk)] for chunk in top_chunks] # Get corresponding Langchain Documents
    print(top_documents)

    # 7. (Optional) You might want to return the similarity scores as well
    # For now, just return the top Document objects
    return top_documents # Or return top_chunks_with_scores if you need scores