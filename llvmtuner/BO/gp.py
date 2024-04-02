###############################################################################
# Copyright (c) 2019 Uber Technologies, Inc.                                  #
#                                                                             #
# Licensed under the Uber Non-Commercial License (the "License");             #
# you may not use this file except in compliance with the License.            #
# You may obtain a copy of the License at the root directory of this project. #
#                                                                             #
# See the License for the specific language governing permissions and         #
# limitations under the License.                                              #
###############################################################################
# from __future__ import annotations
import math

import gpytorch
import numpy as np
import torch
from gpytorch.constraints.constraints import Interval, GreaterThan
from gpytorch.distributions import MultivariateNormal
from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel, CylindricalKernel, InducingPointKernel, GridInterpolationKernel, RFFKernel
from gpytorch.kernels.keops import MaternKernel as KMaternKernel
from gpytorch.likelihoods import GaussianLikelihood
from gpytorch.means import ConstantMean
from gpytorch.mlls import ExactMarginalLogLikelihood
from gpytorch.models import ExactGP
from botorch.models.gpytorch import GPyTorchModel
from botorch.fit import fit_gpytorch_model
from botorch.models import SingleTaskGP, FixedNoiseGP, MixedSingleTaskGP
from botorch.models.transforms.input import Normalize, Warp, ReversibleInputTransform
from gpytorch.priors.torch_priors import LogNormalPrior

class GP(ExactGP, GPyTorchModel):
    _num_outputs = 1 
    def __init__(self, train_x, train_y, likelihood, lengthscale_constraint, outputscale_constraint, ard_dims):
        super(GP, self).__init__(train_x, train_y.squeeze(-1), likelihood)
        self.ard_dims = ard_dims
        self.mean_module = ConstantMean()
        base_kernel = MaternKernel(lengthscale_constraint=lengthscale_constraint, ard_num_dims=ard_dims, nu=2.5)
        self.covar_module = ScaleKernel(base_kernel, outputscale_constraint=outputscale_constraint)


    def forward(self, x):
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return MultivariateNormal(mean_x, covar_x)



def train_gp(train_x, train_y, cat_dims=[], use_ard=True, use_input_warping=False, num_steps=50, lr=0.1, hypers={}):
    """Fit a GP model where train_x is in [0, 1]^d and train_y is standardized."""
    assert train_x.shape[0] == train_y.shape[0]
    n_dim=train_x.shape[-1]
    if len(cat_dims) == 0:
       
        # Create models
        noise_constraint = Interval(1e-6, 0.05)#0.05
        if use_ard:
            lengthscale_constraint = Interval(0.005, 100.0)
        else:
            lengthscale_constraint = Interval(0.005, math.sqrt(train_x.shape[1]))  # [0.005, sqrt(dim)]
        outputscale_constraint = Interval(0.05, 20.0)
        likelihood = GaussianLikelihood(noise_constraint=noise_constraint).to(device=train_x.device, dtype=train_y.dtype)
        ard_dims = n_dim if use_ard else None
        
        if use_input_warping:
            # initialize input_warping transformation
            warp_tf = Warp(
                indices=list(range(train_x.shape[-1])),
                # concentration1_prior=LogNormalPrior(0.0, 0.75 ** 0.5),
                # concentration0_prior=LogNormalPrior(0.0, 0.75 ** 0.5),
            )
            likelihood = GaussianLikelihood(noise_constraint=noise_constraint)
            covar_module = ScaleKernel(  
                MaternKernel(nu=2.5, ard_num_dims=ard_dims, lengthscale_constraint=lengthscale_constraint),
                outputscale_constraint=outputscale_constraint
            )
            
            model = SingleTaskGP(train_x, train_y, likelihood=likelihood, 
                                 covar_module=covar_module, 
                                 input_transform=warp_tf
                                 )
                      
        else:
            likelihood = GaussianLikelihood(noise_constraint=noise_constraint)
            covar_module = ScaleKernel(  
                MaternKernel(nu=2.5, ard_num_dims=ard_dims, lengthscale_constraint=lengthscale_constraint),
                outputscale_constraint=outputscale_constraint
            )
            model = SingleTaskGP(train_x, train_y, covar_module=covar_module, likelihood=likelihood
            ).to(device=train_x.device, dtype=train_x.dtype)
            # input_transform=Normalize(d=n_dim)
            # model = SingleTaskGP(train_x, train_y, covar_module=covar_module, likelihood=likelihood, input_transform=input_transform).to(device=train_x.device, dtype=train_x.dtype)
            
            
    else:
        cont_dims=list(set(range(n_dim))-set(cat_dims))
        if len(cont_dims)==0:
            model = MixedSingleTaskGP(train_x, train_y, cat_dims=cat_dims)
        else:
            input_transform=Normalize(d=n_dim, indices=cont_dims)
            model = MixedSingleTaskGP(train_x, train_y, cat_dims=cat_dims, input_transform=input_transform)


    
        # model = GP(
        #     train_x=train_x,
        #     train_y=train_y,
        #     likelihood=likelihood,
        #     lengthscale_constraint=lengthscale_constraint,
        #     outputscale_constraint=outputscale_constraint,
        #     ard_dims=ard_dims,
        # ).to(device=train_x.device, dtype=train_x.dtype)
    
    
    
    
    # Find optimal model hyperparameters
    model.train()
    likelihood.train()
    

    # "Loss" for GPs - the marginal log likelihood
    mll = ExactMarginalLogLikelihood(likelihood, model).to(train_x)

    # Initialize model hypers
    if hypers:
        model.load_state_dict(hypers)
    else:
        hypers = {}
        hypers["covar_module.outputscale"] = 1.0
        hypers["covar_module.base_kernel.lengthscale"] = 1.0
        hypers["likelihood.noise"] = 0.005
        model.initialize(**hypers)

    optimizer = torch.optim.Adam([{"params": model.parameters()}], lr=lr)      
    
    # if use_input_warping:
    #     my_list = ['input_transform.concentration0', 'input_transform.concentration1']
    #     warp_params = list(map(lambda x: x[1],list(filter(lambda kv: kv[0] in my_list, model.named_parameters()))))
    #     base_params = list(map(lambda x: x[1],list(filter(lambda kv: kv[0] not in my_list, model.named_parameters()))))
    #     optimizer = torch.optim.Adam([
    #                 {'params': base_params},
    #                 {'params': warp_params, 'lr': 0.1}
    #             ], lr=0.1)
    # else:
    #     optimizer = torch.optim.Adam([{"params": model.parameters()}], lr=0.1)  
    
    
    # for name, param in model.named_parameters():
    #     if param.requires_grad:
    #         print(name)
    
    # train_dataset = TensorDataset(train_x, train_y)
    # train_loader = DataLoader(train_dataset, batch_size=512, shuffle=True)
