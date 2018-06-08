import pytest

from coalals.utils.entities import LSPEntity


def test_lsp_entity_name():
    class TextEdit(LSPEntity):
        pass

    assert LSPEntity.entity_name() == 'LSPEntity'
    assert TextEdit.entity_name() == 'TextEdit'


def test_lsp_entity_json():
    with pytest.raises(NotImplementedError):
        LSPEntity().json()
