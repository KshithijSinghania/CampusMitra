from typing import TypedDict, Literal, Optional
from django.conf import settings
import cohere
import chromadb
from .ingestion import embed_query
from assistant.models import MessTiming, Contact

class GraphState(TypedDict):
    question: str
    user_id: Optional[int]
    route: Optional[str]
    documents: Optional[list]
    generation: Optional[str]
    grade: Optional[str]
    follow_up_count: int

ROUTER_SYSTEM_PROMPT = """You are a query router for a college campus assistant chatbot.
Classify the student's question into EXACTLY ONE of these four categories.
Respond with ONLY the category name, nothing else — no punctuation, no explanation.

Categories:
- structured_db: factual lookups with one exact correct answer from a database table.
  Examples: mess timings, hall/room timings, contact numbers, department emails, office hours.
- vector_retrieve: questions answerable from institutional documents like the handbook,
  policies, or FAQs. Examples: hostel allotment process, attendance policy, library rules,
  medical facility info, WiFi setup instructions.
- personal_gmail: questions about the student's OWN personal information that would only
  exist in their own email inbox. Examples: "what did the professor email me about the
  assignment", "when is my exam according to the email I got", "what's the status of my
  hostel application email".
- llm_fallback: general knowledge questions, greetings, or anything not covered by the
  above three categories. Examples: "what is machine learning", "hi", "how are you".

Examples:
Q: What time does Mess Hall A serve breakfast?
A: structured_db

Q: What's the phone number for the Hostel Office?
A: structured_db

Q: How does hostel room allotment work?
A: vector_retrieve

Q: What's the attendance requirement to sit for exams?
A: vector_retrieve

Q: Did my professor email me about the deadline extension?
A: personal_gmail

Q: What did I get told about my hostel application over email?
A: personal_gmail

Q: What is the capital of France?
A: llm_fallback

Q: Hi, how are you?
A: llm_fallback
"""


import cohere

def retrieve(state: GraphState) -> GraphState:
    route = state["route"]
    question = state["question"]
    documents = []

    if route == "structured_db":
        # Structured data is small enough to just format every row as text and
        # let grading/generation figure out what's relevant — no NL-to-SQL needed
        for mt in MessTiming.objects.all():
            documents.append(
                f"{mt.hall} serves {mt.get_meal_display()} from {mt.start_time} to {mt.end_time}."
            )
        for c in Contact.objects.all():
            documents.append(
                f"{c.department} contact: {c.name} ({c.designation}), phone: {c.phone}, email: {c.email}."
            )

    elif route == "vector_retrieve":
        chroma_client = chromadb.PersistentClient(path="vectorstore")
        collection = chroma_client.get_collection("institutional_knowledge")
        query_embedding = embed_query(question)
        results = collection.query(query_embeddings=[query_embedding], n_results=4)
        documents = results["documents"][0] if results["documents"] else []

    elif route == "personal_gmail":
        user_id = state["user_id"]
        chroma_client = chromadb.PersistentClient(path="vectorstore")
        try:
            collection = chroma_client.get_collection(f"gmail_{user_id}")
            query_embedding = embed_query(question)
            # user_id filter here is belt-and-suspenders — the collection is already
            # per-user, but explicit filtering costs nothing and guards against any
            # future refactor that merges collections
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=4,
                where={"user_id": user_id},
            )
            documents = results["documents"][0] if results["documents"] else []
        except Exception:
            documents = []  # user's Gmail collection may not exist yet (still backfilling)

    # llm_fallback intentionally retrieves nothing — it skips straight to generation

    state["documents"] = documents
    return state

GRADER_SYSTEM_PROMPT = """You are grading whether a retrieved document is relevant to a
student's question. Respond with ONLY "yes" or "no", nothing else.

A document is relevant if it contains information that would help answer the question,
even partially. Be lenient — if there's a reasonable chance it helps, say yes."""


def grade_documents(state: GraphState) -> GraphState:
    question = state["question"]
    documents = state["documents"]

    if not documents:
        return state  # nothing to grade

    co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
    relevant_docs = []

    for doc in documents:
        response = co.chat(
            model="command-a-03-2025",
            messages=[
                {"role": "system", "content": GRADER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nDocument: {doc}"},
            ],
            temperature=0,
        )
        grade = response.message.content[0].text.strip().lower()
        if "yes" in grade:
            relevant_docs.append(doc)

    state["documents"] = relevant_docs
    return state

GENERATE_SYSTEM_PROMPT = """You are CampusMitra, a helpful campus assistant chatbot for
IIT Indore students. Answer the student's question using ONLY the provided context
documents. If the context doesn't contain enough information to answer confidently,
say so honestly rather than guessing. Keep answers concise and friendly."""


def generate(state: GraphState) -> GraphState:
    question = state["question"]
    documents = state["documents"]

    if documents:
        context = "\n\n".join(documents)
        user_content = f"Context:\n{context}\n\nQuestion: {question}"
    else:
        # llm_fallback route, or nothing survived grading — answer from general knowledge
        user_content = question

    co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
    response = co.chat(
        model="command-a-03-2025",
        messages=[
            {"role": "system", "content": GENERATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,  # a little creative flexibility for natural-sounding answers, unlike the routing/grading calls
    )

    state["generation"] = response.message.content[0].text.strip()
    return state

def route_query(state: GraphState) -> GraphState:
    co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)

    response = co.chat(
        model="command-a-03-2025",
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": state["question"]},
        ],
        temperature=0,
    )

    route = response.message.content[0].text.strip().lower()

    valid_routes = {"structured_db", "vector_retrieve", "personal_gmail", "llm_fallback"}
    if route not in valid_routes:
        route = "llm_fallback"

    state["route"] = route
    return state