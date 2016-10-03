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


from myreco.exceptions import ModelBaseError, JSONError
from falcon.errors import HTTPNotFound, HTTPMethodNotAllowed
from falcon import HTTP_CREATED, HTTP_NO_CONTENT
from jsonschema import RefResolver, Draft4Validator, ValidationError
from collections import defaultdict
from copy import deepcopy
from importlib import import_module
import json
import os.path


def get_dir_path(filename):
    return os.path.dirname(os.path.abspath(filename))


def get_model_schema(filename):
    return json.load(open(os.path.join(get_dir_path(filename), 'schema.json')))


def build_validator(schema, path):
    handlers = {'': URISchemaHandler(path)}
    resolver = RefResolver.from_schema(schema, handlers=handlers)
    return Draft4Validator(schema, resolver=resolver)


class BaseModelOperationMeta(type):

    def _get_context_values(cls, context):
        session = context['session']
        parameters = context['parameters']
        req_body = parameters['body']
        id_ = parameters['uri_template']
        kwargs = deepcopy(parameters['headers'])
        kwargs.update(parameters['query_string'])
        return session, req_body, id_, kwargs


class BaseModelPostMixinMeta(BaseModelOperationMeta):

    def post_by_body(cls, req, resp):
        cls._insert(req, resp)

    def _insert(cls, req, resp, with_update=False):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)

        if with_update:
            if isinstance(req_body, list):
                [cls._update_dict(obj, id_) for obj in req_body]
            elif isinstance(req_body, dict):
                cls._update_dict(req_body, id_)

        resp_body = cls.insert(session, req_body, **kwargs)
        resp_body = resp_body if isinstance(req_body, list) else resp_body[0]
        resp.body = json.dumps(resp_body)
        resp.status = HTTP_CREATED

    def _update_dict(cls, dict_, other):
        dict_.update({k: v for k, v in other.items() if k not in dict_})

    def post_by_uri_template(cls, req, resp):
        cls._insert(req, resp, with_update=True)


class BaseModelPutMixinMeta(BaseModelPostMixinMeta):

    def put_by_body(cls, req, resp):
        cls._update(req, resp)

    def _update(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        objs = cls.update(session, req_body, **kwargs)

        if objs:
            resp.body = json.dumps(objs)
        else:
            raise HTTPNotFound()

    def put_by_uri_template(cls, req, resp):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)
        req_body_copy = deepcopy(req_body)

        cls._update_dict(req_body, id_)
        objs = cls.update(session, req_body, ids=id_, **kwargs)

        if not objs:
            req_body = req_body_copy
            ambigous_keys = [
                kwa for kwa in id_ if kwa in req_body and str(req_body[kwa]) != id_[kwa]]
            if ambigous_keys:
                body_schema = req.context.get('body_schema')
                raise ValidationError(
                    "Ambiguous value for '{}'".format(
                        "', '".join(ambigous_keys)),
                    instance={'body': req_body, 'uri': id_}, schema=body_schema)

            req.context['parameters']['body'] = req_body
            cls._insert(req, resp, with_update=True)
        else:
            resp.body = json.dumps(objs[0])


class BaseModelPatchMixinMeta(BaseModelPutMixinMeta):

    def patch_by_body(cls, req, resp):
        cls._update(req, resp)

    def patch_by_uri_template(cls, req, resp):
        session, req_body, id_, kwargs = cls._get_context_values(req.context)

        cls._update_dict(req_body, id_)
        objs = cls.update(session, req_body, ids=id_, **kwargs)
        if objs:
            resp.body = json.dumps(objs[0])
        else:
            raise HTTPNotFound()


