import os

import numpy as np
import scipy as sp

# C_ell / sigma_ell calculation
from scipy.stats import invgamma

# Mapping
import healpy as hp

# GSM  (NOTE: GSM is deprecated, they update GDSM now: https://github.com/telegraphic/pygdsm)
from pygdsm import GlobalSkyModel2016
from pygdsm import GlobalSkyModel

# Wigner D matrices
import spherical, quaternionic

# Simulation
import pyuvsim

# Hydra
import sys
sys.path.append("/cosma8/data/dp270/dc-glas1/Hydra") # change this to your own path
import hydra
from hydra.utils import build_hex_array

import argparse

# Linear solver 
from scipy.sparse.linalg import cg, LinearOperator

# All things astropy
from astropy import units
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.coordinates.builtin_frames import AltAz, ICRS
from astropy.time import Time

# Pandas, dataframe
import pandas as pd

# Time
from numba import jit
import time

# Multiprocessing
from multiprocessing import Pool

# Printing full arrays
np.set_printoptions(threshold=sys.maxsize)

# Construct the argument parser
AP = argparse.ArgumentParser()

AP.add_argument("-dir", "--directory", required=False,
        help="output directory")

AP.add_argument("-data_seed", "--data_seed", required=False,
        help="Int. Random seed for data noise")

AP.add_argument("-prior_seed", "--prior_seed", required=False,
        help="Int. Random seed for prior variance and mean")

AP.add_argument("-jobid", "--jobid", required=False,
        help="array job id")

AP.add_argument("-tol", "--tolerance", required=False,
        help="Sets the tolerance for the conjugate gradient solver for the alm-samples")

AP.add_argument("-nsamples", "--number_of_samples", type=int, required=False,
        help="Int. total number of samples")

AP.add_argument("-lmax", "--lmax", type=int, required=False,
        help="the maximum ell-value")

AP.add_argument("-nside", "--nside", type=int, required=False,
        help="the resolution given to HEALpy")

AP.add_argument("-freq", "--frequency", type=float, required=False,
        help="the frequency (MHz) to sample for, will default to 100 MHz") 

AP.add_argument("-NLST", "--number_of_lst", type=int, required=False,
        help="int. Sets the number of LST timesteps. Defaults to 10")

AP.add_argument("-lst_start", "--lst_start", type=float, required=False,
        help="float. Defines start of LST range in hours. Defaults to 0 hr")

AP.add_argument("-lst_end", "--lst_end", type=float, required=False,
        help="float. Defines the end of LST range in hours. Defaults to 8 hr")

AP.add_argument("-ant_dist", "--ant_distance", type=float, required=False,
        help="The distance between the antennas in the hexagonal grid in metres. Defaults to 14.6 m (HERA)")

AP.add_argument("-dish_dia", "--dish_diameter", type=float, required=False,
        help="Sets the diameter of the dish. Defaults to HERA-like 14.0 m")

AP.add_argument("-cosmic_var", "--cosmic_variance", type=str, required=False,
        help="Toggles whether a cosmic variance term is included in the prior variance")

ARGS = vars(AP.parse_args())

