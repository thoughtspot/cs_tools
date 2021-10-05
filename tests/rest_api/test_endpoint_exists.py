from ward import test, using
import httpx

from tests.fixtures import thoughtspot


PARAMETERS = {
    'public': [
        ('GET', 'metadata/listvizheaders'),
        ('GET', 'metadata/listobjectheaders'),
        ('GET', 'user/list'),
        ('POST', 'user/transfer/ownership')
    ],
    'private': [
        ('GET', 'metadata/list'),
        ('GET', 'metadata/listas'),
        ('GET', 'metadata/detail/this-is-a-fake-guid'),
        ('POST', 'metadata/delete'),
        ('GET', 'metadata/listcolumns/this-is-a-fake-guid'),
        ('GET', 'session/group/listuser/this-is-a-fake-guid'),
        ('GET', 'session/group/listgroup/this-is-a-fake-guid'),
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
        # TODO:
        #   if this is a cloud environment, then we need to xfail on tsload cmds.

        @test('endpoint exists: {method: <4} {privacy: >11} {endpoint}', tags=['unit', 'exists'])
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
                    r = ts._rest_api.request(method, endpoint, privacy=privacy, timeout=3)
                    status = r.status_code
                    break
                except httpx.ConnectTimeout:
                    status = 504
                except httpx.HTTPError as exc:
                    status = exc.response.status_code

            assert status != 404