class BaseModelDeleteMixinMeta(BaseModelOperationMeta):

    def delete_by_body(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        cls.delete(session, req_body, **kwargs)
        resp.status = HTTP_NO_CONTENT

    def delete_by_uri_template(cls, req, resp):
        session, _, id_, kwargs = cls._get_context_values(req.context)

        cls.delete(session, id_, **kwargs)
        resp.status = HTTP_NO_CONTENT


class BaseModelGetMixinMeta(BaseModelOperationMeta):

    def get_by_body(cls, req, resp):
        session, req_body, _, kwargs = cls._get_context_values(req.context)

        if req_body:
            resp_body = cls.get(session, req_body, **kwargs)
        else:
            resp_body = cls.get(session, **kwargs)

        if not resp_body:
            raise HTTPNotFound()

        resp.body = json.dumps(resp_body)

    def get_by_uri_template(cls, req, resp):
        session, _, id_, kwargs = cls._get_context_values(req.context)

        resp_body = cls.get(session, id_, **kwargs)
        if not resp_body:
            raise HTTPNotFound()

        resp.body = json.dumps(resp_body[0])

    def get_schema(cls, req, resp):
        resp.body = json.dumps(cls.__schema__)


class URISchemaHandler(object):

    def __init__(self, schemas_path):
        self._schemas_path = schemas_path

    def __call__(self, uri):
        schema_filename = os.path.join(self._schemas_path, uri.replace('schema:', ''))
        with open(schema_filename) as json_schema_file:
            return json.load(json_schema_file)


class JsonBuilderMeta(type):

    def _type_builder(cls, type_):
        return getattr(cls, '_build_' + type_)

    def _build_string(cls, value):
        return str(value)

    def _build_number(cls, value):
        return float(value)

    def _build_boolean(cls, value):
        return bool(value)

    def _build_integer(cls, value):
        return int(value)

    def _build_array(cls, values, schema, nested_types, input_):
        if 'array' in nested_types:
            raise ModelBaseError('nested array was not allowed', input_=input_)

        if isinstance(values, list):
            new_values = []
            [new_values.extend(value.split(',')) for value in values]
            values = new_values
        else:
            values = values.split(',')

        items_schema = schema.get('items')
        if items_schema:
            nested_types.add('array')
            values = [cls._build_value(
                value, items_schema, nested_types, input_) for value in values]

        return values

    def _build_value(cls, value, schema, nested_types, input_):
        type_ = schema['type']
        if type_ == 'array' or type_ == 'object':
            return cls._type_builder(type_)(value, schema, nested_types, input_)

        return cls._type_builder(type_)(value)

    def _build_object(cls, value, schema, nested_types, input_):
        if 'object' in nested_types:
            raise ModelBaseError('nested object was not allowed', input_=input_)

        properties = value.split('|')
        dict_obj = dict()
        nested_types.add('object')
        for prop in properties:
            key, value = prop.split(':')
            dict_obj[key] = \
                cls._build_value(value, schema['properties'][key], nested_types, input_)

        nested_types.discard('object')
        return dict_obj


class JsonBuilder(metaclass=JsonBuilderMeta):

    def __new__(cls, json_value, schema):
        nested_types = set()
        input_ = deepcopy(json_value)
        return cls._build_value(json_value, schema, nested_types, input_)


SWAGGER_VALIDATOR = build_validator(
    {'$ref': 'swagger_schema_extended.json#/definitions/paths'},
    get_dir_path(__file__))
HTTP_METHODS = ('post', 'put', 'patch', 'delete', 'get', 'options', 'head')


class Operation(object):

    def __init__(self, action, schema, all_methods_parameters, definitions, model_dir):
        self._action = action
        self._body_validator = None
        self._uri_template_validator = None
        self._query_string_validator = None
        self._headers_validator = None
        self._model_dir = model_dir
        self._body_required = False
        self._has_body_parameter = False

        query_string_schema = self._build_default_schema()
        uri_template_schema = self._build_default_schema()
        headers_schema = self._build_default_schema()

        for parameter in all_methods_parameters + schema.get('parameters', []):
            if parameter['in'] == 'body':
                if definitions:
                    body_schema = deepcopy(parameter['schema'])
                    body_schema.update({'definitions': definitions})
                else:
                    body_schema = parameter['schema']

                self._body_validator = build_validator(body_schema, self._model_dir)
                self._body_required = parameter.get('required', False)
                self._has_body_parameter = True

            elif parameter['in'] == 'path':
                self._set_parameter_on_schema(parameter, uri_template_schema)

            elif parameter['in'] == 'query':
                self._set_parameter_on_schema(parameter, query_string_schema)

            elif parameter['in'] == 'header':
                self._set_parameter_on_schema(parameter, headers_schema)

        if uri_template_schema['properties']:
            self._uri_template_validator = build_validator(uri_template_schema, self._model_dir)

        if query_string_schema['properties']:
            self._query_string_validator = build_validator(query_string_schema, self._model_dir)

        if headers_schema['properties']:
            self._headers_validator = build_validator(headers_schema, self._model_dir)

    def _build_default_schema(self):
        return {'type': 'object', 'required': [], 'properties': {}}

    def _set_parameter_on_schema(self, parameter, schema):
        name = parameter['name']
        property_ = {'type': parameter['type']}

        if parameter['type'] == 'array':
            items = parameter.get('items', {})
            if items:
                property_['items'] = items

        if parameter['type'] == 'object':
            obj_schema = parameter.get('schema', {})
            if obj_schema:
                property_.update(obj_schema)

        if parameter.get('required'):
            schema['required'].append(name)

        schema['properties'][name] = property_

    def __call__(self, req, resp, **kwargs):
        body_params = self._build_body_params(req)
        query_string_params = self._build_non_body_params(self._query_string_validator, req.params)
        uri_template_params = self._build_non_body_params(self._uri_template_validator, kwargs)
        headers_params = self._build_non_body_params(self._headers_validator, req, 'headers')

        req.context['parameters'] = {
            'query_string': query_string_params,
            'uri_template': uri_template_params,
            'headers': headers_params,
            'body': body_params
        }
        if self._body_validator:
            req.context['body_schema'] = self._body_validator.schema
        self._action(req, resp)

    def _build_body_params(self, req):
        if req.content_length and (req.content_type is None or 'application/json' in req.content_type):
            if not self._has_body_parameter:
                raise ModelBaseError('Request body is not acceptable')

            body = req.stream.read().decode()
            try:
                body = json.loads(body)
            except ValueError as error:
                raise JSONError(*error.args, input_=body)

            if self._body_validator:
                self._body_validator.validate(body)

            return body

        elif self._body_required:
            raise ModelBaseError('Request body is missing')

        else:
            return None

        return req.stream

    def _build_non_body_params(self, validator, kwargs, type_=None):
        if validator:
            params = {}
            for param_name, prop in validator.schema['properties'].items():
                if type_ == 'headers':
                    param = kwargs.get_header(param_name)
                else:
                    param = kwargs.get(param_name)

                if param:
                    params[param_name] = JsonBuilder(param, prop)

            validator.validate(params)
            return params

        elif type_ == 'headers':
            return {}
        else:
            return kwargs


class ModelBaseRoutesMixinMeta(type):

    def __init__(cls, name, bases, attributes):
        cls.__routes__ = defaultdict(dict)
        cls.__key__ = getattr(cls, '__key__', cls.__name__.replace('Model', '').lower())
        cls.__allowed_methods__ = set()
        schema = attributes.get('__schema__')

        if schema:
            SWAGGER_VALIDATOR.validate(schema)
            cls._build_routes_from_schema(schema)

    def get_module_path(cls):
        module_filename = import_module(cls.__module__).__file__
        return get_dir_path(module_filename)

    def _build_routes_from_schema(cls, schema):
        for uri_template in schema:
            all_methods_parameters = schema[uri_template].get('parameters', [])
            for method_name in HTTP_METHODS:
                method = schema[uri_template].get(method_name)
                if method:
                    operation_id = method['operationId']
                    try:
                        action = getattr(cls, operation_id)
                    except AttributeError:
                        raise ModelBaseError("'operationId' '{}' was not found".format(operation_id))

                    definitions = schema.get('definitions')
                    operation = Operation(action, method, all_methods_parameters, definitions, cls.get_module_path())
                    cls.__routes__[uri_template][method_name] = operation
                    cls.__allowed_methods__.add(method_name.upper())

        cls.__routes__[cls._build_schema_uri_template()]['get'] = cls.get_schema

    def _build_schema_uri_template(cls):
        return '/' + cls.__key__ + '/_schema/'

    def on_post(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def _route(cls, req, resp, **kwargs):
        cls._raise_not_found(req, resp, **kwargs)
        cls._raise_method_not_allowed(req, resp, **kwargs)
        cls._add_schema_link(req, resp, **kwargs)
        cls.__routes__[req.uri_template][req.method.lower()](req, resp, **kwargs)

    def _raise_not_found(cls, req, resp, **kwargs):
        if not req.uri_template in cls.__routes__:
            raise HTTPNotFound()

    def _raise_method_not_allowed(cls, req, resp, **kwargs):
        if not req.method.lower() in cls.__routes__[req.uri_template]:
            raise HTTPMethodNotAllowed(cls.__allowed_methods__)

    def _add_schema_link(cls, req, resp, **kwargs):
        if hasattr(cls, '__schema__'):
            resp.add_link(cls._build_schema_uri_template(), 'schema')

    def on_put(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_patch(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_delete(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_get(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_options(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)

    def on_head(cls, req, resp, **kwargs):
        cls._route(req, resp, **kwargs)


class ModelBaseMeta(
        BaseModelPatchMixinMeta,
        BaseModelDeleteMixinMeta,
        BaseModelGetMixinMeta,
        ModelBaseRoutesMixinMeta):

    def _to_list(cls, objs):
        return objs if isinstance(objs, list) else [objs]

    def get_filters_names_key(cls):
        return cls.__key__ + '_filters_names'

    def get_key(cls, filters_names=None):
        if not filters_names or filters_names == cls.__key__:
            return cls.__key__

        return '{}_{}'.format(cls.__key__, filters_names)


class ModelBase(object):
    __session__ = None

    def get_key(self, id_names=None):
        return str(self.get_ids_values(id_names))
