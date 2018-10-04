# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""IconScoreEngine testcase
"""

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from tests.integrate_test.test_integrate_base import TestIntegrateBase

from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateEventLog(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self._update_0_0_3_governance()

    def _update_0_0_3_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "0_0_3/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _deploy_score(self, score_path: str, update_score_addr: 'Address' = None) -> Any:
        address = ZERO_SCORE_ADDRESS
        if update_score_addr:
            address = update_score_addr

        tx = self._make_deploy_tx("test_event_log_scores",
                                  score_path,
                                  self._addr_array[0],
                                  address,
                                  deploy_params={})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _query_score(self, target_addr: 'Address', method: str, params: dict={}):
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": target_addr,
            "dataType": "call",
            "data": {
                "method": method,
                "params": params
            }
        }
        return self._query(query_request)

    def _call_score(self, score_addr: 'Address', method: str, params: dict):
        tx = self._make_score_call_tx(self._addr_array[0],
                                      score_addr,
                                      method,
                                      params)

        prev_block, tx_results = self._make_and_req_block([tx])

        self._write_precommit_state(prev_block)

        return tx_results

    def test_valid_event_log(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # success case: call valid event log and check log data
        # event log which defined parameter's number is zero also treat as valid event log
        method_params ={"value1": "test1", "value2": "test2", "value3": "test3"}
        tx_results = self._call_score(score_addr, "call_valid_event_log", method_params)
        self.assertEqual(tx_results[0].status, int(True))

        # indexed params and non_indexed params should be separately stored in txresult(indexed, data)
        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.indexed[0], "NormalEventLog(str,str,str)")
        self.assertEqual(event_log.indexed[1], "test1")
        self.assertEqual(event_log.indexed[2], "test2")
        self.assertEqual(event_log.data[0], "test3")

        # success case: event log which params are not defined also treat as valid event log
        tx_results = self._call_score(score_addr, "call_event_log_params_are_not_defined", {})
        self.assertEqual(tx_results[0].status, int(True))

        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.data, [])
        self.assertEqual(event_log.indexed[0], "EventLogWithOutParams()")

    def test_event_log_self_is_not_defined(self):
        # failure case: event log which self is not defined treat as invalid event log
        tx_result = self._deploy_score("test_self_is_not_defined_event_log_score")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.message, "define 'self' as the first parameter in the event log")

    def test_event_log_when_error(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # failure case: the case of raising an error when call event log, the state should be revert
        tx_results = self._call_score(score_addr, "call_event_log_raising_error", {})
        self.assertEqual(tx_results[0].status, int(False))

        expected = "default"
        actual = self._query_score(score_addr, "get_value")
        self.assertEqual(expected, actual)

    def test_event_log_having_body(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # success case: even though the event log has body, body should be ignored
        tx_results = self._call_score(score_addr, "call_event_log_having_body", {})
        self.assertEqual(tx_results[0].status, int(True))

        expected = "default"
        actual = self._query_score(score_addr, "get_value")
        self.assertEqual(expected, actual)

    def test_event_log_index_on_deploy(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # success case: set index under 0(index number should be treated as 0)
        tx_results = self._call_score(score_addr, "call_event_log_index_under_zero", {})
        self.assertEqual(tx_results[0].status, int(True))
        event_log = tx_results[0].event_logs[0]

        # params should be stored in data list
        self.assertEqual(event_log.data[0], "test")
        # index length should be 1(including event log method name)
        self.assertEqual(len(event_log.indexed), 1)

        # failure case: setting index more than 4(should raise an error)
        tx_result = self._deploy_score("test_exceed_max_index_event_log_score")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.message, "index can't exceed 3")

        # failure case: setting index more than event log's parameter total count(should raise an error)
        tx_result = self._deploy_score("test_index_exceed_params_event_log_score")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.message, "index exceeds the number of parameters")


    def test_event_log_index_on_execute(self):
        pass

    def test_event_log_parameters_on_deploy(self):
        # failure case: define dict type parameter
        tx_result = self._deploy_score("test_invalid_params_type_event_log_score_dict")
        self.assertEqual(tx_result.failure.message, "'Unsupported type for 'value: <class 'dict'>'")

        # failure case: define list type parameter
        tx_result = self._deploy_score("test_invalid_params_type_event_log_score_array")
        self.assertEqual(tx_result.failure.message, "'Unsupported type for 'value: <class 'list'>'")

        # failure case: omit type hint
        tx_result = self._deploy_score("test_invalid_params_type_hint_event_log_score")
        self.assertEqual(tx_result.failure.message, "Missing argument hint for 'value'")

    def test_event_log_parameters_on_execute(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # failure case: input less parameter to event log(raise error)
        tx_results = self._call_score(score_addr, "call_event_log_input_less_number_of_params", {})
        self.assertEqual(tx_results[0].status, int(False))

        # failure case: input exceed parameter to event log(raise error)
        tx_results = self._call_score(score_addr, "call_event_log_input_exceed_number_of_params", {})
        self.assertEqual(tx_results[0].status, int(False))

        tx_results = self._call_score(score_addr, "call_event_log_input_exceed_number_of_params2", {})
        self.assertEqual(tx_results[0].status, int(False))

        # failure case: input non-matching type parameter to event log(raise error)
        type_list = ["integer", "string", "boolean", "bytes", "address"]

        # case1: defined parameter=integer
        for params_type in type_list:
            if params_type == "integer" or params_type == "boolean":
                continue
            tx_params =  {"test_type": "integer", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

        # case2: defined parameter=string
        for params_type in type_list:
            if params_type == "string":
                continue
            tx_params =  {"test_type": "string", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

        # case3: defined parameter=boolean
        for params_type in type_list:
            if params_type == "boolean":
                continue
            tx_params =  {"test_type": "boolean", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

        # case4: defined parameter=bytes
        for params_type in type_list:
            if params_type == "bytes":
                continue
            tx_params =  {"test_type": "bytes", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

        # case5: defined parameter=address
        for params_type in type_list:
            if params_type == "address":
                continue
            tx_params =  {"test_type": "address", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

