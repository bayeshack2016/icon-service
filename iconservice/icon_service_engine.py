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


import os
from collections import namedtuple

from iconservice.iconscore.icon_score_deployer import IconScoreDeployer

from .base.address import Address, AddressPrefix, ICX_ENGINE_ADDRESS, create_address
from .base.exception import ExceptionCode, IconException, check_exception
from .base.block import Block
from .base.message import Message
from .base.transaction import Transaction
from .database.factory import DatabaseFactory
from .database.batch import BlockBatch, TransactionBatch
from .icx.icx_engine import IcxEngine
from .icx.icx_storage import IcxStorage
from .iconscore.icon_score_info_mapper import IconScoreInfoMapper
from .iconscore.icon_score_context import IconScoreContext
from .iconscore.icon_score_context import IconScoreContextType
from .iconscore.icon_score_context import IconScoreContextFactory
from .iconscore.icon_score_engine import IconScoreEngine
from .iconscore.icon_score_loader import IconScoreLoader
from .iconscore.icon_score_result import IconBlockResult
from .iconscore.icon_score_result import TransactionResult
from .iconscore.icon_score_result import JsonSerializer
from .iconscore.icon_score_step import IconScoreStepCounterFactory
from .logger import Logger
from .icon_config import *

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .iconscore.icon_score_step import IconScoreStepCounter


