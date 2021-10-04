from ward import test, using
import httpx

from tests.fixtures import thoughtspot


PARAMETERS = {
    'metadata': {
        'list_viz_headers': {
            'id': 'bf2b2c6d-d29d-49f3-814c-00a3c40e77b0'
        },
        'list_object_headers': {
            'type': 'LOGICAL_TABLE',
            'subtypes': ['WORKSHEET', 'USER_DEFINED']
        }
    },
    '_metadata': {
        'list': {},
        'listas': {},
        'detail': {},
        'delete': {},
        'list_columns': {}
    }
}


for family, tests in PARAMETERS.items():
    for endpoint, data in tests.items():

        @test('model adheres to contract: {family}.{endpoint}', tags=['unit'])
        @using(ts=thoughtspot)
        def _(ts, family=family, endpoint=endpoint, data=data):
            apis = getattr(ts._rest_api, family)
            meth = getattr(apis, endpoint)
            resp = meth(**data)
            assert resp.status_code == httpx.codes.OK
