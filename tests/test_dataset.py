import numpy as np
import pytest
import os

from collections import deque
from sklearn.model_selection import train_test_split
from d3rlpy.dataset import MDPDataset, Episode, Transition, TransitionMiniBatch
from d3rlpy.dataset import compute_lambda_return


@pytest.mark.parametrize("data_size", [100])
@pytest.mark.parametrize("observation_size", [4])
@pytest.mark.parametrize("action_size", [2])
@pytest.mark.parametrize("n_episodes", [4])
@pytest.mark.parametrize("discrete_action", [True, False])
def test_mdp_dataset(
    data_size, observation_size, action_size, n_episodes, discrete_action
):
    observations = np.random.random((data_size, observation_size)).astype("f4")
    rewards = np.random.uniform(-10.0, 10.0, size=data_size).astype("f4")
    n_steps = data_size // n_episodes
    terminals = np.array(([0] * (n_steps - 1) + [1]) * n_episodes)

    if discrete_action:
        actions = np.random.randint(action_size, size=data_size)
        ref_action_size = np.max(actions) + 1
    else:
        actions = np.random.random((data_size, action_size)).astype("f4")
        ref_action_size = action_size

    dataset = MDPDataset(
        observations=observations,
        actions=actions,
        rewards=rewards,
        terminals=terminals,
        discrete_action=discrete_action,
    )

    # check MDPDataset methods
    assert np.all(dataset.observations == observations)
    assert np.all(dataset.actions == actions)
    assert np.all(dataset.rewards == rewards)
    assert np.all(dataset.terminals == terminals)
    assert dataset.size() == n_episodes
    assert dataset.get_action_size() == action_size
    assert dataset.get_observation_shape() == (observation_size,)
    assert dataset.is_action_discrete() == discrete_action

    # check stats
    ref_returns = []
    for i in range(n_episodes):
        episode_return = 0.0
        for j in range(1, n_steps):
            episode_return += rewards[j + i * n_steps]
        ref_returns.append(episode_return)

    stats = dataset.compute_stats()
    return_stats = stats["return"]
    assert np.allclose(return_stats["mean"], np.mean(ref_returns))
    assert np.allclose(return_stats["std"], np.std(ref_returns))
    assert np.allclose(return_stats["min"], np.min(ref_returns))
    assert np.allclose(return_stats["max"], np.max(ref_returns))
    reward_stats = stats["reward"]
    assert np.allclose(reward_stats["mean"], np.mean(rewards))
    assert np.allclose(reward_stats["std"], np.std(rewards))
    assert np.allclose(reward_stats["min"], np.min(rewards))
    assert np.allclose(reward_stats["max"], np.max(rewards))
    observation_stats = stats["observation"]
    assert np.all(observation_stats["mean"] == np.mean(observations, axis=0))
    assert np.all(observation_stats["std"] == np.std(observations, axis=0))
    if discrete_action:
        freqs, action_ids = stats["action"]["histogram"]
        assert np.sum(freqs) == data_size
        assert list(action_ids) == [i for i in range(action_size)]
    else:
        action_stats = stats["action"]
        assert np.all(action_stats["mean"] == np.mean(actions, axis=0))
        assert np.all(action_stats["std"] == np.std(actions, axis=0))
        assert np.all(action_stats["min"] == np.min(actions, axis=0))
        assert np.all(action_stats["max"] == np.max(actions, axis=0))
        assert len(action_stats["histogram"]) == action_size
        for freqs, _ in action_stats["histogram"]:
            assert np.sum(freqs) == data_size

    # check episodes exported from dataset
    episodes = dataset.episodes
    assert len(episodes) == n_episodes
    for i, e in enumerate(dataset.episodes):
        assert isinstance(e, Episode)
        assert e.size() == n_steps - 1
        head = i * n_steps
        tail = head + n_steps
        assert np.all(e.observations == observations[head:tail])
        assert np.all(e.actions == actions[head:tail])
        assert np.all(e.rewards == rewards[head:tail])
        assert e.get_observation_shape() == (observation_size,)
        assert e.get_action_size() == ref_action_size

    # check list-like behaviors
    assert len(dataset) == n_episodes
    assert dataset[0] is dataset.episodes[0]
    for i, episode in enumerate(dataset.episodes):
        assert isinstance(episode, Episode)
        assert episode is dataset.episodes[i]

    # check append
    dataset.append(observations, actions, rewards, terminals)
    assert len(dataset) == 2 * n_episodes
    assert dataset.observations.shape == (2 * data_size, observation_size)
    assert dataset.rewards.shape == (2 * data_size,)
    assert dataset.terminals.shape == (2 * data_size,)
    if discrete_action:
        assert dataset.actions.shape == (2 * data_size,)
    else:
        assert dataset.actions.shape == (2 * data_size, action_size)

    # check extend
    another_dataset = MDPDataset(
        observations, actions, rewards, terminals, discrete_action
    )
    dataset.extend(another_dataset)
    assert len(dataset) == 3 * n_episodes
    assert dataset.observations.shape == (3 * data_size, observation_size)
    assert dataset.rewards.shape == (3 * data_size,)
    assert dataset.terminals.shape == (3 * data_size,)
    if discrete_action:
        assert dataset.actions.shape == (3 * data_size,)
    else:
        assert dataset.actions.shape == (3 * data_size, action_size)

    # check clip_reward
    dataset.clip_reward(-1.0, 1.0)
    assert rewards[rewards > 1.0].sum() != 0
    assert rewards[rewards < -1.0].sum() != 0
    assert dataset.rewards[dataset.rewards > 1.0].sum() == 0
    assert dataset.rewards[dataset.rewards < -1.0].sum() == 0

    # check dump and load
    dataset.dump(os.path.join("test_data", "dataset.h5"))
    new_dataset = MDPDataset.load(os.path.join("test_data", "dataset.h5"))
    assert np.all(dataset.observations == new_dataset.observations)
    assert np.all(dataset.actions == new_dataset.actions)
    assert np.all(dataset.rewards == new_dataset.rewards)
    assert np.all(dataset.terminals == new_dataset.terminals)
    assert dataset.discrete_action == new_dataset.discrete_action
    assert len(dataset) == len(new_dataset)


