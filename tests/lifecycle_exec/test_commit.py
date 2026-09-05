import subprocess
from opencode_arch.lifecycle_exec.commit import build_trailers

def test_trailers_parseable_by_git():
    block = build_trailers(
        issue_id=42, comment_id="c-1", session_id="s-1",
        revision_from="0000042", revision_to="0000043",
        model_diff_digest="sha256:abc", provider="frontier/claude-4.7",
    )
    r = subprocess.run(
        ["git", "interpret-trailers", "--parse"],
        input=f"subject\n\n{block}\n", capture_output=True, text=True,
    )
    assert r.returncode == 0
    lines = r.stdout.strip().splitlines()
    assert "Issue: logs-db#42" in lines
    assert "Comment: c-1" in lines
    assert "Session: s-1" in lines
    assert "Model-Revision-From: 0000042" in lines
    assert "Model-Revision-To: 0000043" in lines
    assert "Model-Diff-Digest: sha256:abc" in lines
    assert "Provider: frontier/claude-4.7" in lines

def test_optional_provider_absent():
    block = build_trailers(
        issue_id=1, comment_id="c", session_id="s",
        revision_from="0000001", revision_to="0000002",
        model_diff_digest="sha256:0",
    )
    assert "Provider:" not in block
