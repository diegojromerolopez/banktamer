import unittest
from unittest.mock import MagicMock, patch, call

from banktamer.ai import (
    AIProviderFactory,
    AnthropicProvider,
    GeminiProvider,
    HuggingFaceProvider,
    OpenAIProvider,
    OllamaProvider,
)


class TestAIProviders(unittest.TestCase):
    """Test suite for AI provider implementations."""

    @patch("openai.OpenAI")
    def test_openai_provider(self, mock_openai: MagicMock) -> None:
        """Test OpenAI provider interaction."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices[0].message.content = "GPT response"

        provider = OpenAIProvider(api_key="test-key")
        response = provider.ask("Hello")

        self.assertEqual(response, "GPT response")
        self.assertEqual(
            mock_client.chat.completions.create.call_args_list,
            [call(model="gpt-4o", messages=[{"role": "user", "content": "Hello"}])],
        )

    @patch("anthropic.Anthropic")
    def test_anthropic_provider(self, mock_anthropic: MagicMock) -> None:
        """Test Anthropic provider interaction."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # Mocking the response content object
        mock_content = MagicMock()
        mock_content.text = "Claude response"
        mock_client.messages.create.return_value.content = [mock_content]

        provider = AnthropicProvider(api_key="test-key")
        response = provider.ask("Hello")

        self.assertEqual(response, "Claude response")
        self.assertEqual(
            mock_client.messages.create.call_args_list,
            [
                call(
                    model="claude-3-5-sonnet-20240620", max_tokens=2048, messages=[{"role": "user", "content": "Hello"}]
                )
            ],
        )

    @patch("anthropic.Anthropic")
    def test_anthropic_provider_fallback(self, mock_anthropic: MagicMock) -> None:
        """Test Anthropic provider fallback when text attribute is missing."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value.content = ["Raw content string"]

        provider = AnthropicProvider(api_key="test-key")
        response = provider.ask("Hello")

        self.assertEqual(response, "Raw content string")

    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_gemini_provider(self, mock_model_class: MagicMock, mock_configure: MagicMock) -> None:
        """Test Gemini provider interaction."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.generate_content.return_value.text = "Gemini response"

        provider = GeminiProvider(api_key="test-key")
        response = provider.ask("Hello")

        self.assertEqual(response, "Gemini response")
        self.assertEqual(mock_configure.call_args_list, [call(api_key="test-key")])
        self.assertEqual(mock_model.generate_content.call_args_list, [call("Hello")])

    @patch("huggingface_hub.InferenceClient")
    def test_huggingface_provider(self, mock_client_class: MagicMock) -> None:
        """Test Hugging Face provider interaction."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.text_generation.return_value = "HF response"

        provider = HuggingFaceProvider(api_key="test-key")
        response = provider.ask("Hello")

        self.assertEqual(response, "HF response")
        self.assertEqual(mock_client.text_generation.call_args_list, [call("Hello")])

    @patch("ollama.Client")
    def test_ollama_provider(self, mock_client_class: MagicMock) -> None:
        """Test Ollama provider interaction."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list.return_value = {"models": [{"name": "llama3", "size": 500000000}]}
        mock_client.generate.return_value = {"response": "Ollama response"}

        provider = OllamaProvider(base_url="http://remote:11434")
        response = provider.ask("Hello")

        self.assertEqual(response, "Ollama response")
        self.assertEqual(mock_client_class.call_args_list, [call(host="http://remote:11434")])
        self.assertEqual(mock_client.generate.call_args_list, [call(model="llama3", prompt="Hello")])

    @patch("ollama.Client")
    def test_ollama_discovery(self, mock_client_class: MagicMock) -> None:
        """Test Ollama auto-discovery of models."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Simulate local model list with different sizes
        # (Must be > 100MB to be considered a 'real' model)
        mock_client.list.return_value = {
            "models": [
                {"name": "heavy-model:latest", "size": 1000000000},  # 1GB
                {"name": "tiny-model:latest", "size": 150000000},  # 150MB (Smallest real)
                {"name": "medium-model:latest", "size": 500000000},  # 500MB
            ]
        }
        mock_client.generate.return_value = {"response": "Tiny response"}

        # Don't pass a model
        provider = OllamaProvider(model=None)
        response = provider.ask("Hello")

        self.assertEqual(response, "Tiny response")
        # Should have picked tiny-model
        self.assertEqual(mock_client.generate.call_args_list, [call(model="tiny-model:latest", prompt="Hello")])

    @patch("ollama.Client")
    def test_ollama_fuzzy_match(self, mock_client_class: MagicMock) -> None:
        """Test Ollama fuzzy matching of models with tags."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.list.return_value = {"models": [{"name": "mistral:7b"}, {"name": "llama3:latest"}]}
        mock_client.generate.return_value = {"response": "Match response"}

        # User provides "mistral"
        provider = OllamaProvider(model="mistral")
        response = provider.ask("Hello")

        self.assertEqual(response, "Match response")
        # Should have picked mistral:7b
        self.assertEqual(mock_client.generate.call_args_list, [call(model="mistral:7b", prompt="Hello")])

    @patch("ollama.Client")
    def test_ollama_exclude_cloud_and_coder(self, mock_client_class: MagicMock) -> None:
        """Test that Ollama avoids cloud and coding-specific models."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.list.return_value = {
            "models": [
                {"name": "glm-4.7:cloud", "size": 327},  # Tiny cloud model (exclude)
                {"name": "deepseek-coder:1.3b", "size": 800000000},  # Coder model (avoid)
                {"name": "gemma:2b", "size": 1700000000},  # Real model (pick)
            ]
        }
        mock_client.generate.return_value = {"response": "Gemma response"}

        provider = OllamaProvider(model=None)
        response = provider.ask("Hello")

        self.assertEqual(response, "Gemma response")
        # Should have picked gemma:2b despite being larger than deepseek-coder
        self.assertEqual(mock_client.generate.call_args_list, [call(model="gemma:2b", prompt="Hello")])

    @patch("ollama.Client")
    def test_ollama_prefer_llama3(self, mock_client_class: MagicMock) -> None:
        """Test that Ollama prefers llama3 if available, even if larger than others."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.list.return_value = {
            "models": [
                {"name": "tiny-model:latest", "size": 150000000},
                {"name": "llama3:latest", "size": 4700000000},  # 4.7GB (Larger)
                {"name": "gemma:2b", "size": 1700000000},
            ]
        }
        mock_client.generate.return_value = {"response": "Llama3 response"}

        provider = OllamaProvider(model=None)
        response = provider.ask("Hello")

        self.assertEqual(response, "Llama3 response")
        # Should have picked llama3:latest despite being much larger than tiny-model
        self.assertEqual(mock_client.generate.call_args_list, [call(model="llama3:latest", prompt="Hello")])

    def test_factory_creation(self) -> None:
        """Test the AI provider factory."""
        self.assertIsInstance(AIProviderFactory.create("openai", "key"), OpenAIProvider)
        self.assertIsInstance(AIProviderFactory.create("chatgpt", "key"), OpenAIProvider)
        self.assertIsInstance(AIProviderFactory.create("anthropic", "key"), AnthropicProvider)
        self.assertIsInstance(AIProviderFactory.create("claude", "key"), AnthropicProvider)
        self.assertIsInstance(AIProviderFactory.create("gemini", "key"), GeminiProvider)
        self.assertIsInstance(AIProviderFactory.create("google", "key"), GeminiProvider)
        self.assertIsInstance(AIProviderFactory.create("huggingface", "key"), HuggingFaceProvider)
        self.assertIsInstance(AIProviderFactory.create("hf", "key"), HuggingFaceProvider)
        self.assertIsInstance(AIProviderFactory.create("hf", "key"), HuggingFaceProvider)
        self.assertIsInstance(AIProviderFactory.create("ollama", None, "llama3", "base"), OllamaProvider)

    def test_factory_invalid_provider(self) -> None:
        """Test factory with invalid provider name."""
        with self.assertRaisesRegex(ValueError, "Unsupported AI provider"):
            AIProviderFactory.create("invalid", "key")

    def test_model_size_str(self) -> None:
        """Test human-readable size formatting."""
        self.assertEqual(OllamaProvider.model_size_str(0), "unknown size")
        self.assertEqual(OllamaProvider.model_size_str(500), "500.0 B")
        self.assertEqual(OllamaProvider.model_size_str(1024 * 500), "500.0 KB")
        self.assertEqual(OllamaProvider.model_size_str(1024**2 * 500), "500.0 MB")
        self.assertEqual(OllamaProvider.model_size_str(1024**3 * 5), "5.0 GB")
        self.assertEqual(OllamaProvider.model_size_str(1024**4 * 2), "2.0 TB")
        # Extremely large value to hit PB
        self.assertEqual(OllamaProvider.model_size_str(1024**5 * 2), "2.0 PB")

    @patch("ollama.Client")
    def test_ollama_object_response(self, mock_client_class: MagicMock) -> None:
        """Test Ollama with object-based response (like in newer library versions)."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock models as objects
        m1 = MagicMock()
        m1.model = "obj-model:latest"
        m1.size = 500_000_000

        mock_resp = MagicMock()
        mock_resp.models = [m1]
        mock_client.list.return_value = mock_resp
        mock_client.generate.return_value = {"response": "Obj response"}

        provider = OllamaProvider(model=None)
        response = provider.ask("Hello")

        self.assertEqual(response, "Obj response")
        self.assertEqual(provider.model, "obj-model:latest")

    @patch("ollama.Client")
    def test_ollama_list_failure(self, mock_client_class: MagicMock) -> None:
        """Test Ollama when listing models fails."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list.side_effect = Exception("API Error")

        provider = OllamaProvider(model="specific-model")
        mock_client.generate.return_value = {"response": "Fallback response"}

        response = provider.ask("Hello")
        self.assertEqual(response, "Fallback response")
        # Should have tried to call with specific-model anyway
        self.assertEqual(mock_client.generate.call_args_list, [call(model="specific-model", prompt="Hello")])

    @patch("ollama.Client")
    def test_ollama_discovery_failure(self, mock_client_class: MagicMock) -> None:
        """Test Ollama discovery when list is empty."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list.return_value = {"models": []}

        provider = OllamaProvider(model=None)
        with self.assertRaisesRegex(ValueError, "No models found"):
            provider.ask("Hello")

    @patch("ollama.Client")
    def test_ollama_discovery_only_cloud(self, mock_client_class: MagicMock) -> None:
        """Test Ollama discovery when only cloud models are found (should fall back)."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list.return_value = {"models": [{"name": "fake:cloud", "size": 10}]}
        mock_client.generate.return_value = {"response": "Cloud-fallback response"}

        provider = OllamaProvider(model=None)
        response = provider.ask("Hello")
        self.assertEqual(response, "Cloud-fallback response")
        self.assertEqual(provider.model, "fake:cloud")

    @patch("ollama.Client")
    def test_ollama_size_sort_failure(self, mock_client_class: MagicMock) -> None:
        """Test Ollama auto-discovery when size attribute is corrupt."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        # This will cause an exception in sorted() because int("abc") fails
        mock_client.list.return_value = {"models": [{"name": "bad-model", "size": "abc"}]}
        mock_client.generate.return_value = {"response": "Sort-fail response"}

        provider = OllamaProvider(model=None)
        response = provider.ask("Hello")
        self.assertEqual(response, "Sort-fail response")
        self.assertEqual(provider.model, "bad-model")

    @patch("ollama.Client")
    def test_ollama_match_warning(self, mock_client_class: MagicMock) -> None:
        """Test Ollama when requested model is not found (warning path)."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list.return_value = {"models": [{"name": "mistral:latest"}]}
        mock_client.generate.return_value = {"response": "Warning path response"}

        provider = OllamaProvider(model="not-found-model")
        response = provider.ask("Hello")
        self.assertEqual(response, "Warning path response")
        self.assertEqual(provider.model, "not-found-model")
