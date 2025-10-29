# Gibbs sampler for  $C_{\ell}$ and $a_{{\ell}m}$ spherical harmonic modes

**Work in progress...**

This repository aims to build a **Gibbs sampler** for jointly sampling the spherical harmonic power spectrum coefficients $C_{\ell}$ and the corresponding modes $a_{\ell m}$.

Currently based on the [GCR sampler](https://github.com/katrinealice/sph_harm_GCR), which serves as a foundation for incorporating the additional $C_{\ell}$-sampling capability.

---

## Current Status

- Development in progress  
- Transitioning from fixed $C_{\ell}$ inference (GCR) to full Gibbs sampling over $C_{\ell}$ and $a_{\ell m}$
- Implementation and testing phase

---

## Command line arguments

All arguments can be passed using either **long-form** (`--argument`) or **short-form** (`-arg`) syntax.

| Short Flag | Long Name | Type | Default | Description |
|-------------|------------|------|----------|--------------|
| `-dir` | `--directory` | `str` | `"output"` | Output directory for saving results. |
| `-nsamples` | `--number_of_samples` | `int` | `100` | Number of Gibbs samples to generate. |
| `-data_seed` | `--data_seed` | `int` | `10` | Random seed for the noise of the simulated data. |
| `-prior_seed` | `--prior_seed` | `int` | `20` | Random seed for the prior variance and mean. |
| `-jobid` | `--jobid` | `int` | `0` | Job ID to distinguish multiple runs. |
| `-profile` | `--profile` | `bool` | `false` | Use `cProfile` to profile a single Gibbs iteration (`nsamples=1`). |
| `-tol` | `--tol` | `float` | `1e-5` | Tolerance for the CG solver (`scipy` default). |
| `-maxiter` | `--maxiter` | `int` | `20000` | Maximum iterations for the CG solver (suitable for `tol=1e-7`). |
| `-lmax` | `--lmax` | `int` | `20` | Maximum spherical harmonic mode. The `a_lm` vector has size \((l_{\text{max}} + 1)^2\). |
| `-nside` | `--nside` | `int` | `128` | Resolution used for HEALPy operations. |
| `-freq` | `--frequency` | `float` | `100` (MHz) | Frequency (in MHz) to sample at; also defines the reference frequency for the true sky. |
| `-freq_bounds` | `--frequency_bounds` | `list[float]` | `None` | Optional frequency range as `[start, stop, step]` (MHz). |
| `-NLST` | `--NLST` | `int` | `10` | Number of Local Sidereal Time (LST) timesteps. |
| `-lst_start` | `--lst_start` | `float` | `0.0` (hours) | Start of the LST range. |
| `-lst_end` | `--lst_end` | `float` | `8.0` (hours) | End of the LST range. |
| `-dish_dia` | `--dish_diameter` | `float` | `14.0` (m) | Diameter of dishes in the array (HERA-like default). |
| `-ant_dist` | `--ant_distance` | `float` | `14.6` (m) | Distance between antennas in the hexagonal grid (≈ `dish_diameter + 0.6`). |
| `-cl_sampling` | `--cl_sampling` | `bool` | `false` | Enable or disable \( C_{\ell} \) sampling. |
| `-include_wf` | `--include_wiener_filter` | `bool` | `false` | Include Wiener-filtered mean field in the Gibbs update. |
| `-include_RSB` | `--include_RSB` | `bool` | `false` | Include the RSB component in the sky model. |
| `-RSB_only` | `--RSB_only` | `bool` | `false` | Use the RSB model only (ignore other sky contributions). |
| `-RSB_boost` | `--RSB_boost` | `float` | `1.0` | Boost factor applied to the RSB component. |
| `-cosmic_var` | `--cosmic_variance` | `bool` | `false` | Include or exclude cosmic variance in the prior variance. |
| `-front_factor` | `--front_factor` | `float` | `1.0` | Scaling factor for the monopole (\( a_{00} \)) prior covariance. |
| `-zero_prior_mean` | `--zero_prior_mean` | `bool` | `false` | Force the prior mean to zero. |
| `-zero_inv_prior` | `--zero_inv_prior` | `bool` | `false` | Set the inverse prior to zero (for testing). |
| `-cl_prior_pow` | `--cl_prior_power` | `float` | `0.0` | Power-law index applied to the \( C_{\ell} \) prior. |
| `-noise_factor` | `--noise_factor` | `float` | `1.0` | Scale factor for the noise level on the data. |

- All arguments have sensible defaults for testing and debugging.
- For production runs, adjust seeds, sampling options, and solver settings accordingly.

---

## Notes

- Arguments can be provided via the command line, e.g.:
  ```bash
  python run_sampler.py --dir results -lmax 30 -nsamples 200
  ```
