import pytest

from coalals.results.fixes import (TextEdit,
                                   TextEdits)


@pytest.fixture
def sel_range():
    def _internal(sl, sc, el, ec):
        return {
            'start': {
                'line': sl,
                'character': sc,
            },

            'end': {
                'line': el,
                'character': ec,
            },
        }

    return _internal


@pytest.fixture
def text_edit(sel_range):
    sel_range = sel_range(0, 10, 3, 10)
    new_text = 'Sample TextEdit!'

    return TextEdit(sel_range, new_text)


def test_text_edit_init(sel_range):
    sel_range = sel_range(0, 10, 3, 10)
    new_text = 'Sample TextEdit!'

    te_entity = TextEdit(sel_range, new_text)
    assert te_entity._text_edit['range'] == sel_range
    assert te_entity._text_edit['newText'] == new_text


def test_text_edit_get(sel_range):
    sel_range = sel_range(0, 10, 3, 10)
    new_text = 'Sample TextEdit!'

    te_entity = TextEdit(sel_range, new_text)
    assert te_entity.get() == {
        'range': sel_range,
        'newText': new_text,
    }


def test_text_edits_add(text_edit):
    text_edits = TextEdits()

    text_edits.add(text_edit)
    text_edits.add(text_edit)

    assert len(text_edits._edits) == 2


def test_text_edits_get(text_edit):
    text_edits = TextEdits()

    text_edits.add(text_edit)
    text_edits.add(text_edit)

    assert list(text_edits.get())