## Functions
def vis_proj_operator_no_rot(freqs, lsts, beams, ant_pos, lmax, nside, latitude=-0.5361913261514378, include_autos=False, autos_only=False):
    """
    Precompute the real and imaginary blocks of the visibility response 
    operator. This should only be done once and then "apply_vis_response()"
    is used to get the actual visibilities.
    
    Parameters
    ----------
   
    * freqs (array_like):
            Frequencies, in MHz.
    
    * lsts (array):
            lsts (times) for the simulation. In radians.
    
    * beams (list of pyuvbeam):
            List of pyuveam objects, one for each antenna
            
    * ant_pos (dict):
            Dictionary of antenna positions, [x, y, z], in m. The keys should
            be the numerical antenna IDs.    
            
    * lmax (int):
            Maximum ell value. Determines the number of modes used.
             
    * nside (int):
            Healpix nside to use for the calculation (longer baselines should 
            use higher nside).
    * latitude (optional) (float):
            Latitude in decimal format of the simulated array/visibilities. 
            Default: -30.7215 * np.pi / 180 = -0.5361913261514378 (HERA)
            
    * include_autos (optional) (Boolean):
            If True, the auto baselines are included. Default: False. 
    
    Returns
    -------
    
    * vis_response_2D (array_like):
            Visibility operator (δV_ij) for each (l,m) mode, frequency, 
            baseline and lst. Shape (Nvis,N_alms) where Nvis is N_bl x N_times x N_freqs.
            
    * ell (optional: set lm_index = True) (array of int):
            Array of ell-values for the visiblity simulation
            
    * m (optional: set lm_index = True) (array of int):
        Array of ell-values for the visiblity simulation
    
    """
       
    ell, m, vis_alm = hydra.vis_simulator.simulate_vis_per_alm(lmax=lmax, 
                                                               nside=nside, 
                                                               ants=ant_pos, 
                                                               freqs=np.atleast_1d(freqs), 
                                                               lsts=lsts, 
                                                               beams=beams,
                                                               latitude=latitude)
    
    # Removing visibility responses corresponding to the m=0 imaginary parts 
    vis_alm = np.concatenate((vis_alm[:,:,:,:,:len(ell)],vis_alm[:,:,:,:,len(ell)+(lmax+1):]), axis=4)
    
    ants = list(ant_pos.keys())
    antpairs = []
    if autos_only == False and include_autos == False:
        auto_ants = []
    for i in ants:
        for j in ants:
            # Toggle via keyword argument if you want to keep the auto baselines/only have autos
            if include_autos == True:
                if j >= i:
                    antpairs.append((ants[i],ants[j]))
            elif autos_only == True:
                if j == i:
                    antpairs.append((ants[i],ants[j]))
            else:
                if j == i:
                    auto_ants.append((ants[i],ants[j]))
                if j > i:
                    antpairs.append((ants[i],ants[j]))
                
    vis_response = np.zeros((len(antpairs),len(freqs),len(lsts),2*len(ell)-(lmax+1)), dtype=np.complex128)
    # vis_response = np.zeros((len(antpairs),*vis_alm.shape[:-3],2*len(ell)-lmax), dtype=np.complex128)
    
    ## Collapse the two antenna dimensions into one baseline dimension
    # Nfreqs, Ntimes, Nant1, Nant2, Nalms --> Nbl, Nfreqs, Ntimes, Nalms 
    for i, bl in enumerate(antpairs):
        idx1 = ants.index(bl[0])
        idx2 = ants.index(bl[1])
        vis_response[i, :] = vis_alm[:, :, idx1, idx2, :]  
        
    ## Reshape to 2D                                      ## TODO: Make this into a "pack" and "unpack" function
    # Nbl, Nfreqs, Ntimes, Nalms --> Nvis, Nalms
    Nvis = len(antpairs) * len(freqs) * len(lsts)
    # Nvis = np.prod([len(antpairs),*vis_alm.shape[:-3]])
    vis_response_2D = vis_response.reshape(Nvis, 2*len(ell)-(lmax+1))
    
    
    
    if autos_only == False and include_autos == False:
        autos = np.zeros((len(auto_ants),len(freqs),len(lsts),2*len(ell)-(lmax+1)), dtype=np.complex128)
        ## Collapse the two antenna dimensions into one baseline dimension
        # Nfreqs, Ntimes, Nant1, Nant2, Nalms --> Nbl, Nfreqs, Ntimes, Nalms 
        for i, bl in enumerate(auto_ants):
            idx1 = ants.index(bl[0])
            idx2 = ants.index(bl[1])
            autos[i, :] = vis_alm[:, :, idx1, idx2, :]   

        ## Reshape to 2D                                      ## TODO: Make this into a "pack" and "unpack" function
        # Nbl, Nfreqs, Ntimes, Nalms --> Nvis, Nalms
        Nautos = len(auto_ants) * len(freqs) * len(lsts)
        # Nvis = np.prod([len(antpairs),*vis_alm.shape[:-3]])
        autos_2D = autos.reshape(Nautos, 2*len(ell)-(lmax+1))

    
    if autos_only == False and include_autos == False:
        return vis_response_2D, autos_2D, ell, m
    else:
        return vis_response_2D, ell, m


def get_em_ell_idx(lmax):
    """
    Function to get the em, ell, and index of all the modes given the lmax. 
    (m,l)-ordering, (m-major ordering)

    Parameters
    ----------
    * lmax: (int)
        Maximum ell value for alms

    Returns
    -------
    * ems: (list (int))
        List of all the em values of the alms (m,l)-ordering (m-major)

    * ells: (list (int))
        List of all the ell values of the alms (m,l)-ordering (m-major)
        
    * idx: (list (int)) 
        List of all the indices for the alms

    """

    ells_list = np.arange(0,lmax+1)
    em_real = np.arange(0,lmax+1)
    em_imag = np.arange(1,lmax+1)
    
    Nreal = 0
    i = 0
    idx = []
    ems = []
    ells = []

    for em in em_real:
        for ell in ells_list:
            if ell >= em:
                idx.append(i)
                ems.append(em)
                ells.append(ell)
                
                Nreal += 1
                i +=1
    
    Nimag=0

    for em in em_imag:
        for ell in ells_list:
            if ell >= em:
                idx.append(i)
                ems.append(em)
                ells.append(ell)

                Nimag += 1
                i += 1

    return ems, ells, idx

