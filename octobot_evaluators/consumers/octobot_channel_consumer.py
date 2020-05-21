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
from enum import Enum

from octobot_channels.channels.channel_instances import get_chan_at_id
from octobot_commons.channels_name import OctoBotChannelsName
from octobot_commons.logging.logging_util import get_logger

from octobot_commons.enums import OctoBotChannelSubjects

from octobot_evaluators.api.evaluators import create_all_type_evaluators

OCTOBOT_CHANNEL_EVALUATOR_CONSUMER_LOGGER_TAG = "OctoBotChannelEvaluatorConsumer"


class OctoBotChannelEvaluatorActions(Enum):
    """
    OctoBot Channel consumer supported actions
    """

    EVALUATOR = "evaluator"


class OctoBotChannelEvaluatorDataKeys(Enum):
    """
    OctoBot Channel consumer supported data keys
    """

    EXCHANGE_CONFIGURATION = "exchange_configuration"
    MATRIX_ID = "matrix_id"
    TENTACLES_SETUP_CONFIG = "tentacles_setup_config"


async def octobot_channel_callback(bot_id, subject, action, data) -> None:
    """
    OctoBot channel consumer callback
    :param bot_id: the callback bot id
    :param subject: the callback subject
    :param action: the callback action
    :param data: the callback data
    """
    if subject == OctoBotChannelSubjects.CREATION.value:
        await _handle_creation(bot_id, action, data)


async def _handle_creation(bot_id, action, data):
    if action == OctoBotChannelEvaluatorActions.EVALUATOR.value:
        try:
            exchange_configuration = data[OctoBotChannelEvaluatorDataKeys.EXCHANGE_CONFIGURATION.value]
            await create_all_type_evaluators(
                tentacles_setup_config=data[OctoBotChannelEvaluatorDataKeys.TENTACLES_SETUP_CONFIG.value],
                matrix_id=data[OctoBotChannelEvaluatorDataKeys.MATRIX_ID.value],
                exchange_name=exchange_configuration.exchange_name,
                bot_id=bot_id,
                symbols_by_crypto_currencies=exchange_configuration.symbols_by_crypto_currencies,
                symbols=exchange_configuration.symbols,
                time_frames=exchange_configuration.time_frames_without_real_time,
                real_time_time_frames=exchange_configuration.real_time_time_frames
            )
            await get_chan_at_id(OctoBotChannelsName.OCTOBOT_CHANNEL.value, bot_id).get_internal_producer() \
                .send(bot_id=bot_id,
                      subject=OctoBotChannelSubjects.NOTIFICATION.value,
                      action=action,
                      data={OctoBotChannelEvaluatorDataKeys.MATRIX_ID.value:
                            data[OctoBotChannelEvaluatorDataKeys.MATRIX_ID.value]})

        except Exception as e:
            get_logger(OCTOBOT_CHANNEL_EVALUATOR_CONSUMER_LOGGER_TAG).error(f"Error when creating new evaluator {e}")
