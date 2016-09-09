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


from myreco.base.model import model_base_builder
from myreco.base.session import Session
from unittest import mock

import pytest
import sqlalchemy as sa


@pytest.fixture
def model_base():
    return model_base_builder()


@pytest.fixture
def model1(model_base):
    class model1(model_base):
        __tablename__ = 'model1'
        id = sa.Column(sa.Integer, primary_key=True)

    return model1


@pytest.fixture
def model1_nested(model_base):
    class model1(model_base):
        __tablename__ = 'model1'
        id = sa.Column(sa.Integer, primary_key=True)
        test = sa.Column(sa.Integer)

    return model1


@pytest.fixture
def model2(model_base):
    class model2(model_base):
        __tablename__ = 'model2'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model1 = sa.orm.relationship('model1')

    return model2


@pytest.fixture
def model3(model_base):
    class model3(model_base):
        __tablename__ = 'model3'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model2_id = sa.Column(sa.ForeignKey('model2.id'))
        model1 = sa.orm.relationship('model1')
        model2 = sa.orm.relationship('model2')

    return model3


@pytest.fixture
def model2_mtm(model_base):
    mtm_table = sa.Table(
        'mtm', model_base.metadata,
        sa.Column('model1_id', sa.Integer, sa.ForeignKey('model1.id')),
        sa.Column('model2_id', sa.Integer, sa.ForeignKey('model2.id'))
    )

    class model2(model_base):
        __tablename__ = 'model2'
        id = sa.Column(sa.Integer, primary_key=True)
        model1 = sa.orm.relationship(
            'model1', secondary='mtm', uselist=True)

    return model2


@pytest.fixture
def model3_mtm(model_base, model1, model2_mtm):
    model1_ = model1

    class model3(model_base):
        __tablename__ = 'model3'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model2_id = sa.Column(sa.ForeignKey('model2.id'))
        model1 = sa.orm.relationship(model1_)
        model2 = sa.orm.relationship(model2_mtm)

    return model3


@pytest.fixture
def model2_primary_join(model_base, model1):
    model1_ = model1

    class model2(model_base):
        __tablename__ = 'model2'
        id = sa.Column(sa.Integer, primary_key=True)
        id2 = sa.Column(sa.Integer)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        model1 = sa.orm.relationship(
            model1_,
            primaryjoin='and_(model2.model1_id==model1.id, model2.id2==model1.id)')

    return model2


@pytest.fixture
def model1_mto(model_base):
    class model1(model_base):
        __tablename__ = 'model1'
        id = sa.Column(sa.Integer, primary_key=True)

        model2 = sa.orm.relationship('model2', uselist=True)

    return model1


@pytest.fixture
def model2_mto(model_base):
    class model2(model_base):
        __tablename__ = 'model2'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))

    return model2


@pytest.fixture
def model2_mto_nested(model_base):
    class model2(model_base):
        __tablename__ = 'model2'
        id = sa.Column(sa.Integer, primary_key=True)
        model1_id = sa.Column(sa.ForeignKey('model1.id'))
        test = sa.Column(sa.Integer)

    return model2


@pytest.fixture
def session(model_base):
    engine = sa.create_engine('sqlite://')
    model_base.metadata.bind = engine
    model_base.metadata.create_all()
    return Session(bind=engine, redis_bind=mock.MagicMock())


class TestModelBaseTodict(object):
    def test_todict_after_get_from_database(self, model1, model2, session):
        session.add(model2(id=1, model1=model1(id=1)))
        session.commit()
        expected = {
            'id': 1,
            'model1_id': 1,
            'model1': {'id': 1}
        }
        session.query(model2).filter_by(id=1).one().todict() == expected

    def test_todict_after_get_from_database_with_mtm(self, model1, model2_mtm, session):
        session.add(model2_mtm(id=1, model1=[model1(id=1)]))
        session.commit()
        expected = {
            'id': 1,
            'model1': [{'id': 1}]
        }
        session.query(model2_mtm).filter_by(id=1).one().todict() == expected

    def test_todict_after_get_from_database_with_mtm_with_two_relations(
            self, model1, model2_mtm, session):
        session.add(model2_mtm(id=1, model1=[model1(id=1), model1(id=2)]))
        session.commit()
        expected = {
            'id': 1,
            'model1': [{'id': 1}, {'id': 2}]
        }
        session.query(model2_mtm).filter_by(id=1).one().todict() == expected


