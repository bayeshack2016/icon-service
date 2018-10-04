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

from typing import TYPE_CHECKING, List, Optional, Any

from .icon_score_constant import BaseType
from .icon_score_step import StepType
from ..base.address import Address
from ..base.exception import EventLogException
from ..icon_constant import DATA_BYTE_ORDER, ICX_TRANSFER_EVENT_LOG
from ..utils import int_to_bytes, byte_length_of_int

if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext


INDEXED_ARGS_LIMIT = 3


class EventLog(object):
    """ A DataClass of a event log.
    """

    def __init__(
            self,
            score_address: 'Address',
            indexed: List['BaseType'] = None,
            data: List['BaseType'] = None) -> None:
        """
        Constructor

        :param score_address: an address of SCORE in which the event is invoked
        :param indexed: a list of indexed arguments including a event signature
        :param data: a list of normal arguments
        """
        self.score_address: 'Address' = score_address
        self.indexed: 'List[BaseType]' = indexed
        self.data: 'List[BaseType]' = data

    def __str__(self) -> str:
        return '\n'.join([f'{k}: {v}' for k, v in self.__dict__.items()])

    def to_dict(self, casing: Optional = None) -> dict:
        """
        Returns properties as `dict`
        :return: a dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            if value is None:
                # Excludes properties which have `None` value
                continue

            new_dict[casing(key) if casing else key] = value

        return new_dict


class EventLogEmitter(object):
    @staticmethod
    def emit_event_log(context: 'IconScoreContext',
                       score_address: 'Address',
                       event_signature: str,
                       arguments: List[Any],
                       indexed_args_count: int):
        """
        Puts a eventlog to the running context

        :param context: running context.
        :param score_address: score address which event is occurred at.
        :param event_signature: signature of the eventlog
        :param arguments: arguments of eventlog call
        :param indexed_args_count: count of the indexed arguments
        :return:
        """

        if context.readonly:
            raise EventLogException(
                'The event log can not be recorded on readonly context')

        if indexed_args_count > INDEXED_ARGS_LIMIT:
            raise EventLogException(
                f'indexed arguments are overflow: limit={INDEXED_ARGS_LIMIT}')

        if indexed_args_count > len(arguments):
            raise EventLogException(
                f'declared indexed_args_count is {indexed_args_count}, '
                f'but argument count is {len(arguments)}')

        event_size = EventLogEmitter.__get_byte_length(event_signature)
        indexed: List[BaseType] = [event_signature]
        data: List[BaseType] = []
        for i, argument in enumerate(arguments):
            # Raises an exception if the types are not supported
            if not EventLogEmitter.__is_base_type(argument):
                raise EventLogException(f'Not supported type: {type(argument)}')

            event_size += EventLogEmitter.__get_byte_length(argument)

            # Separates indexed type and base type with keeping order.
            if i < indexed_args_count:
                indexed.append(argument)
            else:
                data.append(argument)

        # skip counting steps for auto emitted event 'ICXTransfer(Address,Address,int)'
        if event_signature != ICX_TRANSFER_EVENT_LOG:
            context.step_counter.apply_step(StepType.EVENT_LOG, event_size)

        event = EventLog(score_address, indexed, data)
        context.event_logs.append(event)

    @staticmethod
    def __is_base_type(value) -> bool:
        for base_type in BaseType.__constraints__:
            if isinstance(value, base_type):
                return True
        return False

    @staticmethod
    def __get_byte_length(data: 'BaseType') -> int:
        if isinstance(data, int):
            return byte_length_of_int(data)
        else:
            return len(EventLogEmitter.__base_type_to_bytes(data))

    @staticmethod
    def __base_type_to_bytes(data: 'BaseType') -> bytes:
        if isinstance(data, str):
            return data.encode('utf-8')
        elif isinstance(data, Address):
            return data.body
        elif isinstance(data, bytes):
            return data
        elif isinstance(data, int):
            return int_to_bytes(data)

    @staticmethod
    def get_bloom_data(index: int, data: 'BaseType') -> bytes:
        return index.to_bytes(1, DATA_BYTE_ORDER) + \
               EventLogEmitter.__base_type_to_bytes(data)
