
# Project repository to build a Gibbs sampler for $C_{\ell}$ and $a_{lm}$ spherical harmonic modes. 

Work in progress ...

Currently using the [GCR sampler](https://github.com/katrinealice/sph_harm_GCR) as a 'base' and updating it to include the $C_{\ell}$ sampling too. 

## Current TODOs

* #TODO update initial guess?
* #TODO keep this for cl_sampler version? (referring to setting the ell=0 prior to set value)
* #TODO add more of the params as command line arguments

## Command line arguments
**directory**: Specifies the output directory where the results will be saved. If not provided, it defaults to "output".

**data_seed**: Sets the random seed for the noise of the simulated data. If not provided, it defaults to 10.

**prior_seed**: Sets the random seed for the prior variance and prior mean. If not provided, it defaults to 20.

**jobid**: Specifies the job ID to distinguish multiple runs. If not provided, it defaults to 0.

**number_of_samples**: Defines the number of samples to be generated. If not provided, it defaults to 100.

**lmax**: The maximum ell-mode of the spherical harmonics. The alm-vector has size ((lmax+1)^2). If not provided, it defaults to lmax=20. 

**nside**: The resolution used for HEALpy operations. If not provided, it defaults to 128.

**frequency**: The frequency (in MHz) to sample for. Will also define the reference frequency for the true sky. If not provided, it defaults to 100 MHz.

**NLST**: Specifices the number of LST timesteps. If not provided, it defaults to 10.

**lst_start**: Specifies the start of the LST range in hours. If not provided, it defaults to 0 hr.

**lst_end**: Spedifies the end of the LST range in hours. If not provided, it defaults to 8 hr. 

**dish_diameter**: Specifies the width of the dishes in the array, defaults to HERA-like dishes of 14.0 m. 

**cosmic_variance**: A boolean argument to include or exclude cosmic variance in the prior variance. If not provided, it defaults to False. 
