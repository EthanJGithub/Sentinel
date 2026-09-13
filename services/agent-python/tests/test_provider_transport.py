import httpx
from app.providers.vendors import GroqProvider


def test_groq_uses_httpx_and_records_actual_usage():
    provider = GroqProvider('local-test-key')
    provider._client.close()
    def handle(request):
        assert request.url.path.endswith('/chat/completions')
        return httpx.Response(200, json={'choices':[{'message':{'content':'Evidence reviewed'}}], 'usage':{'prompt_tokens':12,'completion_tokens':3}})
    provider._client = httpx.Client(transport=httpx.MockTransport(handle), base_url='https://example.test/')
    result = provider.complete(system='review', prompt='evidence', model='test')
    assert result.text == 'Evidence reviewed'
    assert result.tokens_in == 12 and result.tokens_out == 3
    provider._client.close()
