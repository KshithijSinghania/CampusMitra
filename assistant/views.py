from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from asgiref.sync import sync_to_async
from .graph import graph


@login_required
def chat_view(request):
    return render(request, "assistant/chat.html")


async def chat_api_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    if not await sync_to_async(lambda: request.user.is_authenticated)():
        return JsonResponse({"error": "Authentication required"}, status=401)

    import json
    body = json.loads(request.body)
    message = body.get("message", "").strip()

    if not message:
        return JsonResponse({"error": "Empty message"}, status=400)

    if not request.session.session_key:
        await sync_to_async(request.session.save)()

    state = {
        "question": message,
        "original_question": None,
        "detected_language": None,
        "user_id": request.user.id,
        "session_id": request.session.session_key,
        "route": None,
        "documents": None,
        "generation": None,
        "grade": None,
        "follow_up_count": 0,
        "short_term_context": None,
    }

    # LangGraph's compiled graph runs synchronously (all our nodes are sync functions,
    # including Django ORM calls) — sync_to_async bridges it into Django's async view
    # without blocking the event loop
    try:
        result = await sync_to_async(graph.invoke)(state)
    except Exception as e:
        if "429" in str(e) or "TooManyRequestsError" in type(e).__name__:
            return JsonResponse({
                "answer": "I'm getting a lot of requests right now — please wait about a minute and try again.",
                "route": "error",
            })
        return JsonResponse({
            "answer": "Something went wrong on my end. Please try again in a moment.",
            "route": "error",
        })

    return JsonResponse({
        "answer": result["generation"],
        "route": result["route"],
    })