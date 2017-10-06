import yaml


class OpenApiReference(yaml.YAMLObject):
    yaml_tag = u'$ref'
    def __init__(self, ref):
        self._ref = ref

    def __repr__(self):
        return "$ref: %s" % self._ref


with open("petstore-expanded.yaml", "r") as stream:
    try:
        spec = yaml.load(stream)
        print(spec)
    except yaml.YAMLError as e:
        print(e)
