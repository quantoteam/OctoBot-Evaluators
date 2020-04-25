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
from octobot_commons.enums import TimeFrames
from octobot_evaluators.evaluator.abstract_evaluator import AbstractEvaluator
from octobot_evaluators.util.evaluation_util import get_shortest_time_frame
from octobot_tentacles_manager.api.configurator import get_tentacle_config


class RealTimeEvaluator(AbstractEvaluator):
    __metaclass__ = AbstractEvaluator

    def __init__(self):
        super().__init__()
        self.load_config()

    def load_config(self):
        self.set_default_config()
        self.specific_config.update(get_tentacle_config(self.__class__))

    def get_symbol_candles(self, exchange_name: str, exchange_id: str, symbol: str, time_frame):
        try:
            from octobot_trading.api.symbol_data import get_symbol_candles_manager
            return get_symbol_candles_manager(self.get_exchange_symbol_data(exchange_name, exchange_id, symbol),
                                              time_frame)
        except ImportError:
            self.logger.error(f"Can't get candles manager: requires OctoBot-Trading package installed")

    def _get_tentacle_registration_topic(self, all_symbols_by_crypto_currencies, time_frames, real_time_time_frames):
        currencies, symbols, _ = super()._get_tentacle_registration_topic(all_symbols_by_crypto_currencies,
                                                                          time_frames,
                                                                          real_time_time_frames)
        to_handle_time_frames = []
        if self.time_frame is None:
            self.logger.error("Missing self.time_frame value, impossible to initialize this evaluator.")
        else:
            ideal_time_frame = TimeFrames(self.time_frame)
            to_handle_time_frame = get_shortest_time_frame(ideal_time_frame, real_time_time_frames, time_frames)
            if ideal_time_frame != to_handle_time_frame:
                self.logger.warning(f"Missing {ideal_time_frame.name} time frame in available time frames, "
                                    f"using {to_handle_time_frame.name} instead.")
            to_handle_time_frames = [to_handle_time_frame]
        # by default time frame registration only for the timeframe of this real-time evaluator
        return currencies, symbols, to_handle_time_frames

