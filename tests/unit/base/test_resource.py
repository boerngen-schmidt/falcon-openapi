# MIT License

# Copyright (c) 2016 Diogo Dutra

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from myreco.base.resource import FalconModelResource, FalconJsonSchemaResource
from falcon.errors import HTTPMethodNotAllowed, HTTPNotFound
from falcon import HTTP_CREATED, HTTP_NO_CONTENT
from unittest import mock

import pytest


@pytest.fixture
def api():
    return mock.MagicMock()


@pytest.fixture
def model():
    return mock.MagicMock(tablename='test', id_name='id_test')


@pytest.fixture
def resource(api, model):
    return FalconModelResource(api, [], model)


class TestFalconModelResource(object):
    def test_if_init_register_routes_corretly(self, api, resource):
        assert api.add_route.call_args_list == [
            mock.call('/test/', resource),
            mock.call('/test/{id_test}/', resource)
        ]

    def test_if_init_register_routes_corretly_with_api_prefix(self, model, api):
        resource = FalconModelResource(api, [], model, '/testing')

        assert api.add_route.call_args_list == [
            mock.call('/testing/test/', resource),
            mock.call('/testing/test/{id_test}/', resource)
        ]

    def test_on_post_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_post(mock.MagicMock(), mock.MagicMock())

    def test_on_put_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_put(mock.MagicMock(), mock.MagicMock())

    def test_on_patch_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_patch(mock.MagicMock(), mock.MagicMock())

    def test_on_delete_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_delete(mock.MagicMock(), mock.MagicMock())

    def test_on_get_raises_method_not_allowed(self, resource):
        with pytest.raises(HTTPMethodNotAllowed):
            resource.on_get(mock.MagicMock(), mock.MagicMock())


