# -*- coding: utf-8 -*-
from utils import pex


class ATMChainError(Exception):
    """ Base exception, used to catch all raiden related exceptions. """
    pass


class EthNodeCommunicationError(ATMChainError):
    """ Raised when something unexpected has happened during
    communication with the underlying ethereum node"""
    pass