def find_common_true_index(arr_em, arr_ell, lmax):
    """
    Find the common index between two arrays of same length consisting of true and false.

    Parameters
    ----------
    * arr1: (ndarray (boolean))
        The first array to compare, consisting of true and false

    * arr2: (ndarray (boolean))
        The second array to compare, consisting of true and false

    Returns
    -------
    * idx_real: (int)
        The common index for the real part

    * idx_imag: (int)
        The common index for the imag part

    """
    real_imag_split_index = int(((lmax+1)**2 + (lmax+1))/2)

    real_idx = []
    imag_idx = []

    for idx in range(len(arr_em)):
        if arr_em[idx] and arr_ell[idx] and idx < real_imag_split_index:
            real_idx = idx
        elif arr_em[idx] and arr_ell[idx] and idx >= real_imag_split_index:
            imag_idx = idx

    return real_idx, imag_idx

def get_idx_ml(em, ell, lmax):
    """
    Get the global index for the alms (m,l)-ordering (m-major) given a m 
    and ell value. 
    
    Parameters
    ----------
    * em: (int)
        The em value of the mode. Note, em cannot be greater than the ell value.

    * ell: (int)
        The ell value of the mode. Note, ell has to be larger or equal to the em value.

    * lmax: (int)
        The lmax of the modes

    Returns
    -------
    * common_idx_real: (int)
        The global index of the real part of the spherical harmonic mode

    * common_idx_imag: (int)
        The global index of the imaginary part of the spherical harmonic mode

    """

    assert np.all(em <= ell), "m cannot be greater than the ell value"
    ems_idx, ells_idx, idx = get_em_ell_idx(lmax)

    em_check = np.array(ems_idx) == em
    ell_check = np.array(ells_idx) == ell

    common_idx_real, common_idx_imag = find_common_true_index(arr_em=em_check,
                                                              arr_ell=ell_check,
                                                              lmax=lmax)
    if common_idx_imag == []: # happens if m=0
        idx_list = [common_idx_real]
    else:
        idx_list = [common_idx_real, common_idx_imag]

    for common_idx in idx_list:
        assert common_idx == idx[common_idx], "the global index does not match the index list"
        assert em == ems_idx[common_idx], "The em corresponding to the global index does not match the chosen em"
        assert ell == ells_idx[common_idx], "The ell corresponding to the global index does not match the vhosen ell"

    return common_idx_real, common_idx_imag

def alms2healpy(alms, lmax):
    """
    Takes a real array split as [real, imag] (without the m=0 modes 
    imag-part) and turns it into a complex array of alms (positive 
    modes only) ordered as in HEALpy.
      
    Parameters
    ----------
    * alms (ndarray (floats))
            Array of zeros except for the specified mode. 
            The array represents all positive (+m) modes including zero 
            and has double length, as real and imaginary values are split. 
            The first half is the real values.

    
    Returns
    -------
    * healpy_modes (ndarray (complex)):
            Array of zeros except for the specified mode. 
            The array represents all positive (+m) modes including zeroth modes.
            
    """
    
    real_imag_split_index = int((np.size(alms)+(lmax+1))/2)
    real = alms[:real_imag_split_index]
    
    add_imag_m0_modes = np.zeros(lmax+1)
    imag = np.concatenate((add_imag_m0_modes, alms[real_imag_split_index:]))
    
    healpy_modes = real + 1.j*imag
    
    return healpy_modes
    
    
def healpy2alms(healpy_modes):
    """
    Takes a complex array of alms (positive modes only) and turns into
    a real array split as [real, imag] making sure to remove the 
    m=0 modes from the imag-part.
      
    Parameters
    ----------
    * healpy_modes (ndarray (complex)):
            Array of zeros except for the specified mode. 
            The array represents all positive (+m) modes including zeroth modes.
    
    Returns
    -------
    * alms (ndarray (floats))
            Array of zeros except for the specified mode. 
            The array represents all positive (+m) modes including zero 
            and is split into a real (first) and imag (second) part. The
            Imag part is smaller as the m=0 modes shouldn't contain and 
            imaginary part. 
    """
    lmax = hp.sphtfunc.Alm.getlmax(healpy_modes.size) # to remove the m=0 imag modes
    alms = np.concatenate((healpy_modes.real,healpy_modes.imag[(lmax+1):]))
        
    return alms   

