#  Copyright (c) 2021 zfit
import abc
from abc import abstractmethod
from collections import OrderedDict
from typing import Mapping, Union

import numpy as np

from .fitresult import FitResult
from .interface import ZfitMinimizer
from ..core.interfaces import ZfitLoss
from ..settings import run
from ..util import ztyping


class FailMinimizeNaN(Exception):
    pass


class ZfitStrategy(abc.ABC):
    @abstractmethod
    def minimize_nan(self, loss: ZfitLoss, params: ztyping.ParamTypeInput, minimizer: ZfitMinimizer,
                     values: Mapping = None) -> float:
        raise NotImplementedError


class BaseStrategy(ZfitStrategy):

    def __init__(self) -> None:
        self.fit_result = None
        self.error = None
        super().__init__()

    def minimize_nan(self, loss: ZfitLoss, params: ztyping.ParamTypeInput, minimizer: ZfitMinimizer,
                     values: Mapping = None) -> float:
        return self._minimize_nan(loss=loss, params=params, minimizer=minimizer, values=values)

    def _minimize_nan(self, loss: ZfitLoss, params: ztyping.ParamTypeInput, minimizer: ZfitMinimizer,
                      values: Mapping = None) -> (float, np.array):
        print("The minimization failed due to too many NaNs being produced in the loss."
              "This is most probably caused by negative"
              " values returned from the PDF. Changing the initial values/stepsize of the parameters can solve this"
              " problem. Also check your model (if custom) for problems. For more information,"
              " visit https://github.com/zfit/zfit/wiki/FAQ#fitting-and-minimization")
        raise FailMinimizeNaN()

    def __str__(self) -> str:
        return repr(self.__class__)[:-2].split(".")[-1]


class ToyStrategyFail(BaseStrategy):

    def __init__(self) -> None:
        super().__init__()
        self.fit_result = FitResult(params={}, edm=-999, fmin=-999, status=-999, converged=False, info={},
                                    loss=None, minimizer=None)

    def _minimize_nan(self, loss: ZfitLoss, params: ztyping.ParamTypeInput, minimizer: ZfitMinimizer,
                      values: Mapping = None) -> float:
        param_vals = run(params)
        param_vals = OrderedDict((param, value) for param, value in zip(params, param_vals))
        self.fit_result = FitResult(params=param_vals, edm=-999, fmin=-999, status=9, converged=False, info={},
                                    loss=loss,
                                    minimizer=minimizer)
        raise FailMinimizeNaN()


class PushbackStrategy(BaseStrategy):

    def __init__(self, nan_penalty: Union[float, int] = 100, nan_tolerance: int = 30, **kwargs):
        """Pushback by adding `nan_penalty * counter` to the loss if NaNs are encountered.

        The counter indicates how many NaNs occurred in a row. The `nan_tolerance` is the upper limit, if this is
        exceeded, the fallback will be used and an error is raised.

        Args:
            nan_penalty: Value to add to the previous loss in order to penalize the step taken.
            nan_tolerance: If the number of NaNs encountered in a row exceeds this number, the fallback is used.
        """
        super().__init__(**kwargs)
        self.nan_penalty = nan_penalty
        self.nan_tolerance = nan_tolerance

    def _minimize_nan(self, loss: ZfitLoss, params: ztyping.ParamTypeInput, minimizer: ZfitMinimizer,
                      values: Mapping = None) -> float:
        assert 'nan_counter' in values, "'nan_counter' not in values, minimizer not correctly implemented"
        nan_counter = values['nan_counter']
        if nan_counter < self.nan_tolerance:
            last_loss = values.get('old_loss')
            last_grad = values.get('old_grad')
            if last_grad is not None:
                last_grad = -last_grad
            if last_loss is not None:

                loss_evaluated = last_loss + self.nan_penalty * nan_counter
            else:
                loss_evaluated = values.get('loss')
            if isinstance(loss_evaluated, str):
                raise RuntimeError("Loss starts already with NaN, cannot minimize.")
            return loss_evaluated, last_grad
        else:
            super()._minimize_nan(loss=loss, params=params, minimizer=minimizer, values=values)


class DefaultToyStrategy(PushbackStrategy, ToyStrategyFail):
    """Same as :py:class:`PushbackStrategy`, but does not raise an error on full failure, instead return an invalid
    FitResult.

    This can be useful for toy studies, where multiple fits are done and a failure should simply be counted as a
    failure instead of rising an error.
    """
    pass