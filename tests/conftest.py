import pytest
from ml.evidence_schema import EvidenceSchema,empty_state
from ml.encoding import EvidenceEncoder

@pytest.fixture(scope='session')
def schema():return EvidenceSchema()

@pytest.fixture(scope='session')
def encoder(schema):return EvidenceEncoder(schema)

@pytest.fixture
def state():return empty_state()

@pytest.fixture(scope='session')
def client():
    from app import create_app
    app=create_app({'TESTING':True})
    assert app.config['MODEL_READY'], 'Required shipped artifact must actually load'
    return app.test_client()
