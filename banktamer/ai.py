from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base class for AI service providers."""

    @abstractmethod
    def ask(self, prompt: str) -> str:
        """Send a prompt to the AI and return the response."""
        pass  # pragma: no cover


class OpenAIProvider(AIProvider):
    """OpenAI (ChatGPT) provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str | None = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def ask(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return str(response.choices[0].message.content)


class AnthropicProvider(AIProvider):
    """Anthropic (Claude) provider."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"):
        self.api_key = api_key
        self.model = model

    def ask(self, prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        # Handle the MessageContent objects properly
        content = response.content[0]
        if hasattr(content, "text"):
            return str(content.text)
        return str(content)


class GeminiProvider(AIProvider):
    """Google (Gemini) provider."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model

    def ask(self, prompt: str) -> str:
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]
            model = genai.GenerativeModel(self.model)  # type: ignore[attr-defined]
            response = model.generate_content(prompt)
            return str(response.text)
        except ImportError:  # pragma: no cover
            raise ImportError("Please install 'google-generativeai' to use Gemini.")


class HuggingFaceProvider(AIProvider):
    """Hugging Face provider."""

    def __init__(self, api_key: str, model: str = "mistralai/Mistral-7B-v0.1"):
        self.api_key = api_key
        self.model = model

    def ask(self, prompt: str) -> str:
        from huggingface_hub import InferenceClient

        client = InferenceClient(model=self.model, token=self.api_key)
        # Use simple text generation
        return str(client.text_generation(prompt))


class OllamaProvider(AIProvider):
    """Ollama provider for local or remote instances."""

    def __init__(self, model: str | None = None, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def ask(self, prompt: str) -> str:
        import ollama

        client = ollama.Client(host=self.base_url)

        try:
            models_resp = client.list()
            # Handle both older dict-based and newer object-based library responses
            if isinstance(models_resp, dict):
                models_data = models_resp.get("models", [])
                available_models = [m["name"] for m in models_data]
            else:
                models_data = getattr(models_resp, "models", [])
                # Some versions use .model, others use .name
                available_models = [getattr(m, "model", getattr(m, "name", "")) for m in models_data]
        except Exception:
            # If we can't list models (e.g. older Ollama version or remote issues),
            # we just try to proceed with what we have.
            available_models = []
            models_data = []

        if not self.model:
            # Auto-discovery logic: Find the smallest model to minimize resource usage
            if not available_models:
                raise ValueError(f"No models found on Ollama instance at {self.base_url}")

            try:
                # Sort available models by size (ascending)
                def get_size(m: object) -> int:
                    if isinstance(m, dict):
                        return int(m.get("size", 0))
                    return int(getattr(m, "size", 0))

                # Filter out manifest-only or cloud models (usually < 1MB)
                # We expect actual models to be at least 100MB and not have ':cloud' in the name
                def is_real_local_model(m: object) -> bool:
                    name = ""
                    if isinstance(m, dict):
                        name = m.get("name", "")
                    else:
                        name = getattr(m, "model", getattr(m, "name", ""))

                    if ":cloud" in name:
                        return False
                    return get_size(m) > 100 * 1024 * 1024

                # Prefer models that are not coding-specific if we have a choice
                def is_coding_model(m: object) -> bool:
                    name = ""
                    if isinstance(m, dict):
                        name = m.get("name", "").lower()
                    else:
                        name = getattr(m, "model", getattr(m, "name", "")).lower()
                    return "coder" in name or "code" in name

                real_models = [m for m in models_data if is_real_local_model(m)]
                non_coding_models = [m for m in real_models if not is_coding_model(m)]
                search_list = non_coding_models if non_coding_models else real_models

                # If still no "real" models found, fall back to all models
                if not search_list:
                    search_list = models_data

                # New preference: Check if llama3 is available among the search list
                llama3_matches = []
                for m in search_list:
                    m_name = m["name"] if isinstance(m, dict) else getattr(m, "model", getattr(m, "name", ""))
                    if m_name == "llama3" or m_name.startswith("llama3:"):
                        llama3_matches.append(m)

                if llama3_matches:
                    # Pick llama3 (smallest version of llama3 if multiple exist for some reason)
                    sorted_llamas = sorted(llama3_matches, key=get_size)
                    smallest_model = sorted_llamas[0]
                else:
                    sorted_data = sorted(search_list, key=get_size)
                    # Get the name of the smallest model in the filtered list
                    smallest_model = sorted_data[0]
                if isinstance(smallest_model, dict):
                    self.model = smallest_model["name"]
                    size = smallest_model.get("size", 0)
                else:
                    self.model = getattr(smallest_model, "model", getattr(smallest_model, "name", ""))
                    size = getattr(smallest_model, "size", 0)

                print(
                    f"No AI model specified. Auto-selected smallest model: {self.model} ({self.model_size_str(size)})"
                )
            except (KeyError, IndexError, AttributeError, ValueError):
                # Fallback to simple first model if size sorting fails
                self.model = available_models[0]
                print(f"No AI model specified. Auto-selected: {self.model}")
        else:
            # Matching logic: if user provided "llama3", but we have "llama3:latest"
            if self.model not in available_models and available_models:
                matches = [m for m in available_models if m.startswith(f"{self.model}:")]
                if matches:
                    self.model = matches[0]
                    print(f"Model '{self.model}' selected as best match for your request.")
                else:
                    print(f"Warning: Requested model '{self.model}' not found in local Ollama list. Trying anyway...")

        response = client.generate(model=self.model, prompt=prompt)
        return str(response["response"])

    @staticmethod
    def model_size_str(size_bytes: int) -> str:
        """Return a human-readable string for the model size."""
        if size_bytes == 0:
            return "unknown size"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes //= 1024
        return f"{size_bytes:.1f} PB"


class AIProviderFactory:
    """Factory to create AI providers based on configuration."""

    @staticmethod
    def create(
        provider_name: str, api_key: str | None = None, model: str | None = None, base_url: str | None = None
    ) -> AIProvider:
        """Create an AI provider instance."""
        match provider_name.lower():
            case "openai" | "chatgpt":
                return OpenAIProvider(api_key or "", model or "gpt-4o", base_url)
            case "anthropic" | "claude":
                return AnthropicProvider(api_key or "", model or "claude-3-5-sonnet-20240620")
            case "google" | "gemini":
                return GeminiProvider(api_key or "", model or "gemini-1.5-pro")
            case "huggingface" | "hf":
                return HuggingFaceProvider(api_key or "", model or "mistralai/Mistral-7B-v0.1")
            case "ollama":
                return OllamaProvider(model, base_url or "http://localhost:11434")
            case _:
                raise ValueError(f"Unsupported AI provider: {provider_name}")