@pytest.mark.parametrize("data_size", [100])
@pytest.mark.parametrize("observation_size", [4])
@pytest.mark.parametrize("action_size", [2])
def test_episode(data_size, observation_size, action_size):
    observations = np.random.random((data_size, observation_size)).astype("f4")
    actions = np.random.random((data_size, action_size)).astype("f4")
    rewards = np.random.random(data_size).astype("f4")

    episode = Episode(
        observation_shape=(observation_size,),
        action_size=action_size,
        observations=observations,
        actions=actions,
        rewards=rewards,
    )

    # check Episode methods
    assert np.all(episode.observations == observations)
    assert np.all(episode.actions == actions)
    assert np.all(episode.rewards == rewards)
    assert episode.size() == data_size - 1
    assert episode.get_observation_shape() == (observation_size,)
    assert episode.get_action_size() == action_size
    assert episode.compute_return() == np.sum(rewards[1:])

    # check transitions exported from episode
    assert len(episode.transitions) == data_size - 1
    for i, t in enumerate(episode.transitions):
        assert isinstance(t, Transition)
        assert t.get_observation_shape() == (observation_size,)
        assert t.get_action_size() == action_size
        assert np.all(t.observation == observations[i])
        assert np.all(t.action == actions[i])
        assert np.allclose(t.reward, rewards[i])
        assert np.all(t.next_observation == observations[i + 1])
        assert np.all(t.next_action == actions[i + 1])
        assert np.allclose(t.next_reward, rewards[i + 1])
        assert t.terminal == (1.0 if (i == data_size - 2) else 0.0)

    # check forward pointers
    count = 1
    transition = episode[0]
    while transition.next_transition:
        transition = transition.next_transition
        count += 1
    assert count == data_size - 1

    # check backward pointers
    count = 1
    transition = episode[-1]
    while transition.prev_transition:
        transition = transition.prev_transition
        count += 1
    assert count == data_size - 1

    # check list-like bahaviors
    assert len(episode) == data_size - 1
    assert episode[0] is episode.transitions[0]
    for i, transition in enumerate(episode):
        assert isinstance(transition, Transition)
        assert transition is episode.transitions[i]


