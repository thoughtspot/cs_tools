from ward import test, using
import httpx

from tests.fixtures import thoughtspot


PARAMETERS = {
    'tokens_static': {},
    'tokens_dynamic': {},
    'query': {
        'data': {
            'context': {
                'schema': 'falcon_default_schema',
                'server_schema_version': -1
            },
            'query': {
                'statement': 'SHOW DATABASES;'
            }
        }
    },
    'script': {
        'data': {
            'context': {
                'schema': 'falcon_default_schema',
                'server_schema_version': -1
            },
            'script_type': 1,
            'script': 'SHOW DATABASES;'
        }
    }
}


for endpoint, data in PARAMETERS.items():

    @test('model adheres to contract: ts_dataservice.{endpoint}', tags=['unit'])
    @using(ts=thoughtspot)
    def _(ts, endpoint=endpoint):
        data = PARAMETERS[endpoint]
        meth = getattr(ts._rest_api.ts_dataservice, endpoint)
        resp = meth(**data)
        assert resp.status_code == httpx.codes.OK