#     for _ in range(num_steps):
#         for x_batch, y_batch in train_loader: 
#             optimizer.zero_grad()
#             output = model(x_batch)
#             loss = -mll(output, y_batch.squeeze())
#             loss.backward()
#             optimizer.step()
#             if use_input_warping:
#                 with torch.no_grad():
#                     model.input_transform.concentration0.data.clamp_(1e-4, 1-1e-4)
#                     model.input_transform.concentration1.data.clamp_(1e-4, 1-1e-4)


    for step in range(num_steps):
        optimizer.zero_grad()
        output = model(train_x)
        loss = -mll(output, train_y.squeeze())
        loss.backward()
        optimizer.step()
        # print('step{} loss:'.format(step),loss.item())
        if use_input_warping:
            with torch.no_grad():
                model.input_transform.concentration0.data.clamp_(1e-5, 1e5)
                model.input_transform.concentration1.data.clamp_(1e-5, 1e5)
    posterior = model.posterior(train_x)
    y_pre = posterior.mean.view(-1).cpu().detach().numpy()
    y_train = train_y.squeeze().cpu().detach().numpy()
    residuals = y_pre - y_train
    squared_residuals = residuals ** 2
    rmse = np.sqrt(np.mean(squared_residuals))
    print('rmse:',rmse)
    max_error = np.max(np.abs(residuals))
    print('max_error:',max_error)


    # print(f'Noise constraint: {likelihood.noise_covar.raw_noise_constraint}')    
    # fit_gpytorch_model(mll)
    # Switch to eval mode
    
    # if use_input_warping:
    #     print(model.input_transform.concentration0.data)
    #     print(model.input_transform.concentration1.data)
    # print('loss:{}'.format(loss.item()))
    # print(model.state_dict())
    # print(likelihood.noise)
    
    
    # find features not in training samples but in candidates and modify the coresponding lengthscale
    tmp_x=train_x-train_x[0]
    mask = tmp_x.sum(dim=0)==0
    mask = mask.unsqueeze(0)
    # print(torch.min(model.covar_module.base_kernel.lengthscale).detach())
    # print(mask)
    # print(model.covar_module.base_kernel.lengthscale)
    # print(model.covar_module.base_kernel.lengthscale[mask])
    # a=model.covar_module.base_kernel.lengthscale.data
    # a[mask]=0.1
    # print(a)
    # model.covar_module.base_kernel.lengthscale.data=a
    # print(model.covar_module.base_kernel.lengthscale)
    
    
    lengthscale=model.covar_module.base_kernel.lengthscale
    # lengthscale[mask] = torch.min(model.covar_module.base_kernel.lengthscale).data
    lengthscale[mask] = 99
    model.covar_module.base_kernel.lengthscale=lengthscale

    model.eval()
    likelihood.eval()
    # print(model.covar_module.base_kernel.lengthscale)
    return model