class IconServiceEngine(object):
    """The entry of all icon service related components

    It MUST NOT have any loopchain dependencies.
    It is contained in IconOuterService.
    """

    def __init__(self) -> None:
        """Constructor

        :param icon_score_root_path:
        :param state_db_root_path:
        """
        # jsonrpc handlers
        self._handlers = {
            'icx_getBalance': self._handle_icx_getBalance,
            'icx_getTotalSupply': self._handle_icx_getTotalSupply,
            'icx_call': self._handle_icx_call,
            'icx_sendTransaction': self._handle_icx_sendTransaction
        }

        # The precommit state is the state that been already invoked,
        # but not written to levelDB or file system.
        self._PrecommitState = namedtuple(
            'PrecommitState', ['block_batch', 'block_result'])
        self._step_counter_factory: IconScoreStepCounterFactory = None

    def open(self,
             icon_score_root_path: str,
             state_db_root_path: str) -> None:
        """Get necessary parameters and initialize diverse objects

        :param icon_score_root_path:
        :param state_db_root_path:
        """
        if not os.path.isdir(icon_score_root_path):
            os.mkdir(icon_score_root_path)
        if not os.path.isdir(state_db_root_path):
            os.mkdir(state_db_root_path)

        self._db_factory = DatabaseFactory(state_db_root_path)
        self._context_factory = IconScoreContextFactory(max_size=5)
        self._icon_score_loader = IconScoreLoader(icon_score_root_path)

        self._icx_context_db = self._db_factory.create_by_name('icon_dex')
        self._icx_context_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_context_db)

        self._icx_engine = IcxEngine()
        self._icx_engine.open(self._icx_storage)

        self._icon_score_mapper = IconScoreInfoMapper(
            self._icx_storage, self._db_factory, self._icon_score_loader)

        self._icon_score_deployer = IconScoreDeployer(icon_score_root_path)
        self._icon_score_engine = IconScoreEngine(
            self._icx_storage,
            self._icon_score_mapper,
            self._icon_score_deployer)
        self._step_counter_factory = IconScoreStepCounterFactory(
            6000, 200, 50, -100, 10000, 1000, 20)

    def close(self) -> None:
        """Free all resources occupied by IconServiceEngine
        including db, memory and so on
        """
        self._icx_engine.close()

    def genesis_invoke(self, accounts: list) -> None:
        """Process the list of account info in the genesis block

        :param accounts: account infos in the genesis block
        """

        context = self._context_factory.create(IconScoreContextType.GENESIS)

        genesis_account = accounts[0]
        self._icx_engine.init_genesis_account(
            context=context,
            address=genesis_account['address'],
            amount=genesis_account['balance'])

        fee_treasury_account = accounts[1]
        self._icx_engine.init_fee_treasury_account(
            context=context,
            address=fee_treasury_account['address'],
            amount=fee_treasury_account['balance'])

        self._context_factory.destroy(context)

    @check_exception
    def invoke(self,
               block_height: int,
               block_hash: str,
               block_timestamp: int,
               transactions) -> 'IconBlockResult':
        """Process transactions in a block sent by loopchain

        :param block_height:
        :param block_hash:
        :param block_timestamp:
        :param transactions: transactions in a block
        :return: The results of transactions
        """
        context = self._context_factory.create(IconScoreContextType.INVOKE)
        context.block = Block(block_height, block_hash, block_timestamp)
        context.block_batch = BlockBatch(block_height, block_hash)
        context.tx_batch = TransactionBatch()
        block_result = IconBlockResult(JsonSerializer())

        for i, tx in enumerate(transactions):
            method = tx['method']
            params = tx['params']
            _from = params['from']

            context.tx = Transaction(tx_hash=params['txHash'],
                                     index=i,
                                     origin=_from,
                                     timestamp=params['timestamp'],
                                     nonce=params.get('nonce', None))

            context.msg = Message(sender=_from, value=params.get('value', 0))

            context.step_counter: IconScoreStepCounter = \
                self._step_counter_factory.create(params.get('step', 5000000))

            tx_result: TransactionResult = self.call(context, method, params)
            tx_result.step_used = context.step_counter.step_used
            block_result.append(tx_result)

            context.block_batch.put_tx_batch(context.tx_batch)
            context.tx_batch.clear()

        # precommit_state will be written to levelDB on commit()
        self._precommit_state = self._PrecommitState(
            block_batch=context.block_batch,
            block_result=block_result)

        self._context_factory.destroy(context)
        return block_result

    @check_exception
    def query(self, method: str, params: dict) -> object:
        """Process a query message call from outside

        State change is not allowed in a query message call

        * icx_getBalance
        * icx_getTotalSupply
        * icx_call

        :param method:
        :param params:
        :return: the result of query
        """
        context = self._context_factory.create(IconScoreContextType.QUERY)

        if params:
            from_ = params.get('from', None)
            context.msg = Message(sender=from_)

        ret = self.call(context, method, params)

        self._context_factory.destroy(context)

        return ret

    def call(self,
             context: 'IconScoreContext',
             method: str,
             params: dict) -> object:
        """Call invoke and query requests in jsonrpc format

        This method is designed to be called in icon_outer_service.py.
        We assume that all param values have been already converted to the proper types.
        (types: Address, int, str, bool, bytes and array)

        invoke: Changes states of icon scores or icx
        query: query states of icon scores or icx without state changing

        :param context:
        :param method: 'icx_sendTransaction' only
        :param params: params in jsonrpc message
        :return:
            icx_sendTransaction: (bool) True(success) or False(failure)
            icx_getBalance, icx_getTotalSupply, icx_call:
                (dict) result or error object in jsonrpc response
        """
        try:
            handler = self._handlers[method]
            return handler(context, params)
        except KeyError as ke:
            Logger.error(ke, ICON_SERVICE_LOG_TAG)
        except Exception as e:
            Logger.error(e, ICON_SERVICE_LOG_TAG)

    def _handle_icx_getBalance(self,
                               context: 'IconScoreContext',
                               params: dict) -> int:
        """Returns the icx balance of the given address

        :param context:
        :param params:
        :return: icx balance in loop
        """
        address = params['address']
        return self._icx_engine.get_balance(context, address)

    def _handle_icx_getTotalSupply(self,
                                   context: 'IconScoreContext',
                                   params: dict) -> int:
        """Returns the amount of icx total supply

        :param context:
        :return: icx amount in loop (1 icx == 1e18 loop)
        """
        return self._icx_engine.get_total_supply(context)

    def _handle_icx_call(self,
                         context: 'IconScoreContext',
                         params: dict) -> object:
        """Handles an icx_call jsonrpc request

        State change is possible in icx_call message

        :param params:
        :return:
        """
        icon_score_address: Address = params['to']
        data_type = params.get('dataType', None)
        data = params.get('data', None)

        return self._icon_score_engine.query(context,
                                             icon_score_address,
                                             data_type,
                                             data)

    def _handle_icx_sendTransaction(self,
                                    context: 'IconScoreContext',
                                    params: dict) -> 'TransactionResult':
        """icx_sendTransaction message handler

        * EOA to EOA
        * EOA to Score

        :param params: jsonrpc params
        :return: return value of an IconScoreBase method
            None is allowed
        """
        _from: Address = params['from']
        to: Address = params['to']
        value: int = params.get('value', 0)

        self._icx_engine.transfer(context, _from, to, value)

        if to is None or to.is_contract:
            # EOA to Score
            data_type: str = params.get('dataType')
            data: dict = params.get('data')
            tx_result = self.__handle_score_invoke(
                context, to, data_type, data)
        else:
            # EOA to EOA
            tx_result = TransactionResult(context.tx.hash,
                                          context.block,
                                          to,
                                          TransactionResult.SUCCESS)

        return tx_result

    def __handle_score_invoke(self,
                              context: 'IconScoreContext',
                              to: Address,
                              data_type: str,
                              data: dict) -> 'TransactionResult':
        """Handle score invocation

        :param tx_hash: transaction hash
        :param to: a recipient address
        :param context:
        :param data_type:
        :param data: calldata
        :return: A result of the score transaction
        """
        tx_result = TransactionResult(context.tx.hash, context.block, to)

        try:
            if data_type == 'install':
                content_type = data.get('contentType')
                if content_type == 'application/tbears':
                    content = data.get('content')
                    proj_name = content.split('/')[-1]
                    to = create_address(AddressPrefix.CONTRACT, proj_name.encode())
                else:
                    to = self.__generate_contract_address(
                        context.tx.origin, context.tx.timestamp, context.tx.nonce)
                tx_result.contract_address = to

            self._icon_score_engine.invoke(context, to, data_type, data)

            context.block_batch.put_tx_batch(context.tx_batch)
            context.tx_batch.clear()

            tx_result.status = TransactionResult.SUCCESS
        except:
            tx_result.status = TransactionResult.FAILURE

        return tx_result

    @staticmethod
    def __generate_contract_address(from_: 'Address',
                                    timestamp: int,
                                    nonce: int = None) -> 'Address':
        """Generates a contract address from the transaction information.

        :param from_:
        :param timestamp:
        :param nonce:
        :return: score address
        """
        data = from_.body + timestamp.to_bytes(32, 'big')
        if nonce is not None:
            data += nonce.to_bytes(32, 'big')

        return create_address(AddressPrefix.CONTRACT, data)

    def commit(self):
        """Write updated states in a context.block_batch to StateDB
        when the candidate block has been confirmed
        """
        if self._precommit_state is None:
            raise IconException(
                ExceptionCode.INTERNAL_ERROR,
                'Precommit state is none on commit')

        Logger.debug(f'precommit: {self._precommit_state.block_batch}', ICON_SERVICE_LOG_TAG)

        context = self._context_factory.create(IconScoreContextType.GENESIS)
        block_batch = self._precommit_state.block_batch

        for address in block_batch:
            if address == ICX_ENGINE_ADDRESS:
                context_db = self._icx_context_db
            else:
                icon_score = self._icon_score_mapper.get_icon_score(address)
                context_db = icon_score.db._context_db

            context_db.write_batch(context=None, states=block_batch[address])

        self._icon_score_engine.commit(context)
        self._precommit_state = None

        self._context_factory.destroy(context)

    def rollback(self):
        """Throw away a precommit state
        in context.block_batch and IconScoreEngine
        """
        self._precommit_state = None
        self._icon_score_engine.rollback()
