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
from feedback.models import ChatbotFeedback
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
                "bot": response_text,
                "feedback": None
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
        session_id = request.session.session_key
        query = data.get('query')
        chatbot_response = data.get('chatbot_response')
        feedback_type = data.get('feedback_type') # Expecting 'up' or 'down'

        # --- Input Validation ---
        if not session_id:
             # This case might happen if session expired or cookies are disabled client-side
             logger.warning("Feedback submitted without a valid session ID.")
             return JsonResponse({'status': 'error', 'message': 'Active session not found. Please refresh.'}, status=400)

        if not all([query, chatbot_response, feedback_type]):
             logger.warning(f"Feedback submission missing data for session {session_id}. Data: {data}")
             return JsonResponse({'status': 'error', 'message': 'Missing required feedback data (query, response, or type)'}, status=400)

        if feedback_type not in ['up', 'down']:
            logger.warning(f"Invalid feedback type received for session {session_id}. Type: {feedback_type}")
            return JsonResponse({'status': 'error', 'message': 'Invalid feedback type. Must be "up" or "down".'}, status=400)

        # Convert feedback_type ('up'/'down') to boolean (True/False)
        feedback_boolean = (feedback_type == 'up')

        # --- Get ChatSession ---
        try:
            chat_session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            logger.warning(f"Feedback submitted for non-existent session ID: {session_id}")
            # You might decide to still save to ChatbotFeedback if session is not critical,
            # but linking requires it. Returning error is safer.
            return JsonResponse({'status': 'error', 'message': 'Chat session not found'}, status=400)

        # --- MODIFICATION: Update conversation_history ---
        history = chat_session.conversation_history.get('history', [])
        history_updated = False
        # Iterate through history *in reverse* to find the most recent matching message pair
        for i in range(len(history) - 1, -1, -1):
            item = history[i]
            # Check if the dictionary item has 'user' and 'bot' keys, and they match the feedback data.
            # We target the specific interaction the user provided feedback for.
            if (item.get('user') == query and item.get('bot') == chatbot_response):
                  # Found the matching interaction in history. Update its feedback status.
                  # Use .get('feedback', -1) != feedback_boolean to prevent redundant updates if needed
                  # or allow overwriting feedback by simply assigning:
                  item['feedback'] = feedback_boolean
                  history_updated = True
                  logger.debug(f"Found match at index {i} in history for session {session_id}. Updating feedback to {feedback_boolean}.")
                  break # Stop after finding and updating the most recent match

        if history_updated:
            # Assign the modified list back to the conversation_history field
            chat_session.conversation_history['history'] = history
            # Save the ChatSession object to persist the change in the JSON field.
            # update_fields ensures only these fields are part of the SQL UPDATE query.
            chat_session.save(update_fields=['conversation_history', 'last_activity'])
            logger.info(f"Feedback ({feedback_type}) stored successfully in conversation_history for session {session_id}")
        else:
            # Log a warning if no matching message pair was found in the history.
            # This could indicate a frontend issue sending incorrect query/response,
            # or maybe the history structure differs from expectations.
            logger.warning(
                f"Could not find matching message pair in conversation_history for session {session_id} "
                f"to update feedback. Query: '{query[:50]}...', Response: '{chatbot_response[:50]}...'"
            )

        feedback_instance = ChatbotFeedback(
            session=chat_session,        # Link to the ChatSession
            query=query,                 # User's query
            response=chatbot_response,   # Bot's response that was rated
            thumbs_up=feedback_boolean,  # Store the boolean feedback
            topic="General",             # Set a default topic, or modify to get topic context if available
            # feedback=data.get('comment') # If you add a comment field in the future
        )
        feedback_instance.save()
        logger.info(f"Feedback also saved to ChatbotFeedback table for session {session_id}. Feedback ID: {feedback_instance.feedback_id}")
        # --- End existing logic ---

        return JsonResponse({'status': 'success', 'message': 'Feedback received successfully.'})

    except json.JSONDecodeError:
        logger.error("Invalid JSON received in feedback request body.", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data provided.'}, status=400)
    # Catching DoesNotExist again just in case logic changes, though it's checked above.
    except ChatSession.DoesNotExist:
         logger.error(f"ChatSession.DoesNotExist caught unexpectedly for session {session_id} during feedback processing.")
         return JsonResponse({'status': 'error', 'message': 'Chat session not found unexpectedly.'}, status=400)
    except Exception as e:
        # Catch any other unexpected errors during processing
        logger.error(f"Unexpected error processing feedback for session {session_id}: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'An internal error occurred while saving feedback.'}, status=500)

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