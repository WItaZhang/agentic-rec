"""Real local Transformers backend; actual input/output tensor counts, no character proxy."""

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CompletionResult:
    text: str
    status: str
    input_tokens: int | None
    output_tokens: int | None
    elapsed_ms: float
    cpu_seconds: float
    finish_reason: str
    usage_source: str
    error: str | None = None


class LocalTransformersLLM:
    def __init__(self, config, root):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if config["provider"] != "local_transformers" or config["device"] != "cpu":
            raise ValueError("This backend only authorizes local CPU inference")
        if config["dtype"] != "float32" or config["temperature"] != 0:
            raise ValueError("This experiment fixes float32 greedy decoding")
        torch.set_num_threads(config["cpu_threads"])
        torch.set_num_interop_threads(config["interop_threads"])
        torch.manual_seed(config["seed"])
        path = root / config["model_path"]
        self.config = config
        started, cpu_started = time.perf_counter(), time.process_time()
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        self.model = AutoModelForCausalLM.from_pretrained(
            path, local_files_only=True, trust_remote_code=False, torch_dtype=torch.float32,
            attn_implementation="sdpa").eval()
        self.setup = {"wall_seconds": time.perf_counter() - started,
                      "cpu_seconds": time.process_time() - cpu_started}

    def truncate(self, text, token_limit):
        ids = self.tokenizer.encode(str(text or ""), add_special_tokens=False)
        return self.tokenizer.decode(ids[:token_limit]), len(ids) > token_limit

    def encode_messages(self, messages):
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        return self.tokenizer(text, return_tensors="pt", add_special_tokens=False)

    def complete(self, encoded):
        import torch

        n_input = int(encoded["input_ids"].shape[-1])
        start, cpu_start = time.perf_counter(), time.process_time()
        try:
            with torch.inference_mode():
                output = self.model.generate(
                    **encoded, do_sample=False, max_new_tokens=self.config["max_output_tokens"],
                    max_time=self.config["timeout_seconds"],
                    pad_token_id=self.tokenizer.eos_token_id, use_cache=True,
                    logits_to_keep=1)
            generated = output[0, n_input:]
            elapsed = time.perf_counter() - start
            n_output = int(generated.numel())
            timed_out = elapsed > self.config["timeout_seconds"]
            finish = "timeout" if timed_out else (
                "length" if n_output >= self.config["max_output_tokens"] else "eos")
            return CompletionResult(
                self.tokenizer.decode(generated, skip_special_tokens=True),
                "timeout" if timed_out else "success", n_input, n_output,
                elapsed * 1000, time.process_time() - cpu_start, finish, "local_token_tensors")
        except Exception as error:
            # Generation may have performed work before failing. Do not invent token usage.
            return CompletionResult("", "generation_error", n_input, None,
                                    (time.perf_counter() - start) * 1000,
                                    time.process_time() - cpu_start, "error", "partially_unavailable",
                                    f"{type(error).__name__}: {error}")
