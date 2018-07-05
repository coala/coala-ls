import pytest
from json import load, dumps

from coalals.utils.files import FileProxy
from coalals.results.diagnostics import Diagnostics
from coalals.results.fixes import coalaPatch, TextEdits
from helpers.resources import sample_diagnostics, url


class DummyDiff:
    pass


def get_all_samples():
    with open(sample_diagnostics) as samples:
        return load(samples)['samples']


def get_all_fixes_samples():
    with open(sample_diagnostics) as samples:
        return load(samples)['fixes']


def test_diagnostics_init():
    diagnostics = Diagnostics(warnings=[{}])
    assert diagnostics.warnings() == [{}]


def test_diagnostics_fixes():
    diagnostics = Diagnostics(fixes=[('', DummyDiff())])
    assert len(diagnostics.fixes()) == 1


@pytest.mark.parametrize('sample', get_all_samples())
def test_from_coala_op_json(sample):
    coala = sample['coala']
    exp_langserver = sample['langserver']

    coala_json_op = dumps(coala)
    gen_diags = Diagnostics.from_coala_json(coala_json_op)
    assert gen_diags.warnings() == exp_langserver


@pytest.mark.parametrize('sample', get_all_fixes_samples())
def test_fixes_load_from_coala_json(sample):
    diags_fixes = Diagnostics.from_coala_json(dumps(sample))
    assert len(diags_fixes.fixes()) == 3


def test_fixes_to_text_edits():
    failure3 = url('failure3.py')

    with open(failure3) as failure3_file:
        failure3_content = failure3_file.read()

    # sample patch with that will always mismatch failure3
    #  and raise an error when applied.
    wronged = coalaPatch('--- \n+++ \n@@ -2,5 +2,4 @@\n     hello = \"Hey\"'
                         '\n \n if Trues:\n-     poss\n-\n+    pass\n')

    proxy = FileProxy(failure3)
    patch = coalaPatch('')
    fixes = Diagnostics(fixes=[
        (failure3, patch), ('random.py', patch), (failure3, wronged)])

    text_edits = fixes.fixes_to_text_edits(proxy)
    text_edits_list = list(text_edits.get())

    assert isinstance(text_edits, TextEdits)
    replace_text = text_edits_list[0]['newText']
    assert replace_text == failure3_content
