from ward import test, using
import httpx

from tests.fixtures import thoughtspot


PARAMETERS = {
    'list_viz_headers': {
        'id': 'bf2b2c6d-d29d-49f3-814c-00a3c40e77b0'
    },
    'list_object_headers': {
        'type': 'LOGICAL_TABLE',
        'subtypes': ['WORKSHEET', 'USER_DEFINED']
    }
}


for endpoint, data in PARAMETERS.items():

    @test('model adheres to contract: metadata.{endpoint}', tags=['unit'])
    @using(ts=thoughtspot)
    def _(ts, endpoint=endpoint):
        data = PARAMETERS[endpoint]
        meth = getattr(ts._rest_api.metadata, endpoint)
        resp = meth(**data)
        assert resp.status_code == httpx.codes.OK
