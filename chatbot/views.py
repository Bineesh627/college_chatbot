# views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_http_methods
import json
from django.utils import timezone
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

from typing import Dict, List
import re

COLLEGE_TOPIC_MAP = {
    'admissions': {
        'keywords': ['admission', 'apply', 'deadline', 'requirement', 'eligibility', 'application fee'],
        'subtopics': ['undergraduate', 'postgraduate', 'international', 'transfer', 'documents']
    },
    'courses': {
        'keywords': ['course', 'subject', 'curriculum', 'syllabus', 'elective', 'credit', 'module'],
        'subtopics': ['computer_science', 'engineering', 'business', 'humanities', 'sciences']
    },
    'facilities': {
        'keywords': ['library', 'hostel', 'lab', 'sports', 'cafeteria', 'transport', 'wifi'],
        'subtopics': []
    },
    'exams': {
        'keywords': ['exam', 'test', 'midterm', 'final', 'schedule', 'pattern', 'marks'],
        'subtopics': ['entrance', 'semester', 'practical', 'theory']
    },
    'fees': {
        'keywords': ['fee', 'payment', 'scholarship', 'loan', 'installment', 'refund'],
        'subtopics': ['tuition', 'hostel', 'mess', 'library']
    },
    'placements': {
        'keywords': ['placement', 'internship', 'recruitment', 'package', 'company', 'career'],
        'subtopics': []
    }
}

def analyze_college_topic(user_query: str) -> Dict:
    """
    Analyze college-related queries and return structured topic information
    Returns: {
        'main_topic': str,
        'subtopic': str,
        'category': str,
        'confidence': float,
        'course_code': str or None
    }
    """
    # Detect course codes first (e.g., "CS101", "MATH202")
    course_code = detect_course_code(user_query)
    
    # Structured prompt for LLaMA 3
    prompt = f"""<|begin_of_text|>
    <|start_header_id|>system<|end_header_id|>
    You are a college information specialist. Analyze this query and identify:
    1. Main topic category (Only: {', '.join(COLLEGE_TOPIC_MAP.keys())})
    2. Specific subtopic if present
    3. Academic department if mentioned
    
    Return JSON format: {{"topic": "", "subtopic": "", "department": ""}}
    <|eot_id|>
    <|start_header_id|>user<|end_header_id|>
    Query: {user_query}<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """
    
    try:
        # Get LLM response
        llm_response = invoke_llama3(prompt)
        
        # Clean and parse response
        json_str = extract_json(llm_response)
        result = json.loads(json_str)
        
        # Validate and normalize
        validated = validate_topic(result, user_query)
        validated['course_code'] = course_code
        
        return {
            'main_topic': validated.get('topic', 'general'),
            'subtopic': validated.get('subtopic', ''),
            'category': validated.get('department', ''),
            'confidence': 0.9,  # Can implement confidence scoring
            'course_code': course_code
        }
        
    except Exception as e:
        return fallback_topic_analysis(user_query, course_code)


def detect_course_code(text: str) -> str:
    """Find course codes like CS101 or MATH202"""
    matches = re.findall(r'\b([A-Z]{2,4}\s?\d{3})\b', text.upper())
    return matches[0] if matches else None

def validate_topic(result: Dict, query: str) -> Dict:
    """Validate and sanitize LLM output"""
    # Ensure main topic is valid
    if result['topic'].lower() not in COLLEGE_TOPIC_MAP:
        result['topic'] = 'general'
    
    # Check subtopic validity
    valid_subtopics = COLLEGE_TOPIC_MAP.get(result['topic'], {}).get('subtopics', [])
    if result['subtopic'] and result['subtopic'].lower() not in valid_subtopics:
        result['subtopic'] = ''
        
    # Department normalization
    result['department'] = normalize_department(result.get('department', ''))
    
    return result

def normalize_department(dept: str) -> str:
    """Standardize department names"""
    dept = dept.lower().replace(' ', '_')
    return {
        'cs': 'computer_science',
        'cse': 'computer_science',
        'mech': 'mechanical_engineering',
        'eee': 'electrical_engineering',
        'mba': 'business_administration'
    }.get(dept, dept)

def fallback_topic_analysis(query: str, course_code: str) -> Dict:
    """Fallback analysis using keyword matching"""
    query_lower = query.lower()
    
    for topic, data in COLLEGE_TOPIC_MAP.items():
        if any(kw in query_lower for kw in data['keywords']):
            return {
                'main_topic': topic,
                'subtopic': '',
                'category': 'general',
                'confidence': 0.7,
                'course_code': course_code
            }
    
    return {
        'main_topic': 'general',
        'subtopic': '',
        'category': '',
        'confidence': 0.5,
        'course_code': course_code
    }

def prompt_temp(context, question):
    # Use __in lookup for boolean filtering
    prompt_obj = SystemPrompt.objects.filter(is_active__in=[True]).first()
    if not prompt_obj:
        prompt_obj = SystemPrompt.objects.first()  # Fallback if no active prompt is found

    PROMPT_TEMPLATE = (
        f"{prompt_obj.prompt_text}\n\n"
        "Instructions:\n"
        "1. Provide concise, accurate answers\n"
        "2. Never repeat the same information\n"
        "3. End after providing complete information\n"
        "4. If listing items, use bullet points\n"
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
        feedback_type = data.get('feedback_type', 'neutral')  # Default to neutral

        # Input validation
        if not session_id:
            return JsonResponse({'status': 'error', 'message': 'Active session not found.'}, status=400)
        if not all([query, chatbot_response]):
            return JsonResponse({'status': 'error', 'message': 'Missing required data'}, status=400)
        if feedback_type not in ['up', 'down', 'neutral']:
            return JsonResponse({'status': 'error', 'message': 'Invalid feedback type'}, status=400)

        # Convert feedback type to boolean or None
        feedback_boolean = {
            'up': True,
            'down': False,
            'neutral': None
        }[feedback_type]

        topic_data = analyze_college_topic(query)
        main_topic = topic_data.get('main_topic', 'general')

        try:
            chat_session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            chat_session = ChatSession.objects.create(
                session_id=session_id,
                conversation_history={'history': []}
            )

        # Initialize conversation_history if null
        if not chat_session.conversation_history:
            chat_session.conversation_history = {'history': []}

        history = chat_session.conversation_history.get('history', [])
        history_updated = False

        # Search for matching interaction
        for i in reversed(range(len(history))):
            item = history[i]
            if item.get('user') == query and item.get('bot') == chatbot_response:
                item['feedback'] = feedback_boolean
                history_updated = True
                break

        if history_updated:
            chat_session.conversation_history['history'] = history
            chat_session.save(update_fields=['conversation_history', 'last_activity'])
        else:
            new_entry = {
                'user': query,
                'bot': chatbot_response,
                'feedback': feedback_boolean,
                'timestamp': str(timezone.now()),
                'topic': main_topic,  # Store topic in conversation history
            }
            chat_session.conversation_history['history'].append(new_entry)
            chat_session.save(update_fields=['conversation_history', 'last_activity'])

        # Always save feedback regardless of history state
        feedback_instance, created = ChatbotFeedback.objects.update_or_create(
            session=chat_session,
            query=query,
            response=chatbot_response,
            defaults={
                'thumbs_up': feedback_boolean,
                'topic': main_topic,  # Store topic in feedback
            }
        )

        return JsonResponse({'status': 'success', 'message': 'Feedback received successfully.'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in submit_feedback: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)

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