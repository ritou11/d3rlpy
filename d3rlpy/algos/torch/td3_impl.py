from typing import Optional, Sequence

import torch

from ...optimizers import OptimizerFactory
from ...encoders import EncoderFactory
from ...q_functions import QFunctionFactory
from ...gpu import Device
from ...preprocessing import Scaler
from ...augmentation import AugmentationPipeline
from .ddpg_impl import DDPGImpl


class TD3Impl(DDPGImpl):

    _target_smoothing_sigma: float
    _target_smoothing_clip: float

    def __init__(
        self,
        observation_shape: Sequence[int],
        action_size: int,
        actor_learning_rate: float,
        critic_learning_rate: float,
        actor_optim_factory: OptimizerFactory,
        critic_optim_factory: OptimizerFactory,
        actor_encoder_factory: EncoderFactory,
        critic_encoder_factory: EncoderFactory,
        q_func_factory: QFunctionFactory,
        gamma: float,
        tau: float,
        n_critics: int,
        bootstrap: bool,
        share_encoder: bool,
        target_smoothing_sigma: float,
        target_smoothing_clip: float,
        use_gpu: Optional[Device],
        scaler: Optional[Scaler],
        augmentation: AugmentationPipeline,
    ):
        super().__init__(
            observation_shape=observation_shape,
            action_size=action_size,
            actor_learning_rate=actor_learning_rate,
            critic_learning_rate=critic_learning_rate,
            actor_optim_factory=actor_optim_factory,
            critic_optim_factory=critic_optim_factory,
            actor_encoder_factory=actor_encoder_factory,
            critic_encoder_factory=critic_encoder_factory,
            q_func_factory=q_func_factory,
            gamma=gamma,
            tau=tau,
            n_critics=n_critics,
            bootstrap=bootstrap,
            share_encoder=share_encoder,
            use_gpu=use_gpu,
            scaler=scaler,
            augmentation=augmentation,
        )
        self._target_smoothing_sigma = target_smoothing_sigma
        self._target_smoothing_clip = target_smoothing_clip

    def compute_target(self, x: torch.Tensor) -> torch.Tensor:
        assert self._targ_policy is not None
        assert self._targ_q_func is not None
        with torch.no_grad():
            action = self._targ_policy(x)
            # smoothing target
            noise = torch.randn(action.shape, device=x.device)
            scaled_noise = self._target_smoothing_sigma * noise
            clipped_noise = scaled_noise.clamp(
                -self._target_smoothing_clip, self._target_smoothing_clip
            )
            smoothed_action = action + clipped_noise
            clipped_action = smoothed_action.clamp(-1.0, 1.0)
            return self._targ_q_func.compute_target(x, clipped_action)
