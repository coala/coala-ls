from json import loads

import logging
logger = logging.getLogger(__name__)


class Diagnostics:
    """
    Handle the diagnostics format transformation
    and processing.
    """

    @classmethod
    def from_coala_json(cls, json_op):
        """
        Transform coala json output into valid
        diagnostic messages following LSP protocol
        structure.

        :param json_op:
            coala json output as string.
        :return:
            Instance of Diagnostics class.
        """
        coala_op = loads(json_op)['results']
        warnings, fixes = [], []

        def convert_offset(x):
            return x - 1 if x else x

        for section, coala_warnings in coala_op.items():
            for warning in coala_warnings:
                """
                Transform RESULT_SEVERITY of coala to DiagnosticSeverity of LSP
                coala: INFO = 0, NORMAL = 1, MAJOR = 2
                LSP: Error = 1, Warning = 2, Information = 3, Hint = 4
                """
                severity = 3 - warning['severity']
                message = warning['message']
                origin = warning['origin']
                full_message = '[{}] {}: {}'.format(section, origin, message)

                # TODO Handle results for multiple files
                for code in warning['affected_code']:
                    start_line = convert_offset(code['start']['line'])
                    start_char = convert_offset(code['start']['column'])
                    end_line = convert_offset(code['end']['line'])
                    end_char = convert_offset(code['end']['column'])

                    if start_char is None or end_char is None:
                        start_char, end_char = 0, 0
                        end_line = start_line + 1

                    warnings.append({
                      'severity': severity,
                      'range': {
                          'start': {
                            'line': start_line,
                            'character': start_char,
                          },
                          'end': {
                            'line': end_line,
                            'character': end_char,
                          },
                      },
                      'source': 'coala',
                      'message': full_message,
                    })

                # TODO Handle results for multiple files
                # and also figure out a way to resolve
                # overlapping patches.

                # for file, diff in warning['diffs'].items():
                #   for parsed_diff in parse_patch(diff):
                #     pass

        logger.debug(warnings)
        return cls(warnings, fixes=fixes)

    def __init__(self, warnings=[], fixes=[]):
        """
        :param warnings:
            A list of initial warnings to initialize
            instance with.
        :param fixes:
            A list of initial code fixes to initialize
            instance with.
        """
        self._warnings = warnings
        self._fixes = fixes

    def warnings(self):
        """
        :return:
            Returns a list of warnings.
        """
        return self._warnings

    def fixes(self):
        """
        :return:
            Returns a list of fixes.
        """
        return self._fixes
