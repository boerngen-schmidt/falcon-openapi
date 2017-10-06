from falcon.routing import CompiledRouter


class OpenapiRouter(CompiledRouter):
    """ OpenAPI Router Class which extends falcon's CompiledRouter

    Reads the OpenAPI definition of the project and adds the defined routes to the compiled router.
    """
    def __init__(self, file):
        CompiledRouter.__init__(self)

        #check if file exists
        # read the Json or Yaml file
        # iterate over the read definitions
        # add route and validation
