import pytest
from json import load, dumps

from coalals.results import Diagnostics
from helpers.resources import sample_diagnostics


class DummyDiff:
    pass


def get_all_samples():
    with open(sample_diagnostics) as samples:
        return load(samples)['samples']


def test_diagnostics_init():
    diagnostics = Diagnostics(warnings=[{}])
    assert diagnostics.warnings() == [{}]


def test_diagnostics_fixes():
    diagnostics = Diagnostics(fixes=[DummyDiff()])
    assert len(diagnostics.fixes()) == 1


@pytest.mark.parametrize('sample', get_all_samples())
def test_from_coala_op_json(sample):
    coala = sample['coala']
    exp_langserver = sample['langserver']

    coala_json_op = dumps(coala)
    gen_diags = Diagnostics.from_coala_json(coala_json_op)
    assert gen_diags.warnings() == exp_langserver
