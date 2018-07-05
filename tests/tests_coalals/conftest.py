import sys
from os.path import join, dirname, abspath

current = dirname(__file__)
sys.path.append(join(current, 'helpers'))
sys.path.append(abspath(join(current, '../../')))