class TestFalconModelResourcePost(object):
    def test_on_post_with_id_raises_not_found(self, model, api):
        resource = FalconModelResource(api, ['post'], model)

        with pytest.raises(HTTPNotFound):
            resource.on_post(mock.MagicMock(), mock.MagicMock(), id_test=1)

    def test_on_post_created_with_object(self, model, api):
        model.insert.return_value = [{'id_test': 1}]
        resource = FalconModelResource(api, ['post'], model, '/testing')
        resp = mock.MagicMock()
        req = mock.MagicMock()
        req.context = {'body': {}, 'session': mock.MagicMock()}

        resource.on_post(req, resp)

        assert resp.status == HTTP_CREATED
        assert resp.body == {'id_test': 1}

    def test_on_post_created_with_list(self, model, api):
        model.insert.return_value = [{'id_test': 1}]
        resource = FalconModelResource(api, ['post'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()
        req.context = {'body': [], 'session': mock.MagicMock()}

        resource.on_post(req, resp)

        assert resp.status == HTTP_CREATED
        assert resp.body == [{'id_test': 1}]

    def test_on_post_with_id_raises_not_found(self, model, api):
        model.update.return_value = []
        resource = FalconModelResource(api, ['post'], model)

        with pytest.raises(HTTPNotFound):
            resource.on_post(mock.MagicMock(), mock.MagicMock(), id_test=1)


class TestFalconModelResourcePut(object):
    def test_on_put_with_update_no_result_raises_not_found(self, model, api):
        model.update.return_value = []
        resource = FalconModelResource(api, ['put'], model)

        with pytest.raises(HTTPNotFound):
            resource.on_put(mock.MagicMock(), mock.MagicMock())

    def test_on_put_created(self, model, api):
        model.update.return_value = []
        model.insert.return_value = [{'id_test': 1}]
        resource = FalconModelResource(api, ['put'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        resource.on_put(req, resp, id_test=1)

        assert resp.status == HTTP_CREATED
        assert resp.body == 1

    def test_on_put_with_id(self, model, api):
        model.update.return_value = [1]
        resource = FalconModelResource(api, ['put'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        resource.on_put(req, resp, id_test=1)
        assert resp.body == 1

    def test_on_put_with_list(self, model, api):
        model.update.return_value = [1]
        resource = FalconModelResource(api, ['put'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        resource.on_put(req, resp)
        assert resp.body == [1]


class TestFalconModelResourcePatch(object):
    def test_on_patch_with_update_no_result_raises_not_found(self, model, api):
        model.update.return_value = []
        resource = FalconModelResource(api, ['patch'], model)

        with pytest.raises(HTTPNotFound):
            resource.on_patch(mock.MagicMock(), mock.MagicMock())

    def test_on_patch_with_id(self, model, api):
        model.update.return_value = [1]
        resource = FalconModelResource(api, ['patch'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        resource.on_patch(req, resp, id_test=1)
        assert resp.body == 1

    def test_on_patch_with_id_no_result_found(self, model, api):
        model.update.return_value = []
        resource = FalconModelResource(api, ['patch'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        with pytest.raises(HTTPNotFound):
            resource.on_patch(req, resp, id_test=1)

    def test_on_patch_with_list(self, model, api):
        model.update.return_value = [1]
        resource = FalconModelResource(api, ['patch'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        resource.on_patch(req, resp)
        assert resp.body == [1]


class TestFalconModelResourceDelete(object):
    def test_on_delete_with_id(self, model, api):
        resource = FalconModelResource(api, ['delete'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        resource.on_delete(req, resp, id_test=1)
        assert resp.status == HTTP_NO_CONTENT

    def test_on_delete_with_list(self, model, api):
        resource = FalconModelResource(api, ['delete'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        resource.on_delete(req, resp)
        assert resp.status == HTTP_NO_CONTENT


class TestFalconModelResourceGet(object):
    def test_on_get_with_no_result_raises_not_found(self, model):
        model.get.return_value = []
        resource = FalconModelResource(mock.MagicMock(), ['get'], model)

        with pytest.raises(HTTPNotFound):
            resource.on_get(mock.MagicMock(), mock.MagicMock())

    def test_on_get_with_id(self, model, api):
        model.get.return_value = [{'id_test': 1}]
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        resource.on_get(req, resp, id_test=1)
        assert resp.body == {'id_test': 1}

    def test_on_get_with_id_raises_not_found(self, model, api):
        model.get.return_value = []
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        with pytest.raises(HTTPNotFound):
            resource.on_get(req, resp, id_test=1)

    def test_on_get_with_list(self, model, api):
        model = mock.MagicMock(tablename='test', id_name='id_test')
        model.get.return_value = [{'id_test': 1}]
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        resource.on_get(req, resp)
        assert resp.body == [{'id_test': 1}]

    def test_on_get_with_list_raises_not_found(self, model, api):
        model = mock.MagicMock(tablename='test', id_name='id_test')
        model.get.return_value = []
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock()

        with pytest.raises(HTTPNotFound):
            resource.on_get(req, resp)

    def test_on_get_without_id_and_body(self, model, api):
        model = mock.MagicMock(tablename='test', id_name='id_test')
        model.get.return_value = [{'id_test': 1}]
        resource = FalconModelResource(api, ['get'], model)
        resp = mock.MagicMock()
        req = mock.MagicMock(context={'body': {}, 'session': mock.MagicMock()})

        resource.on_get(req, resp)
        assert resp.body == [{'id_test': 1}]


class TestFalconJsonSchemaResource(object):
    def test_build_post_validator(self):
        resource = FalconJsonSchemaResource(post_input_json_schema={'type': 'object'})
        assert hasattr(resource, 'on_post_validator')

    def test_build_put_validator(self):
        resource = FalconJsonSchemaResource(put_input_json_schema={'type': 'object'})
        assert hasattr(resource, 'on_put_validator')

    def test_build_patch_validator(self):
        resource = FalconJsonSchemaResource(patch_input_json_schema={'type': 'object'})
        assert hasattr(resource, 'on_patch_validator')

    def test_build_delete_validator(self):
        resource = FalconJsonSchemaResource(delete_input_json_schema={'type': 'object'})
        assert hasattr(resource, 'on_delete_validator')

    def test_build_get_validator(self):
        resource = FalconJsonSchemaResource(get_input_json_schema={'type': 'object'})
        assert hasattr(resource, 'on_get_validator')
