
from forgeai.core.config import get_settings
from forgeai.llm.ollama_provider import OllamaProvider
from forgeai.llm.tool_schemas import (
    LLMMessage,
    LLMToolDefinition,
)


def main() -> None:
    provider = OllamaProvider(get_settings())

    response = provider.generate_with_tools(
        messages=[
            LLMMessage(
                role="user",
                content="What is 25 + 17? Use the add_numbers tool.",
            )
        ],
        tools=[
            LLMToolDefinition(
                name="add_numbers",
                description="Add two integers and return their sum.",
                parameters={
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {"type": "integer"},
                    },
                    "required": ["a", "b"],
                    "additionalProperties": False,
                },
            )
        ],
    )

    print("Model:", response.model)
    print("Input tokens:", response.input_tokens)
    print("Output tokens:", response.output_tokens)
    print("Content:", response.content)
    print("Tool calls:", response.tool_calls)


if __name__ == "__main__":
    main()
