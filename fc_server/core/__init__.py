# -*- coding: utf-8 -*-

import os
from core.logger import Logger
from core.config import Config


fc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
Logger.init(fc_path)
Config.parse(fc_path)
