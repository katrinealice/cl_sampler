
# Project repository to build a Gibbs sampler for $C_{\ell}$ and $a_{lm}$ spherical harmonic modes. 

Work in progress ...

Currently using the [GCR sampler](https://github.com/katrinealice/sph_harm_GCR) as a 'base' and updating it to include the $C_{\ell}$ sampling too. 

## Current TODOs

* #TODO update initial guess?
* #TODO keep this for cl_sampler version? (referring to setting the ell=0 prior to set value)
* #TODO set up all timing again!!

## Command line arguments
1.	directory: Specifies the output directory where the results will be saved. If not provided, it defaults to "output".
2.	data_seed: Sets the random seed for the noise of the simulated data. If not provided, it defaults to 10.
3.	prior_seed: Sets the random seed for the prior variance and prior mean. If not provided, it defaults to 20.
4.	jobid: Specifies the job ID to distinguish multiple runs. If not provided, it defaults to 0.
5.	number_of_samples: Defines the number of samples to be generated. If not provided, it defaults to 100.
6.	cosmic_variance: A boolean argument to include or exclude cosmic variance in the prior variance. It accepts values like ‘true’, ‘yes’, ‘t’, ‘y’, ‘1’ for True and ‘false’, ‘no’, ‘f’, ‘n’, ‘0’ for False. If not provided, it defaults to False. 
