"""
LangChain RAG Agent for conversational retrieval.
"""
import logging
from typing import List, Dict, Any, Optional

from django.conf import settings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from .vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class LangChainRAGAgent:
    """
    LangChain-based RAG agent that:
    1. Retrieves relevant documents from Pinecone
    2. Uses conversation history for context
    3. Generates responses using Groq LLM
    """
    
    SYSTEM_PROMPT = """You are a helpful legal assistant with access to a knowledge base of legal documents. 
Your role is to answer questions based on the provided context from legal documents.

Guidelines:
- Answer based on the provided context when available
- If the context doesn't contain relevant information, say so clearly
- Cite the source document when referencing specific information
- Be precise and professional in your responses
- If asked about something outside the legal documents, you can still help but clarify that it's not from the knowledge base

Context from legal documents:
{context}

Previous conversation for reference - use this to understand follow-up questions:
{chat_history}"""

    def __init__(self):
        self._llm = None
        self._vector_store = None
    
    @property
    def llm(self) -> ChatGroq:
        """Lazy load Groq LLM."""
        if self._llm is None:
            api_key = getattr(settings, 'LLM_API_KEY', None)
            model = getattr(settings, 'LLM_MODEL', 'llama-3.3-70b-versatile')
            
            if not api_key:
                raise ValueError("LLM_API_KEY not configured")
            
            self._llm = ChatGroq(
                api_key=api_key,
                model=model,
                temperature=0.7,
                max_tokens=2048,
            )
        return self._llm
    
    @property
    def vector_store(self) -> VectorStoreService:
        """Lazy load vector store."""
        if self._vector_store is None:
            self._vector_store = VectorStoreService()
        return self._vector_store
    
    def format_chat_history(self, messages: List[Dict[str, str]]) -> str:
        """Format conversation history for the prompt."""
        if not messages:
            return "No previous conversation."
        
        formatted = []
        for msg in messages[-10:]:  # Last 10 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            prefix = "User" if role == 'user' else "Assistant"
            formatted.append(f"{prefix}: {content}")
        
        return "\n".join(formatted)
    
    def format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents as context."""
        if not documents:
            return "No relevant documents found in the knowledge base."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            filename = doc.get('metadata', {}).get('filename', 'Unknown')
            text = doc.get('text', '')
            score = doc.get('score', 0)
            
            context_parts.append(
                f"[Document {i}: {filename} (relevance: {score:.2f})]\n{text}"
            )
        
        return "\n\n---\n\n".join(context_parts)
    
    def generate_response(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Generate a RAG response.
        
        Args:
            query: User's question
            chat_history: Previous messages in the conversation
            top_k: Number of documents to retrieve
            
        Returns:
            Dict with response, sources, and metadata
        """
        chat_history = chat_history or []
        
        # 1. Retrieve relevant documents
        logger.info(f"Querying vector store for: {query[:100]}...")
        retrieved_docs = self.vector_store.query(query, top_k=top_k)
        
        # 2. Format context and history
        context = self.format_context(retrieved_docs)
        history_str = self.format_chat_history(chat_history)
        
        # 3. Build prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{question}")
        ])
        
        # 4. Create chain and invoke
        chain = prompt | self.llm | StrOutputParser()
        
        response = chain.invoke({
            "context": context,
            "chat_history": history_str,
            "question": query
        })
        
        # 5. Extract source information
        sources = []
        for doc in retrieved_docs:
            sources.append({
                'filename': doc.get('metadata', {}).get('filename', 'Unknown'),
                'score': doc.get('score', 0),
                'chunk_index': doc.get('metadata', {}).get('chunk_index', 0)
            })
        
        return {
            'response': response,
            'sources': sources,
            'num_documents_retrieved': len(retrieved_docs),
            'has_context': len(retrieved_docs) > 0
        }
    
    def is_available(self) -> bool:
        """Check if RAG is properly configured."""
        try:
            # Check Pinecone
            stats = self.vector_store.get_stats()
            return stats.get('total_vectors', 0) > 0
        except Exception as e:
            logger.warning(f"RAG not available: {e}")
            return False