class TestModelBaseGetRelated(object):
    def test_get_related_with_one_model(self, model1, model2, session):
        m11 = model1(id=1)
        m21 = model2(id=1)
        m21.model1 = m11
        session.add_all([m11, m21])
        session.commit()

        assert m11.get_related(session) == {m21}

    def test_get_related_with_two_models(self, model1, model2, model3, session):
        m11 = model1(id=1)
        m21 = model2(id=1)
        m31 = model3(id=1)
        m31.model1 = m11
        m31.model2 = m21
        session.add_all([m11, m21, m31])
        session.commit()

        assert m11.get_related(session) == {m31}
        assert m21.get_related(session) == {m31}

    def test_get_related_with_two_related(self, model1, model2, model3, session):
        m11 = model1(id=1)
        m21 = model2(id=1)
        m31 = model3(id=1)
        m31.model1 = m11
        m21.model1 = m11
        session.add_all([m11, m21, m31])
        session.commit()

        assert m11.get_related(session) == {m31, m21}

    def test_get_related_with_two_models_and_two_related(self, model1, model2, model3, session):
        m11 = model1(id=1)
        m21 = model2(id=1)
        m31 = model3(id=1)
        m31.model1 = m11
        m21.model1 = m11
        m22 = model2(id=2)
        m32 = model3(id=2)
        m32.model1 = m11
        m22.model1 = m11
        session.add_all([m11, m21, m31, m22, m32])
        session.commit()

        assert m11.get_related(session) == {m31, m21, m22, m32}

    def test_get_related_with_mtm(
            self, model1, model2_mtm, model3_mtm, session):
        m11 = model1(id=1)
        m12 = model1(id=2)
        m21 = model2_mtm(id=1)
        m31 = model3_mtm(id=1)
        m31.model1 = m11
        m21.model1 = [m11, m12]
        m22 = model2_mtm(id=2)
        m32 = model3_mtm(id=2)
        m32.model1 = m11
        m22.model1 = [m11, m12]
        session.add_all([m11, m12, m21, m31, m22, m32])
        session.commit()

        assert m11.get_related(session) == {m31, m21, m22, m32}
        assert m12.get_related(session) == {m21, m22}

    def test_get_related_with_primary_join(
            self, model1, model2_primary_join, session):
        m11 = model1(id=5)
        m21 = model2_primary_join(id=1, id2=5)
        m21.model1 = m11
        session.add_all([m11, m21])
        session.commit()

        assert m21.model1 == m11
        assert m11.get_related(session) == {m21}
        assert m21.get_related(session) == {m11}

    def test_get_related_with_primary_join_get_no_result(
            self, model1, model2_primary_join, session):
        m11 = model1(id=1)
        m21 = model2_primary_join(id=1, id2=5)
        m21.model1 = m11
        session.add_all([m11, m21])
        session.commit()

        assert m21.model1 == None
        assert m11.get_related(session) == set()
        assert m21.get_related(session) == set()

    def test_get_related_with_mto(
            self, model1_mto, model2_mto, session):
        m11 = model1_mto(id=1)
        m21 = model2_mto(id=1)
        m11.model2 = [m21]
        session.add_all([m11, m21])
        session.commit()

        assert m11.model2 == [m21]
        assert m11.get_related(session) == {m21}
        assert m21.get_related(session) == {m11}

    def test_get_related_with_mto_with_two_related(
            self, model1_mto, model2_mto, session):
        m11 = model1_mto(id=1)
        m21 = model2_mto(id=1)
        m22 = model2_mto(id=2)
        m11.model2 = [m21, m22]
        session.add(m11)
        session.commit()

        assert m11.model2 == [m21, m22]
        assert m11.get_related(session) == {m21, m22}
        assert m21.get_related(session) == {m11}


