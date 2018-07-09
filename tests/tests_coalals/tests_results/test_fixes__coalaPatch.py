import pytest
from json import loads
from types import GeneratorType

from coalals.results.fixes import coalaPatch
from helpers.resources import sample_fixes_file


@pytest.fixture
def sample_fixes():
    with open(sample_fixes_file) as sample:
        return loads(sample.read())


def test_coalaPatch_join():
    sample = ['Sample', 'String']
    joined = coalaPatch.join_parts(sample)

    # assuming that the splitlines() behaves
    # as required and does split by newlines.
    assert list(joined.splitlines()) == sample

    # TODO Add platform dependent newline combins.


def test_coalaPatch_init(sample_fixes):
    for fix in sample_fixes['diffs']:
        coalaPatch(fix['diff'])


def test_coalaPatch_wp_parsed(sample_fixes):
    for fix in sample_fixes['diffs']:
        coa = coalaPatch(fix['diff'])

        # should not raise any issue
        assert isinstance(coa.wp_parsed(), GeneratorType)


def test_coalaPatch_apply(sample_fixes):
    for l, fix in enumerate(sample_fixes['diffs']):
        orig, patched = fix['original'], fix['patched']
        diff = fix['diff']

        coa = coalaPatch(diff)
        parsed_patch = None

        if l % 2 == 1:
            parsed_patch = coa.wp_parsed()

        modified = coa.apply(orig, parsed_patch)
        assert modified == patched


def test_coalaPatch_apply_diff(sample_fixes):
    for fix in sample_fixes['diffs']:
        orig, patched = fix['original'], fix['patched']
        text_diff = fix['diff']

        coa = coalaPatch(text_diff)

        patches = coa.wp_parsed()
        diff = list(patches)[0]

        modified = coa.apply_diff(diff, orig)
        assert coalaPatch.join_parts(modified) == patched
