from pathlib import Path


def get_random_path(suffix, as_obj=False, py=True):
    ext = 'py' if py else 'txt'
    filename = 'coala-rox-{}.{}'.format(suffix, ext)
    path = Path.cwd().joinpath('coala-x-miss', filename)

    return path if as_obj else str(path)
