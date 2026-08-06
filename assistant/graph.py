from typing import TypedDict, Literal, Optional
from django.conf import settings
import cohere


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