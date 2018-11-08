import tensorflow as tf

from zfit.core.minimizer import BaseMinimizer


class WrapOptimizer(BaseMinimizer):
    def __init__(self, optimizer, *args, **kwargs):
        if not isinstance(optimizer, tf.train.Optimizer):
            raise TypeError("optimizer {} has to be from class Optimizer".format(str(optimizer)))
        # TODO auto-initialize variables?
        super().__init__(*args, **kwargs)
        self._optimizer_tf = optimizer

    def _step_tf(self, params):
        loss = self.loss
        # var_list = self.get_parameters()
        var_list = params
        minimization_step = self._optimizer_tf.minimize(loss=loss, var_list=var_list)

        # auto-initialize variables from optimizer
        optimizer_vars = list(self._optimizer_tf.variables())
        # all_params = self.get_parameters(only_floating=False) + optimizer_vars
        all_params = optimizer_vars
        is_initialized = [tf.is_variable_initialized(p) for p in all_params]
        is_initialized = self.sess.run(is_initialized)
        inits = [p.initializer for p, is_init in zip(all_params, is_initialized) if not is_init]
        if inits:
            self.sess.run(inits)

        return minimization_step
