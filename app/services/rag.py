import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from upstash_vector import Index, Vector
import uuid
from config import Config
from pathlib import Path

class RAG:
    def __init__(self, upstash_url: str, upstash_token: str, openai_api_key: str):
        """
        Initialize RAG class with Upstash and OpenAI configurations.

        Args:
            upstash_url (str): Upstash vector database URL
            upstash_token (str): Upstash vector database token
            openai_api_key (str): OpenAI API key for embeddings
        """
        self.index = Index(url=upstash_url, token=upstash_token)
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

    def process_and_store_document(self, document_path: str, document_id: str):
        """
        Process document and store its embeddings in Upstash.

        Args:
            document_path (str): Path to the document file
            document_id (str): Unique identifier for the document
        """
        try:
            # Load document


            doc = Path(document_path)
            if not doc.exists():
                raise FileNotFoundError(f"File not found: {document_path}")


            if document_path.lower().endswith('.pdf'):
                loader = PyPDFLoader(document_path)
            else:
                loader = TextLoader(document_path)


            documents = loader.load()



            # Split document into chunks
            chunks = self.text_splitter.split_documents(documents)


            # Generate embeddings for each chunk
            vectors = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                embedding = self.embeddings.embed_query(chunk.page_content)

                # Create vector with metadata
                vector = Vector(
                    id=chunk_id,
                    vector=embedding,
                    metadata={
                        "document_id": document_id,
                        "chunk_index": i,
                        "text": chunk.page_content
                    }
                )
                vectors.append(vector)

            # Upsert vectors to Upstash
            self.index.upsert(vectors=vectors)
            return {"status": "success", "message": f"Stored {len(vectors)} chunks for document {document_id}"}

        except Exception as e:
            print(e)
            return {"status": "error", "message": str(e)}

    def query(self, question: str, document_id: str, top_k: int = 1):
        """
        Query the vector database for relevant document chunks.

        Args:
            question (str): The query question
            document_id (str): Document ID in format documentID_filename
            top_k (int): Number of results to return

        Returns:
            List of relevant document chunks with metadata
        """
        try:
            # Generate embedding for the question
            query_embedding = self.embeddings.embed_query(question)

            # Query Upstash vector database
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_vectors=True,
                include_metadata=True,
                filter=f"document_id = '{document_id}'"
            )



            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.metadata.get("text"),
                    "chunk_index": result.metadata.get("chunk_index"),
                    "document_id": result.metadata.get("document_id")
                })

            return formatted_results

        except Exception as e:
            return {"status": "error", "message": str(e)}



def get_rag_service():
    return RAG(
        upstash_url=Config.UPSTASH_URL,
        upstash_token=Config.UPSPLASH_VECTOR_DATABASE_TOKEN,
        openai_api_key=Config.OPENAI_API_KEY
    )
