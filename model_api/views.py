from django.shortcuts import render
from langchain_aws import BedrockEmbeddings
import boto3
import json
from botocore.exceptions import ClientError

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