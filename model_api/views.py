from django.shortcuts import render
from langchain_aws import BedrockEmbeddings
import boto3
import json
from botocore.exceptions import ClientError
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .models import ModelSettings

# Create your views here.

def get_embedding_function():
    embeddings = BedrockEmbeddings(
        credentials_profile_name="default", region_name="us-east-1"
    )
    # embeddings = OllamaEmbeddings(model="nomic-embed-text") # Use this for Ollama embeddings
    # embeddings = OllamaEmbeddings(model="llama3.2", base_url="http://localhost:11434") # Use this for local Ollama embeddings
    return embeddings

def generate_embeddings(text_to_embedding):
    """Generate embeddings for the given text."""
    embeddings = get_embedding_function()  # Get the embedding function
    embedding_vector = embeddings.embed_query(text_to_embedding)  # Generate the embedding vector
    return embedding_vector  # Return the generated embedding vector

def get_model_settings():
    """Fetch settings from the database."""
    try:
        return ModelSettings.objects.first()
    except ModelSettings.DoesNotExist:
        return None

def invoke_llama3(prompt):
    """Invoke LLaMA using settings from the database."""
    
    settings = get_model_settings()
    if not settings:
        raise ValueError("No AWS settings found in the database")

    # Initialize Bedrock client
    bedrock_runtime_client = boto3.client(
        service_name='bedrock-runtime',
        aws_access_key_id=settings.api_key,
        aws_secret_access_key=settings.secret_key,
        region_name=settings.aws_region
    )

    try:
        body = {
            "prompt": prompt,
            "temperature": settings.temperature,
            "max_gen_len": settings.max_tokens,
            "context_length": settings.context_window,  # ✅ Add context window
            "top_p": 0.9  # ✅ Added top_p for nucleus sampling
        }

        model_id = 'us.meta.llama3-3-70b-instruct-v1:0'  # Modify if required
        response = bedrock_runtime_client.invoke_model(
            modelId=model_id, body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())
        return response_body["generation"]

    except ClientError as e:
        print("Couldn't invoke LLaMA 3:", e)
        raise

def chunk_content(text):
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=80, length_function=len, is_separator_regex=False
    ).split_text(text)
    return chunks