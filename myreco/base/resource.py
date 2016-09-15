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


from jsonschema import Draft4Validator
from falcon.errors import HTTPMethodNotAllowed, HTTPNotFound
from falcon import HTTP_CREATED, HTTP_NO_CONTENT
from myreco.base.session import Session
from myreco.exceptions import JSONError
from importlib import import_module
from glob import glob
from re import match as re_match

import os.path
import json


class FalconJsonSchemaResource(object):
    def __init__(
            self, post_input_json_schema={},
            post_output_json_schema={},
            put_input_json_schema={},
            put_output_json_schema={},
            patch_input_json_schema={},
            patch_output_json_schema={},
            delete_input_json_schema={},
            delete_output_json_schema={},
            get_input_json_schema={},
            get_output_json_schema={}):
        self.post_input_json_schema = post_input_json_schema
        self.post_output_json_schema = post_output_json_schema
        self.put_input_json_schema = put_input_json_schema
        self.put_output_json_schema = put_output_json_schema
        self.patch_input_json_schema = patch_input_json_schema
        self.patch_output_json_schema = patch_output_json_schema
        self.delete_input_json_schema = delete_input_json_schema
        self.delete_output_json_schema = delete_output_json_schema
        self.get_input_json_schema = get_input_json_schema
        self.get_output_json_schema = get_output_json_schema

        if post_input_json_schema:
            self.on_post_validator = Draft4Validator(post_input_json_schema)

        if put_input_json_schema:
            self.on_put_validator = Draft4Validator(put_input_json_schema)

        if patch_input_json_schema:
            self.on_patch_validator = Draft4Validator(patch_input_json_schema)

        if delete_input_json_schema:
            self.on_delete_validator = Draft4Validator(delete_input_json_schema)

        if get_input_json_schema:
            self.on_get_validator = Draft4Validator(get_input_json_schema)


class FalconModelResource(FalconJsonSchemaResource):
    def __init__(self, api, allowed_methods, model, api_prefix='/', **kwargs):
        self.allowed_methods = [am.upper() for am in allowed_methods]
        self.model = model
        self._add_route(api, api_prefix)
        FalconJsonSchemaResource.__init__(self, **self._build_schemas(kwargs))

    def _add_route(self, api, api_prefix):
        uri = uri_single = os.path.join(api_prefix, '{}/'.format(self.model.tablename))

        for id_name in self.model.id_names:
            uri_single += '{' + id_name + '}/'

        api.add_route(uri, self)
        api.add_route(uri_single, self)

    def _build_schemas(self, user_schemas):
        schemas = user_schemas
        module_filename = import_module(type(self).__module__).__file__
        module_path = os.path.dirname(os.path.abspath(module_filename))
        schemas_path = os.path.join(module_path, 'schemas')
        schemas_glob = os.path.join(schemas_path, '*.json')
        schema_regex = '(post|put|patch|delete|get)_(input|output).json'

        for json_schema_filename in glob(schemas_glob):
            json_schema_basename = os.path.basename(json_schema_filename)
            if re_match(schema_regex, json_schema_basename):
                with open(json_schema_filename) as json_schema_file:
                    schema_name = json_schema_basename.replace('.json', '_json_schema')
                    schemas[schema_name] = json.load(json_schema_file)

        return schemas

    def on_post(self, req, resp, **kwargs):
        self._raise_method_not_allowed('POST')

        if self._id_names_in_kwargs(kwargs):
            raise HTTPNotFound()

        session = req.context['session']
        resp.body = self.model.insert(session, req.context['body'])
        resp.body = resp.body if isinstance(req.context['body'], list) else resp.body[0]
        resp.status = HTTP_CREATED

    def _id_names_in_kwargs(self, kwargs):
        return bool([True for id_name in self.model.id_names if id_name in kwargs])

    def _raise_method_not_allowed(self, method):
        if not method in self.allowed_methods:
            raise HTTPMethodNotAllowed(self.allowed_methods)

    def on_put(self, req, resp, **kwargs):
        self._update(req, resp, **kwargs)

    def _update(self, req, resp, with_insert=True, **kwargs):
        self._raise_method_not_allowed(req.method.upper())
        session = req.context['session']

        if self._id_names_in_kwargs(kwargs):
            id_ = self.model.get_ids_from_values(kwargs)
            id_dict = self.model.build_id_dict(id_)
            req.context['body'].update(id_dict)
            ids = self.model.update(session, req.context['body'])

            if not ids and with_insert:
                id_ = self.model.insert(session, req.context['body'])[0]
                resp.status = HTTP_CREATED
            elif ids:
                id_ = ids[0]
            else:
                raise HTTPNotFound()

            resp.body = id_

        else:
            ids = self.model.update(session, req.context['body'])

            if ids:
                resp.body = ids
            else:
                raise HTTPNotFound()

    def on_patch(self, req, resp, **kwargs):
        self._update(req, resp, with_insert=False, **kwargs)

    def on_delete(self, req, resp, **kwargs):
        self._raise_method_not_allowed('DELETE')
        session = req.context['session']

        if self._id_names_in_kwargs(kwargs):
            id_ = self.model.get_ids_from_values(kwargs)
            self.model.delete(session, id_)
        else:
            self.model.delete(session, req.context['body'])

        resp.status = HTTP_NO_CONTENT

    def on_get(self, req, resp, **kwargs):
        self._raise_method_not_allowed('GET')
        session = req.context['session']

        if self._id_names_in_kwargs(kwargs):
            id_ = self.model.get_ids_from_values(kwargs)
            resp.body = self.model.get(session, id_)
            if resp.body:
                resp.body = resp.body[0]

        elif req.context['body']:
            resp.body = self.model.get(session, req.context['body'])

        else:
            resp.body = self.model.get(session)

        if not resp.body:
            raise HTTPNotFound()