class TestModelBaseInsert(object):
    def test_insert_with_one_object(self, model1, session):
        objs = model1.insert(session, {'id': 1})
        assert objs == [{'id': 1}]

    def test_insert_without_todict(self, model1, session):
        objs = model1.insert(session, {'id': 1}, todict=False)
        assert [o.todict() for o in objs] == [{'id': 1}]

    def test_insert_with_two_objects(self, model1, session):
        objs = model1.insert(session, [{'id': 1}, {'id': 2}])
        assert objs == [{'id': 1}, {'id': 2}]

    def test_insert_with_two_nested_objects(self, model1, model2, session):
        objs = model2.insert(session, {'id': 1, 'model1': {'id': 1}})
        assert objs == [{'id': 1, 'model1_id': 1, 'model1': {'id': 1}}]

    def test_insert_with_three_nested_objects(self, model1, model2, model3, session):
        m1 = {'id': 1}
        m2 = {'id': 1, 'model1': m1}
        objs = model3.insert(session, {'id': 1, 'model2': m2})

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1_id': 1,
                'model1': {
                    'id': 1
                }
            }
        }
        assert objs == [expected]

    def test_insert_with_nested_update(self, model1, model2, model3, session):
        model1.insert(session, {'id': 1})
        model2.insert(session, {'id': 1})

        m3 = {
            'id': 1,
            'model2': {
                'id': 1,
                '_update': True,
                'model1_id': 1
            }
        }
        objs = model3.insert(session, m3)

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1_id': 1,
                'model1': {
                    'id': 1
                }
            }
        }
        assert objs == [expected]

    def test_insert_with_two_nested_update(self, model1_nested, model2, model3, session):
        model1_nested.insert(session, {'id': 1})
        model2.insert(session, {'id': 1})

        m3 = {
            'id': 1,
            'model2': {
                'id': 1,
                '_update': True,
                'model1': {
                    'id': 1,
                    '_update': True,
                    'test': 'test_updated'
                }
            }
        }
        objs = model3.insert(session, m3)

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1_id': 1,
                'model1': {
                    'id': 1,
                    'test': 'test_updated'
                }
            }
        }
        assert objs == [expected]

    def test_insert_with_two_nested_update_with_mtm(
            self, model1_nested, model2_mtm, model3, session):
        model1_nested.insert(session, [{'id': 1}, {'id': 2}])
        model2_mtm.insert(session, {'id': 1})

        m3 = {
            'id': 1,
            'model2': {
                'id': 1,
                '_update': True,
                'model1': [
                    {
                        'id': 1,
                        '_update': True,
                        'test': 'test_updated'
                    }, {
                        'id': 2,
                        '_update': True,
                        'test': 'test_updated2'
                    }
                ]
            }
        }
        objs = model3.insert(session, m3)

        expected = {
            'id': 1,
            'model1_id': None,
            'model1': None,
            'model2_id': 1,
            'model2': {
                'id': 1,
                'model1': [
                    {
                        'id': 1,
                        'test': 'test_updated'
                    },{
                        'id': 2,
                        'test': 'test_updated2'
                    }
                ]
            }
        }
        assert objs == [expected]

    def test_insert_with_two_nested_update_with_mto(
            self, model1_mto, model2_mto_nested, model3, session):
        model1_mto.insert(session, {'id': 1})
        model2_mto_nested.insert(session, [{'id': 1}, {'id': 2}])

        m3 = {
            'id': 1,
            'model1': {
                'id': 1,
                '_update': True,
                'model2': [
                    {
                        'id': 1,
                        '_update': True,
                        'test': 'test_updated'
                    }, {
                        'id': 2,
                        '_update': True,
                        'test': 'test_updated2'
                    }
                ]
            }
        }
        objs = model3.insert(session, m3)

        expected = {
            'id': 1,
            'model2_id': None,
            'model2': None,
            'model1_id': 1,
            'model1': {
                'id': 1,
                'model2': [
                    {
                        'id': 1,
                        'model1_id': 1,
                        'test': 'test_updated'
                    },{
                        'id': 2,
                        'model1_id': 1,
                        'test': 'test_updated2'
                    }
                ]
            }
        }
        assert objs == [expected]