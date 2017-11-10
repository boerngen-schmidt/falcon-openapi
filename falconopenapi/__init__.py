import json
import yaml
from pathlib import Path


class OpenApiDefinition(object):
    """ Data class for storing OpenApi definition


    """
    __slots__ = ['openapi', 'info', 'servers', 'paths', 'components', 'security', 'tags', 'externalDocs']

    def __init__(self, definition_file: str):
        # Initialize the slots to an empty dict
        for slot in type(self).__slots__:
            if slot == 'openapi':
                setattr(self, slot, str())
            else:
                setattr(self, slot, dict())

        definition = self._read_definitions_file(definition_file)
        for slot in type(self).__slots__:
            if slot not in definition:
                continue
            setattr(self, slot, definition[slot])

    def __getitem__(self, item):
        if item not in type(self).__slots__:
            raise KeyError(item)
        return getattr(self, item)

    @staticmethod
    def _read_definitions_file(definition_file):
        f = Path(definition_file)
        if not f.is_file():
            raise FileNotFoundError("Definition file: '" + str(f) + "' was not found.")

        with f.open() as definition:
            if f.suffix.lower() in (".yaml", ".yml"):
                return yaml.load(definition)
            elif f.suffix.lower() == ".json":
                return json.load(definition)
            else:
                raise TypeError("Unknown definition file type: '" + f.suffix + "'")
