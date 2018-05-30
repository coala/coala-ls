from json import loads

import logging
logger = logging.getLogger(__name__)


class Diagnostics:

    @classmethod
    def from_coala_json(cls, json_op):
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
        self._warnings = warnings
        self._fixes = fixes

    def warnings(self):
        return self._warnings

    def fixes(self):
        return self._fixes
