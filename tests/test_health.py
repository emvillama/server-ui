def test_health_returns_ok_and_ollama_flag(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # Don't assert True/False specifically -- whether the real Ollama
    # server is reachable depends on the network this test runs on.
    assert isinstance(body["ollama_reachable"], bool)