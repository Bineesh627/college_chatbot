from django.shortcuts import render
from django.http import HttpResponse
import numpy as np 
from langchain.prompts import ChatPromptTemplate # Import ChatPromptTemplate
from langchain_community.llms import Ollama # Import Ollama
from langchain_ollama import OllamaEmbeddings
from data_processing.models import DocumentChunks
from langchain_community.docstore.document import Document
from data_processing.views import get_embedding_function
from botocore.exceptions import ClientError
import boto3
import json

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

def invoke_llama3(prompt):
    bedrock_runtime_client = boto3.client(service_name='bedrock-runtime')
    try:
        body = {
            "prompt": prompt,
            "temperature": 0.5,
            "top_p": 0.9,
            "max_gen_len": 100,
        }

        ## Change Llama 3.1 model id from bedrock
        model_id = 'us.meta.llama3-3-70b-instruct-v1:0'
        response = bedrock_runtime_client.invoke_model(
            modelId=model_id, body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())
        completion = response_body["generation"]

        return completion

    except ClientError:
        print("Couldn't invoke Llama 3")
        raise

def qa_workflow(request):
    chat_input_text = ""
    chat_output_text = ""
    search_results_text = "" # Initialize

    if request.method == 'POST':
        chat_input_text = request.POST.get('chat_input', '')
        search_results_docs = query_rag(chat_input_text) # Call query_rag and get Document objects

        if search_results_docs:
            # Format retrieved documents into context string for prompt
            context_text = "\n\n---\n\n".join([doc.page_content for doc in search_results_docs])

            # Create prompt template
            prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)

            # Format the prompt with context and question
            prompt = prompt_template.format(context=context_text, question=chat_input_text)
            print("\n--- Formatted Prompt ---")
            print(prompt)

            # Initialize Ollama LLM
            # llm = Ollama(model="llama3.2", base_url="http://localhost:11434") # Ensure Ollama server is running

            # Invoke LLM with the prompt
            # response_text = llm.invoke(prompt)
            response_text = invoke_llama3(prompt)
            print("\n--- LLM Response ---")
            print(response_text)
            chat_output_text = response_text # Set LLM response as chat output

            # Format search results for display (optional - you can still show search results if you want)
            search_results_text = "Retrieved Document Chunks:\n"
            for i, doc in enumerate(search_results_docs):
                search_results_text += f"Result {i+1}:\nContent: {doc.page_content[:200]}...\nMetadata: {doc.metadata}\n---\n" # Show snippet of content

        else:
            search_results_text = "No relevant document chunks found for your query."
            chat_output_text = "I'm sorry, but I couldn't find relevant information to answer your question."


    context = {
        'chat_input_text': chat_input_text,
        'chat_output_text': chat_output_text,
        'search_results_text': search_results_text # Pass search results for display (optional)
    }
    return render(request, 'qa_app/qa_workflow.html', context)

def query_rag(query_text):
    # Get the embedding function
    embedding_model = get_embedding_function()
    print(query_text)
    # Generate embedding for the query
    query_embedding_vector = embedding_model.embed_query(query_text)

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
    top_k = min(5, len(similarities)) # Adjust k as needed
    top_chunks_with_scores = similarities[:top_k] # Get top chunks with their scores
    top_chunks = [chunk_obj for similarity_score, chunk_obj in top_chunks_with_scores] # Extract just the DocumentChunks objects
    top_documents = [documents_for_search[document_chunks.index(chunk)] for chunk in top_chunks] # Get corresponding Langchain Documents
    print(top_documents)

    # 7. (Optional) You might want to return the similarity scores as well
    # For now, just return the top Document objects
    return top_documents # Or return top_chunks_with_scores if you need scores