def get_healpy_from_gsm(freq, lmax, nside=64, resolution="low", output_model=False, output_map=False):
    """
    Generate an array of alms (HEALpy ordered) from gsm 2016 (https://github.com/telegraphic/pygdsm)
    
    Parameters
    ----------
    * freqs: (float or np.array)
        Frequency (in MHz) for which to return GSM model
        
    * lmax: (int)
        Maximum l value for alms
        
    * nside: (int)
        The NSIDE you want to upgrade/downgrade the map to. Default is nside=64.

    * resolution: (str)
        if "low/lo/l":  The GSM nside = 64  (default)
        if "hi/high/h": The GSM nside = 1024 

    * output_model: (Boolean) optional
        If output_model=True: Outputs model generated from the GSM data. 
        If output_model=False (default): no model output.

    * output_map: (Boolean) optional
        If output_map=True: Outputs map generated from the GSM data. 
        If output_map=False (default): no map output.

    Returns
    -------
    *healpy_modes: (np.array)
        Complex array of alms with same size and ordering as in healpy (m,l)
    
    *gsm_2016: (PyGDSM 2016 model) optional
        If output_model=True: Outputs model generated from the GSM data. 
        If output_model=False (default): no model output.

    *gsm_map: (healpy map) optional
        If output_map=True: Outputs map generated from the GSM data. 
        If output_map=False (default): no map output.
    
    """
    gsm_2016 = GlobalSkyModel2016(freq_unit='MHz', resolution=resolution) 
    gsm_map = gsm_2016.generate(freqs=freq)
    gsm_upgrade = hp.ud_grade(gsm_map, nside)
    healpy_modes_gal = hp.map2alm(maps=gsm_upgrade,lmax=lmax)

    # Per default it is in gal-coordinates, convert to equatorial
    rot_gal2eq = hp.Rotator(coord="GC")
    healpy_modes_eq = rot_gal2eq.rotate_alm(healpy_modes_gal)

    if output_model == False and output_map == False: # default
        return healpy_modes_eq
    elif output_model == False and output_map == True:
        return healpy_modes_eq, gsm_map 
    elif output_model == True and output_map == False:
        return healpy_modes_eq, gsm_2016 
    else:
        return healpy_modes_eq, gsm_2016, gsm_map

def get_alms_from_gsm(freq, lmax, nside=64, resolution='low', output_model=False, output_map=False):
    """
    Generate a real array split as [real, imag] (without the m=0 modes 
    imag-part) from gsm 2016 (https://github.com/telegraphic/pygdsm)
    
    Parameters
    ----------
    * freqs: (float or np.array)
        Frequency (in MHz) for which to return GSM model
        
    * lmax: (int)
        Maximum l value for alms
        
    * nside: (int)
        The NSIDE you want to upgrade/downgrade the map to. Default is nside=64.
        
    * resolution: (str)
        if "low/lo/l":  nside = 64  (default)
        if "hi/high/h": nside = 1024 
        
    * output_model: (Boolean) optional
        If output_model=True: Outputs model generated from the GSM data. 
        If output_model=False (default): no model output.
        
    * output_map: (Boolean) optional
        If output_map=True: Outputs map generated from the GSM data. 
        If output_map=False (default): no map output.

    Returns
    -------
    * alms (ndarray (floats))
            Array of zeros except for the specified mode. 
            The array represents all positive (+m) modes including zero 
            and has double length, as real and imaginary values are split. 
            The first half is the real values.
            
    * gsm_2016: (PyGDSM 2016 model) optional
        If output_model=True: Outputs model generated from the GSM data. 
        If output_model=False (default): no model output.
            
    * gsm_map: (healpy map) optional
        If output_map=True: Outputs map generated from the GSM data. 
        If output_map=False (default): no map output.
    
    """
    return healpy2alms(get_healpy_from_gsm(freq, lmax, nside, resolution, output_model, output_map))

def construct_rhs_no_rot(data, inv_noise_cov, inv_signal_cov, omega_0, omega_1, a_0, vis_response):
    
    real_data_term = vis_response.real.T @ (inv_noise_cov*data.real + np.sqrt(inv_noise_cov)*omega_1.real)
    imag_data_term = vis_response.imag.T @ (inv_noise_cov*data.imag + np.sqrt(inv_noise_cov)*omega_1.imag)
    prior_term = inv_signal_cov*a_0 + np.sqrt(inv_signal_cov)*omega_0

    right_hand_side = real_data_term + imag_data_term + prior_term 
    
    return right_hand_side

def apply_lhs_no_rot(x, x_true, inv_noise_cov, inv_signal_cov, vis_response):
    
    # Fixing the monopole (a_00) to the true value
    real_0_idx, _ = get_idx_ml(em=0, ell=0, lmax=lmax)
    a_cr = np.zeros_like(x_true)
    a_cr[real_0_idx] = x_true[real_0_idx]
    a_cr[~real_0_idx] = x

    # LHS of GCR equation
    real_noise_term = vis_response.real.T @ ( inv_noise_cov[:,np.newaxis]* vis_response.real ) @ a_cr
    imag_noise_term = vis_response.imag.T @ ( inv_noise_cov[:,np.newaxis]* vis_response.imag ) @ a_cr
    signal_term = inv_signal_cov * a_cr
    
    left_hand_side = (real_noise_term + imag_noise_term + signal_term) 

    return left_hand_side

def lhs_operator(x):
    """
    Wrapper function for matvec for LinearOperator since matvec only takes
    one argument.
    Make sure that the inverse noise covariance, inverse signal covariance,
    and vis_response are correctly defined in the code before use.

    """

    return apply_lhs_no_rot(x, x_true, inv_noise_cov, inv_signal_cov, vis_response)

