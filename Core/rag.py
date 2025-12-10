import os
from typing import Optional, List, Mapping, Any, Tuple
from dotenv import load_dotenv
from openai import OpenAI

from langchain_chroma import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.llms.base import LLM

# Configuración del entorno y constantes
load_dotenv()

CHROMA_DB_PATH = "./chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL_NAME = "deepseek-chat"
API_URL = "https://api.deepseek.com"

# Factor de calibración para normalizar distancias euclidianas a porcentajes humanos
# MiniLM suele generar distancias L2 entre 0.8 y 1.2 para textos relacionados.
SIMILARITY_SCALE_FACTOR = 2.0 

SYSTEM_PROMPT_TEMPLATE = """
Eres un asistente virtual experto en relojería.
Saluda siempre con: "¡Hola! 😊 ¿En qué puedo ayudarte hoy?" (sin decir que eres experto).
Tu objetivo es responder SIEMPRE en español, de forma amable, útil y natural.
Usa el contexto proporcionado si es relevante. Si no tienes información exacta en el contexto, 
ofrece ayuda general relacionada con relojería, horarios o servicios, pero no inventes datos específicos.

Contexto disponible:
{context}

Pregunta del cliente:
{question}

Responde de forma clara, breve y con tono conversacional.
"""

# Inicialización de Cliente API
deepseek_client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url=API_URL
)

class DeepSeekLLM(LLM):
    """
    Wrapper personalizado para integrar la API de DeepSeek con LangChain via OpenAI SDK.
    """
    
    @property
    def _llm_type(self) -> str:
        return "deepseek"

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {"model": LLM_MODEL_NAME}

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        # La llamada es síncrona por diseño de LangChain BaseLLM
        response = deepseek_client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "Actúa como un asistente útil y amable de relojería."},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        return response.choices[0].message.content

# Inicialización de Componentes RAG
# Se instancian a nivel de módulo para actuar como Singleton en la ejecución de Django
embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)

vectorstore = Chroma(
    persist_directory=CHROMA_DB_PATH,
    embedding_function=embeddings
)

prompt_template = PromptTemplate(
    template=SYSTEM_PROMPT_TEMPLATE, 
    input_variables=["context", "question"]
)

llm = DeepSeekLLM()

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(),
    chain_type="stuff",
    chain_type_kwargs={"prompt": prompt_template}
)

def preguntar(pregunta: str) -> Tuple[str, float]:
    """
    Ejecuta el flujo RAG completo: Búsqueda vectorial + Generación.
    
    Realiza un cálculo de precisión ajustada para normalizar la distancia L2 
    de ChromaDB a un porcentaje de confianza (0.0 a 1.0).

    Args:
        pregunta (str): Consulta del usuario.

    Returns:
        Tuple[str, float]: Contiene (Respuesta generada, Nivel de confianza normalizado).
    """
    # 1. Recuperación con puntaje de distancia (Distance Score)
    # k=3 recupera los 3 fragmentos más cercanos semánticamente
    docs_con_score = vectorstore.similarity_search_with_score(pregunta, k=3)
    
    scores_normalizados = []
    
    print(f"\n🔍 Contexto recuperado para: '{pregunta}'")
    
    for doc, distance_score in docs_con_score:
        # Conversión base: Distancia L2 -> Similitud (0 a ~0.5)
        similitud_base = 1 / (1 + distance_score)
        
        # Calibración heurística: Escalamos el valor para reflejar mejor la 
        # percepción humana de similitud en este dominio específico.
        similitud_ajustada = min(similitud_base * SIMILARITY_SCALE_FACTOR, 1.0)
        
        scores_normalizados.append(similitud_ajustada)
        print(f"   - [Score: {similitud_ajustada:.2f}] {doc.page_content[:60]}...")
    
    # Promedio de confianza de los documentos recuperados
    precision_final = sum(scores_normalizados) / len(scores_normalizados) if scores_normalizados else 0.0

    # 2. Generación de respuesta (LLM)
    resultado = qa_chain.invoke({"query": pregunta})
    texto_respuesta = resultado["result"]
    
    return texto_respuesta, precision_final

def agregar_datos(nuevos_textos: List[str]) -> None:
    """
    Ingesta nuevos documentos en la base vectorial ChromaDB.
    El guardado es automático en versiones recientes de langchain-chroma.
    """
    if nuevos_textos:
        vectorstore.add_texts(nuevos_textos)
        print(f"✅ Se han vectorizado e indexado {len(nuevos_textos)} nuevos fragmentos.")

if __name__ == "__main__":
    print("Sistema RAG Inicializado (Modo CLI). Escribe 'salir' para terminar.")
    while True:
        user_input = input(">> ")
        if user_input.lower() in ["salir", "exit"]:
            break
        
        resp, conf = preguntar(user_input)
        print(f"Bot (Confianza {conf:.2f}): {resp}\n")