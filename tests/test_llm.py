"""The provider seam. Nothing here touches the network.

The HTTP call is stubbed rather than recorded, because the point is to pin the
request shape we send Fireworks and the way its reply is unpacked -- both of
which are ours to get wrong.
"""

from __future__ import annotations

import pytest

from core import llm


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError(f"unhandled status {self.status_code}")


# --- choosing a provider ----------------------------------------------------


def test_no_keys_means_no_provider():
    assert llm.provider() == ""
    assert llm.available() is False


def test_a_fireworks_key_selects_fireworks(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    assert llm.provider() == "fireworks"
    assert llm.available() is True


def test_an_anthropic_key_selects_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert llm.provider() == "anthropic"
    assert llm.available() is True


def test_the_cheaper_provider_wins_when_both_keys_are_set(monkeypatch):
    """Documented in PROVIDERS' ordering, so it is a decision and not an accident."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    assert llm.provider() == "fireworks"


def test_an_explicit_provider_overrides_the_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    monkeypatch.setenv("EDUBOT_PROVIDER", "anthropic")
    assert llm.provider() == "anthropic"


def test_an_unknown_provider_is_refused_loudly(monkeypatch):
    """Silently falling back would look like the key was wrong."""
    monkeypatch.setenv("EDUBOT_PROVIDER", "ollama")
    with pytest.raises(ValueError, match="ollama"):
        llm.provider()


# --- choosing a model -------------------------------------------------------


def test_each_provider_has_its_own_default_model(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    assert llm.model() == llm.PROVIDERS["fireworks"]["model"]

    monkeypatch.setenv("EDUBOT_PROVIDER", "anthropic")
    assert llm.model() == llm.PROVIDERS["anthropic"]["model"]


def test_edubot_model_overrides_any_provider_default(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    monkeypatch.setenv("EDUBOT_MODEL", "accounts/fireworks/models/something-else")
    assert llm.model() == "accounts/fireworks/models/something-else"


def test_asking_for_a_model_with_no_provider_fails_clearly():
    with pytest.raises(RuntimeError, match="no provider configured"):
        llm.model()


def test_saying_something_with_no_provider_fails_clearly():
    with pytest.raises(RuntimeError, match="no provider configured"):
        llm.say("system", "user")


# --- the Fireworks request --------------------------------------------------

REPLY = {"choices": [{"message": {"content": "  What have you tried so far?  "}}]}


def test_fireworks_sends_the_openai_chat_shape(monkeypatch):
    sent = {}

    def fake_post(url, **kwargs):
        sent["url"] = url
        sent.update(kwargs)
        return FakeResponse(REPLY)

    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    monkeypatch.setattr("httpx2.post", fake_post)

    assert llm.say("be a tutor", "2x = 4") == "What have you tried so far?"

    assert sent["url"] == f"{llm.FIREWORKS_URL}/chat/completions"
    assert sent["headers"]["Authorization"] == "Bearer fw-test"
    body = sent["json"]
    assert body["model"] == llm.PROVIDERS["fireworks"]["model"]
    assert body["max_tokens"] == llm.MAX_TOKENS
    # The system prompt travels as a message here, not as its own argument.
    assert body["messages"] == [
        {"role": "system", "content": "be a tutor"},
        {"role": "user", "content": "2x = 4"},
    ]


def test_fireworks_uses_the_overridden_model(monkeypatch):
    sent = {}
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    monkeypatch.setenv("EDUBOT_MODEL", "accounts/fireworks/models/chosen-by-hand")
    monkeypatch.setattr("httpx2.post", lambda url, **kw: (sent.update(kw), FakeResponse(REPLY))[1])

    llm.say("s", "u")
    assert sent["json"]["model"] == "accounts/fireworks/models/chosen-by-hand"


@pytest.mark.parametrize("status", [400, 404])
def test_a_retired_model_id_gets_an_error_that_says_so(monkeypatch, status):
    """Fireworks retires serverless models, and its own message does not explain."""
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    monkeypatch.setattr("httpx2.post", lambda url, **kw: FakeResponse({}, status))

    with pytest.raises(RuntimeError, match="core.models"):
        llm.say("s", "u")