def radiometer_eq(auto_visibilities, ants, delta_time, delta_freq, Nnights = 1, include_autos=False):
    nbls = len(ants)
    indx = auto_visibilities.shape[0]//nbls
    
    sigma_full = np.empty((0))#, autos.shape[-1]))

    for i in ants:
        vis_ii = auto_visibilities[i*indx:(i+1)*indx]#,:]

        for j in ants:
            if include_autos == True:
                if j >= i:
                    vis_jj = auto_visibilities[j*indx:(j+1)*indx]#,:]
                    sigma_ij = ( vis_ii*vis_jj ) / ( Nnights*delta_time*delta_freq )
                    sigma_full = np.concatenate((sigma_full,sigma_ij))
            else:
                if j > i:  # only keep this line if you don't want the auto baseline sigmas
                    vis_jj = auto_visibilities[j*indx:(j+1)*indx]#,:]
                    sigma_ij = ( vis_ii*vis_jj ) / ( Nnights*delta_time*delta_freq )
                    sigma_full = np.concatenate((sigma_full,sigma_ij))
 
    # this will be complex type due to inputs, check that the imag part is zero and recast type
    assert np.all(sigma_full.imag == 0), "The imag part of the radiometer eq is not zero"                   
    
    return sigma_full.real

def get_alm_samples(data_vec,
                    inv_noise_cov,
                    inv_signal_cov,
                    a_0,
                    vis_response,
                    initial_guess,
                    random_seed,
                    tolerance):
    """
    Function to draw samples from the GCR equation.
    """
    t_iter = time.time()

    np.random.seed(random_seed)
    #random_seed = np.random.get_state()[1][0] #for test/output purposes
    
    # Generate random maps for the realisations
    omega_0 = np.random.randn(a_0.size)
    omega_1 = (np.random.randn(data_vec.size) + 1.j*np.random.randn(data_vec.size))/np.sqrt(2)
    
    # Construct RHS
    rhs = construct_rhs_no_rot(data_vec,
                               inv_noise_cov, 
                               inv_signal_cov,
                               omega_0,
                               omega_1,
                               a_0,
                               vis_response)

    # Construct LHS operator
    lhs_shape = (rhs.size, rhs.size)
    lhs_linear_op = LinearOperator(matvec = lhs_operator,
                                   shape = lhs_shape)
    
    
    # Run and time solver
    time_start_solver = time.time()
    x_soln, convergence_info = solver(A = lhs_linear_op,
                                      b = rhs,
                                      tol = tolerance,
                                      maxiter = 15000,
                                      x0 = initial_guess) 

    solver_time = time.time() - time_start_solver
    iteration_time = time.time()-t_iter
            
    # Save output
    np.savez(path+'alms_'+f'{data_seed}_'+f'{random_seed}',
             omega_0=omega_0,
             omega_1=omega_1,
             alm_random_seed=random_seed,
             x_soln=x_soln,
             rhs=rhs,
             convergence_info=convergence_info,
             solver_time=solver_time,
             iteration_time=iteration_time
            )
        
    return x_soln, iteration_time

def get_sigma_ell(alms,lmax):
    """
    Calculates sigma_ell for the angular powerspectrum given a set of
    alms and an lmax. The alms are 'realified' i.e. flattened with first 
    the real-part and then the imaginary part. Note, there should be no
    m=0 imaginary modes. The alms are (m,l)-ordered (m-major).
    The invgamm function is not defined for ell=0 so this mode is left out.

    Parameters
    ----------
    * alms: (ndarray (floats))
        The array represents all postive (+m) modes including zero
        and has double length, as real and imaginary values are split.
        The first hald is the real values.

    * lmax: (int)
        The lmax of the modes.

    Returns
    -------
    * sigma_ell: (ndarray (floats))
        An array of sigma_ell values for the angular power spectrum.
    """

    # excluding ell=0 because it's not defined for the invgamma func.
    sigma_ell = np.zeros(shape = ((lmax+1)-1))

    # Calculate sigma_ell = 1/(2*ell + 1) sum_m |a_lm|^2
    for ell in np.arange(1,lmax+1):
        real_idx, _ = get_idx_ml(0,ell,lmax)
        sigma_ell[ell-1] = alms[real_idx] * alms[real_idx]

        for em in np.arange(1,ell+1):
            real_idx, imag_idx = get_idx_ml(em, ell, lmax)
            sigma_ell[ell-1] += 2 * (alms[real_idx] * alms[real_idx] +
                                     alms[imag_idx] * alms[imag_idx])
        
        sigma_ell[ell-1] /= 2*ell + 1

    return sigma_ell

