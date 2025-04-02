# views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_http_methods
import json
import numpy as np
from prompt_management.models import SystemPrompt
from langchain.prompts import ChatPromptTemplate
from pdf_data.models import DocumentChunks
from langchain_community.docstore.document import Document
from model_api.views import generate_embeddings, invoke_llama3
from .models import ChatSession
from feedback.models import ChatFeedback
import logging

logger = logging.getLogger('custom_logger')

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

@ensure_csrf_cookie
@csrf_protect
def qa_workflow(request):

    if request.method == 'POST':
        chat_input_text = request.POST.get('chat_input_text', '')

        if not chat_input_text.strip():
            return JsonResponse({
                'response': "Please enter a question or message.",
                'search_results': ""
            })

        try:
            # Get relevant documents using RAG
            search_results_docs = query_rag(chat_input_text)

            if search_results_docs:
                # Prepare context from retrieved documents
                context_text = "\n\n---\n\n".join([doc.page_content for doc in search_results_docs])

                # Generate prompt using template
                PROMPT_TEMPLATE = prompt_temp(context_text, chat_input_text)
                prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)

                # Generate response using LLM
                prompt = prompt_template.format(context=context_text, question=chat_input_text)
                response_text = invoke_llama3(prompt)

                # Prepare search results summary
                search_results_text = "Retrieved Document Chunks:\n"
                for i, doc in enumerate(search_results_docs):
                    search_results_text += f"Result {i+1}:\nContent: {doc.page_content[:200]}...\nMetadata: {doc.metadata}\n---\n"
            else:
                response_text = "I'm sorry, but I couldn't find relevant information to answer your question."
                search_results_text = "No relevant document chunks found for your query."

            # Save to chat history
            session_id = request.session.session_key or request.session.create()
            current_session, created = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={'conversation_history': {'history': []}}
            )

            history = current_session.conversation_history.get('history', [])
            history.append({
                "user": chat_input_text,
                "bot": response_text
            })

            current_session.conversation_history = {'history': history}
            current_session.save()

            return JsonResponse({
                'response': response_text,
                'search_results': search_results_text
            })

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            return JsonResponse({
                'response': "I'm sorry, but there was an error processing your request.",
                'search_results': ""
            })

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@require_http_methods(["GET"])
def get_chat_history(request):
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key

    try:
        current_session = ChatSession.objects.get(session_id=session_id)
        history = current_session.conversation_history.get('history', [])
    except ChatSession.DoesNotExist:
        history = []

    return JsonResponse({'history': history})

@require_http_methods(["POST"])
@csrf_protect
def submit_feedback(request):
    try:
        data = json.loads(request.body)
        session_id = request.session.session_key # Get session_id from request.session
        query = data.get('query')
        chatbot_response = data.get('chatbot_response')
        feedback_type = data.get('feedback_type') # 'up' or 'down'

        # Validate feedback_type
        if feedback_type not in ['up', 'down']:
            return JsonResponse({'status': 'error', 'message': 'Invalid feedback type'}, status=400)

        # Get ChatSession instance (assuming session exists)
        try:
            chat_session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Chat session not found'}, status=400)

        # Create ChatFeedback instance
        feedback_instance = ChatFeedback(
            session=chat_session,
            query=query,
            chatbot_response=chatbot_response,
            thumbs_up=(feedback_type == 'up'), # Convert 'up'/'down' to Boolean for thumbs_up field
        )
        feedback_instance.save()

        logger.info(f"Feedback received: {feedback_type} for session {session_id}")
        return JsonResponse({'status': 'success'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except ChatSession.DoesNotExist: # Catch ChatSession.DoesNotExist again just in case
        return JsonResponse({'status': 'error', 'message': 'Chat session not found'}, status=400)
    except Exception as e:
        logger.error(f"Error processing feedback: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Error saving feedback'}, status=400)

@require_http_methods(["POST"])
def process_voice(request):
    try:
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return JsonResponse({'error': 'No audio file received'}, status=400)

        # Here you would implement voice processing logic
        # For now, we'll return a simple response
        return JsonResponse({
            'response': "I've received your voice message, but voice processing is not implemented yet."
        })
    except Exception as e:
        logger.error(f"Error processing voice message: {e}", exc_info=True)
        return JsonResponse({'error': 'Error processing voice message'}, status=500)

def query_rag(query_text):
    # Generate embedding for the query
    query_embedding_vector = generate_embeddings(query_text)

    # Fetch all DocumentChunks
    document_chunks_queryset = DocumentChunks.objects.all()
    document_chunks = list(document_chunks_queryset)

    if not document_chunks:
        return []

    # Calculate similarities
    similarities = []
    documents_for_search = []

    for chunk_obj in document_chunks:
        chunk_embedding = chunk_obj.embedding

        if chunk_embedding:
            similarity_score = np.dot(np.array(query_embedding_vector), np.array(chunk_embedding)) / (
                np.linalg.norm(np.array(query_embedding_vector)) * np.linalg.norm(np.array(chunk_embedding))
            )
            similarities.append((similarity_score, chunk_obj))
        else:
            similarities.append((0.0, chunk_obj))

        documents_for_search.append(
            Document(
                page_content=chunk_obj.content,
                metadata={"chunk_id": chunk_obj.chunk_id, "crawled_url_id": chunk_obj.crawled_url_id}
            )
        )

    # Sort and get top results
    similarities.sort(key=lambda x: x[0], reverse=True)
    top_k = min(5, len(similarities))
    top_chunks = [chunk_obj for similarity_score, chunk_obj in similarities[:top_k]]
    top_documents = [documents_for_search[document_chunks.index(chunk)] for chunk in top_chunks]

    return top_documents