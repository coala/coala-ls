from pathlib import Path

# relative to the project directory
base_relative_url = Path.cwd().joinpath(
    'tests', 'resources')


def url(val, as_obj=False):
    names = val.split('|')
    path = base_relative_url.joinpath(*names)

    return path if as_obj else str(path)


sample_diagnostics = url('diagnostics.json')

sample_code_files = {
    url('failure.py'): {
        'diagnostics': 1,
    },

    url('failure2.py'): {
        'diagnostics': 2,
    },
}


def count_diagnostics(diagnostics):
    diagnostics_count = 0
    for section, diags in diagnostics.items():
        diagnostics_count += len(diags)

    return diagnostics_count
