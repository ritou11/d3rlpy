import pytest

from d3rlpy.algos.bcq import BCQ, DiscreteBCQ
from tests import performance_test
from .algo_test import algo_tester, algo_update_tester
from .algo_test import algo_pendulum_tester, algo_cartpole_tester


@pytest.mark.parametrize("observation_shape", [(100,), (4, 84, 84)])
@pytest.mark.parametrize("action_size", [2])
@pytest.mark.parametrize("q_func_factory", ["mean", "qr", "iqn", "fqf"])
@pytest.mark.parametrize("scaler", [None, "standard"])
def test_bcq(observation_shape, action_size, q_func_factory, scaler):
    bcq = BCQ(q_func_factory=q_func_factory, scaler=scaler)
    algo_tester(bcq, observation_shape)
    algo_update_tester(bcq, observation_shape, action_size)


@pytest.mark.skip(reason="BCQ is computationally expensive.")
def test_bcq_performance():
    bcq = BCQ(use_batch_norm=False)
    algo_pendulum_tester(bcq, n_trials=5)


@pytest.mark.parametrize("observation_shape", [(100,), (4, 84, 84)])
@pytest.mark.parametrize("action_size", [2])
@pytest.mark.parametrize("q_func_factory", ["mean", "qr", "iqn", "fqf"])
@pytest.mark.parametrize("scaler", [None, "standard"])
def test_discrete_bcq(observation_shape, action_size, q_func_factory, scaler):
    bcq = DiscreteBCQ(q_func_factory=q_func_factory, scaler=scaler)
    algo_tester(bcq, observation_shape)
    algo_update_tester(bcq, observation_shape, action_size, discrete=True)


@performance_test
@pytest.mark.parametrize("q_func_factory", ["mean", "qr", "iqn", "fqf"])
def test_discrete_bcq_performance(q_func_factory):
    bcq = DiscreteBCQ(q_func_factory=q_func_factory)
    algo_cartpole_tester(bcq)
