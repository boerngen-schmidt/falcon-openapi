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


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.ext.declarative.base import _declarative_constructor
from sqlalchemy.ext.declarative.clsregistry import _class_resolver
from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import or_

from myreco.exceptions import ModelBaseError


MODEL_BASE_CLASS_NAME = 'ModelBase'


class _SQLAlchemyModelMeta(DeclarativeMeta):
    def __init__(cls, name, bases_classes, attributes):
        DeclarativeMeta.__init__(cls, name, bases_classes, attributes)

        if name != MODEL_BASE_CLASS_NAME:
            if not hasattr(cls, 'id_name'):
                cls.id_name = 'id'
            cls.get_model_id()

            base_class = None
            for base in bases_classes:
                if base.__name__ == MODEL_BASE_CLASS_NAME:
                    base_class = base
                    break

            if base_class is None:
                raise ModelBaseError(
                    "'{}' class must inherit from '{}'".format(
                        name, MODEL_BASE_CLASS_NAME))

            cls.backrefs = set()
            cls.relationships = set()
            cls.columns = set(cls.__table__.c)
            cls.tablename = str(cls.__table__.name)
            cls.todict_schema = {}
            base_class.all_models.add(cls)

            cls._build_backrefs_for_all_models(base_class.all_models)
        else:
            cls.all_models = set()

    def get_model_id(cls):
        return getattr(cls, cls.id_name)

    def _build_backrefs_for_all_models(cls, all_models):
        all_relationships = set()

        for model in all_models:
            model._build_relationships()
            all_relationships.update(model.relationships)

        for model in all_models:
            for relationship in all_relationships:
                if model != cls.get_model_from_rel(relationship, all_models, parent=True) and \
                    model == cls.get_model_from_rel(relationship, all_models):
                    model.backrefs.add(relationship)

    def _build_relationships(cls):
        if cls.relationships:
            return

        for attr_name in cls.__dict__:
            relationship = cls._get_relationship(attr_name)
            if relationship:
                cls.relationships.add(relationship)

    def _get_relationship(cls, attr_name):
        attr = getattr(cls, attr_name)
        if isinstance(attr, InstrumentedAttribute) and isinstance(attr.prop, RelationshipProperty):
            return attr

    def get_model_from_rel(cls, relationship, all_models=None, parent=False):
        if parent:
            return relationship.prop.parent.class_

        if isinstance(relationship.prop.argument, _class_resolver):
            if all_models is None:
                return relationship.prop.argument()

            for model in all_models:
                if model.__name__ == relationship.prop.argument.arg:
                    return model

            return

        return relationship.prop.argument

    def insert(cls, session, objs, commit=True, todict=True):
        objs = cls._to_list(objs)

        for obj in objs:
            cls._do_operations_in_relationships(session, obj)

        objs = [cls(**obj) for obj in objs]

        session.add_all(objs)

        if commit:
            session.commit()

        if todict:
            objs = [o.todict() for o in objs]

        return objs

    def _to_list(cls, objs):
        return objs if isinstance(objs, list) else [objs]

    def _do_operations_in_relationships(cls, session, values):
        for attr_name in set(values.keys()):
            relationship = cls._get_relationship(attr_name)

            if relationship is not None:
                rel_model = cls.get_model_from_rel(relationship)
                rels_values = values.pop(attr_name)
                new_rels = []
                alreadly_rels_ids = set()

                if relationship.prop.uselist is not True:
                    rels_values = [rels_values]

                cls._do_operations_in_relationships_values(
                    session, values, rel_model, rels_values, new_rels, alreadly_rels_ids)

                if new_rels:
                    values[attr_name] = \
                        new_rels if relationship.prop.uselist is True else new_rels[0]

                if alreadly_rels_ids:
                    alreadly_rels = cls._get_alreadly_insts(session, rel_model, alreadly_rels_ids)
                    if new_rels:
                        values[attr_name].extend(alreadly_rels)
                    elif relationship.prop.uselist is True:
                        values[attr_name] = alreadly_rels
                    else:
                        values[attr_name] = alreadly_rels[0]

    def _get_alreadly_insts(cls, session, rel_model, alreadly_rels_ids):
        return session.query(rel_model).get(list(alreadly_rels_ids), todict=False)

    def _do_operations_in_relationships_values(
            cls, session, values, rel_model,
            rels_values, new_rels, alreadly_rels_ids):
        for rel_values in rels_values:
            to_update = rel_values.pop('_update', None)
            to_delete = rel_values.pop('_delete', None)
            rel_id = rel_values.get(rel_model.id_name)

            if to_update is not None and to_delete is not None:
                raise ModelBaseError(
                    "ambiguous operations 'delete'"\
                    " and 'update' for values {}".format(values))

            if to_update is not None:
                cls._raise_id_not_found_error(rel_id, 'update', values)
                rel_id = rel_values.pop(rel_model.id_name)
                rel_model.update(session, {rel_id: rel_values}, commit=False)
                alreadly_rels_ids.add(rel_id)

            elif to_delete is not None:
                cls._raise_id_not_found_error(rel_id, 'delete', values)
                rel_model.delete(session, rel_id, commit=False)

            else:
                objs = rel_model.insert(session, rel_values, commit=False, todict=False)
                new_rels.extend(objs)

    def update(cls, session, ids_objs_map, commit=True):
        for id_, values in ids_objs_map.items():
            cls._do_operations_in_relationships(session, values)
            orm_update = [True for key in values.keys() if cls._get_relationship(key)]

            if orm_update:
                cls._do_orm_update(session, ids_objs_map)
            else:
                session.query(cls).filter(cls.get_model_id() == id_).update(values)

        if commit:
            session.commit()

        return set(ids_objs_map.keys())

    def _do_orm_update(cls, session, ids_objs_map):
        insts = cls._get_alreadly_insts(session, cls, ids_objs_map.keys())
        id_insts_map = {inst.get_id(): inst for inst in insts}

        for id_, inst in id_insts_map.items():
            inst.update_(**ids_objs_map[id_])

    def _raise_id_not_found_error(cls, rel_id, type_, values):
        if rel_id is None:
            rel_error_message = "can't execute '{}' without '{}' for values {}"
            raise ModelBaseError(rel_error_message.format(type_, cls.id_name, values))

    def delete(cls, ids, commit=True):
        ids = cls._to_list(ids)
        for id_ in ids:
            session.query(cls).filter(cls.get_model_id() == id_).delete()

        if commit:
            session.commit()

        return set(ids)

    def get(cls, session, ids=None, limit=None, offset=None):
        if (ids is not None) and (limit is not None or offset is not None):
            raise ModelBaseError(
                "'get' method can't be called with 'ids' and with 'offset' or 'limit'")

        if ids is None:
            query = session.query(cls)

            if limit is not None:
                query = query.limit(limit)

            if offset is not None:
                query = query.offset(limit)

            return query.all(todict=True)

        return session.query(cls).get(ids)


