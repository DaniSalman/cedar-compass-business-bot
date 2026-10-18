"""Run with python app.py. Also used unchanged on Hugging Face Spaces."""
import os
import gradio as gr
from agent import BusinessAgent

try:
    # ZeroGPU Spaces (the free hosting option) expect at least one GPU function.
    # The app is CPU-only and never calls it; locally `spaces` is not installed.
    import spaces

    @spaces.GPU(duration=1)
    def _zerogpu_placeholder():
        return None
except Exception:
    pass

TITLE = "Cedar & Compass Travel, Chat with Layla"
EXAMPLES = ["What's included in the Istanbul package?",
            "Do you offer student discounts?",
            "I want a quote for 4 people to Barcelona in June.",
            "Do you sell travel insurance?"]


def build_demo(agent=None):
    agent = agent or BusinessAgent()
    demo = gr.ChatInterface(
        fn=agent.chat, type="messages", title=TITLE,
        description=("Your friendly travel concierge for the Mediterranean and Middle East. "
                     "Fictional classroom business. Please use simulated contact details "
                     "and keep passport and payment information out of chat."),
        examples=EXAMPLES, cache_examples=False,
        chatbot=gr.Chatbot(type="messages", height=460, label="Layla"),
        textbox=gr.Textbox(placeholder="Tell Layla what you have in mind…", max_length=2000),
        save_history=False, concurrency_limit=1,
        theme=gr.themes.Soft(primary_hue="teal"),
    )
    return demo


if __name__ == "__main__":
    build_demo().launch(server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
                        share=os.getenv("GRADIO_SHARE", "false").lower() == "true")
