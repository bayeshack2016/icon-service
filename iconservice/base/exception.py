# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

from enum import IntEnum, unique
from functools import wraps
from ..logger import Logger
from ..icon_config import *

from typing import Optional


@unique
class ExceptionCode(IntEnum):
    """Result code enumeration

    Refer to http://www.simple-is-better.org/json-rpc/jsonrpc20.html#examples
    """
    OK = 0
    ICON = 100
    DB = 200
    ICX = 300
    SCORE = 400
    SCORE_EXTERNAL = 500
    SCORE_EXTERNAL_METHOD_NOT_FOUND = 501
    SCORE_PAYABLE = 600
    SCORE_REVERT = 700
    SCORE_INTERFACE = 800
    SCORE_EVENTLOG = 900
    SCORE_CONTAINERDB = 1000
    SCORE_INSTALL = 1100
    SCORE_INSTALL_EXTRACT = 1200

    # -32000 ~ -32099: Server error
    INVALID_REQUEST = 32600
    METHOD_NOT_FOUND = 32601
    INVALID_PARAMS = 32602
    INTERNAL_ERROR = 32603
    PARSE_ERROR = 32700

    LOCKED_ACCOUNT = 40000
    NOT_ENOUGH_BALANCE = 40001
    INVALID_FEE = 40002

    def __str__(self) -> str:
        if self.value == self.INVALID_REQUEST:
            return "Invalid Request"
        else:
            return str(self.name).capitalize().replace('_', ' ')


# 아이콘 서비스에서 사용하는 모든 예외는 다음을 상속받는다.
class IconServiceBaseException(BaseException):

    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.OK):
        if message is None:
            message = str(code)
        self.__message = message
        self.__code = code

    @property
    def message(self):
        return self.__message

    @property
    def code(self):
        return self.__code

    def __str__(self):
        return f'{self.message} ({self.code})'


class IconException(IconServiceBaseException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.ICON):
        super().__init__(message, code)


class DatabaseException(IconServiceBaseException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.DB):
        super().__init__(message, code)


class ICXException(IconServiceBaseException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.ICX):
        super().__init__(message, code)


class IconScoreException(IconServiceBaseException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.SCORE):
        super().__init__(message, code)


class APIIconScoreBaseException(IconScoreException):
    def __init__(self, message: Optional[str], func_name: str, cls_name: str,
                 code: ExceptionCode = ExceptionCode.SCORE):
        super().__init__(message, code)
        self.__func_name = func_name
        self.__cls_name = cls_name

    @property
    def func_name(self):
        return self.__func_name

    @property
    def cls_name(self):
        return self.__cls_name

    def __str__(self):
        return f'msg: {self.message} func: {self.func_name} cls: {self.cls_name} ({self.code})'


def check_exception(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (IconServiceBaseException, Exception) as e:
            Logger.exception(e, ICON_EXCEPTION_LOG_TAG)
            raise e
        finally:
            pass
    return _wrapper


class ExternalException(APIIconScoreBaseException):
    def __init__(self, message: Optional[str], func_name: str, cls_name: str,
                 code: ExceptionCode = ExceptionCode.SCORE_EXTERNAL):
        super().__init__(message, func_name, cls_name, code)


class PayableException(APIIconScoreBaseException):
    def __init__(self, message: Optional[str], func_name: str, cls_name: str,
                 code: ExceptionCode = ExceptionCode.SCORE_PAYABLE):
        super().__init__(message, func_name, cls_name, code)


class RevertException(IconScoreException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.SCORE_REVERT):
        super().__init__(message, code)


class InterfaceException(IconScoreException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.SCORE_INTERFACE):
        super().__init__(message, code)


class EventLogException(IconScoreException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.SCORE_EVENTLOG):
        super().__init__(message, code)


class ContainerDBException(IconScoreException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.SCORE_CONTAINERDB):
        super().__init__(message, code)


class ScoreInstallException(IconScoreException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.SCORE_INSTALL):
        super().__init__(message, code)


class ScoreInstallExtractException(IconScoreException):
    def __init__(self, message: Optional[str], code: ExceptionCode = ExceptionCode.SCORE_INSTALL_EXTRACT):
        super().__init__(message, code)
