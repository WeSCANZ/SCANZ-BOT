import logging
import os

import aiohttp

logger = logging.getLogger("discord")


async def query_llm(prompt: str) -> str:
    """
    Sends a query to the configured LLM endpoint.
    """
    llm_url = os.getenv("LLM_ENDPOINT", "http://localhost:11434/api/generate")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "llama3")

    headers = {"Content-Type": "application/json"}
    if llm_api_key:
        headers["Authorization"] = f"Bearer {llm_api_key}"

    # Default payload format, might need adjustment based on specific LLM API (Ollama, OpenAI compatible, etc.)
    # Here using a format common for Ollama or similar local models
    payload = {"model": llm_model, "prompt": prompt, "stream": False}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(llm_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    # Extract response text based on API format.
                    # This assumes an Ollama-like response structure: {"response": "text..."}
                    # Or OpenAI style: {"choices": [{"message": {"content": "text..."}}]}
                    if "response" in data:
                        return data["response"]
                    elif "choices" in data and len(data["choices"]) > 0:
                        choice = data["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            return choice["message"]["content"]
                        elif "text" in choice:
                            return choice["text"]

                    return "Received an unexpected response format from the AI."
                else:
                    logger.error(f"LLM API error: {response.status} - {await response.text()}")
                    return f"Error communicating with AI (HTTP {response.status})."
    except Exception as e:
        logger.error(f"Failed to query LLM: {e}")
        return "Sorry, I am having trouble connecting to my neural network right now."
