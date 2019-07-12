import unittest

from iconservice.icx.issue.issue_formula import IssueFormula

EXPECTED_REWARD_RATE_PER_STAKE_PERCENTAGE = [1200,
                                             1172,
                                             1144,
                                             1116,
                                             1089,
                                             1062,
                                             1036,
                                             1010,
                                             984,
                                             959,
                                             935,
                                             910,
                                             887,
                                             863,
                                             840,
                                             817,
                                             795,
                                             773,
                                             752,
                                             731,
                                             710,
                                             690,
                                             670,
                                             651,
                                             632,
                                             613,
                                             595,
                                             577,
                                             560,
                                             543,
                                             527,
                                             510,
                                             495,
                                             479,
                                             464,
                                             450,
                                             436,
                                             422,
                                             409,
                                             396,
                                             384,
                                             372,
                                             360,
                                             349,
                                             338,
                                             328,
                                             318,
                                             308,
                                             299,
                                             290,
                                             282,
                                             274,
                                             266,
                                             259,
                                             252,
                                             246,
                                             240,
                                             234,
                                             229,
                                             225,
                                             220,
                                             217,
                                             213,
                                             210,
                                             207,
                                             205,
                                             203,
                                             202,
                                             201,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200,
                                             200]


class TestIssueFormula(unittest.TestCase):
    def test_calculate_rrep(self):
        rmin = 200
        rmax = 1200
        rpoint = 7000
        for x in range(0, 100):
            ret = IssueFormula.calculate_rrep(rmin, rmax, rpoint, 100, x)
            assert abs(ret - EXPECTED_REWARD_RATE_PER_STAKE_PERCENTAGE[x]) <= 1