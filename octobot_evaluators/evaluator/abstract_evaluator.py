#  Drakkar-Software OctoBot-Evaluators
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import time
from abc import ABCMeta, abstractmethod

from octobot_commons.constants import TENTACLES_EVALUATOR_PATH
from octobot_commons.tentacles_management.abstract_tentacle import AbstractTentacle

from octobot_evaluators.channels import MatrixChannelProducer, MatrixChannels, MATRIX_CHANNEL
from octobot_evaluators.constants import START_PENDING_EVAL_NOTE, START_EVAL_PERTINENCE, EVALUATOR_EVAL_DEFAULT_TYPE, \
    INIT_EVAL_NOTE, CONFIG_EVALUATOR


class AbstractEvaluator(AbstractTentacle, MatrixChannelProducer):
    __metaclass__ = ABCMeta

    def __init__(self):
        AbstractTentacle.__init__(self)
        MatrixChannelProducer.__init__(self, MatrixChannels.get_chan(MATRIX_CHANNEL))
        self.logger = None
        self.config = None
        self.specific_config = {}

        # If this indicator is enabled
        self.enabled = True

        # Symbol is the cryptocurrency symbol
        self.symbol = None

        # Evaluation related exchange name
        self.exchange_name = None

        # Time_frame is the chart time frame
        self.time_frame = None

        #  history time represents the period of time of the indicator
        self.history_time = None

        #  Eval note will be set by the eval_impl at each call
        self.eval_note = START_PENDING_EVAL_NOTE

        # Pertinence of indicator will be used with the eval_note to provide a relevancy
        self.pertinence = START_EVAL_PERTINENCE

        # Active tells if this evaluator is currently activated (an evaluator can be paused)
        self.is_active = True

        # set to true if start_task has to be called to start evaluator
        self.is_to_be_started_as_task = False

        self.eval_note_time_to_live = None
        self.eval_note_changed_time = None

    @staticmethod
    def get_eval_type():
        """
        Override this method when self.eval_note is other than : START_PENDING_EVAL_NOTE or float[-1:1]
        :return: type
        """
        return EVALUATOR_EVAL_DEFAULT_TYPE

    @classmethod
    @abstractmethod
    def get_config_tentacle_type(cls) -> str:
        pass

    @classmethod
    def get_tentacle_folder(cls) -> str:
        return TENTACLES_EVALUATOR_PATH

    async def evaluation_completed(self, eval_note) -> None:
        """
        Main async method to notify matrix to update
        :param eval_note:
        :return: None
        """
        try:
            self.ensure_eval_note_is_not_expired()
            await self.send_eval_note(evaluator_name=self.get_name(),
                                      evaluator_type=self.get_eval_type(),
                                      eval_note=eval_note,
                                      exchange_name=self.exchange_name,
                                      symbol=self.symbol,
                                      time_frame=self.time_frame)
        except Exception as e:
            # if ConfigManager.is_in_dev_mode(self.config): # TODO
            #     raise e
            # else:
            self.logger.error("Exception in evaluation_completed(): " + str(e))
            self.logger.exception(e)
        finally:
            if self.eval_note == "nan":
                self.eval_note = START_PENDING_EVAL_NOTE
                self.logger.warning(str(self.symbol) + " evaluator returned 'nan' as eval_note, ignoring this value.")

    async def start_evaluator(self) -> None:
        """
        Start a task as matrix producer
        :return: None
        """
        await self.start()
        self.logger.info("STARTED")
        await self.evaluation_completed(1)

    def set_config(self, config) -> None:
        """
        Used to provide the global config
        :param config: global config
        :return: None
        """
        self.config = config
        self.enabled = self.is_enabled(config, False)

    def set_default_config(self):
        """
        To implement in subclasses if config necessary
        :return:
        """
        self.specific_config = {}

    def reset(self) -> None:
        """
        Reset temporary parameters to enable fresh start
        :return: None
        """
        self.eval_note = START_PENDING_EVAL_NOTE

    @classmethod
    def has_class_in_parents(cls, klass) -> bool:
        """
        Explore up to the 2nd degree parent
        :param klass: python Class to explore
        :return: Boolean
        """
        if klass in cls.__bases__:
            return True
        elif any(klass in base.__bases__ for base in cls.__bases__):
            return True
        else:
            for base in cls.__bases__:
                if any(klass in super_base.__bases__ for super_base in base.__bases__):
                    return True
        return False

    @classmethod
    def get_parent_evaluator_classes(cls, higher_parent_class_limit=None) -> list:
        """
        Return the evaluator parent classe(s)
        :param higher_parent_class_limit:
        :return: list of classes
        """
        return [
            class_type
            for class_type in cls.mro()
            if (higher_parent_class_limit if higher_parent_class_limit else AbstractEvaluator) in class_type.mro()
        ]

    def set_eval_note(self, new_eval_note) -> None:
        """
        Performs additionnal check to eval_note before changing it
        :param new_eval_note:
        :return: None
        """
        self.eval_note_changed()

        if self.eval_note == START_PENDING_EVAL_NOTE:
            self.eval_note = INIT_EVAL_NOTE

        if self.eval_note + new_eval_note > 1:
            self.eval_note = 1
        elif self.eval_note + new_eval_note < -1:
            self.eval_note = -1
        else:
            self.eval_note += new_eval_note

    @classmethod
    def is_enabled(cls, config, default) -> dict:
        """
        Check if the evaluator is enabled by configuration
        :param config: global config
        :param default: default value if evaluator config is not found
        :return: evaluator config
        """
        if config[CONFIG_EVALUATOR] is not None:
            if cls.get_name() in config[CONFIG_EVALUATOR]:
                return config[CONFIG_EVALUATOR][cls.get_name()]
            else:
                for parent in cls.mro():
                    if parent.__name__ in config[CONFIG_EVALUATOR]:
                        return config[CONFIG_EVALUATOR][parent.__name__]
                return default

    def save_evaluation_expiration_time(self, eval_note_time_to_live, eval_note_changed_time=None) -> None:
        """
        Use only if the current evaluation is to stay for a pre-defined amount of seconds
        :param eval_note_time_to_live:
        :param eval_note_changed_time:
        :return: None
        """
        self.eval_note_time_to_live = eval_note_time_to_live
        self.eval_note_changed_time = eval_note_changed_time if eval_note_changed_time else time.time()

    def eval_note_changed(self) -> None:
        """
        Eval note changed callback
        :return: None
        """
        if self.eval_note_time_to_live is not None and self.eval_note_changed_time is None:
            self.eval_note_changed_time = time.time()

    def ensure_eval_note_is_not_expired(self) -> None:
        """
        Eval note expiration check
        :return: None
        """
        if self.eval_note_time_to_live is not None:
            if self.eval_note_changed_time is None:
                self.eval_note_changed_time = time.time()

            if time.time() - self.eval_note_changed_time > self.eval_note_time_to_live:
                self.eval_note = START_PENDING_EVAL_NOTE
                self.eval_note_time_to_live = None
                self.eval_note_changed_time = None