def get_cl_samples(alms, lmax, random_seed):
    """
    Uses the inverse gamma function (see Eriksen 2007) to generate 
    samples of C_ell given the alms. The inverse gammafunction doesn't
    work for ell=0. 

    Parameters
    ----------
    * alms: (ndarray (floats))
        The array (shape=((lmax+1)**2)) represents all postive (+m) modes including zero
        and has double length, as real and imaginary values are split.
        The first hald is the real values.

    * lmax: (int)
        The lmax of the modes.

    * random_seed: (int)
        Sets the random seed for the specific function call

    Returns
    -------
    * cl_samples: (ndarray (floats))
        An array (shape = lmax) containing the C_ell samples ordered by ell-value. 
        Note, the inverse gamma function doesn't work for ell=0, so this mode is
        excluded.
    """
    np.random.seed(random_seed)
    
    sigma_ell = get_sigma_ell(alms, lmax)

    unique_ell = np.arange(1,lmax+1)
    a = (2*unique_ell - 1)/2
    
    cl_samples = invgamma.rvs(a, loc=0, scale=1)
    cl_samples *= sigma_ell * (2*unique_ell +1)/2

    # Save output
    np.savez(path+'cls_'+f'{data_seed}_'+f'{random_seed}',
             sigma_ell=sigma_ell,
             cl_samples=cl_samples,
             cl_random_seed=random_seed,
            )
 
    return cl_samples

def set_signal_cov_by_cl(prior_cov, cl_samples, lmax):
    """
    Set the signal covariance matrix (S) to be given by the C_ell samples for the 
    a_lms. The invgamma function is not defined for ell = 0, so for these modes 
    the prior_cov values are used and are thus held fixed throughout. The ordering
    of the signal_cov matrix is given by the same ordering and shape as the 
    realified a_lms, since it is enough to define the diagonal.
    There is a factor 1/2 on the signal_cov due to accounting for the realification
    when setting the signal variance by the C_ell values.

    Parameters
    ----------
    * prior_cov: (ndarray (floats))
        An array (shape = ((lmax+1)**2) ) containing the diagonal of the prior
        covariance. This is used to define the signal_cov for ell = 0.

    * cl_samples: (ndarray (floats))
        An array (shape = lmax) containing the C_ell samples ordered by ell-value. 
        Note, the inverse gamma function doesn't work for ell=0, so this mode is
        excluded.

    * lmax: (int)
        The lmax of the modes.

    Returns
    -------
    * signal_cov: (ndarray (floats))
        An array (shape = ((lmax+1)**2) ) containing the signal covariance 
        corresponding to the realified alm-modes defiend by the power spectrum
        samples (cl_samples) and the prior covariance (prior_cov). 

    """

    # The get_cl_samples function is not defined for ell=0, use prior_cov instead
    signal_cov = prior_cov.copy()

    # Then update all other entries (ell > 0)
    for ell in np.arange(1,lmax+1):
        real_idx, _ = get_idx_ml(0,ell,lmax)
        signal_cov[real_idx] = 0.5 * cl_samples[ell-1]  # factor 1/2 due to 'realification'

        for em in np.arange(1,ell+1):
            real_idx, imag_idx = get_idx_ml(em, ell, lmax)
            signal_cov[real_idx] = 0.5 * cl_samples[ell-1]  # factor 1/2 due to 'realification'
            signal_cov[imag_idx] = 0.5 * cl_samples[ell-1]  # factor 1/2 due to 'realification'

    return signal_cov


