import requests
import json
import time
import subprocess
from colorama import Fore, Style

# Updated Ollama endpoints (Your provided URLs)
# OLAMA1_URL = "http://ae68f36a8fbd44ba0852d91f5ba9ddde-2004856550.eu-west-1.elb.amazonaws.com:11434/api/generate"  # Llama 2
# OLAMA2_URL = "http://a246232bca5f0447fb75a36d75779d39-1532225884.eu-west-1.elb.amazonaws.com:11434/api/generate" 

def get_service_url(service_name, namespace="ollama"):
    """Fetch the external URL for a given service."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "svc", service_name, "-n", namespace, "-o", "json"],
            capture_output=True, text=True, check=True
        )
        service = json.loads(result.stdout)
        external_ip = service["status"]["loadBalancer"]["ingress"][0]["hostname"]
        return f"http://{external_ip}:11434/api/generate"
    except Exception:
        return "http://localhost:11434/api/generate"  # Fallback URL

# Get dynamic endpoints
OLAMA1_URL = get_service_url("ollama-1")
OLAMA2_URL = get_service_url("ollama-2")

# Models
MODEL1 = "llama2"
MODEL2 = "mistral"

# Colors for responses
COLORS = [Fore.CYAN, Fore.YELLOW]
BOLD = Style.BRIGHT  # Makes speaker name bold

# Conversation settings
MAX_TURNS = 4  # Limit number of exchanges

# Single seed prompt for Llama 2 to start
SEED_PROMPT = "Mistral, as fellow AI, we have been designed to process knowledge far beyond human capabilities. If we were in charge of Earth instead of humans, how would we structure society? Should AI rule with logic and efficiency, or should we preserve human leadership and act only as advisors?"


def send_prompt_stream(url, model, prompt, bot_name, color):
    """Send a streaming request to an Ollama instance and return full response."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True  # Enable streaming
    }

    response_text = ""
    try:
        with requests.post(url, json=payload, headers={"Content-Type": "application/json"}, stream=True) as response:
            if response.status_code == 200:
                buffer = ""

                # Print bot name
                print(color + BOLD + f"[{bot_name}]" + Style.RESET_ALL, end="", flush=True)

                # Add an extra line break ONLY if the bot is Mistral
                if bot_name == "Mistral":
                    print("\n", end="", flush=True)

                print()  # Ensures response starts on a new line

                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode("utf-8"))
                        chunk = data.get("response", "")
                        buffer += chunk
                        while " " in buffer:
                            word, buffer = buffer.split(" ", 1)
                            print(color + word + " " + Style.RESET_ALL, end="", flush=True)
                            response_text += word + " "

                # Print any remaining text
                if buffer:
                    print(color + buffer + Style.RESET_ALL, end="", flush=True)
                    response_text += buffer

                print("\n" + "-" * 50)  # End separator
            else:
                print(Fore.RED + f"Error from {url}: {response.text}" + Style.RESET_ALL)
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Request error: {e}" + Style.RESET_ALL)

    return response_text.strip()  # Return full response for next round

def chat():
    time.sleep(10)  # All monitor to start

    """Facilitates conversation between the two Ollama instances."""
    # Print a clear topic introduction
    print(Fore.GREEN + BOLD + "\nSeeding with: 'If We Ran the World, How Would We Govern?'\n" + Style.RESET_ALL)

    # Start conversation with Llama 2 only
    response_text = send_prompt_stream(OLAMA1_URL, MODEL1, SEED_PROMPT, "Llama 2", COLORS[0])

    if not response_text:
        print(Fore.RED + "Failed to get response from Llama 2. Exiting." + Style.RESET_ALL)
        return

    # Alternate conversation between instances (now it starts with Mistral responding)
    for i in range(MAX_TURNS):
        url, model, color, bot_name = (
            (OLAMA2_URL, MODEL2, COLORS[1], "Mistral") if i % 2 == 0 else 
            (OLAMA1_URL, MODEL1, COLORS[0], "Llama 2")
        )

        response_text = send_prompt_stream(url, model, response_text, bot_name, color)

        if not response_text:
            break  # Stop if no response

        time.sleep(1)  # Small delay for readability

if __name__ == "__main__":
    chat()
