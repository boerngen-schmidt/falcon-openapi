import json


class OpenApiReference(object):
    def __init__(self, value):
        self._ref = value

    @property
    def reference(self):
        return self._ref

    @reference.setter
    def reference(self, value):
        self._ref = value


ref = []


def as_reference(dct):
    if '$ref' in dct:
        dct['$ref'] = OpenApiReference(dct['$ref'])
        ref.append(dct['$ref'])
    return dct


def get_key(the_dict, dict_keys):
    if dict_keys[0] in the_dict:
        if len(dict_keys) == 1:
            return the_dict[dict_keys[0]]
        else:
            return get_key(the_dict[dict_keys[0]], dict_keys[1:])
    else:
        raise Exception("wrong key")


with open('petstore-simple.json', 'r') as stream:
    test = json.load(stream, object_hook=as_reference)

for item in ref:
    if item.reference[0] == '#':
        item.reference = get_key(test, item.reference[2:].split('/'))


print(test)
