from ward import test, using
import httpx

from tests.fixtures import thoughtspot


PARAMETERS = {
    'public': [
        ('GET', 'metadata/listvizheaders'),
        ('GET', 'metadata/listobjectheaders'),
    ],
    'private': [
        ('GET', 'metadata/list'),
        ('GET', 'metadata/listas'),
        ('GET', 'metadata/detail/this-is-a-fake-guid'),
        ('POST', 'metadata/delete'),
        ('GET', 'metadata/listcolumns/this-is-a-fake-guid'),
    ],
    'dataservice': [
        ('GET', 'tql/tokens/static'),
        ('GET', 'tql/tokens/dynamic'),
        ('POST', 'tql/query'),
        ('POST', 'tql/script'),
        ('POST', 'tsload/session'),
        ('POST', 'tsload/loads'),
        ('POST', 'tsload/loads/this-is-a-fake-cycle-id'),
        ('POST', 'tsload/loads/this-is-a-fake-cycle-id/commit'),
        ('GET', 'tsload/loads/this-is-a-fake-cycle-id'),
    ]
}


for privacy, endpoints in PARAMETERS.items():
    for method, endpoint in endpoints:

        @test('endpoint exists: {method} {endpoint} ({privacy})', tags=['unit', 'exists'])
        @using(ts=thoughtspot)
        def _(ts, method=method, endpoint=endpoint, privacy=privacy):
            # handle tsload being located at resource port 8442
            if endpoint.startswith('tsload'):
                endpoint = endpoint.replace('tsload', ts._rest_api.ts_dataservice.etl_server_fullpath)

            # HEAD usually is enough to handle detecting if a resource exists at a given
            # path, but if the POST endpoint accepts form data, then HTML disallows this
            # so we'll have to try with the intended method instead.
            for meth in ('HEAD', method):
                try:
                    r = ts._rest_api.request(method, endpoint, privacy=privacy)
                    break
                except httpx.HTTPError as exc:
                    r = exc.response

            assert r.status_code != 404
