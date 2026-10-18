"""Deploy the app to a Hugging Face Space; never writes credentials.

Needs GEMINI_API_KEY, HF_TOKEN and HF_SPACE_ID in the environment (or .env).
Free personal accounts can only host Gradio Spaces on ZeroGPU hardware, so that
is the default; set HF_SPACE_HARDWARE=cpu-basic if your account has PRO.
The Space is private unless HF_SPACE_PUBLIC=true (needed for others to open it).
Only source files are uploaded: neither runtime logs nor Git history are sent.
"""
import os
import time
from pathlib import Path
from huggingface_hub import HfApi
from agent import get_key

ROOT = Path(__file__).resolve().parent
ALLOW = ["README.md", "app.py", "agent.py", "budget.py", "requirements.txt", "me/**"]


def main():
    token, repo_id = os.getenv("HF_TOKEN"), os.getenv("HF_SPACE_ID")
    if not token or not repo_id or "/" not in repo_id:
        raise SystemExit("Set HF_TOKEN and HF_SPACE_ID=username/space-name in your environment. See README for manual steps.")
    hardware = os.getenv("HF_SPACE_HARDWARE", "zero-a10g")
    private = os.getenv("HF_SPACE_PUBLIC", "false").lower() != "true"
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="gradio", private=private,
                    space_hardware=hardware, exist_ok=True)
    api.add_space_secret(repo_id=repo_id, key="GEMINI_API_KEY", value=get_key())
    api.add_space_variable(repo_id=repo_id, key="GRADIO_SERVER_NAME", value="0.0.0.0")
    api.add_space_variable(repo_id=repo_id, key="API_BUDGET_USD", value="1.00")
    api.upload_folder(repo_id=repo_id, repo_type="space", folder_path=str(ROOT), allow_patterns=ALLOW)
    url = f"https://huggingface.co/spaces/{repo_id}"
    print(f"Uploaded source files ({hardware}, {'private' if private else 'public'}):", url)
    # Bounded polling; never upgrades hardware or purchases storage.
    for _ in range(40):
        runtime = api.get_space_runtime(repo_id=repo_id)
        if runtime.stage == "RUNNING":
            from gradio_client import Client
            answer = Client(repo_id, hf_token=token).predict(
                message="What are your office hours?", api_name="/chat")
            if not isinstance(answer, str) or not answer.strip():
                raise SystemExit("Space is running but its chat response was empty.")
            print("Live chat response:", answer)
            print("Verified Space:", url)
            return
        if runtime.stage in ("BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR"):
            raise SystemExit(f"Space reported {runtime.stage}; inspect its build logs.")
        time.sleep(15)
    raise SystemExit("Upload complete; build is still pending. Inspect the Space URL.")


if __name__ == "__main__":
    main()
