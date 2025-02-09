import numpy as np
import pytest
import gym

from d3rlpy.online.buffers import ReplayBuffer
from d3rlpy.dataset import TransitionMiniBatch, Episode


@pytest.mark.parametrize("n_episodes", [10])
@pytest.mark.parametrize("batch_size", [32])
@pytest.mark.parametrize("maxlen", [50])
def test_replay_buffer(n_episodes, batch_size, maxlen):
    env = gym.make("CartPole-v0")

    buffer = ReplayBuffer(maxlen, env)

    total_step = 0
    for episode in range(n_episodes):
        observation, reward, terminal = env.reset(), 0.0, False
        while not terminal:
            action = env.action_space.sample()
            buffer.append(observation.astype("f4"), action, reward, terminal)
            observation, reward, terminal, _ = env.step(action)
            total_step += 1
        buffer.append(observation.astype("f4"), action, reward, terminal)
        total_step += 1

    assert len(buffer) == maxlen

    observation_shape = env.observation_space.shape
    batch = buffer.sample(batch_size)
    assert len(batch) == batch_size
    assert batch.observations.shape == (batch_size,) + observation_shape
    assert batch.actions.shape == (batch_size,)
    assert batch.rewards.shape == (batch_size, 1)
    assert batch.next_observations.shape == (batch_size,) + observation_shape
    assert batch.next_actions.shape == (batch_size,)
    assert batch.next_rewards.shape == (batch_size, 1)
    assert batch.terminals.shape == (batch_size, 1)
    assert isinstance(batch.observations, np.ndarray)
    assert isinstance(batch.next_observations, np.ndarray)


@pytest.mark.parametrize("maxlen", [200])
@pytest.mark.parametrize("data_size", [100])
def test_replay_buffer_with_episode(maxlen, data_size):
    env = gym.make("CartPole-v0")

    observation_shape = env.observation_space.shape
    action_size = env.action_space.n

    observations = np.random.random((data_size, *observation_shape))
    actions = np.random.randint(action_size, size=data_size, dtype=np.int32)
    rewards = np.random.random(data_size)

    episode = Episode(
        observation_shape=observation_shape,
        action_size=action_size,
        observations=observations.astype("f4"),
        actions=actions,
        rewards=rewards.astype("f4"),
    )

    buffer = ReplayBuffer(maxlen, env, episodes=[episode])

    # check episode initialization
    assert len(buffer) == data_size - 1

    # check append_episode
    buffer.append_episode(episode)
    assert len(buffer) == 2 * (data_size - 1)