###### MAIN ######    
if __name__ == "__main__":
    start_time = time.time()
    
    # Creating directory for output
    if ARGS['directory']: 
        directory = str(ARGS['directory'])
    else:
        directory = "output"

    path = f'/cosma8/data/dp270/dc-glas1/{directory}/'
    try: 
        os.makedirs(path)
        print(f'Created folder {path}\n')
    except FileExistsError:
        print(f'Folder {path} already exists\n')
    
    # Defining the data_seed for the noise of the simulated data
    if ARGS['data_seed']:
        data_seed = int(ARGS['data_seed'])
    else:
        # if none is passed go back to 10 as before
        data_seed = 10

    # Defining the prior_seed for the prior variance and prior mean
    if ARGS['prior_seed']:
        prior_seed = int(ARGS['prior_seed'])
    else:
        # If none is passed, default will be 20
        prior_seed = 20

    # Defining the jobid to distinguish multiple runs in one go
    if ARGS['jobid']: 
        jobid = int(ARGS['jobid'])
    else:
        # if none is passed then don't change the keys
        jobid = 0

    # Setting the tolerance for the conjugate gradient solver for the alm-samples
    if ARGS['tolerance']:
        tolerance = float(ARGS['tolerance'])
    else:
        # Defaults to the scipy/cg solver's default:
        tolerance = 1e-05

    # Including cosmic variance into the prior variance:
    if ARGS['cosmic_variance']:
        if ARGS['cosmic_variance'].lower() in ('true', 'yes', 't', 'y', '1'):
            incl_cosmic_var = True
        elif ARGS['cosmic_variance'].lower() in ('false', 'no', 'f', 'n', '0'):
            incl_cosmic_var = False
        else:
            raise argparse.ArgumentTypeError('Boolean value expected')
    else:
        incl_cosmic_var = False

    # Number of samples
    if ARGS['number_of_samples']:
        n_samples = int(ARGS['number_of_samples'])
    else:
        # If none is passed use 100 samples as default
        n_samples = 100

    # The lmax for the spherical harmonic modes
    if ARGS['lmax']:
        lmax = int(ARGS['lmax'])
    else:
        lmax = 20

    # The nside / resolution for HEALpy operations
    if ARGS['nside']:
        nside = int(ARGS['nside'])
    else:
        nside = 128

    # Frequency and reference frequency
    if ARGS['frequency']:
        freqs = np.array([float(ARGS['frequency'])*1e06]) # MHz -> Hz, required by Hydra
        ref_freq = float(ARGS['frequency']) # MHz, required by PyGSM
    else:
        freqs = np.array([100e06]) # Hz, Hydra requires this
        ref_freq = 100. # MHz, PyGSM requires this 

    # NLST
    if ARGS['number_of_lst']:
        NLST = int(ARGS['number_of_lst'])
    else:
        NLST = 10

    # Start of lst range
    if ARGS['lst_start']:
        lst_start = float(ARGS['lst_start'])
    else:
        lst_start = 0. # hr

    # End of lst range
    if ARGS['lst_end']:
        lst_end = float(ARGS['lst_end'])
    else:
        lst_end = 8. #hr

    # distance between antennas
    if ARGS['ant_distance']:
        ant_distance = float(ARGS['ant_distance']) # m
    else:
        # defaults to HERA antenna distance
        ant_distance = 14.6 # m

    # diameter of dish
    if ARGS['dish_diameter']:
        dish_diameter = float(ARGS['dish_diameter'])
    else:
        # defaults to HERA dishes
        dish_diameter = 14. # m

    # Build the antenna array and output. 
    ant_pos = build_hex_array(hex_spec=(3,4), d=ant_distance)  #builds array with (3,4,3) ants = 10 total
    ants = list(ant_pos.keys())
    ant_dict = dict((str(ant), ant_pos[ant]) for ant in ant_pos)
    np.savez(path+'ant_pos',**ant_dict)

    beams = [pyuvsim.AnalyticBeam('gaussian', diameter=dish_diameter) for ant in ants]
    lsts_hours = np.linspace(lst_start,lst_end,NLST)      # in hours for easy setting
    lsts = np.deg2rad((lsts_hours/24)*360) # in radian, used by HYDRA (and this code)
    delta_time = 60 # s
    delta_freq = 1e+06 # (M)Hz
    latitude = 30.7215 * np.pi / 180  # HERA loc in decimal numbers ## There's some sign error in the code, so this missing sign is a quick fix
    solver = cg

    vis_response, autos, ell, m = vis_proj_operator_no_rot(freqs=freqs, 
                                                        lsts=lsts, 
                                                        beams=beams, 
                                                        ant_pos=ant_pos, 
                                                        lmax=lmax, 
                                                        nside=nside,
                                                        latitude=latitude)

    # Setting the random seed to the prior_seed and calculating true sky
    np.random.seed(prior_seed)
    x_true = get_alms_from_gsm(freq=ref_freq,lmax=lmax, nside=nside)
    model_true = vis_response @ x_true

    # Inverse signal covariance 
    min_prior_std = 0.5
    prior_cov = (0.1 * x_true)**2.
    prior_cov[prior_cov < min_prior_std**2.] = min_prior_std**2.

    # Cosmic variance (if chosen)
    if incl_cosmic_var == True:
        cls = hp.alm2cl(alms2healpy(x_true, lmax))
        f_sky = 1 
        _, ell_idx, _ = get_em_ell_idx(lmax) 
        cosmic_var = np.zeros(shape=(len(ell_idx)))
        for i, ell in enumerate(ell_idx):
            # !! FixMe !!   f_sky is most likely incorrectly placed
            cosmic_var[i] = 0.1 * np.sqrt(2/(2*ell+1))*cls[ell]*f_sky
        prior_cov += cosmic_var

    inv_prior_cov = 1/prior_cov
    
    # Set the prior mean by the prior variance 
    a_0 = np.random.randn(x_true.size)*np.sqrt(prior_cov) + x_true # gaussian centered on alms with S variance 
    #_, ell_idx, _ = get_em_ell_idx(lmax) 
    
    # setting the ell=0 mode to be the true value
    real_0_idx, _ = get_idx_ml(em=0, ell=0, lmax=lmax)
    a_0[real_0_idx] = x_true[real_0_idx]
    #a_0[np.where(np.array(ell_idx) == 0)[0][0]] = x_true[np.where(np.array(ell_idx) == 0)[0][0]]
    
    # Save a_0 in separate file as there has been issues with the combined .npz file
    np.savez(path+'a_0_'+f'{prior_seed}_'+f'{jobid}', a_0 = a_0)
    
    # Inverse noise covariance and noise on data
    np.random.seed(data_seed)
    noise_cov = 0.5 * radiometer_eq(autos@x_true, ants, delta_time, delta_freq)
    inv_noise_cov = 1/noise_cov
    data_noise = (np.random.randn(noise_cov.size) 
                  + 1.j*np.random.randn(noise_cov.size)) * np.sqrt(noise_cov) 
    data_vec = model_true + data_noise
    
    # Define the inv_signal_cov before calling the LinearOperator function
    inv_signal_cov = inv_prior_cov.copy()

    # RHS: Wiener filter solution to provide initial guess:
    omega_0_wf = np.zeros_like(a_0)
    omega_1_wf = np.zeros_like(model_true, dtype=np.complex128)
    rhs_wf = construct_rhs_no_rot(data_vec,
                                  inv_noise_cov, 
                                  inv_signal_cov, 
                                  omega_0_wf, 
                                  omega_1_wf, 
                                  a_0, 
                                  vis_response)
    
    # LHS: Build linear operator object 
    lhs_shape = (rhs_wf.size, rhs_wf.size)
    lhs_linear_op = LinearOperator(matvec = lhs_operator,
                                       shape = lhs_shape)

    # Get the Wiener Filter solution for initial guess
    wf_soln, wf_convergence_info = solver(A = lhs_linear_op,
                                          b = rhs_wf,
                                          tol = tolerance,
                                          maxiter = 15000)
    initial_guess = wf_soln.copy()

    # Time for all precomputations
    precomp_time = time.time()-start_time
    print(f'\nprecomputation took:\n{precomp_time} sec.\n')
  
    # Saving all precomputed data
    np.savez(path+'precomputed_data_'+f'{data_seed}_'+f'{jobid}',
             vis_response=vis_response,
             autos=autos,
             x_true=x_true,
             inv_noise_cov=inv_noise_cov,
             min_prior_std=min_prior_std,
             inv_prior_cov=inv_prior_cov,
             a_0=a_0,
             data_seed=data_seed,
             prior_seed=prior_seed,
             incl_cosmic_var=incl_cosmic_var,
             wf_soln=wf_soln,
             nside=nside,
             lmax=lmax,
             ants=ants,
             dish_diameter=dish_diameter,
             freqs=freqs,
             lsts_hours=lsts_hours,
             precomp_time=precomp_time
             )


    avg_iter_time = 0
    # Get alm and cl samples
    for key in range(n_samples):

        sample_start_time = time.time()

        # Set random seeds by the sample no. to pass into the sample functions
        alm_random_seed = 100*jobid + key
        cl_random_seed = 100*jobid + key  

        # get alm samples using prior for the first sample, then C_ell 
        x_soln, iteration_time = get_alm_samples(data_vec = data_vec,
                                                 inv_noise_cov = inv_noise_cov,
                                                 inv_signal_cov = inv_signal_cov,
                                                 a_0 = a_0,
                                                 initial_guess = initial_guess,
                                                 vis_response = vis_response,
                                                 random_seed = alm_random_seed,
                                                 tolerance=tolerance)
        initial_guess = x_soln.copy()

        # get cl samples
        cl_samples = get_cl_samples(alms=x_soln,
                                    lmax=lmax,
                                    random_seed=cl_random_seed)
        

        # Change signal_cov to use C_ell values
        signal_cov = set_signal_cov_by_cl(prior_cov = prior_cov,
                                          cl_samples = cl_samples,
                                          lmax = lmax)
        inv_signal_cov = 1/signal_cov

        sample_total_time = time.time() - sample_start_time
        avg_iter_time += sample_total_time

  
    ## Multiprocessing, getting the samples    
    #number_of_cores = int(os.environ['SLURM_CPUS_PER_TASK'])
    #print(f'\nSLURM_CPUS_PER_TASK = {number_of_cores}')

    #with Pool(number_of_cores) as pool:
    #    # issue tasks and process results
    #    for result in pool.map(samples, range(n_samples)):
    #        key, iteration_time = result
    #        avg_iter_time += iteration_time
    #        #print(f'Iteration {key} completed in {iteration_time:.2f} seconds')

    avg_iter_time /= n_samples
    print(f'average_iter_time:\n{avg_iter_time} sec.\n')

    total_time = time.time()-start_time
    print(f'total_time:\n{total_time} sec.\n')
    print(f'All output saved in folder {path}\n')
    print(f'Note, ant_pos (dict) is saved in own file in {path}\n')
   
    np.savez(path+'timing_data_'+f'{data_seed}_'+f'{jobid}',
             precomp_time=precomp_time,
             avg_iter_time=avg_iter_time,
             total_time=total_time
            )
   
    