class _SQLAlchemyModel(object):
    def get_id(self):
        return getattr(self, type(self).id_name)

    def get_related(self, session):
        related = set()
        cls = type(self)

        for relationship in cls.relationships:
            related_model_insts = self._get_related_model_insts(session, relationship)
            related.update(related_model_insts)

        for relationship in cls.backrefs:
            related_model_insts = self._get_related_model_insts(session, relationship, parent=True)
            related.update(related_model_insts)

        return related

    def _get_related_model_insts(self, session, relationship, parent=False):
        cls = type(self)
        rel_model = cls.get_model_from_rel(relationship, parent=parent)

        result = set(session.query(rel_model).join(relationship).filter(
            cls.get_model_id() == self.get_id()).all(todict=False))
        return result

    def todict(self, schema=None):
        dict_inst = dict()
        if schema is None:
            schema = type(self).todict_schema

        self._todict_columns(dict_inst, schema)
        self._todict_relationships(dict_inst, schema)

        return dict_inst

    def _todict_columns(self, dict_inst, schema):
        for col in type(self).columns:
            col_name = str(col.name)
            if self._attribute_in_schema(col_name, schema):
                dict_inst[col_name] = getattr(self, col_name)

    def _attribute_in_schema(self, attr_name, schema):
        return (attr_name in schema and schema[attr_name]) or (not attr_name in schema)

    def _todict_relationships(self, dict_inst, schema):
        for rel in type(self).relationships:
            rel_name = rel.key
            if self._attribute_in_schema(rel_name, schema):
                rel_schema = schema.get(rel_name)
                rel_schema = rel_schema if isinstance(rel_schema, dict) else None
                attr = getattr(self, rel.prop.key)
                relationships = None
                if rel.prop.uselist is True:
                    relationships = [rel.todict(rel_schema) for rel in attr]
                elif attr is not None:
                    relationships = attr.todict(rel_schema)

                dict_inst[rel_name] = relationships

    def update_(self, **kwargs):
        type(self).__init__(self, **kwargs)


def model_base_builder(
        bind=None, metadata=None, mapper=None,
        constructor=_declarative_constructor,
        class_registry=None):
    return declarative_base(
        name=MODEL_BASE_CLASS_NAME, metaclass=_SQLAlchemyModelMeta,
        cls=_SQLAlchemyModel, bind=bind, metadata=metadata,
        mapper=mapper, constructor=constructor)
