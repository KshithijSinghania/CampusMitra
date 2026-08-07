from typing import TypedDict, Literal, Optional
from django.conf import settings
import cohere
import chromadb
from .ingestion import embed_query
from assistant.models import MessTiming, Contact
from .language import detect_language, translate

class GraphState(TypedDict):
    question: str
    original_question: Optional[str]
    detected_language: Optional[str]
    user_id: Optional[int]
    session_id: Optional[str]
    route: Optional[str]
    documents: Optional[list]
    generation: Optional[str]
    grade: Optional[str]
    follow_up_count: int
    short_term_context: Optional[str]

def load_short_term_context(state: GraphState) -> GraphState:
    from .models import ConversationLog

    if not state.get("user_id") or not state.get("session_id"):
        return state

    recent_logs = ConversationLog.objects.filter(
        user_id=state["user_id"],
        session_id=state["session_id"],
    ).order_by("-timestamp")[:5]  # last 5 turns is enough context without bloating the prompt

    if recent_logs:
        context_lines = [f"Q: {log.question}\nA: {log.answer}" for log in reversed(recent_logs)]
        state["short_term_context"] = "\n\n".join(context_lines)
    else:
        state["short_term_context"] = ""

    return state

def detect_and_translate_query(state: GraphState) -> GraphState:
    original = state["question"]
    lang = detect_language(original)

    state["original_question"] = original
    state["detected_language"] = lang

    if lang != "en":
        state["question"] = translate(original, "en")

    return state


def translate_response(state: GraphState) -> GraphState:
    lang = state.get("detected_language", "en")
    if lang != "en":
        state["generation"] = translate(state["generation"], lang)
    return state

def log_conversation(state: GraphState) -> GraphState:
    from .models import ConversationLog

    if state.get("user_id") and state.get("session_id"):
        ConversationLog.objects.create(
            user_id=state["user_id"],
            session_id=state["session_id"],
            question=state.get("original_question") or state["question"],
            answer=state["generation"],
        )
    return state

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
        return state

    co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)

    numbered_docs = "\n\n".join(f"[{i}] {doc}" for i, doc in enumerate(documents))
    response = co.chat(
        model="command-a-03-2025",
        messages=[
            {"role": "system", "content": (
                "You are grading which retrieved documents are relevant to a student's "
                "question. Respond with ONLY a comma-separated list of the relevant "
                "document numbers, e.g. '0,2'. If none are relevant, respond with 'none'."
            )},
            {"role": "user", "content": f"Question: {question}\n\nDocuments:\n{numbered_docs}"},
        ],
        temperature=0,
    )

    answer = response.message.content[0].text.strip().lower()
    if answer == "none":
        state["documents"] = []
    else:
        try:
            relevant_indices = [int(i.strip()) for i in answer.split(",") if i.strip().isdigit()]
            state["documents"] = [documents[i] for i in relevant_indices if i < len(documents)]
        except (ValueError, IndexError):
            state["documents"] = documents  # if parsing fails, fail open rather than losing all documents
    return state

GENERATE_SYSTEM_PROMPT = """You are CampusMitra, a helpful campus assistant chatbot for
IIT Indore students. Answer the student's question using ONLY the provided context
documents. If the context doesn't contain enough information to answer confidently,
say so honestly rather than guessing. Keep answers concise and friendly."""


def generate(state: GraphState) -> GraphState:
    question = state["question"]
    documents = state["documents"]
    short_term_context = state.get("short_term_context", "")

    parts = []
    if short_term_context:
        parts.append(f"Recent conversation:\n{short_term_context}")
    if documents:
        parts.append(f"Context:\n{chr(10).join(documents)}")
    parts.append(f"Question: {question}")

    user_content = "\n\n".join(parts)

    co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
    response = co.chat(
        model="command-a-03-2025",
        messages=[
            {"role": "system", "content": GENERATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
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

RESPONSE_GRADER_PROMPT = """You are checking whether a chatbot's answer actually
addresses the student's question. Respond with ONLY "useful" or "not_useful".

An answer is "useful" if it directly addresses the question with real information,
even if brief. An answer is "not_useful" if it's vague, says it doesn't know, or
fails to address what was actually asked."""


def grade_response(state: GraphState) -> GraphState:
    co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
    response = co.chat(
        model="command-a-03-2025",
        messages=[
            {"role": "system", "content": RESPONSE_GRADER_PROMPT},
            {"role": "user", "content": f"Question: {state['question']}\n\nAnswer: {state['generation']}"},
        ],
        temperature=0,
    )
    grade = response.message.content[0].text.strip().lower()
    state["grade"] = "useful" if "useful" in grade and "not_useful" not in grade else "not_useful"
    return state

def escalate_human(state: GraphState) -> GraphState:
    from .models import HumanEscalation
    from django.contrib.auth.models import User

    user = User.objects.filter(id=state["user_id"]).first() if state.get("user_id") else None

    HumanEscalation.objects.create(
        user=user,
        question=state["question"],
        last_generation=state.get("generation", ""),
    )

    state["generation"] = (
        "I wasn't able to fully answer that after a couple of tries. "
        "I've forwarded your question to campus support staff, who'll follow up with you directly."
    )
    return state

from langgraph.graph import StateGraph, END


def route_decision(state: GraphState) -> str:
    """Tells LangGraph which node to go to after route_query, based on the classified route."""
    return state["route"]


def route_after_grade(state: GraphState) -> str:
    if state["grade"] == "useful":
        return "end"
    state["follow_up_count"] = state.get("follow_up_count", 0) + 1
    if state["follow_up_count"] >= 2:
        return "escalate_human"
    return "retry"


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("detect_and_translate_query", detect_and_translate_query)
    workflow.add_node("load_short_term_context", load_short_term_context)
    workflow.add_node("route_query", route_query)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)
    workflow.add_node("grade_response", grade_response)
    workflow.add_node("escalate_human", escalate_human)
    workflow.add_node("translate_response", translate_response)
    workflow.add_node("log_conversation", log_conversation)

    workflow.set_entry_point("detect_and_translate_query")

    workflow.add_edge("detect_and_translate_query", "load_short_term_context")
    workflow.add_edge("load_short_term_context", "route_query")
    workflow.add_edge("route_query", "retrieve")
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_edge("grade_documents", "generate")
    workflow.add_edge("generate", "grade_response")

    workflow.add_conditional_edges(
        "grade_response",
        route_after_grade,
        {
            "end": "translate_response",
            "retry": "route_query",
            "escalate_human": "escalate_human",
        },
    )
    workflow.add_edge("escalate_human", "translate_response")
    workflow.add_edge("translate_response", "log_conversation")
    workflow.add_edge("log_conversation", END)

    return workflow.compile()


graph = build_graph()