@pytest.mark.parametrize("data_size", [100])
@pytest.mark.parametrize("observation_shape", [(100,), (4, 84, 84)])
@pytest.mark.parametrize("action_size", [2])
@pytest.mark.parametrize("n_frames", [1, 4])
@pytest.mark.parametrize("n_steps", [1, 3])
@pytest.mark.parametrize("gamma", [0.99])
@pytest.mark.parametrize("discrete_action", [False, True])
def test_transition_minibatch(
    data_size,
    observation_shape,
    action_size,
    n_frames,
    n_steps,
    gamma,
    discrete_action,
):
    if len(observation_shape) == 3:
        observations = np.random.randint(
            256, size=(data_size, *observation_shape), dtype=np.uint8
        )
    else:
        observations = np.random.random(
            (data_size,) + observation_shape
        ).astype("f4")
    if discrete_action:
        actions = np.random.randint(action_size, size=data_size)
    else:
        actions = np.random.random((data_size, action_size)).astype("f4")
    rewards = np.random.random((data_size, 1)).astype("f4")

    episode = Episode(
        observation_shape=observation_shape,
        action_size=action_size,
        observations=observations,
        actions=actions,
        rewards=rewards,
    )

    if len(observation_shape) == 3:
        n_channels = n_frames * observation_shape[0]
        image_size = observation_shape[1:]
        batched_observation_shape = (data_size - 1, n_channels, *image_size)
    else:
        batched_observation_shape = (data_size - 1, *observation_shape)

    batch = TransitionMiniBatch(episode.transitions, n_frames, n_steps, gamma)
    assert batch.observations.shape == batched_observation_shape
    assert batch.next_observations.shape == batched_observation_shape

    for i, t in enumerate(episode.transitions):
        observation = batch.observations[i]
        next_observation = batch.next_observations[i]
        n = int(batch.n_steps[i][0])
        print(i)

        assert n == min(data_size - i - 1, n_steps)

        if n_frames > 1 and len(observation_shape) == 3:
            # create padded observations for check stacking
            pad = ((n_frames - 1, 0), (0, 0), (0, 0), (0, 0))
            padded_observations = np.pad(observations, pad, "edge")

            # check frame stacking
            head_index = i
            tail_index = head_index + n_frames
            window = padded_observations[head_index:tail_index]
            next_window = padded_observations[head_index + n : tail_index + n]
            ref_observation = np.vstack(window)
            ref_next_observation = np.vstack(next_window)
            assert observation.shape == ref_observation.shape
            assert next_observation.shape == ref_next_observation.shape
            assert np.all(observation == ref_observation)
            assert np.all(next_observation == ref_next_observation)
        else:
            next_t = t
            for _ in range(n - 1):
                next_t = next_t.next_transition
            assert np.allclose(observation, t.observation)
            assert np.allclose(next_observation, next_t.next_observation)

        next_reward = 0.0
        next_action = 0.0
        terminal = 0.0
        next_t = t
        for j in range(n):
            next_reward += next_t.next_reward * gamma ** j
            next_action = next_t.next_action
            terminal = next_t.terminal
            next_t = next_t.next_transition

        assert np.all(batch.actions[i] == t.action)
        assert np.all(batch.rewards[i][0] == t.reward)
        assert np.all(batch.next_actions[i] == next_action)
        assert np.allclose(batch.next_rewards[i][0], next_reward)
        assert np.all(batch.terminals[i][0] == terminal)

    # check list-like behavior
    assert len(batch) == data_size - 1
    assert batch[0] is episode.transitions[0]
    for i, transition in enumerate(batch):
        assert isinstance(transition, Transition)
        assert transition is episode.transitions[i]


@pytest.mark.parametrize("data_size", [100])
@pytest.mark.parametrize("observation_shape", [(100,), (4, 84, 84)])
@pytest.mark.parametrize("action_size", [2])
@pytest.mark.parametrize("n_frames", [1, 4])
@pytest.mark.parametrize("gamma", [0.99])
@pytest.mark.parametrize("lam", [0.95])
def test_compute_lambda_return(
    data_size, observation_shape, action_size, n_frames, gamma, lam
):
    if len(observation_shape) == 3:
        observations = np.random.randint(
            256, size=(data_size, *observation_shape), dtype=np.uint8
        )
    else:
        observations = np.random.random(
            (data_size,) + observation_shape
        ).astype("f4")
    actions = np.random.random((data_size, action_size)).astype("f4")
    rewards = np.random.random((data_size, 1)).astype("f4")

    episode = Episode(
        observation_shape=observation_shape,
        action_size=action_size,
        observations=observations,
        actions=actions,
        rewards=rewards,
    )

    class DummyAlgo:
        def predict_value(self, observations):
            batch_size = observations.shape[0]
            return np.mean(observations.reshape((batch_size, -1)), axis=1)

    algo = DummyAlgo()

    transitions = episode.transitions
    transition = transitions[3]

    # compute reference naively
    t = transition
    observations = []
    returns = []
    R = 0.0
    for i in range(data_size):
        observation = TransitionMiniBatch([t], n_frames).next_observations[0]
        observations.append(observation)
        R += (gamma ** i) * t.next_reward
        returns.append(R)
        t = t.next_transition
        if t is None:
            break
    values = algo.predict_value(np.array(observations))
    values[-1] = 0.0
    gammas = gamma ** (np.arange(len(observations)) + 1)
    returns += gammas * values

    lambdas = lam ** np.arange(len(observations))
    ref_lambda_return = (1.0 - lam) * np.sum(lambdas[:-1] * returns[:-1])
    ref_lambda_return += lambdas[-1] * returns[-1]

    # compute lambda return
    lambda_return = compute_lambda_return(
        transition, algo, gamma, lam, n_frames
    )

    assert np.allclose(ref_lambda_return, lambda_return)


@pytest.mark.parametrize("data_size", [100])
@pytest.mark.parametrize("observation_size", [4])
@pytest.mark.parametrize("action_size", [2])
@pytest.mark.parametrize("n_episodes", [10])
@pytest.mark.parametrize("test_size", [0.2])
def test_dataset_with_sklearn(
    data_size, observation_size, action_size, n_episodes, test_size
):
    observations = np.random.random((data_size, observation_size)).astype("f4")
    actions = np.random.random((data_size, action_size))
    rewards = np.random.random(data_size)
    n_steps = data_size // n_episodes
    terminals = np.array(([0] * (n_steps - 1) + [1]) * n_episodes)

    dataset = MDPDataset(observations, actions, rewards, terminals)

    # check compatibility with train_test_split
    train_episodes, test_episodes = train_test_split(
        dataset, test_size=test_size
    )
    assert len(train_episodes) == int(n_episodes * (1.0 - test_size))
    assert len(test_episodes) == int(n_episodes * test_size)
