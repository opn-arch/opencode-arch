from __future__ import annotations
import hashlib, json, time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CachedResult:
    output: str
    model: str
    prompt_hash: str
    content_hash: str
    cached: bool
    timestamp: str


class LLMCache:
    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / ".opencode-arch" / "llm-cache"

    def get(self, content_hash: str, prompt_hash: str) -> CachedResult | None:
        """Look up cached result by content + prompt hash."""
        path = self._path(content_hash, prompt_hash)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return CachedResult(**data, cached=True)

    def put(self, content_hash: str, prompt_hash: str, output: str, model: str) -> None:
        """Store result in cache."""
        path = self._path(content_hash, prompt_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "output": output,
            "model": model,
            "prompt_hash": prompt_hash,
            "content_hash": content_hash,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        path.write_text(json.dumps(data))

    def clear(self) -> int:
        """Remove all cached results. Returns count deleted."""
        count = 0
        if self.cache_dir.exists():
            for f in self.cache_dir.rglob("*.json"):
                f.unlink()
                count += 1
        return count

    def _path(self, content_hash: str, prompt_hash: str) -> Path:
        combined = hashlib.sha256(f"{content_hash}:{prompt_hash}".encode()).hexdigest()
        return self.cache_dir / combined[:2] / f"{combined}.json"


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def cached_llm_call(
    runner,  # RunnerBackend
    prompt: str,
    content_hash: str,
    prompt_template_hash: str,
    repo_path: str,
    cache: LLMCache | None = None,
) -> CachedResult:
    """Call LLM via runner, with caching."""
    if cache is not None:
        hit = cache.get(content_hash, prompt_template_hash)
        if hit is not None:
            return hit

    result = await runner.run(prompt, repo_path)

    cached_result = CachedResult(
        output=result.output,
        model="unknown",
        prompt_hash=prompt_template_hash,
        content_hash=content_hash,
        cached=False,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    if cache is not None:
        cache.put(content_hash, prompt_template_hash, result.output, "unknown")

    return cached_result
