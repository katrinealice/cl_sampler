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

<div style="font-size:0.9em">

<table>
  <thead>
    <tr>
      <th>Short Flag</th>
      <th>Long Name</th>
      <th>Type</th>
      <th>Default</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr><td><code>-dir</code></td><td><code>--directory</code></td><td>str</td><td>"output"</td><td>Output directory for saving results.</td></tr>
    <tr><td><code>-nsamples</code></td><td><code>--number_of_samples</code></td><td>int</td><td>100</td><td>Number of Gibbs samples to generate.</td></tr>
    <tr><td><code>-data_seed</code></td><td><code>--data_seed</code></td><td>int</td><td>10</td><td>Random seed for the noise of the simulated data.</td></tr>
    <tr><td><code>-prior_seed</code></td><td><code>--prior_seed</code></td><td>int</td><td>20</td><td>Random seed for the prior variance and mean.</td></tr>
    <tr><td><code>-jobid</code></td><td><code>--jobid</code></td><td>int</td><td>0</td><td>Job ID to distinguish multiple runs.</td></tr>
    <tr><td><code>-profile</code></td><td><code>--profile</code></td><td>bool</td><td>false</td><td>Use <code>cProfile</code> to profile a single Gibbs iteration (requires <code>nsamples=1</code>).</td></tr>
    <tr><td><code>-tol</code></td><td><code>--tol</code></td><td>float</td><td>1e-5</td><td>Tolerance for the CG solver (SciPy default).</td></tr>
    <tr><td><code>-maxiter</code></td><td><code>--maxiter</code></td><td>int</td><td>20000</td><td>Maximum iterations for the CG solver (suitable for <code>tol=1e-7</code>).</td></tr>
    <tr><td><code>-lmax</code></td><td><code>--lmax</code></td><td>int</td><td>20</td><td>Maximum spherical harmonic mode. The <code>a_lm</code> vector has size (<code>l_max+1</code>)².</td></tr>
    <tr><td><code>-nside</code></td><td><code>--nside</code></td><td>int</td><td>128</td><td>Resolution used for HEALPy operations.</td></tr>
    <tr><td><code>-freq</code></td><td><code>--frequency</code></td><td>float</td><td>100 (MHz)</td><td>Frequency (MHz) to sample at; defines the reference frequency for the true sky.</td></tr>
    <tr><td><code>-freq_bounds</code></td><td><code>--frequency_bounds</code></td><td>list[float]</td><td>None</td><td>Frequency range for RSB ordered as <code>[start, stop, step]</code> (MHz). Requires <code>include_RSB=true</code>.</td></tr>
    <tr><td><code>-NLST</code></td><td><code>--NLST</code></td><td>int</td><td>10</td><td>Number of Local Sidereal Time timesteps.</td></tr>
    <tr><td><code>-lst_start</code></td><td><code>--lst_start</code></td><td>float</td><td>0.0 (hours)</td><td>Start of the LST range.</td></tr>
    <tr><td><code>-lst_end</code></td><td><code>--lst_end</code></td><td>float</td><td>8.0 (hours)</td><td>End of the LST range.</td></tr>
    <tr><td><code>-dish_dia</code></td><td><code>--dish_diameter</code></td><td>float</td><td>14.0 (m)</td><td>Diameter of dishes in the array (HERA-like default).</td></tr>
    <tr><td><code>-ant_dist</code></td><td><code>--ant_distance</code></td><td>float</td><td>dish_dia + 0.6 (m)</td><td>Distance between antennas in the hex grid (≈ 14.6 m for HERA).</td></tr>
    <tr><td><code>-cl_sampling</code></td><td><code>--cl_sampling</code></td><td>bool</td><td>false</td><td>Toggles C<sub>ℓ</sub> sampling.</td></tr>
    <tr><td><code>-include_wf</code></td><td><code>--include_wiener_filter</code></td><td>bool</td><td>false</td><td>Include Wiener-filtered mean field in the Gibbs update.</td></tr>
    <tr><td><code>-include_RSB</code></td><td><code>--include_RSB</code></td><td>bool</td><td>false</td><td>Include the RSB component in the sky model.</td></tr>
    <tr><td><code>-RSB_only</code></td><td><code>--RSB_only</code></td><td>bool</td><td>false</td><td>Use RSB-only sky model (ignore other contributions).</td></tr>
    <tr><td><code>-RSB_boost</code></td><td><code>--RSB_boost</code></td><td>float</td><td>1.0</td><td>Boost factor applied to the RSB component.</td></tr>
    <tr><td><code>-cosmic_var</code></td><td><code>--cosmic_variance</code></td><td>bool</td><td>false</td><td>Toggles inclusion of cosmic variance in the prior variance.</td></tr>
    <tr><td><code>-front_factor</code></td><td><code>--front_factor</code></td><td>float</td><td>1.0</td><td>Scaling factor for the monopole (<code>a_00</code>) prior covariance.</td></tr>
    <tr><td><code>-zero_prior_mean</code></td><td><code>--zero_prior_mean</code></td><td>bool</td><td>false</td><td>Force the prior mean to zero.</td></tr>
    <tr><td><code>-zero_inv_prior</code></td><td><code>--zero_inv_prior</code></td><td>bool</td><td>false</td><td>Set the inverse prior to zero (for testing).</td></tr>
    <tr><td><code>-cl_prior_pow</code></td><td><code>--cl_prior_power</code></td><td>float</td><td>0.0</td><td>Power-law index applied to the C<sub>ℓ</sub> prior.</td></tr>
    <tr><td><code>-noise_factor</code></td><td><code>--noise_factor</code></td><td>float</td><td>1.0</td><td>Scale factor for the noise level on the data.</td></tr>
  </tbody>
</table>

</div>

- All arguments have sensible defaults for testing and debugging.
- For production runs, adjust seeds, sampling options, and solver settings accordingly.

---

## Notes

- Arguments can be provided via the command line, e.g.:
  ```bash
  python run_sampler.py --dir results -lmax 30 -nsamples 200
  ```
