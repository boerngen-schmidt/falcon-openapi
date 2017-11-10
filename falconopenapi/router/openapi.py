from falcon.constants import HTTP_METHODS
from falcon.routing import CompiledRouter, create_http_method_map
from falconopenapi import OpenApiDefinition
from falconopenapi.exceptions import OpenApiError

import importlib


class OpenApiRouter(CompiledRouter):
    """ OpenAPI Router Class which extends falcon's CompiledRouter

    Reads the OpenAPI definition of the project and adds the defined routes to the compiled router.
    """
    def __init__(self, definition: OpenApiDefinition):
        CompiledRouter.__init__(self)

        self.definition = definition
        self.resources = dict()

        for path in definition.paths:
            self.add_route(path, self._lookup_resource(path))
        #check if file exists
        # read the Json or Yaml file
        # iterate over the read definitions
        # add route and validation

    def _lookup_resource(self, path):
        if path in self.resources:
            return self.resources[path]

        resources = set()

        # find all resources for a given path which should be encoded in the operationId
        for method in HTTP_METHODS:
            if method.lower() in self.definition[path]:
                if 'operationId' not in self.definition[path][method.lower()]:
                    raise OpenApiError('Elemten operationId was not found for path: ' + path + " method: " + method.lower())
                # set ignores duplicates
                resources.add(self.definition[path][method.lower()]['operationId'])

        for resource in resources:
            package, obj = resource.rsplit('.', 1)
            mod = importlib.import_module(package)
            if not hasattr(mod, obj):
                raise OpenApiError("Resource '" + resource + "' has not been found.")
            cls = getattr(mod, obj)
            zemap = create_http_method_map(cls)